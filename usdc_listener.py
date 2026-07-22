"""
BDE Score™ — ZeroFriction Layer 3: USDC On-Chain Payment Listener
=================================================================
监听 Base 链上 USDC 转入指定钱包，自动触发 Premium API Key 激活。

架构: Base Chain (RPC) → Event Filter → Amount Match → Auto-Activate Key
依赖: web3.py (已安装 v7.x), bcrypt
注意: 只读监听，不需要私钥。

增强 v2.0:
  - 集成 payment_to_key 模块，实现 支付→Key 自动激活闭环
  - 支持月度($29)和年度($290)两种订阅
  - 新地址自动生成key，已有地址自动延期
  - 写入 activation_log.json 完整审计日志
  - 支持 --dry-run 模式模拟测试

配置:
  WALLET_ADDRESS: 收款钱包地址（checksum格式）
  USDC_CONTRACT: Base链 USDC 合约地址
  PREMIUM_AMOUNT: 月付金额（USDC，6位精度）
"""

import os
import sys
import json
import time
import logging
import hashlib
import secrets
import argparse
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from pathlib import Path

from web3 import Web3
from web3.exceptions import ContractLogicError

# 导入 payment_to_key 模块
from payment_to_key import process_payment, determine_tier, MONTHLY_PRICE, YEARLY_PRICE

# ============================================================
# 配置
# ============================================================
# Base链公共RPC
BASE_RPC_URL = os.environ.get('BASE_RPC_URL', 'https://mainnet.base.org')

# USDC合约地址（Base Mainnet）
USDC_CONTRACT_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

# 收款钱包地址
WALLET_ADDRESS = os.environ.get(
    'BDE_WALLET_ADDRESS',
    "0x349Eea0E2f4d3594797851758325Da3eb49D4343"
)

# Premium 定价（USDC，6位精度 = 实际值 * 1e6）
PREMIUM_PRICE_USD = 29
USDC_DECIMALS = 6
PREMIUM_AMOUNT_RAW = PREMIUM_PRICE_USD * (10 ** USDC_DECIMALS)  # 29,000,000

# 年度价格
YEARLY_AMOUNT_RAW = YEARLY_PRICE * (10 ** USDC_DECIMALS)  # 290,000,000

# 最低接受金额（USDC，6位精度）— 不低于月付价格
MIN_ACCEPT_AMOUNT_RAW = PREMIUM_AMOUNT_RAW

# 监听配置
POLL_INTERVAL_SECONDS = int(os.environ.get('POLL_INTERVAL', '12'))
CONFIRMATION_BLOCKS = 3
MAX_BLOCK_LOOKBACK = 1000
LISTEN_FROM_BLOCK = int(os.environ.get('LISTEN_FROM_BLOCK', '0'))

# 数据文件路径
DATA_DIR = Path(__file__).parent
PAYMENTS_DB_PATH = DATA_DIR / 'usdc_payments.json'
ACTIVATION_LOG_PATH = DATA_DIR / 'activation_log.json'

# ============================================================
# USDC ABI（仅 Transfer 事件）
# ============================================================
USDC_ABI = json.dumps([
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"}
        ],
        "name": "Transfer",
        "type": "event"
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
])

# ============================================================
# Logger
# ============================================================
logger = logging.getLogger('usdc_listener')


# ============================================================
# 核心类：USDCListener（链上扫描，保持不变）
# ============================================================
class USDCListener:
    """
    USDC链上支付监听器
    - 连接 Base 链 RPC
    - 监听 USDC Transfer 事件到指定钱包
    - 识别金额 ≥ $29 USDC
    - 返回付款信息供激活逻辑使用
    """

    def __init__(self, rpc_url: str = BASE_RPC_URL):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 30}))
        self.usdc_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(USDC_CONTRACT_ADDRESS),
            abi=USDC_ABI
        )
        self.wallet_checksum = None
        self._validate_wallet_address()
        self._last_scanned_block = 0

    def _validate_wallet_address(self):
        addr = WALLET_ADDRESS
        try:
            self.wallet_checksum = Web3.to_checksum_address(addr)
            logger.info(f"钱包地址验证通过: {self.wallet_checksum}")
        except Exception as e:
            logger.error(f"钱包地址无效: {addr} — {e}")
            raise ValueError(f"Invalid wallet address: {addr}")

    def is_connected(self) -> bool:
        try:
            return self.w3.is_connected()
        except Exception:
            return False

    def get_chain_info(self) -> Dict:
        try:
            block = self.w3.eth.block_number
            chain_id = self.w3.eth.chain_id
            return {
                'connected': True,
                'chain_id': chain_id,
                'current_block': block,
                'wallet': self.wallet_checksum,
                'usdc_contract': USDC_CONTRACT_ADDRESS,
            }
        except Exception as e:
            return {'connected': False, 'error': str(e)}

    def get_wallet_balance(self) -> Dict:
        try:
            balance_raw = self.usdc_contract.functions.balanceOf(
                self.wallet_checksum
            ).call()
            balance_usd = balance_raw / (10 ** USDC_DECIMALS)
            return {
                'wallet': self.wallet_checksum,
                'balance_raw': balance_raw,
                'balance_usd': balance_usd,
                'token': 'USDC',
            }
        except Exception as e:
            return {'wallet': self.wallet_checksum, 'error': str(e)}

    def scan_for_payments(
        self,
        from_block: Optional[int] = None,
        to_block: Optional[int] = None,
    ) -> List[Dict]:
        """
        扫描链上 USDC Transfer 事件，筛选转入指定钱包的交易。
        金额要求: ≥ $29 USDC（最低月付价格）
        """
        if not self.is_connected():
            logger.error("RPC连接断开")
            return []

        current_block = self.w3.eth.block_number

        if from_block is None:
            from_block = self._last_scanned_block or (current_block - 100)
        if to_block is None:
            to_block = current_block - CONFIRMATION_BLOCKS

        if from_block > to_block:
            return []

        if to_block - from_block > MAX_BLOCK_LOOKBACK:
            from_block = to_block - MAX_BLOCK_LOOKBACK

        logger.info(f"扫描区块 {from_block} → {to_block} (链最新: {current_block})")

        try:
            transfer_event = self.usdc_contract.events.Transfer()
            logs = transfer_event.get_logs(
                from_block=from_block,
                to_block=to_block,
                argument_filters={'to': self.wallet_checksum},
            )
        except Exception as e:
            logger.error(f"事件扫描失败: {e}")
            return self._scan_fallback(from_block, to_block)

        results = []
        for log_entry in logs:
            payment = self._parse_transfer_log(log_entry)
            if payment:
                results.append(payment)

        self._last_scanned_block = to_block
        return results

    def _scan_fallback(self, from_block: int, to_block: int) -> List[Dict]:
        """备用扫描方式"""
        logger.warning(f"使用备用扫描模式（区块 {from_block} → {to_block}）")
        results = []
        try:
            for block_num in range(from_block, to_block + 1):
                block = self.w3.eth.get_block(block_num, full_transactions=True)
                for tx in block.transactions:
                    if tx.get('to') and tx['to'].lower() == USDC_CONTRACT_ADDRESS.lower():
                        try:
                            receipt = self.w3.eth.get_transaction_receipt(tx['hash'])
                            for log_entry in receipt['logs']:
                                payment = self._parse_raw_log(log_entry)
                                if payment:
                                    payment['block_number'] = block_num
                                    results.append(payment)
                        except Exception:
                            continue
        except Exception as e:
            logger.error(f"备用扫描也失败: {e}")

        self._last_scanned_block = to_block
        return results

    def _parse_transfer_log(self, log_entry) -> Optional[Dict]:
        """解析 Transfer 事件日志"""
        try:
            from_addr = log_entry['args']['from']
            to_addr = log_entry['args']['to']
            value = log_entry['args']['value']

            if to_addr.lower() != self.wallet_checksum.lower():
                return None

            # 金额检查：≥ 最低月付价格
            if value < MIN_ACCEPT_AMOUNT_RAW:
                logger.debug(f"金额不足: {value / 1e6} < ${PREMIUM_PRICE_USD}")
                return None

            amount_usd = value / (10 ** USDC_DECIMALS)

            # 确定订阅类型
            if amount_usd >= YEARLY_PRICE:
                plan = 'yearly_premium'
            else:
                plan = 'monthly_premium'

            return {
                'tx_hash': log_entry['transactionHash'].hex()
                    if isinstance(log_entry['transactionHash'], bytes)
                    else str(log_entry['transactionHash']),
                'from_address': from_addr,
                'to_address': to_addr,
                'amount_raw': value,
                'amount_usd': amount_usd,
                'plan': plan,
                'block_number': log_entry['blockNumber'],
                'log_index': log_entry['logIndex'],
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'status': 'detected',
            }
        except Exception as e:
            logger.error(f"解析Transfer日志失败: {e}")
            return None

    def _parse_raw_log(self, log_entry) -> Optional[Dict]:
        """解析原始日志条目（备用模式）"""
        try:
            TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
            topics = log_entry.get('topics', [])

            if not topics or topics[0] != TRANSFER_TOPIC:
                return None
            if len(topics) < 3:
                return None

            if log_entry['address'].lower() != USDC_CONTRACT_ADDRESS.lower():
                return None

            from_addr = '0x' + topics[1].hex()[-40:] if isinstance(topics[1], bytes) else '0x' + str(topics[1])[-40:]
            to_addr = '0x' + topics[2].hex()[-40:] if isinstance(topics[2], bytes) else '0x' + str(topics[2])[-40:]

            if to_addr.lower() != self.wallet_checksum.lower():
                return None

            data = log_entry.get('data', '0x0')
            if isinstance(data, bytes):
                value = int.from_bytes(data, 'big')
            else:
                value = int(data, 16) if data != '0x' else 0

            if value < MIN_ACCEPT_AMOUNT_RAW:
                return None

            amount_usd = value / (10 ** USDC_DECIMALS)

            if amount_usd >= YEARLY_PRICE:
                plan = 'yearly_premium'
            else:
                plan = 'monthly_premium'

            return {
                'tx_hash': log_entry['transactionHash'].hex()
                    if isinstance(log_entry['transactionHash'], bytes)
                    else str(log_entry['transactionHash']),
                'from_address': from_addr,
                'to_address': to_addr,
                'amount_raw': value,
                'amount_usd': amount_usd,
                'plan': plan,
                'block_number': log_entry.get('blockNumber', 0),
                'log_index': log_entry.get('logIndex', 0),
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'status': 'detected',
            }
        except Exception as e:
            logger.error(f"解析原始日志失败: {e}")
            return None

    def verify_transaction(self, tx_hash: str) -> Dict:
        """验证特定交易"""
        try:
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
        except Exception as e:
            return {'valid': False, 'error': f'Transaction not found: {e}'}

        current_block = self.w3.eth.block_number
        confirmations = current_block - receipt['blockNumber']

        if confirmations < CONFIRMATION_BLOCKS:
            return {
                'valid': False,
                'status': 'pending',
                'confirmations': confirmations,
                'required_confirmations': CONFIRMATION_BLOCKS,
            }

        for log_entry in receipt.get('logs', []):
            payment = self._parse_raw_log(log_entry)
            if payment and payment['to_address'].lower() == self.wallet_checksum.lower():
                if payment['amount_usd'] >= PREMIUM_PRICE_USD:
                    return {
                        'valid': True,
                        'status': 'confirmed',
                        'confirmations': confirmations,
                        'from_address': payment['from_address'],
                        'amount_usd': payment['amount_usd'],
                        'block_number': receipt['blockNumber'],
                        'tx_hash': tx_hash,
                    }

        return {'valid': False, 'status': 'no_matching_transfer', 'confirmations': confirmations}


# ============================================================
# 核心类：PaymentRecord（轻量级支付记录器）
# ============================================================
class PaymentRecord:
    """
    轻量级支付记录器。
    仅负责将检测到的付款记录到 usdc_payments.json。
    Key 激活逻辑委托给 payment_to_key 模块。
    """

    def __init__(self, payments_db_path: str = None):
        self.payments_db_path = Path(payments_db_path or PAYMENTS_DB_PATH)
        self.payments = self._load_payments()

    def _load_payments(self) -> Dict:
        try:
            with open(self.payments_db_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {p['tx_hash']: p for p in data}
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_payments(self):
        with open(self.payments_db_path, 'w') as f:
            json.dump(list(self.payments.values()), f, indent=2, ensure_ascii=False)

    def is_processed(self, tx_hash: str) -> bool:
        """检查交易是否已处理"""
        return tx_hash in self.payments

    def record(self, payment_data: Dict) -> str:
        """
        记录新付款到 usdc_payments.json。
        Returns: payment_id
        """
        tx_hash = payment_data['tx_hash']

        if tx_hash in self.payments:
            return self.payments[tx_hash].get('payment_id', '')

        payment_id = hashlib.sha256(tx_hash.encode()).hexdigest()[:16]

        self.payments[tx_hash] = {
            'payment_id': payment_id,
            'tx_hash': tx_hash,
            'from_address': payment_data.get('from_address', ''),
            'amount_usd': payment_data.get('amount_usd', 0),
            'plan': payment_data.get('plan', 'monthly_premium'),
            'block_number': payment_data.get('block_number', 0),
            'detected_at': payment_data.get('timestamp', datetime.utcnow().isoformat() + 'Z'),
            'status': 'processed',
        }
        self._save_payments()
        logger.info(f"付款已记录: {payment_id} | ${payment_data.get('amount_usd', 0)} from {payment_data.get('from_address', 'unknown')[:10]}...")
        return payment_id

    def mark_activated(self, tx_hash: str, key_prefix: str):
        """标记交易已激活并关联 key"""
        if tx_hash in self.payments:
            self.payments[tx_hash]['status'] = 'activated'
            self.payments[tx_hash]['key_prefix'] = key_prefix
            self.payments[tx_hash]['activated_at'] = datetime.utcnow().isoformat() + 'Z'
            self._save_payments()

    def get_all(self) -> List[Dict]:
        return list(self.payments.values())


# ============================================================
# 核心类：BackgroundListener（增强版：支付→Key闭环）
# ============================================================
class BackgroundListener:
    """
    后台监听进程（v2.0）：
    扫描 → 记录 → 激活Key → 写日志

    完整闭环:
    1. 检测到 USDC Transfer ≥ $29
    2. 记录到 usdc_payments.json
    3. 调用 payment_to_key.process_payment → 生成/激活 key
    4. 写入 activation_log.json
    5. 更新 usdc_payments.json 状态
    """

    def __init__(self, listener: USDCListener, recorder: PaymentRecord):
        self.listener = listener
        self.recorder = recorder
        self._running = False

    def _process_detected_payment(self, payment: Dict) -> Optional[Dict]:
        """
        处理单个检测到的付款：
        记录 → 生成/激活Key → 写日志

        Returns:
            处理结果 or None
        """
        tx_hash = payment['tx_hash']
        from_address = payment['from_address']
        amount_usd = payment['amount_usd']

        # 防重入
        if self.recorder.is_processed(tx_hash):
            existing = self.recorder.payments.get(tx_hash, {})
            if existing.get('status') == 'activated':
                logger.debug(f"交易已激活，跳过: {tx_hash[:16]}...")
                return None

        # Step 1: 记录付款
        payment_id = self.recorder.record(payment)
        logger.info(f"[Step 1] 付款已记录: {payment_id}")

        # Step 2: 调用 payment_to_key 处理（生成/激活 key）
        try:
            result = process_payment(
                payer_address=from_address,
                amount_usd=amount_usd,
                tx_hash=tx_hash,
            )
            logger.info(f"[Step 2] Key处理完成: {result['action']} | prefix={result['key_prefix']}")
        except Exception as e:
            logger.error(f"[Step 2] Key处理失败: {e}", exc_info=True)
            # 记录已保存但激活失败，标记状态
            return {
                'payment_id': payment_id,
                'status': 'key_generation_failed',
                'error': str(e),
            }

        # Step 3: 更新付款记录状态
        self.recorder.mark_activated(tx_hash, result['key_prefix'])
        logger.info(f"[Step 3] 付款状态已更新为 activated")

        # 输出结果
        plan = '年度' if amount_usd >= YEARLY_PRICE else '月度'
        logger.info(
            f"✅ 支付→Key闭环完成 | "
            f"{plan} ${amount_usd} | "
            f"Key: {result['key_prefix']}... | "
            f"操作: {result['action']} | "
            f"到期: {result['expires_at']}"
        )

        return result

    def run_loop_sync(self, auto_activate: bool = True):
        """
        同步主循环（用于独立运行模式）。
        """
        self._running = True
        logger.info("USDC后台监听启动 (v2.0 支付→Key闭环)")

        while self._running:
            try:
                if not self.listener.is_connected():
                    logger.warning("RPC断开，等待30秒后重连...")
                    time.sleep(30)
                    continue

                payments = self.listener.scan_for_payments()

                for payment in payments:
                    if auto_activate:
                        self._process_detected_payment(payment)
                    else:
                        # 仅记录不激活
                        self.recorder.record(payment)

            except Exception as e:
                logger.error(f"监听循环异常: {e}", exc_info=True)

            time.sleep(POLL_INTERVAL_SECONDS)

    def stop(self):
        self._running = False
        logger.info("USDC后台监听已停止")


# ============================================================
# Dry-Run 模式（模拟测试）
# ============================================================
def run_dry_run():
    """
    Dry-run模式：模拟 $29 USDC 转入场景，验证完整闭环。
    不连接区块链，直接使用模拟数据测试 支付→Key 流程。
    """
    print("\n" + "=" * 60)
    print("🧪 BDE Score™ — USDC Listener Dry-Run Test")
    print("=" * 60)

    # 模拟付款数据
    test_payments = [
        {
            'tx_hash': '0xdry_run_monthly_' + secrets.token_hex(8),
            'from_address': '0x' + secrets.token_hex(20),
            'to_address': WALLET_ADDRESS,
            'amount_raw': MONTHLY_PRICE * (10 ** USDC_DECIMALS),
            'amount_usd': float(MONTHLY_PRICE),
            'plan': 'monthly_premium',
            'block_number': 99999999,
            'log_index': 0,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'status': 'detected',
        },
        {
            'tx_hash': '0xdry_run_yearly_' + secrets.token_hex(8),
            'from_address': '0x' + secrets.token_hex(20),
            'to_address': WALLET_ADDRESS,
            'amount_raw': YEARLY_PRICE * (10 ** USDC_DECIMALS),
            'amount_usd': float(YEARLY_PRICE),
            'plan': 'yearly_premium',
            'block_number': 99999999,
            'log_index': 1,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'status': 'detected',
        },
    ]

    recorder = PaymentRecord()
    listener_stub = None  # 不需要真实监听器

    print(f"\n📋 模拟 {len(test_payments)} 笔付款:")
    for i, p in enumerate(test_payments):
        print(f"  [{i+1}] ${p['amount_usd']} from {p['from_address'][:14]}... (tx: {p['tx_hash'][:20]}...)")

    # 处理每笔付款
    print("\n🔄 开始处理...")
    results = []
    for payment in test_payments:
        print(f"\n--- 处理 ${payment['amount_usd']} 付款 ---")

        # Step 1: 记录
        payment_id = recorder.record(payment)
        print(f"  ✅ Step 1: 付款已记录 (ID: {payment_id})")

        # Step 2: 生成/激活 Key
        try:
            result = process_payment(
                payer_address=payment['from_address'],
                amount_usd=payment['amount_usd'],
                tx_hash=payment['tx_hash'],
            )
            print(f"  ✅ Step 2: Key {result['action']} | prefix={result['key_prefix']}")
            print(f"     类型: {result['tier']} | 有效{result['duration_months']}个月")
            print(f"     到期: {result['expires_at']}")
            if result.get('key_full'):
                print(f"     🔑 完整Key: {result['key_full']} (仅显示一次)")
            results.append(result)
        except Exception as e:
            print(f"  ❌ Step 2 失败: {e}")
            import traceback
            traceback.print_exc()
            results.append({'error': str(e)})

        # Step 3: 更新状态
        recorder.mark_activated(payment['tx_hash'], result.get('key_prefix', 'N/A'))
        print(f"  ✅ Step 3: 付款状态已更新")

    # 验证结果
    print("\n" + "=" * 60)
    print("📊 验证结果")
    print("=" * 60)

    # 检查 api_keys.json
    keys_path = DATA_DIR / 'api_keys.json'
    try:
        with open(keys_path, 'r') as f:
            keys = json.load(f)
        print(f"\n📁 api_keys.json: {len(keys)} 条记录")
        # 显示最新的2条
        for k in keys[-2:]:
            print(f"  - prefix: {k.get('key_prefix', 'N/A')} | tier: {k.get('tier')} | active: {k.get('active')} | expires: {k.get('expires_at', 'N/A')}")
    except Exception as e:
        print(f"  ⚠️ 读取api_keys.json失败: {e}")

    # 检查 activation_log.json
    log_path = DATA_DIR / 'activation_log.json'
    try:
        with open(log_path, 'r') as f:
            logs = json.load(f)
        print(f"\n📁 activation_log.json: {len(logs)} 条记录")
        for entry in logs[-2:]:
            print(f"  - tx: {entry.get('tx_hash', '')[:20]}... | payer: {entry.get('payer', '')[:14]}...")
            print(f"    amount: ${entry.get('amount')} | tier: {entry.get('tier')} | key: {entry.get('key_prefix')}")
            print(f"    activated: {entry.get('activated_at')} | expires: {entry.get('expires_at')}")
    except Exception as e:
        print(f"  ⚠️ 读取activation_log.json失败: {e}")

    # 检查 usdc_payments.json
    try:
        with open(PAYMENTS_DB_PATH, 'r') as f:
            payments = json.load(f)
        if isinstance(payments, list):
            print(f"\n📁 usdc_payments.json: {len(payments)} 条记录")
        else:
            print(f"\n📁 usdc_payments.json: {len(payments)} 条记录")
    except Exception as e:
        print(f"  ⚠️ 读取usdc_payments.json失败: {e}")

    # 检查 address_key_map.json
    map_path = DATA_DIR / 'address_key_map.json'
    try:
        with open(map_path, 'r') as f:
            addr_map = json.load(f)
        print(f"\n📁 address_key_map.json: {len(addr_map)} 条映射")
        for addr, info in list(addr_map.items())[-2:]:
            print(f"  - {addr[:14]}... → {info.get('key_prefix')} | payments: ${info.get('total_payments_usd', 0)}")
    except Exception as e:
        print(f"  ⚠️ 读取address_key_map.json失败: {e}")

    print("\n" + "=" * 60)
    success_count = sum(1 for r in results if 'error' not in r and r.get('action'))
    print(f"🏁 Dry-Run完成: {success_count}/{len(test_payments)} 成功")
    print("=" * 60)

    return results


# ============================================================
# 便捷函数
# ============================================================
def create_listener() -> USDCListener:
    return USDCListener()


def create_recorder() -> PaymentRecord:
    return PaymentRecord()


def get_payment_config() -> Dict:
    return {
        'wallet_address': WALLET_ADDRESS,
        'usdc_contract': USDC_CONTRACT_ADDRESS,
        'monthly_price_usd': PREMIUM_PRICE_USD,
        'yearly_price_usd': YEARLY_PRICE,
        'chain': 'Base',
        'chain_id': 8453,
        'required_confirmations': CONFIRMATION_BLOCKS,
        'poll_interval_seconds': POLL_INTERVAL_SECONDS,
    }


# ============================================================
# 独立运行入口
# ============================================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='BDE Score USDC Listener v2.0')
    parser.add_argument('--dry-run', action='store_true', help='模拟测试模式（不连接区块链）')
    parser.add_argument('--info', action='store_true', help='仅显示配置和状态信息')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
    )

    if args.dry_run:
        run_dry_run()
        sys.exit(0)

    if args.info:
        print("=" * 60)
        print("BDE Score™ — USDC Payment Listener v2.0")
        print("=" * 60)
        print(f"\n配置: {json.dumps(get_payment_config(), indent=2)}")
        sys.exit(0)

    # 正常监听模式
    print("=" * 60)
    print("BDE Score™ — USDC Payment Listener v2.0 (支付→Key闭环)")
    print("=" * 60)

    listener = create_listener()
    info = listener.get_chain_info()
    print(f"\n链信息: {json.dumps(info, indent=2)}")

    if not info.get('connected'):
        print("\n❌ RPC连接失败，退出")
        sys.exit(1)

    balance = listener.get_wallet_balance()
    print(f"\n钱包余额: {json.dumps(balance, indent=2)}")

    print(f"\n配置: {json.dumps(get_payment_config(), indent=2)}")
    print(f"\n监听模式: 月度 ${MONTHLY_PRICE} / 年度 ${YEARLY_PRICE}")
    print(f"轮询间隔: {POLL_INTERVAL_SECONDS}秒")
    print(f"\n开始监听... (Ctrl+C 退出)")

    recorder = create_recorder()
    bg = BackgroundListener(listener, recorder)

    import signal
    def shutdown(sig, frame):
        print("\n收到停止信号，正在退出...")
        bg.stop()
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    bg.run_loop_sync()
