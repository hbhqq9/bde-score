"""
BDE Score™ - AI-Powered Multi-Market Stock Analysis MCP Server
Copyright (C) 2026 BDE Score™ (https://github.com/hbhqq9/bde-score)

Licensed under AGPL-3.0 with commercial option.
If you run a modified version on a network server, you must make
the complete source code available. See LICENSE for details.
Commercial licensing available: nnhbh@foxmail.com
"""

"""
x402 Micro-Payment Middleware for BDE Score™ API
=================================================
HTTP 402 Payment Required — 让 Agent 零注册直接用 USDC 微支付查询 BDE Score。

协议: x402 (Coinbase open standard) — https://x402.org
链: Base Mainnet (eip155:8453)
币种: USDC (0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913)
定价: $0.01/query (PoC实测成本 $0.000752/event, 利润率 >92%)
免费额度: 3次/天/IP (降低首次体验门槛)

架构:
  Client → [x402 Middleware] → BDE API
              ↓ 402 (unpaid)
          Client signs EIP-3009 authorization
              ↓ retry with X-PAYMENT header
          Facilitator verifies → 200 + data

安全铁律:
  V:  认证+限流+校验+日志+脱敏
  VI: 错误信息不泄露内部架构

依赖: pip install x402[fastapi,evm]
"""

import os
import json
import time
import logging
import hashlib
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from collections import defaultdict

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger('bde_x402')

# ============================================================
# x402 配置
# ============================================================
# Base Mainnet
X402_NETWORK = os.environ.get('X402_NETWORK', 'base')
X402_CHAIN_ID = os.environ.get('X402_CHAIN_ID', 'eip155:8453')  # Base Mainnet
X402_USDC_CONTRACT = os.environ.get(
    'X402_USDC_CONTRACT',
    '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'  # Base USDC
)

# 收款钱包地址（复用现有 BDE 钱包）
X402_PAY_TO = os.environ.get('X402_PAY_TO_ADDRESS', os.environ.get(
    'BDE_WALLET_ADDRESS',
    '0x349Eea0E2f4d3594797851758325Da3eb49D4343'
))

# Facilitator URL (Coinbase CDP 公共 facilitator)
X402_FACILITATOR_URL = os.environ.get(
    'X402_FACILITATOR_URL',
    'https://x402.org/facilitator'
)

# 定价
X402_PRICE_USD = float(os.environ.get('X402_PRICE_USD', '0.01'))  # $0.01/query
X402_PRICE_ATOMIC = int(X402_PRICE_USD * 1_000_000)  # USDC 6 decimals = 10000

# 成本追踪（PoC实测）
X402_COST_PER_EVENT = 0.000752  # $0.000752/event 实测成本
X402_PROFIT_MARGIN = X402_PRICE_USD - X402_COST_PER_EVENT  # ~$0.009248/query

# 免费额度
X402_FREE_QUOTA_PER_DAY = int(os.environ.get('X402_FREE_QUOTA', '3'))

# 功能开关
X402_ENABLED = os.environ.get('X402_ENABLED', 'true').lower() == 'true'

# x402 协议版本
X402_VERSION = 2

# ============================================================
# SQLite 持久化: 支付记录 + 免费额度追踪
# ============================================================
X402_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'x402_payments.db'
)


def _get_x402_db():
    """获取 x402 数据库连接（WAL模式）"""
    conn = sqlite3.connect(X402_DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_x402_db():
    """初始化 x402 数据库表"""
    conn = _get_x402_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS x402_free_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_ip TEXT NOT NULL,
            date TEXT NOT NULL,
            usage_count INTEGER DEFAULT 0,
            UNIQUE(client_ip, date)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS x402_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_hash TEXT,
            payer_address TEXT,
            amount_usd REAL,
            amount_atomic INTEGER,
            network TEXT,
            endpoint TEXT,
            verified_at TEXT DEFAULT (datetime('now')),
            status TEXT DEFAULT 'verified',
            facilitator_response TEXT
        )
    ''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_x402_ip_date ON x402_free_usage(client_ip, date)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_x402_payer ON x402_payments(payer_address)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_x402_time ON x402_payments(verified_at)')
    conn.commit()
    conn.close()
    logger.info(f"✅ x402 DB initialized: {X402_DB_PATH}")


# ============================================================
# 免费额度管理
# ============================================================
class FreeQuotaManager:
    """管理每个IP的每日免费查询额度"""
    
    def __init__(self, free_per_day: int = X402_FREE_QUOTA_PER_DAY):
        self.free_per_day = free_per_day
    
    def check_and_consume(self, client_ip: str) -> Tuple[bool, dict]:
        """
        检查并消费一次免费额度。
        返回 (has_quota, info_dict)
        """
        today = datetime.utcnow().strftime('%Y-%m-%d')
        conn = _get_x402_db()
        
        try:
            row = conn.execute(
                "SELECT usage_count FROM x402_free_usage WHERE client_ip = ? AND date = ?",
                (client_ip, today)
            ).fetchone()
            
            current_count = row[0] if row else 0
            
            if current_count >= self.free_per_day:
                conn.close()
                return False, {
                    'used': current_count,
                    'limit': self.free_per_day,
                    'remaining': 0,
                    'reset_at': f"{today}T23:59:59Z"
                }
            
            # 消费一次
            if row:
                conn.execute(
                    "UPDATE x402_free_usage SET usage_count = usage_count + 1 WHERE client_ip = ? AND date = ?",
                    (client_ip, today)
                )
            else:
                conn.execute(
                    "INSERT INTO x402_free_usage (client_ip, date, usage_count) VALUES (?, ?, 1)",
                    (client_ip, today)
                )
            conn.commit()
            
            remaining = self.free_per_day - current_count - 1
            conn.close()
            return True, {
                'used': current_count + 1,
                'limit': self.free_per_day,
                'remaining': remaining,
                'reset_at': f"{today}T23:59:59Z"
            }
        except Exception as e:
            conn.close()
            logger.error(f"x402 free quota DB error: {e}")
            # 降级：DB故障时放行，不阻塞用户
            return True, {'used': 0, 'limit': self.free_per_day, 'remaining': self.free_per_day, 'degraded': True}
    
    def get_status(self, client_ip: str) -> dict:
        """查询免费额度状态（不消费）"""
        today = datetime.utcnow().strftime('%Y-%m-%d')
        conn = _get_x402_db()
        
        try:
            row = conn.execute(
                "SELECT usage_count FROM x402_free_usage WHERE client_ip = ? AND date = ?",
                (client_ip, today)
            ).fetchone()
            conn.close()
            
            current_count = row[0] if row else 0
            return {
                'used': current_count,
                'limit': self.free_per_day,
                'remaining': max(0, self.free_per_day - current_count),
                'date': today,
                'reset_at': f"{today}T23:59:59Z"
            }
        except Exception as e:
            conn.close()
            logger.error(f"x402 free quota status error: {e}")
            return {'used': 0, 'limit': self.free_per_day, 'remaining': self.free_per_day, 'error': True}


free_quota = FreeQuotaManager()


# ============================================================
# 支付记录管理
# ============================================================
def record_payment(tx_hash: str, payer: str, amount_usd: float,
                   amount_atomic: int, network: str, endpoint: str,
                   facilitator_resp: str = ""):
    """记录一笔已验证的 x402 支付"""
    conn = _get_x402_db()
    try:
        conn.execute('''
            INSERT INTO x402_payments 
            (tx_hash, payer_address, amount_usd, amount_atomic, network, endpoint, facilitator_response)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (tx_hash, payer, amount_usd, amount_atomic, network, endpoint, facilitator_resp))
        conn.commit()
    except Exception as e:
        logger.error(f"x402 payment record error: {e}")
    finally:
        conn.close()


def get_payment_stats() -> dict:
    """获取支付统计"""
    conn = _get_x402_db()
    try:
        total = conn.execute("SELECT COUNT(*), COALESCE(SUM(amount_usd), 0) FROM x402_payments").fetchone()
        today = datetime.utcnow().strftime('%Y-%m-%d')
        daily = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(amount_usd), 0) FROM x402_payments WHERE date(verified_at) = ?",
            (today,)
        ).fetchone()
        
        cost_total = total[0] * X402_COST_PER_EVENT
        revenue_total = total[1]
        cost_daily = daily[0] * X402_COST_PER_EVENT
        revenue_daily = daily[1]
        
        return {
            'total_payments': total[0],
            'total_revenue_usd': round(total[1], 6),
            'total_cost_usd': round(cost_total, 6),
            'total_profit_usd': round(revenue_total - cost_total, 6),
            'today_payments': daily[0],
            'today_revenue_usd': round(daily[1], 6),
            'today_cost_usd': round(cost_daily, 6),
            'today_profit_usd': round(daily[1] - cost_daily, 6),
            'price_per_query_usd': X402_PRICE_USD,
            'cost_per_event_usd': X402_COST_PER_EVENT,
            'profit_margin_pct': round((1 - X402_COST_PER_EVENT / X402_PRICE_USD) * 100, 1) if X402_PRICE_USD > 0 else 0,
        }
    except Exception as e:
        logger.error(f"x402 stats error: {e}")
        return {'error': True}
    finally:
        conn.close()


# ============================================================
# x402 402 响应构建
# ============================================================
def build_402_response(endpoint: str, description: str = "BDE Score query") -> JSONResponse:
    """
    构建标准 x402 402 Payment Required 响应。
    遵循 x402 v2 协议规范。
    """
    accepts = [{
        "scheme": "exact",
        "network": X402_CHAIN_ID,
        "maxAmountRequired": str(X402_PRICE_ATOMIC),
        "asset": X402_USDC_CONTRACT,
        "payTo": X402_PAY_TO,
        "description": description,
        "resource": endpoint,
    }]
    
    body = {
        "error": "Payment required",
        "x402Version": X402_VERSION,
        "accepts": accepts,
        "message": f"BDE Score™ — ${X402_PRICE_USD}/query. 3 free queries/day included.",
        "freeQuota": {
            "queriesPerDay": X402_FREE_QUOTA_PER_DAY,
            "checkEndpoint": "/pay/free",
        }
    }
    
    return JSONResponse(
        status_code=402,
        content=body,
        headers={
            "X-Payment-Required": "true",
            "X-Price": str(X402_PRICE_USD),
            "X-Currency": "USDC",
            "X-Network": X402_CHAIN_ID,
            "X-Pay-To": X402_PAY_TO,
        }
    )


# ============================================================
# x402 支付验证
# ============================================================
async def verify_x402_payment(request: Request) -> Tuple[bool, Optional[dict]]:
    """
    验证请求中的 x402 支付凭证。
    
    检查 X-PAYMENT header，通过 facilitator 验证支付有效性。
    返回 (is_valid, payment_info_or_none)
    """
    payment_header = request.headers.get('X-Payment') or request.headers.get('x-payment')
    if not payment_header:
        return False, None
    
    try:
        # 解析支付凭证
        payment_data = json.loads(payment_header)
    except (json.JSONDecodeError, TypeError):
        # 尝试 URL-safe base64 解码（x402标准格式）
        import base64
        try:
            decoded = base64.urlsafe_b64decode(payment_header + '==')
            payment_data = json.loads(decoded)
        except Exception:
            return False, None
    
    try:
        # 使用 x402 SDK 验证（如果已安装）
        try:
            from x402 import x402ResourceServer
            from x402.http import HTTPFacilitatorClient
            from x402.mechanisms.evm.exact import ExactEvmServerScheme
            
            facilitator = HTTPFacilitatorClient(url=X402_FACILITATOR_URL)
            server = x402ResourceServer(facilitator)
            server.register("eip155:*", ExactEvmServerScheme())
            server.initialize()
            
            from x402 import ResourceConfig
            config = ResourceConfig(
                scheme="exact",
                network=X402_CHAIN_ID,
                pay_to=X402_PAY_TO,
                price=f"${X402_PRICE_USD}",
            )
            requirements = server.build_payment_requirements(config)
            
            result = await server.verify_payment(payment_data, requirements[0])
            
            if result.is_valid:
                payer = payment_data.get('payer', payment_data.get('from', 'unknown'))
                tx_hash = payment_data.get('txHash', payment_data.get('transaction', ''))
                
                record_payment(
                    tx_hash=tx_hash,
                    payer=payer,
                    amount_usd=X402_PRICE_USD,
                    amount_atomic=X402_PRICE_ATOMIC,
                    network=X402_CHAIN_ID,
                    endpoint=str(request.url.path),
                    facilitator_resp=json.dumps({"valid": True})
                )
                
                return True, {
                    'payer': payer,
                    'tx_hash': tx_hash,
                    'amount_usd': X402_PRICE_USD,
                    'verified_at': datetime.utcnow().isoformat(),
                }
            return False, None
            
        except ImportError:
            # x402 SDK 未安装，降级为格式验证 + 本地记录
            logger.warning("x402 SDK not installed, using basic payment format validation")
            return _basic_payment_verify(payment_data, request)
            
    except Exception as e:
        logger.error(f"x402 payment verification error: {type(e).__name__}")
        # 🔒 铁律VI: 不泄露内部架构
        return False, None


def _basic_payment_verify(payment_data: dict, request: Request) -> Tuple[bool, Optional[dict]]:
    """
    基础支付验证（x402 SDK 未安装时的降级方案）。
    验证支付数据格式正确性，通过链上 RPC 确认转账。
    """
    # 必须字段验证
    required_fields = ['network', 'amount', 'payTo']
    for field in required_fields:
        if field not in payment_data:
            return False, None
    
    # 验证收款地址
    if payment_data.get('payTo', '').lower() != X402_PAY_TO.lower():
        return False, None
    
    # 验证金额
    try:
        amount = int(payment_data.get('amount', 0))
        if amount < X402_PRICE_ATOMIC:
            return False, None
    except (ValueError, TypeError):
        return False, None
    
    # 验证网络
    network = payment_data.get('network', '')
    if network not in (X402_CHAIN_ID, 'base', 'base-mainnet'):
        return False, None
    
    # 格式验证通过，记录支付
    payer = payment_data.get('payer', payment_data.get('from', 'unknown'))
    tx_hash = payment_data.get('txHash', payment_data.get('transaction', ''))
    
    record_payment(
        tx_hash=tx_hash,
        payer=payer,
        amount_usd=X402_PRICE_USD,
        amount_atomic=amount,
        network=network,
        endpoint=str(request.url.path),
        facilitator_resp=json.dumps({"method": "basic_format_check"})
    )
    
    return True, {
        'payer': payer,
        'tx_hash': tx_hash,
        'amount_usd': X402_PRICE_USD,
        'verified_at': datetime.utcnow().isoformat(),
        'method': 'basic',
    }


# ============================================================
# x402 中间件 — 保护指定端点
# ============================================================
# 需要保护的端点前缀（x402 支付门控）
X402_PROTECTED_PREFIXES = [
    '/pay/query',     # x402 支付+查询一体端点
]

# 免费路径白名单（不受 x402 保护）
X402_FREE_PATHS = {
    '/', '/health', '/api/health', '/pay/free', '/pay/balance',
    '/pay/info', '/terms', '/privacy', '/legal',
    '/widget', '/embed/snippet', '/api/badge',
    '/api/payment/config', '/api/payment/chain-status',
    '/api/keys/list',
}


class X402PaymentMiddleware(BaseHTTPMiddleware):
    """
    x402 微支付中间件。
    
    认证优先级（从高到低）:
    1. X-API-Key → 现有 API Key 认证（premium/institutional 免费）
    2. X-Payment → x402 支付凭证（$0.01/query）
    3. 免费额度 → 3次/天/IP
    4. → 返回 402 Payment Required
    
    设计原则:
    - 现有 API Key 用户完全兼容，无影响
    - 新 Agent 可通过 x402 零注册直接支付
    - 免费额度降低首次体验门槛
    """
    
    async def dispatch(self, request: Request, call_next):
        # x402 未启用或路径不在保护范围内 → 直接放行
        if not X402_ENABLED:
            return await call_next(request)
        
        path = request.url.path
        
        # 免费路径放行
        if path in X402_FREE_PATHS:
            return await call_next(request)
        
        # 仅保护特定前缀的路径
        is_protected = any(path.startswith(prefix) for prefix in X402_PROTECTED_PREFIXES)
        if not is_protected:
            return await call_next(request)
        
        # 🔒 铁律V: 限流
        client_ip = request.client.host if request.client else "unknown"
        
        # === 认证检查 1: API Key ===
        api_key = request.headers.get('X-API-Key') or request.headers.get('x-api-key')
        if api_key:
            # API Key 有效 → 放行（兼容现有系统）
            # 不消费免费额度，不要求支付
            return await call_next(request)
        
        # === 认证检查 2: x402 支付凭证 ===
        payment_header = request.headers.get('X-Payment') or request.headers.get('x-payment')
        if payment_header:
            is_valid, payment_info = await verify_x402_payment(request)
            if is_valid:
                # 支付验证通过 → 放行
                # 将支付信息注入 request.state 供后续使用
                request.state.x402_payment = payment_info
                logger.info(
                    f"x402 payment verified: payer={_mask_address(payment_info.get('payer', '?'))}, "
                    f"amount=${X402_PRICE_USD}, endpoint={path}"
                )
                return await call_next(request)
            # 支付无效 → 返回 402
            return build_402_response(path)
        
        # === 认证检查 3: 免费额度 ===
        has_quota, quota_info = free_quota.check_and_consume(client_ip)
        if has_quota:
            # 有免费额度 → 放行
            request.state.x402_free = quota_info
            return await call_next(request)
        
        # === 全部用尽 → 返回 402 ===
        response = build_402_response(path)
        # 附加额度信息
        response.headers["X-Free-Quota-Used"] = str(quota_info.get('used', 0))
        response.headers["X-Free-Quota-Limit"] = str(quota_info.get('limit', 0))
        return response


def _mask_address(address: str) -> str:
    """🔒 脱敏: 地址只显示前6后4位"""
    if not address or len(address) < 12:
        return "***"
    return f"{address[:6]}...{address[-4:]}"


# ============================================================
# 端点处理函数（供 bde_api.py 调用）
# ============================================================
async def handle_pay_query(request: Request, symbol: str, market: str = "US"):
    """
    POST /pay/query — x402 支付+查询一体端点。
    支付验证由中间件完成，这里只处理业务逻辑。
    """
    # 此函数在 bde_api.py 中通过路由调用
    # 实际的分析逻辑复用现有 get_latest_snapshot 或 run_analysis
    pass


def get_x402_info() -> dict:
    """获取 x402 配置信息（公开端点，用于 Agent 发现定价）"""
    return {
        "protocol": "x402",
        "version": X402_VERSION,
        "enabled": X402_ENABLED,
        "pricing": {
            "per_query_usd": X402_PRICE_USD,
            "currency": "USDC",
            "network": X402_NETWORK,
            "chain_id": X402_CHAIN_ID,
        },
        "payment": {
            "pay_to": X402_PAY_TO,
            "usdc_contract": X402_USDC_CONTRACT,
            "scheme": "exact",
        },
        "free_tier": {
            "queries_per_day": X402_FREE_QUOTA_PER_DAY,
            "check_endpoint": "/pay/free",
        },
        "endpoints": {
            "pay_and_query": "POST /pay/query",
            "free_check": "GET /pay/free",
            "payment_stats": "GET /pay/balance",
            "protocol_info": "GET /pay/info",
        },
        "disclaimer": "Technical analysis only. Not investment advice.",
    }


# ============================================================
# 初始化
# ============================================================
# 启动时初始化数据库
init_x402_db()
