"""
BDE Score™ — Payment-to-Key Bridge
====================================
独立模块：连接 USDC 支付检测与 API Key 管理。

职责:
  1. 根据支付金额确定 tier 和有效期
  2. 生成新的 premium API Key（bcrypt hash 存储）
  3. 查找/关联付款地址与已有 Key
  4. 延长已有 Key 的有效期
  5. 同步写入 api_keys.json

安全:
  - 不接触私钥，仅做随机字符串 + bcrypt
  - 所有金额验证由调用方（usdc_listener）基于链上数据完成
"""

import json
import secrets
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Tuple

import bcrypt

logger = logging.getLogger('payment_to_key')

# ============================================================
# 配置
# ============================================================
DATA_DIR = Path(__file__).parent
API_KEYS_PATH = DATA_DIR / 'api_keys.json'
ADDRESS_KEY_MAP_PATH = DATA_DIR / 'address_key_map.json'
ACTIVATION_LOG_PATH = DATA_DIR / 'activation_log.json'

# 定价（USDC）
MONTHLY_PRICE = 29      # $29/月
YEARLY_PRICE = 290      # $290/年 (10个月价格)


# ============================================================
# 地址-Key 映射管理
# ============================================================
def _load_address_map() -> Dict:
    """加载 付款地址 → key_prefix 映射"""
    try:
        with open(ADDRESS_KEY_MAP_PATH, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_address_map(mapping: Dict):
    """持久化地址映射"""
    with open(ADDRESS_KEY_MAP_PATH, 'w') as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)


def _load_api_keys() -> list:
    """加载 api_keys.json"""
    try:
        with open(API_KEYS_PATH, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_api_keys(keys: list):
    """持久化 api_keys.json"""
    with open(API_KEYS_PATH, 'w') as f:
        json.dump(keys, f, indent=2, ensure_ascii=False)


def _load_activation_log() -> list:
    """加载激活日志"""
    try:
        with open(ACTIVATION_LOG_PATH, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_activation_log(log: list):
    """持久化激活日志"""
    with open(ACTIVATION_LOG_PATH, 'w') as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


# ============================================================
# 核心功能
# ============================================================
def determine_tier(amount_usd: float) -> Tuple[str, int]:
    """
    根据支付金额确定 tier 和有效月数。

    Args:
        amount_usd: 支付金额（USDC）

    Returns:
        (tier_name, duration_months)
    """
    if amount_usd >= YEARLY_PRICE:
        return 'premium', 12
    elif amount_usd >= MONTHLY_PRICE:
        return 'premium', 1
    else:
        return 'free', 0


def generate_premium_key(payer_address: str, amount_usd: float) -> Dict:
    """
    为付款地址生成新的 premium API Key。

    流程:
      1. 生成随机 key: bde_ + 12位随机字符
      2. 计算 bcrypt hash
      3. 写入 api_keys.json（hash 存储模式）
      4. 建立 payer_address → key_prefix 映射
      5. 返回 key 信息（仅返回一次完整 key）

    Args:
        payer_address: 付款方钱包地址
        amount_usd: 支付金额

    Returns:
        dict: {
            'key_prefix': 'bde_xxx-',
            'key_full': 'bde_xxxxxxxxxxxxx',  # 仅本次可见
            'key_hash': '$2b$12$...',
            'tier': 'premium',
            'duration_months': 1 or 12,
            'expires_at': '2026-08-23T...',
            'created_at': '2026-07-23T...',
        }
    """
    tier, duration_months = determine_tier(amount_usd)
    now = datetime.utcnow()
    expires_at = now + timedelta(days=30 * duration_months)

    # 生成 key: bde_ + 12位随机字符
    random_part = secrets.token_urlsafe(9)[:12]  # 确保12位
    key_full = f"bde_{random_part}"
    key_prefix = f"bde_{random_part[:4]}"

    # bcrypt hash
    key_hash = bcrypt.hashpw(key_full.encode(), bcrypt.gensalt(rounds=12)).decode()

    # 写入 api_keys.json
    keys = _load_api_keys()
    key_entry = {
        'key_hash': key_hash,
        'key_prefix': key_prefix,
        'tier': tier,
        'email': None,
        'payer_address': payer_address.lower(),
        'created_at': now.isoformat(),
        'active': True,
        'expires_at': expires_at.isoformat(),
        'duration_months': duration_months,
        'source': 'usdc_payment',
    }
    keys.append(key_entry)
    _save_api_keys(keys)

    # 建立地址映射
    addr_map = _load_address_map()
    addr_map[payer_address.lower()] = {
        'key_prefix': key_prefix,
        'created_at': now.isoformat(),
        'last_payment': now.isoformat(),
        'total_payments_usd': amount_usd,
    }
    _save_address_map(addr_map)

    logger.info(f"新Premium Key生成: {key_prefix}... for {payer_address[:10]}... | 有效{duration_months}个月")

    return {
        'key_prefix': key_prefix,
        'key_full': key_full,
        'key_hash': key_hash,
        'tier': tier,
        'duration_months': duration_months,
        'expires_at': expires_at.isoformat() + 'Z',
        'created_at': now.isoformat() + 'Z',
    }


def extend_key(payer_address: str, amount_usd: float) -> Dict:
    """
    延长已有 Key 的有效期。

    流程:
      1. 通过地址映射找到 key_prefix
      2. 在 api_keys.json 中找到对应条目
      3. 延长 expires_at
      4. 确保 key 处于 active 状态

    Args:
        payer_address: 付款方钱包地址
        amount_usd: 支付金额

    Returns:
        dict: 更新结果，或 None（如果未找到已有 key）
    """
    addr_map = _load_address_map()
    addr_lower = payer_address.lower()

    if addr_lower not in addr_map:
        return None

    key_prefix = addr_map[addr_lower]['key_prefix']

    keys = _load_api_keys()
    target_idx = None
    for i, k in enumerate(keys):
        if k.get('key_prefix') == key_prefix:
            target_idx = i
            break

    if target_idx is None:
        logger.warning(f"地址映射存在但api_keys中未找到: {key_prefix}")
        return None

    tier, duration_months = determine_tier(amount_usd)
    now = datetime.utcnow()

    # 计算新的过期时间：从当前过期时间或现在（取较晚者）+ duration
    existing_expires = keys[target_idx].get('expires_at')
    if existing_expires:
        try:
            base_time = datetime.fromisoformat(existing_expires.replace('Z', ''))
            if base_time < now:
                base_time = now
        except (ValueError, TypeError):
            base_time = now
    else:
        base_time = now

    new_expires = base_time + timedelta(days=30 * duration_months)

    # 更新
    keys[target_idx]['expires_at'] = new_expires.isoformat()
    keys[target_idx]['active'] = True
    keys[target_idx]['tier'] = tier
    keys[target_idx]['last_extended'] = now.isoformat()
    keys[target_idx]['duration_months'] = keys[target_idx].get('duration_months', 0) + duration_months
    _save_api_keys(keys)

    # 更新地址映射
    addr_map[addr_lower]['last_payment'] = now.isoformat()
    addr_map[addr_lower]['total_payments_usd'] = addr_map[addr_lower].get('total_payments_usd', 0) + amount_usd
    _save_address_map(addr_map)

    logger.info(f"Key延期成功: {key_prefix} | +{duration_months}月 → {new_expires.isoformat()}")

    return {
        'key_prefix': key_prefix,
        'tier': tier,
        'duration_months': duration_months,
        'previous_expires': existing_expires,
        'new_expires_at': new_expires.isoformat() + 'Z',
        'extended_at': now.isoformat() + 'Z',
    }


def find_key_for_address(payer_address: str) -> Optional[Dict]:
    """
    查找付款地址关联的 API Key。

    Returns:
        Key信息 或 None
    """
    addr_map = _load_address_map()
    addr_lower = payer_address.lower()

    if addr_lower not in addr_map:
        return None

    key_prefix = addr_map[addr_lower]['key_prefix']

    keys = _load_api_keys()
    for k in keys:
        if k.get('key_prefix') == key_prefix:
            return {
                'key_prefix': k['key_prefix'],
                'tier': k.get('tier', 'premium'),
                'active': k.get('active', False),
                'expires_at': k.get('expires_at'),
                'created_at': k.get('created_at'),
            }

    return None


def link_payment_to_key(tx_hash: str, key_prefix: str) -> Dict:
    """
    建立 交易哈希 → key_prefix 的映射记录。
    写入 activation_log.json。

    Args:
        tx_hash: 链上交易哈希
        key_prefix: API Key 前缀

    Returns:
        映射记录
    """
    return {
        'tx_hash': tx_hash,
        'key_prefix': key_prefix,
        'linked_at': datetime.utcnow().isoformat() + 'Z',
    }


def write_activation_log(entry: Dict):
    """
    追加一条激活记录到 activation_log.json。

    Args:
        entry: 激活记录，包含 tx_hash, payer, amount, tier, key_prefix, activated_at, expires_at
    """
    log = _load_activation_log()
    log.append(entry)
    _save_activation_log(log)
    logger.info(f"激活日志已写入: tx={entry.get('tx_hash', '')[:16]}... key={entry.get('key_prefix', '')}")


def process_payment(payer_address: str, amount_usd: float, tx_hash: str) -> Dict:
    """
    完整的 支付→Key 处理流程（一站式）。

    流程:
      1. 根据金额确定 tier 和 duration
      2. 查找是否已有关联 key
      3. 有则延期，无则新生成
      4. 写入 activation_log.json

    Args:
        payer_address: 链上付款方地址
        amount_usd: USDC 金额（由链上数据得出）
        tx_hash: 交易哈希

    Returns:
        处理结果 dict
    """
    tier, duration_months = determine_tier(amount_usd)
    now = datetime.utcnow()

    # 查找已有 key
    existing = find_key_for_address(payer_address)

    if existing and existing.get('active'):
        # 延期
        result = extend_key(payer_address, amount_usd)
        if result:
            action = 'extended'
            key_prefix = result['key_prefix']
            expires_at = result['new_expires_at']
        else:
            # 映射存在但key丢失，重新生成
            result = generate_premium_key(payer_address, amount_usd)
            action = 'generated'
            key_prefix = result['key_prefix']
            expires_at = result['expires_at']
    else:
        # 新生成
        result = generate_premium_key(payer_address, amount_usd)
        action = 'generated'
        key_prefix = result['key_prefix']
        expires_at = result['expires_at']

    # 写入激活日志
    log_entry = {
        'tx_hash': tx_hash,
        'payer': payer_address,
        'amount': amount_usd,
        'tier': tier,
        'key_prefix': key_prefix,
        'action': action,
        'duration_months': duration_months,
        'activated_at': now.isoformat() + 'Z',
        'expires_at': expires_at,
    }
    write_activation_log(log_entry)

    # 建立 tx→key 映射
    link = link_payment_to_key(tx_hash, key_prefix)

    return {
        'action': action,
        'key_prefix': key_prefix,
        'tier': tier,
        'duration_months': duration_months,
        'expires_at': expires_at,
        'tx_hash': tx_hash,
        'payer': payer_address,
        'amount': amount_usd,
        'link': link,
        # 仅在新生成时返回完整 key（安全考虑）
        'key_full': result.get('key_full') if action == 'generated' else None,
    }


# ============================================================
# CLI 测试入口
# ============================================================
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

    print("=" * 50)
    print("BDE Score™ — Payment-to-Key Bridge (Test)")
    print("=" * 50)

    # 模拟 $29 月度付款
    print("\n--- 测试1: $29 月度付款 (新地址) ---")
    result = process_payment(
        payer_address="0xTest1234567890abcdef1234567890abcdef12",
        amount_usd=29.0,
        tx_hash="0xaaa111bbb222ccc333ddd444eee555fff666aaa111bbb222ccc333ddd444eee555ff"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 模拟 $290 年度付款（同一地址 → 延期）
    print("\n--- 测试2: $290 年度付款 (同一地址 → 延期) ---")
    result2 = process_payment(
        payer_address="0xTest1234567890abcdef1234567890abcdef12",
        amount_usd=290.0,
        tx_hash="0xbbb222ccc333ddd444eee555fff666aaa111bbb222ccc333ddd444eee555fff666aa"
    )
    print(json.dumps(result2, indent=2, ensure_ascii=False))

    # 查看生成的文件
    print("\n--- 文件状态 ---")
    for f in [API_KEYS_PATH, ADDRESS_KEY_MAP_PATH, ACTIVATION_LOG_PATH]:
        if f.exists():
            with open(f) as fh:
                data = json.load(fh)
            print(f"{f.name}: {len(data)} 条记录")
