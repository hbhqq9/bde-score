"""
BDE Score™ — ZeroFriction Layer 3: USDC On-Chain Payment Listener
=================================================================
监听 Base 链上 USDC 转入指定钱包，自动触发 Premium API Key 激活。

架构: Base Chain (RPC) → Event Filter → Amount Match → Auto-Activate Key
依赖: web3.py (已安装 v7.x)
注意: 只读监听，不需要私钥。

配置:
  WALLET_ADDRESS: 收款钱包地址（checksum格式）
  USDC_CONTRACT: Base链 USDC 合约地址
  PREMIUM_AMOUNT: 月付金额（USDC，6位精度）
"""

import os
import json
import time
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from pathlib import Path

from web3 import Web3
from web3.exceptions import ContractLogicError

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

# 监听配置
POLL_INTERVAL_SECONDS = int(os.environ.get('POLL_INTERVAL', '12'))  # Base出块约2秒，但公共RPC限频，12秒轮询
CONFIRMATION_BLOCKS = 3  # 等待3个区块确认（约6秒 on Base）
MAX_BLOCK_LOOKBACK = 1000  # 单次扫描最大回溯区块数
LISTEN_FROM_BLOCK = int(os.environ.get('LISTEN_FROM_BLOCK', '0'))  # 0=从当前区块开始

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
# 核心类：USDCListener
# ============================================================
class USDCListener:
    """
    USDC链上支付监听器
    - 连接 Base 链 RPC
    - 监听 USDC Transfer 事件到指定钱包
    - 识别金额匹配（$29 USDC）
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
        """验证并规范化钱包地址"""
        addr = WALLET_ADDRESS
        try:
            self.wallet_checksum = Web3.to_checksum_address(addr)
            logger.info(f"钱包地址验证通过: {self.wallet_checksum}")
        except Exception as e:
            logger.error(f"钱包地址无效: {addr} — {e}")
            raise ValueError(
                f"Invalid wallet address: {addr}. "
                "Must be a valid 42-char hex Ethereum address (0x + 40 hex chars)."
            )

    def is_connected(self) -> bool:
        """检查RPC连接状态"""
        try:
            return self.w3.is_connected()
        except Exception:
            return False

    def get_chain_info(self) -> Dict:
        """获取链信息"""
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
        """查询钱包USDC余额"""
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
        exact_amount: bool = True,
    ) -> List[Dict]:
        """
        扫描链上 USDC Transfer 事件，筛选转入指定钱包的交易。

        Args:
            from_block: 起始区块（默认从上次扫描位置）
            to_block: 结束区块（默认最新）
            exact_amount: 是否严格匹配 $29 金额

        Returns:
            匹配的付款记录列表
        """
        if not self.is_connected():
            logger.error("RPC连接断开")
            return []

        current_block = self.w3.eth.block_number

        if from_block is None:
            from_block = self._last_scanned_block or (current_block - 100)
        if to_block is None:
            # 留出确认区块余量
            to_block = current_block - CONFIRMATION_BLOCKS

        if from_block > to_block:
            return []

        # 限制单次扫描范围
        if to_block - from_block > MAX_BLOCK_LOOKBACK:
            from_block = to_block - MAX_BLOCK_LOOKBACK

        logger.info(f"扫描区块 {from_block} → {to_block} (链最新: {current_block})")

        try:
            # 构建事件过滤器：Transfer(address, address, uint256)
            transfer_event = self.usdc_contract.events.Transfer()

            # 获取转入钱包的 Transfer 事件
            logs = transfer_event.get_logs(
                fromBlock=from_block,
                toBlock=to_block,
                argument_filters={'to': self.wallet_checksum},
            )
        except Exception as e:
            logger.error(f"事件扫描失败: {e}")
            # 公共RPC可能不支持 eth_getLogs 或限频，回退到逐区块
            return self._scan_fallback(from_block, to_block, exact_amount)

        results = []
        for log_entry in logs:
            payment = self._parse_transfer_log(log_entry, exact_amount)
            if payment:
                results.append(payment)

        self._last_scanned_block = to_block
        return results

    def _scan_fallback(self, from_block: int, to_block: int, exact_amount: bool) -> List[Dict]:
        """
        备用扫描方式：当 get_logs 不可用时，通过逐区块读取交易。
        注意：这较慢，但公共RPC通常支持 get_logs。
        """
        logger.warning(f"使用备用扫描模式（区块 {from_block} → {to_block}）")
        results = []
        try:
            # 尝试直接获取区块中的交易receipt
            for block_num in range(from_block, to_block + 1):
                block = self.w3.eth.get_block(block_num, full_transactions=True)
                for tx in block.transactions:
                    if tx.get('to') and tx['to'].lower() == USDC_CONTRACT_ADDRESS.lower():
                        try:
                            receipt = self.w3.eth.get_transaction_receipt(tx['hash'])
                            for log_entry in receipt['logs']:
                                payment = self._parse_raw_log(log_entry, exact_amount)
                                if payment:
                                    payment['block_number'] = block_num
                                    results.append(payment)
                        except Exception:
                            continue
        except Exception as e:
            logger.error(f"备用扫描也失败: {e}")

        self._last_scanned_block = to_block
        return results

    def _parse_transfer_log(self, log_entry, exact_amount: bool) -> Optional[Dict]:
        """解析 Transfer 事件日志"""
        try:
            from_addr = log_entry['args']['from']
            to_addr = log_entry['args']['to']
            value = log_entry['args']['value']

            # 确认目标地址匹配
            if to_addr.lower() != self.wallet_checksum.lower():
                return None

            # 金额检查
            if exact_amount and value != PREMIUM_AMOUNT_RAW:
                logger.debug(f"金额不匹配: {value} != {PREMIUM_AMOUNT_RAW}")
                return None

            if value < PREMIUM_AMOUNT_RAW:
                logger.debug(f"金额不足: {value / 1e6} < ${PREMIUM_PRICE_USD}")
                return None

            amount_usd = value / (10 ** USDC_DECIMALS)

            return {
                'tx_hash': log_entry['transactionHash'].hex()
                    if isinstance(log_entry['transactionHash'], bytes)
                    else str(log_entry['transactionHash']),
                'from_address': from_addr,
                'to_address': to_addr,
                'amount_raw': value,
                'amount_usd': amount_usd,
                'block_number': log_entry['blockNumber'],
                'log_index': log_entry['logIndex'],
                'timestamp': datetime.now().isoformat(),
                'status': 'detected',
            }
        except Exception as e:
            logger.error(f"解析Transfer日志失败: {e}")
            return None

    def _parse_raw_log(self, log_entry, exact_amount: bool) -> Optional[Dict]:
        """解析原始日志条目（备用模式）"""
        try:
            # Transfer event signature: keccak256("Transfer(address,address,uint256)")
            TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
            topics = log_entry.get('topics', [])

            if not topics or topics[0] != TRANSFER_TOPIC:
                return None
            if len(topics) < 3:
                return None

            # 检查合约地址
            if log_entry['address'].lower() != USDC_CONTRACT_ADDRESS.lower():
                return None

            from_addr = '0x' + topics[1].hex()[-40:] if isinstance(topics[1], bytes) else '0x' + str(topics[1])[-40:]
            to_addr = '0x' + topics[2].hex()[-40:] if isinstance(topics[2], bytes) else '0x' + str(topics[2])[-40:]

            if to_addr.lower() != self.wallet_checksum.lower():
                return None

            # 解析 value（data字段）
            data = log_entry.get('data', '0x0')
            if isinstance(data, bytes):
                value = int.from_bytes(data, 'big')
            else:
                value = int(data, 16) if data != '0x' else 0

            if exact_amount and value != PREMIUM_AMOUNT_RAW:
                return None

            amount_usd = value / (10 ** USDC_DECIMALS)

            return {
                'tx_hash': log_entry['transactionHash'].hex()
                    if isinstance(log_entry['transactionHash'], bytes)
                    else str(log_entry['transactionHash']),
                'from_address': from_addr,
                'to_address': to_addr,
                'amount_raw': value,
                'amount_usd': amount_usd,
                'block_number': log_entry.get('blockNumber', 0),
                'log_index': log_entry.get('logIndex', 0),
                'timestamp': datetime.now().isoformat(),
                'status': 'detected',
            }
        except Exception as e:
            logger.error(f"解析原始日志失败: {e}")
            return None

    def verify_transaction(self, tx_hash: str) -> Dict:
        """
        验证特定交易：确认是否有效 USDC 付款到指定钱包。

        Args:
            tx_hash: 交易哈希

        Returns:
            验证结果字典
        """
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

        # 解析日志寻找匹配的 Transfer 事件
        for log_entry in receipt.get('logs', []):
            payment = self._parse_raw_log(log_entry, exact_amount=False)
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
# 核心类：PaymentActivator（付款 → Key 激活）
# ============================================================
class PaymentActivator:
    """
    将链上付款记录与 API Key 激活关联。
    管理支付状态持久化和 Key 自动生成。
    """

    def __init__(self, payments_db_path: str = None, activation_log_path: str = None):
        self.payments_db_path = Path(payments_db_path or PAYMENTS_DB_PATH)
        self.activation_log_path = Path(activation_log_path or ACTIVATION_LOG_PATH)
        self.payments = self._load_payments()

    def _load_payments(self) -> Dict:
        """加载支付记录"""
        try:
            with open(self.payments_db_path, 'r') as f:
                data = json.load(f)
                # 转为 dict keyed by tx_hash
                if isinstance(data, list):
                    return {p['tx_hash']: p for p in data}
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_payments(self):
        """持久化支付记录"""
        with open(self.payments_db_path, 'w') as f:
            json.dump(list(self.payments.values()), f, indent=2, ensure_ascii=False)

    def _load_activation_log(self) -> List[Dict]:
        """加载激活日志"""
        try:
            with open(self.activation_log_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_activation_log(self, log: List[Dict]):
        with open(self.activation_log_path, 'w') as f:
            json.dump(log, f, indent=2, ensure_ascii=False)

    def _generate_api_key(self, tier: str = 'premium') -> str:
        """生成 API Key（与 KeyManager 兼容的格式）"""
        key = f"bde_{secrets.token_urlsafe(24)}"
        return key

    def _generate_payment_id(self, tx_hash: str) -> str:
        """生成支付ID（用于前端轮询）"""
        return hashlib.sha256(tx_hash.encode()).hexdigest()[:16]

    def record_payment(self, payment_data: Dict) -> str:
        """
        记录新付款，生成 payment_id 用于追踪。

        Returns:
            payment_id: 用于前端查询支付状态的标识符
        """
        tx_hash = payment_data['tx_hash']

        # 防止重复记录
        if tx_hash in self.payments:
            existing = self.payments[tx_hash]
            if existing.get('api_key'):
                logger.info(f"交易已处理: {tx_hash}")
                return existing.get('payment_id', self._generate_payment_id(tx_hash))

        payment_id = self._generate_payment_id(tx_hash)

        self.payments[tx_hash] = {
            'payment_id': payment_id,
            'tx_hash': tx_hash,
            'from_address': payment_data.get('from_address', ''),
            'amount_usd': payment_data.get('amount_usd', 0),
            'block_number': payment_data.get('block_number', 0),
            'detected_at': payment_data.get('timestamp', datetime.now().isoformat()),
            'status': 'pending_confirmation',
            'api_key': None,
            'email': payment_data.get('email'),
        }
        self._save_payments()
        logger.info(f"新付款记录: {payment_id} | ${payment_data.get('amount_usd', 0)} from {payment_data.get('from_address', 'unknown')}")
        return payment_id

    def activate_from_payment(self, tx_hash: str, email: str = None) -> Optional[Dict]:
        """
        根据已确认的交易自动生成 Premium API Key。

        Args:
            tx_hash: 已确认的链上交易哈希
            email: 可选绑定邮箱

        Returns:
            激活结果（包含 API Key），或 None（如果失败）
        """
        payment = self.payments.get(tx_hash)
        if not payment:
            logger.error(f"交易记录不存在: {tx_hash}")
            return None

        if payment.get('api_key'):
            logger.info(f"交易已激活: {tx_hash}")
            return {
                'payment_id': payment['payment_id'],
                'api_key': payment['api_key'],
                'tier': 'premium',
                'status': 'already_activated',
            }

        if payment['status'] not in ('detected', 'pending_confirmation', 'confirmed'):
            logger.error(f"交易状态不允许激活: {payment['status']}")
            return None

        # 生成 API Key
        api_key = self._generate_api_key('premium')

        # 更新支付记录
        payment['status'] = 'activated'
        payment['api_key'] = api_key
        payment['tier'] = 'premium'
        payment['email'] = email or payment.get('email')
        payment['activated_at'] = datetime.now().isoformat()
        self.payments[tx_hash] = payment
        self._save_payments()

        # 写入激活日志
        log = self._load_activation_log()
        log.append({
            'payment_id': payment['payment_id'],
            'tx_hash': tx_hash,
            'from_address': payment['from_address'],
            'amount_usd': payment['amount_usd'],
            'api_key_prefix': api_key[:12] + '...',
            'tier': 'premium',
            'email': email,
            'activated_at': payment['activated_at'],
        })
        self._save_activation_log(log)

        logger.info(f"Premium 激活成功: {payment['payment_id']} | Key: {api_key[:12]}...")

        return {
            'payment_id': payment['payment_id'],
            'api_key': api_key,
            'tier': 'premium',
            'status': 'activated',
            'activated_at': payment['activated_at'],
        }

    def get_payment_status(self, payment_id: str = None, tx_hash: str = None) -> Optional[Dict]:
        """
        查询支付状态（支持 payment_id 或 tx_hash 查询）。
        """
        if tx_hash:
            return self.payments.get(tx_hash)

        if payment_id:
            for p in self.payments.values():
                if p.get('payment_id') == payment_id:
                    return p
        return None

    def get_all_payments(self) -> List[Dict]:
        """获取所有支付记录"""
        return list(self.payments.values())

    def sync_with_key_manager(self, key_manager) -> int:
        """
        将已激活但未同步到 KeyManager 的 Key 同步过去。
        在 bde_api.py 启动时调用。

        Returns:
            同步数量
        """
        synced = 0
        for tx_hash, payment in self.payments.items():
            if payment.get('status') == 'activated' and payment.get('api_key'):
                api_key = payment['api_key']
                if api_key not in key_manager.keys:
                    key_manager.keys[api_key] = {
                        'key': api_key,
                        'tier': payment.get('tier', 'premium'),
                        'email': payment.get('email'),
                        'created_at': payment.get('activated_at'),
                        'active': True,
                        'source': 'usdc_payment',
                        'tx_hash': tx_hash,
                        'from_address': payment.get('from_address'),
                    }
                    synced += 1
                    logger.info(f"同步Key到KeyManager: {api_key[:12]}... (tx: {tx_hash[:16]}...)")

        if synced > 0:
            key_manager._save()
            logger.info(f"共步 {synced} 个Key到KeyManager")

        return synced


# ============================================================
# 后台监听循环（可选独立运行）
# ============================================================
class BackgroundListener:
    """
    后台监听进程：持续扫描链上付款并自动激活。
    可通过 bde_api.py 的 lifespan 启动，或独立运行。
    """

    def __init__(self, listener: USDCListener, activator: PaymentActivator):
        self.listener = listener
        self.activator = activator
        self._running = False

    async def run_loop(self, auto_activate: bool = True):
        """
        主循环：扫描 → 记录 → 激活。
        由 asyncio 事件循环驱动。
        """
        import asyncio
        self._running = True
        logger.info("USDC后台监听启动")

        while self._running:
            try:
                if not self.listener.is_connected():
                    logger.warning("RPC断开，等待重连...")
                    await asyncio.sleep(30)
                    continue

                payments = self.listener.scan_for_payments()

                for payment in payments:
                    tx_hash = payment['tx_hash']

                    # 检查是否已处理
                    existing = self.activator.get_payment_status(tx_hash=tx_hash)
                    if existing and existing.get('api_key'):
                        continue

                    # 记录付款
                    payment_id = self.activator.record_payment(payment)

                    # 自动激活（金额匹配即激活）
                    if auto_activate and payment.get('amount_usd', 0) >= PREMIUM_PRICE_USD:
                        result = self.activator.activate_from_payment(tx_hash)
                        if result:
                            logger.info(
                                f"✅ 自动激活成功: {payment_id} | "
                                f"${payment['amount_usd']} from {payment['from_address']}"
                            )

            except Exception as e:
                logger.error(f"监听循环异常: {e}", exc_info=True)

            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    def stop(self):
        """停止监听"""
        self._running = False
        logger.info("USDC后台监听已停止")


# ============================================================
# 便捷函数（供 bde_api.py 调用）
# ============================================================
def create_listener() -> USDCListener:
    """创建 USDC 监听器实例"""
    return USDCListener()


def create_activator() -> PaymentActivator:
    """创建付款激活器实例"""
    return PaymentActivator()


def get_payment_config() -> Dict:
    """获取支付配置信息（供前端使用）"""
    return {
        'wallet_address': WALLET_ADDRESS,
        'usdc_contract': USDC_CONTRACT_ADDRESS,
        'premium_price_usd': PREMIUM_PRICE_USD,
        'chain': 'Base',
        'chain_id': 8453,
        'required_confirmations': CONFIRMATION_BLOCKS,
        'poll_interval_seconds': POLL_INTERVAL_SECONDS,
    }


# ============================================================
# 独立运行入口（测试/调试用）
# ============================================================
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
    )

    print("=" * 60)
    print("BDE Score™ — USDC Payment Listener (Standalone)")
    print("=" * 60)

    listener = create_listener()
    info = listener.get_chain_info()
    print(f"\n链信息: {json.dumps(info, indent=2)}")

    balance = listener.get_wallet_balance()
    print(f"\n钱包余额: {json.dumps(balance, indent=2)}")

    print(f"\n配置: {json.dumps(get_payment_config(), indent=2)}")

    print("\n监听模式（Ctrl+C 退出）...")
    activator = create_activator()
    bg = BackgroundListener(listener, activator)

    import signal
    def shutdown(sig, frame):
        bg.stop()
    signal.signal(signal.SIGINT, shutdown)

    import asyncio
    asyncio.run(bg.run_loop())
