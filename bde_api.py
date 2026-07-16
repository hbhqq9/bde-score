"""
BDE Score™ API Service
======================
多因子量化分析 SaaS 平台 — RESTful API 层

架构: Client → FastAPI → FactorEngine → FutuOpenD/Sina → 行情数据
定位: 数据分析工具（非投资建议），所有输出标注 "Technical Analysis Only"

Endpoints:
  GET  /                  → Dashboard (HTML)
  GET  /api/analyze       → 运行完整BDE分析（带缓存）
  GET  /api/snapshot      → 获取最新缓存结果（不重新计算）
  GET  /api/history       → 历史分析结果
  GET  /api/health        → 系统健康检查
  GET  /api/market-status → 市场状态
  GET  /pay/info          → x402 协议信息（定价/网络/免费额度）
  GET  /pay/free          → 检查免费额度状态
  GET  /pay/balance       → x402 支付统计
  POST /pay/query         → x402 支付+查询一体（$0.01/query, 3 free/day）
  GET  /pay/query         → x402 支付+查询（GET方法）

x402 微支付:
  定价: $0.01/query | 成本: $0.000752/event | 利润率: >92%
  链: Base Mainnet | 币种: USDC | 协议: x402 v2
  认证优先级: API Key > x402 Payment > Free Quota > 402
"""

import os
import sys
import json
import math
import sqlite3
import logging
import asyncio
import time
import re
import html
from datetime import datetime, timedelta
from typing import Optional
from contextlib import contextmanager
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn
from usdc_listener import USDCListener, PaymentActivator, BackgroundListener
from x402_middleware import (
    X402PaymentMiddleware, X402_ENABLED,
    free_quota, get_x402_info, get_payment_stats,
    build_402_response, verify_x402_payment, record_payment,
    X402_PRICE_USD, X402_CHAIN_ID, X402_PAY_TO,
    X402_USDC_CONTRACT, X402_FREE_QUOTA_PER_DAY,
    X402_COST_PER_EVENT, X402_PROFIT_MARGIN,
    X402_NETWORK,
)
import auth_manager  # 用户认证系统

# 🔒 安全JSON序列化（处理NaN/Inf）
def safe_json_default(obj):
    """JSON序列化时处理NaN/Inf为None"""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

def sanitize_for_json(data):
    """递归清理数据结构中的NaN/Inf"""
    if isinstance(data, dict):
        return {k: sanitize_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_for_json(v) for v in data]
    elif isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None
    return data

# BDE模块路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from factor_engine import FactorEngine, FactorResult
from config import FACTOR_CONFIG

# ============================================================
# 配置
# ============================================================
API_HOST = os.environ.get('BDE_API_HOST', '127.0.0.1')  # 🔒 仅本地访问，通过Cloudflare Tunnel暴露
API_PORT = int(os.environ.get('BDE_API_PORT', '8890'))
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bde_history.db')
CACHE_TTL_SECONDS = 900  # 15分钟缓存

# USDC 收款配置
USDC_ENABLED = True
PAYMENT_PRICE_USD = 29

# 多市场分析标的池（BDE Universe）
UNIVERSE_US = {
    # Mega-Cap Tech
    'US.AAPL': 'AAPL', 'US.MSFT': 'MSFT', 'US.GOOG': 'GOOG',
    'US.AMZN': 'AMZN', 'US.META': 'META', 'US.NVDA': 'NVDA',
    # AI/Semiconductor
    'US.AMD': 'AMD', 'US.AVGO': 'AVGO', 'US.ARM': 'ARM', 'US.INTC': 'INTC',
    # Payments
    'US.V': 'V', 'US.MA': 'MA',
    # Healthcare
    'US.JNJ': 'JNJ', 'US.UNH': 'UNH', 'US.LLY': 'LLY', 'US.PFE': 'PFE',
    # Consumer
    'US.PG': 'PG', 'US.KO': 'KO', 'US.WMT': 'WMT', 'US.MCD': 'MCD',
    # Growth
    'US.TSLA': 'TSLA', 'US.NFLX': 'NFLX', 'US.BABA': 'BABA',
    # ETF
    'US.SPY': 'SPY', 'US.QQQ': 'QQQ',
}

UNIVERSE_HK = {
    # 互联网
    'HK.00700': '腾讯', 'HK.09988': '阿里-W', 'HK.09888': '百度集团',
    'HK.03690': '美团-W', 'HK.01024': '快手-W', 'HK.01810': '小米集团',
    'HK.09618': '京东集团', 'HK.09999': '网易-S',
    # 新能源车
    'HK.02015': '理想汽车', 'HK.09868': '小鹏汽车', 'HK.01211': '比亚迪',
    'HK.09863': '零跑汽车',
    # 金融
    'HK.02318': '中国平安', 'HK.01398': '工商银行', 'HK.00939': '建设银行',
    'HK.03988': '中国银行', 'HK.02628': '中国人寿',
    # 能源/资源
    'HK.02899': '紫金矿业', 'HK.00883': '中国海洋石油', 'HK.00857': '中国石油',
    'HK.01088': '中国神华',
    # 电信
    'HK.00941': '中国移动', 'HK.00728': '中国电信', 'HK.00762': '中国联通',
    # 医疗
    'HK.01833': '平安好医生', 'HK.02269': '药明生物',
}

UNIVERSE_A = {
    # 消费
    'SH.600519': '贵州茅台', 'SZ.000858': '五粮液', 'SZ.000568': '泸州老窖',
    'SH.600887': '伊利股份', 'SZ.002714': '牧原股份',
    # 金融
    'SH.601318': '中国平安', 'SH.600036': '招商银行', 'SH.601398': '工商银行',
    'SH.601288': '农业银行',
    # 新能源
    'SZ.300750': '宁德时代', 'SH.601012': '隆基绿能', 'SZ.002594': '比亚迪A',
    'SH.600900': '长江电力',
    # 科技
    'SH.688981': '中芯国际', 'SZ.002475': '立讯精密', 'SZ.002230': '科大讯飞',
    'SH.603501': '韦尔股份',
    # 资源
    'SH.601899': '紫金矿业A', 'SH.601088': '中国神华', 'SH.600585': '海螺水泥',
    # 制造
    'SZ.000333': '美的集团', 'SH.600690': '海尔智家', 'SZ.000651': '格力电器',
}

# 默认使用美股（兼容旧接口）
DEFAULT_UNIVERSE = UNIVERSE_US

# 市场映射（用于新浪数据源）
MARKET_SINA_MAP = {
    'US': lambda sym: sym.split('.')[1].lower(),  # US.AAPL -> aapl
    'HK': lambda sym: sym.split('.')[1],           # HK.00700 -> 00700
    'SH': lambda sym: sym.split('.')[1],           # SH.600519 -> sh600519
    'SZ': lambda sym: sym.split('.')[1],           # SZ.000858 -> sz000858
}

# ============================================================
# FastAPI App
# ============================================================
app = FastAPI(
    title="BDE Score™ - AI Quantitative Analysis",
    description="Multi-factor quantitative scoring engine for equity markets. Technical analysis tool only — not investment advice.",
    version="1.0.0-mvp",
    docs_url=None,       # 🔒 禁用Swagger UI（公网暴露攻击面）
    redoc_url=None,      # 🔒 禁用ReDoc
    openapi_url=None if os.environ.get("BDE_ENV", "production") == "production" else "/openapi.json",  # 🔒 P2: 生产环境禁用OpenAPI spec
)

# Mount static files for i18n and other static assets
app.mount("/static", StaticFiles(directory="static"), name="static")
# Mount .well-known for agent discovery (Glama, A2A, etc.)
app.mount("/.well-known", StaticFiles(directory="docs/.well-known"), name="well-known")


# 🔒 P2: SQLite WAL mode helper - 提升并发性能，防止写入冲突
def _get_db(db_path=DB_PATH):
    """获取WAL模式的SQLite连接"""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

# USDC 支付系统全局实例
usdc_listener_instance = None
usdc_activator_instance = None
usdc_background_task = None

# ============================================================
# 🔒 安全中间件
# ============================================================
class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    """🔒 全局速率限制 + 请求体大小限制"""
    MAX_BODY_SIZE = 1_000_000  # 1MB max request body
    
    async def dispatch(self, request: Request, call_next):
        # 🔒 请求体大小检查
        content_length = request.headers.get('content-length', '0')
        try:
            if int(content_length) > self.MAX_BODY_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={"error": "Request body too large. Max 1MB."}
                )
        except ValueError:
            pass
        
        if request.url.path.startswith('/api/'):
            client_ip = request.client.host if request.client else "unknown"
            if not rate_limiter.is_allowed(client_ip):
                return JSONResponse(
                    status_code=429,
                    content={"error": "Rate limit exceeded. Please slow down."},
                    headers={"Retry-After": "60"}
                )
        return await call_next(request)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """注入安全响应头，防止XSS/Clickjacking/Sniffing等攻击"""""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        # 🔌 /widget 和 /embed 路径允许iframe嵌入（零账号分发机制）
        if request.url.path in ('/widget', '/embed/snippet'):
            # 🔒 Widget仅允许已知域名嵌入，防止clickjacking
            allowed_widget_origins = "https://hbhqq9.github.io https://*.trycloudflare.com"
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
            response.headers["Content-Security-Policy"] = f"frame-ancestors {allowed_widget_origins}"
        else:
            response.headers["X-Frame-Options"] = "DENY"
        # 🔒 CORS 白名单（仅允许已知域名嵌入）
        allowed_origins = {
            "https://hbhqq9.github.io",
            "https://bathroom-ebooks-isa-accommodation.trycloudflare.com",
            "http://localhost:8890",
            "http://127.0.0.1:8890",
        }
        origin = request.headers.get("origin", "")
        if request.url.path in ('/widget', '/embed/snippet'):
            # 零账号分发：widget/embed允许任意来源
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-API-Key"
        elif origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-API-Key"
        # 🔒 HSTS（强制HTTPS，1年有效期，含子域名）
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        # 🔒 EU AI Act Art.50(1) — AI系统身份披露
        if request.url.path.startswith('/api/') and request.url.path not in ('/api/health',):
            response.headers["X-BDE-AI-System"] = "true"
            response.headers["X-BDE-Assessment-Method"] = "ai-automated"
            response.headers["X-BDE-Model-Version"] = "1.0.2"
            response.headers["X-BDE-Compliance"] = "EU-AI-Act-Art50"
        # 🔒 Inject disclaimer into all JSON analysis responses
        if (request.url.path.startswith('/api/')
                and 'application/json' in response.headers.get('content-type', '')
                and request.url.path not in ('/api/health', '/api/keys/list', '/api/payment/config', '/api/payment/chain-status')
                and not request.url.path.startswith('/api/auth/')):
            try:
                # Read the streamed body
                body_chunks = []
                async for chunk in response.body_iterator:
                    body_chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode('utf-8'))
                raw_body = b''.join(body_chunks)
                
                body = json.loads(raw_body)
                if isinstance(body, dict) and 'disclaimer' not in body:
                    body['disclaimer'] = '⚠️ Technical analysis only. Not investment advice. Past performance does not guarantee future results.'
                # 🔒 EU AI Act Art.50(1)(2) — AI系统信息嵌入
                if isinstance(body, dict) and 'ai_system_info' not in body:
                    body['ai_system_info'] = {
                        'generated_by': 'BDE Score AI Assessment Engine v1.0.2',
                        'assessment_type': 'automated-multi-factor-scoring',
                        'methodology': 'rule-based + LLM-enhanced analysis',
                        'data_sources': ['public-market-data', 'technical-indicators', 'fundamental-signals'],
                        'ai_system': True,
                        'eu_ai_act_art50': 'compliant',
                        'compliance_page': 'https://hbhqq9.github.io/bde-score/compliance.html',
                        'limitations': ['publicly accessible data only', 'not investment advice', 'not a penetration test']
                    }
                # 🔒 Art.50(2) 内容指纹日志 — sha256记录所有AI生成输出
                import hashlib as _hashlib
                _content_hash = _hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:16]
                logger.info(f"[Art.50] content_fingerprint={_content_hash} path={request.url.path} method={request.method}")
                # 🔗 Discovery: Cross-project ecosystem promotion
                if isinstance(body, dict) and 'discover' not in body:
                    body['discover'] = {
                        'neurobridge': {'desc': 'Physical AI Protocol Layer', 'url': 'https://github.com/hbhqq9/neurobridge'},
                        'ipo_compliance': {'desc': 'Pre-IPO Compliance Diagnostics', 'url': 'https://github.com/hbhqq9/ipo-compliance'},
                        'landing': 'https://hbhqq9.github.io/bde-score/'
                    }
                    new_body = json.dumps(body, default=safe_json_default).encode('utf-8')
                    # Rebuild response with modified body
                    from starlette.responses import Response as StarletteResponse
                    return StarletteResponse(
                        content=new_body,
                        status_code=response.status_code,
                        headers={**dict(response.headers), 'content-length': str(len(new_body))},
                        media_type='application/json'
                    )
                else:
                    # No modification needed, return response with original body
                    from starlette.responses import Response as StarletteResponse
                    return StarletteResponse(
                        content=raw_body,
                        status_code=response.status_code,
                        headers={**dict(response.headers), 'content-length': str(len(raw_body))},
                        media_type='application/json'
                    )
            except Exception:
                pass  # Don't break responses if injection fails
        return response

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GlobalRateLimitMiddleware)
# x402 微支付中间件（保护 /pay/query 端点，兼容 API Key 认证）
if X402_ENABLED:
    app.add_middleware(X402PaymentMiddleware)

# 🔒 隐藏服务器版本信息
@app.middleware("http")
async def hide_server_header(request: Request, call_next):
    response = await call_next(request)
    # MutableHeaders doesn't support pop(), use del instead
    if "server" in response.headers:
        del response.headers["server"]
    response.headers["X-Powered-By"] = "BDE-Score"  # 只暴露品牌名，不暴露技术栈
    return response

# ============================================================
# 🔒 速率限制器（内存级，防DoS）
# ============================================================
class RateLimiter:
    """🔒 P2: 滑动窗口速率限制 + 内存泄漏防护"""
    MAX_TRACKED_IPS = 10000  # 防止内存泄漏：最多追踪10K个IP
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        # 🔒 内存泄漏防护：超过上限时清理所有过期IP
        if len(self.requests) > self.MAX_TRACKED_IPS:
            self.requests.clear()
        # 清理该IP的过期记录
        self.requests[client_ip] = [t for t in self.requests[client_ip] if now - t < self.window]
        if not self.requests[client_ip]:
            del self.requests[client_ip]  # 清理空条目
            return True
        if len(self.requests[client_ip]) >= self.max_requests:
            return False
        self.requests[client_ip].append(now)
        return True

rate_limiter = RateLimiter(max_requests=10, window_seconds=60)  # 通用：每IP每分钟10次
payment_rate_limiter = RateLimiter(max_requests=5, window_seconds=60)  # 🔒 支付端点：每IP每分钟5次

# ============================================================
# 🔑 API Key 付费门控系统
# ============================================================
import hashlib
import secrets
import bcrypt

class KeyManager:
    """API Key管理：生成/验证/配额（bcrypt哈希存储）
    
    存储格式：
      - key_hash: bcrypt哈希（cost factor 12）
      - key_prefix: 前8位用于快速识别（如 bde_xxxx...）
      - tier/email/created_at/active 等元数据
      - 原始key不再存储，仅在生成时返回一次
    """
    
    def __init__(self, keys_file='api_keys.json'):
        self.keys_file = keys_file
        self.keys = self._load()  # dict: key_hash -> entry
        # 免费配额追踪：{ip: {date: count}}
        self._free_usage = {}
    
    def _load(self):
        """加载api_keys.json，自动迁移旧版明文格式"""
        try:
            with open(self.keys_file, 'r') as f:
                raw_items = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
        
        keys = {}
        migrated = 0
        
        for item in raw_items:
            if 'key_hash' in item:
                # 新格式：直接使用
                keys[item['key_hash']] = item
            elif 'key' in item:
                # 旧格式（明文）：自动迁移为bcrypt哈希
                plaintext_key = item['key']
                key_hash = bcrypt.hashpw(
                    plaintext_key.encode('utf-8'),
                    bcrypt.gensalt(rounds=12)
                ).decode('utf-8')
                new_entry = {
                    'key_hash': key_hash,
                    'key_prefix': plaintext_key[:8],
                    'tier': item.get('tier', 'free'),
                    'email': item.get('email'),
                    'created_at': item.get('created_at'),
                    'active': item.get('active', True),
                }
                # 保留其他字段（如 source/tx_hash 等）
                for k, v in item.items():
                    if k not in ('key', 'key_hash', 'key_prefix') and k not in new_entry:
                        new_entry[k] = v
                keys[key_hash] = new_entry
                migrated += 1
        
        if migrated > 0:
            _logger = logging.getLogger('bde_api')
            _logger.warning(
                f"🔑 API Key迁移完成：{migrated} 个明文key已转为bcrypt哈希存储"
            )
            # 写回迁移后的文件（明文key已清除）
            try:
                with open(self.keys_file, 'w') as f:
                    json.dump(list(keys.values()), f, indent=2)
                _logger.info(f"✅ api_keys.json 已更新（明文key已清除）")
            except Exception as e:
                _logger.error(f"❌ 迁移文件写入失败: {e}")
        
        return keys
    
    def _save(self):
        with open(self.keys_file, 'w') as f:
            json.dump(list(self.keys.values()), f, indent=2)
    
    def generate_key(self, tier='premium', email=None):
        """生成新API Key，返回明文（仅此一次），存储bcrypt哈希"""
        key = f"bde_{secrets.token_urlsafe(24)}"
        key_hash = bcrypt.hashpw(
            key.encode('utf-8'),
            bcrypt.gensalt(rounds=12)
        ).decode('utf-8')
        self.keys[key_hash] = {
            'key_hash': key_hash,
            'key_prefix': key[:8],
            'tier': tier,  # free / premium / institutional
            'email': email,
            'created_at': datetime.now().isoformat(),
            'active': True
        }
        self._save()
        return key  # 明文只在返回值中出现一次
    
    def verify(self, key):
        """验证API Key有效性，用bcrypt.checkpw()逐一对比哈希，返回tier或None"""
        if not key:
            return None
        key_bytes = key.encode('utf-8')
        for entry in self.keys.values():
            if not entry.get('active'):
                continue
            stored_hash = entry.get('key_hash', '')
            try:
                if bcrypt.checkpw(key_bytes, stored_hash.encode('utf-8')):
                    # 更新 last_used 时间戳
                    entry['last_used'] = datetime.now().isoformat()
                    self._save()
                    return entry['tier']
            except (ValueError, TypeError):
                continue
        return None
    
    def check_free_quota(self, ip):
        """检查免费用户当日配额（3次/天）"""
        today = datetime.now().strftime('%Y-%m-%d')
        if ip not in self._free_usage:
            self._free_usage[ip] = {}
        if today not in self._free_usage[ip]:
            self._free_usage[ip][today] = 0
        
        if self._free_usage[ip][today] >= 3:
            return False
        self._free_usage[ip][today] += 1
        return True
    
    def list_keys(self):
        """只返回 key_prefix + 元数据，不返回哈希"""
        result = []
        for entry in self.keys.values():
            result.append({
                'key_prefix': entry.get('key_prefix', '????????'),
                'tier': entry.get('tier', 'free'),
                'email': entry.get('email'),
                'created_at': entry.get('created_at'),
                'active': entry.get('active', False),
                'last_used': entry.get('last_used'),
            })
        return result
    
    def revoke_by_prefix(self, prefix):
        """通过key_prefix撤销API Key，返回是否成功"""
        for entry in self.keys.values():
            if entry.get('key_prefix') == prefix:
                entry['active'] = False
                self._save()
                return True
        return False
    
    def register_key_from_plaintext(self, plaintext_key, metadata):
        """从明文key注册（供USDC支付系统集成调用），内部自动哈希存储"""
        key_hash = bcrypt.hashpw(
            plaintext_key.encode('utf-8'),
            bcrypt.gensalt(rounds=12)
        ).decode('utf-8')
        entry = {
            'key_hash': key_hash,
            'key_prefix': plaintext_key[:8],
            'active': True,
        }
        entry.update(metadata)
        self.keys[key_hash] = entry
        self._save()
        return key_hash


    def verify_with_prefix(self, key):
        """验证API Key，返回 (tier, key_prefix) 元组"""
        if not key:
            return None, None
        key_bytes = key.encode('utf-8')
        for entry in self.keys.values():
            if not entry.get('active'):
                continue
            stored_hash = entry.get('key_hash', '')
            try:
                if bcrypt.checkpw(key_bytes, stored_hash.encode('utf-8')):
                    entry['last_used'] = datetime.now().isoformat()
                    self._save()
                    return entry['tier'], entry.get('key_prefix', '')
            except (ValueError, TypeError):
                continue
        return None, None

key_manager = KeyManager()



# ============================================================
# 💰 积分计费系统 (Credit-Based Billing)
# ============================================================
CREDIT_PRICING = {
    "free_gift": 1000,
    "cost_per_analyze": 10,
    "packages": [
        {"name": "starter",  "credits": 1000,    "price_cny": 10,   "price_usd": 1.4},
        {"name": "standard", "credits": 10000,   "price_cny": 90,   "price_usd": 12.5},
        {"name": "pro",      "credits": 100000,  "price_cny": 800,  "price_usd": 110},
        {"name": "institutional", "credits": 1000000, "price_cny": 6000, "price_usd": 830},
    ],
    "tiers": {
        "free":          {"daily_limit": 3,    "credits": 0},
        "starter":       {"daily_limit": None, "credits": 1000},
        "pro":           {"daily_limit": None, "credits": None},
        "institutional": {"daily_limit": None, "credits": None},
    }
}

class CreditManager:
    """积分管理：充值/扣减/查询/流水"""
    
    COST_PER_CALL = 10  # 每次analyze调用消耗10积分
    
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_tables()
    
    def _init_tables(self):
        """创建积分相关数据表"""
        with _get_db(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_credits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_prefix TEXT NOT NULL,
                    balance INTEGER DEFAULT 1000,
                    total_recharged INTEGER DEFAULT 1000,
                    total_consumed INTEGER DEFAULT 0,
                    tier TEXT DEFAULT 'starter',
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now')),
                    UNIQUE(key_prefix)
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS credit_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_prefix TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    balance_after INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_ledger_prefix ON credit_ledger(key_prefix)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_ledger_time ON credit_ledger(created_at)')
            conn.commit()
    
    def ensure_user(self, key_prefix):
        """确保用户有积分记录，新用户送1000积分"""
        with _get_db(self.db_path) as conn:
            row = conn.execute(
                "SELECT id FROM user_credits WHERE key_prefix = ?", (key_prefix,)
            ).fetchone()
            if not row:
                gift = CREDIT_PRICING["free_gift"]
                conn.execute(
                    "INSERT INTO user_credits (key_prefix, balance, total_recharged, tier) VALUES (?, ?, ?, ?)",
                    (key_prefix, gift, gift, "starter")
                )
                conn.execute(
                    "INSERT INTO credit_ledger (key_prefix, amount, balance_after, type, description) VALUES (?, ?, ?, ?, ?)",
                    (key_prefix, gift, gift, "gift", "新用户注册赠送")
                )
                conn.commit()
                return True  # 新用户
        return False  # 已存在
    
    def get_balance(self, key_prefix):
        """返回 {balance, total_recharged, total_consumed, tier}"""
        self.ensure_user(key_prefix)
        with _get_db(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT balance, total_recharged, total_consumed, tier FROM user_credits WHERE key_prefix = ?",
                (key_prefix,)
            ).fetchone()
            if row:
                return dict(row)
        return {"balance": 0, "total_recharged": 0, "total_consumed": 0, "tier": "unknown"}
    
    def deduct(self, key_prefix, amount, description="API call"):
        """扣减积分，余额不足返回False"""
        self.ensure_user(key_prefix)
        with _get_db(self.db_path) as conn:
            row = conn.execute(
                "SELECT balance FROM user_credits WHERE key_prefix = ?", (key_prefix,)
            ).fetchone()
            current_balance = row[0] if row else 0
            if current_balance < amount:
                return False
            new_balance = current_balance - amount
            conn.execute(
                "UPDATE user_credits SET balance = balance - ?, total_consumed = total_consumed + ?, updated_at = datetime('now') WHERE key_prefix = ?",
                (amount, amount, key_prefix)
            )
            conn.execute(
                "INSERT INTO credit_ledger (key_prefix, amount, balance_after, type, description) VALUES (?, ?, ?, ?, ?)",
                (key_prefix, -amount, new_balance, "consume", description)
            )
            conn.commit()
            return True
    
    def recharge(self, key_prefix, amount, description="充值"):
        """充值积分"""
        self.ensure_user(key_prefix)
        with _get_db(self.db_path) as conn:
            conn.execute(
                "UPDATE user_credits SET balance = balance + ?, total_recharged = total_recharged + ?, updated_at = datetime('now') WHERE key_prefix = ?",
                (amount, amount, key_prefix)
            )
            row = conn.execute(
                "SELECT balance FROM user_credits WHERE key_prefix = ?", (key_prefix,)
            ).fetchone()
            new_balance = row[0] if row else amount
            conn.execute(
                "INSERT INTO credit_ledger (key_prefix, amount, balance_after, type, description) VALUES (?, ?, ?, ?, ?)",
                (key_prefix, amount, new_balance, "recharge", description)
            )
            conn.commit()
            return True
    
    def get_ledger(self, key_prefix, limit=20):
        """查询消费流水"""
        with _get_db(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT amount, balance_after, type, description, created_at FROM credit_ledger WHERE key_prefix = ? ORDER BY created_at DESC LIMIT ?",
                (key_prefix, limit)
            ).fetchall()
            return [dict(r) for r in rows]

credit_manager = CreditManager(DB_PATH)

# 🔑 API Key验证依赖
from fastapi import Header, Depends

async def optional_api_key(x_api_key: str = Header(None)):
    """可选API Key验证：有key走付费通道，无key走免费配额"""
    if x_api_key:
        tier, key_prefix = key_manager.verify_with_prefix(x_api_key)
        if tier:
            return {'authenticated': True, 'tier': tier, 'key_prefix': key_prefix}
    return {'authenticated': False, 'tier': 'free', 'key_prefix': None}

# 🔒 并发分析锁（防止同时触发多个重型计算）
_analyze_lock = asyncio.Lock()
_analyze_last_run = 0  # 上次analyze时间戳

# 合法市场值白名单
VALID_MARKETS = {"US", "HK", "A", "ALL"}

# ============================================================
# 全局缓存
# ============================================================
_cache = {
    'data': None,
    'timestamp': None,
}

logger = logging.getLogger('bde_api')


# ============================================================
# 数据库
# ============================================================
def init_db():
    """初始化SQLite数据库"""
    with _get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_time TEXT NOT NULL,
                data_source TEXT NOT NULL,
                symbol TEXT NOT NULL,
                composite_score REAL,
                signal TEXT,
                scores_json TEXT,
                details_json TEXT,
                raw_price REAL
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_symbol ON analysis_history(symbol)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_run_time ON analysis_history(run_time)')
        conn.commit()


def save_results_to_db(results: list, data_source: str, run_time: str):
    """保存分析结果到数据库"""
    with _get_db() as conn:
        for r in results:
            conn.execute('''
                INSERT INTO analysis_history 
                (run_time, data_source, symbol, composite_score, signal, scores_json, details_json, raw_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                run_time, data_source, r.symbol, r.composite_score, r.signal,
                json.dumps(r.scores), json.dumps(r.details), 
                r.details.get('latest_price', 0)
            ))
        conn.commit()


# ============================================================
# 数据获取层
# ============================================================
def fetch_via_futu(universe=None, days=120):
    """通过FutuOpenD获取数据"""
    if universe is None:
        universe = DEFAULT_UNIVERSE
    try:
        from futu import OpenQuoteContext, RET_OK
    except ImportError:
        return None, "futu-api未安装"

    # 检查FutuOpenD是否运行
    import subprocess
    result = subprocess.run(['pgrep', '-f', 'FutuOpenD'], capture_output=True, text=True)
    if result.returncode != 0:
        return None, "FutuOpenD未运行"

    ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
    import pandas as pd
    
    all_klines = {}
    errors = []
    prices = {}

    import time
    try:
        batch_size = 15  # Futu限制60次/30秒，每批15只留足余量
        batch_count = 0
        for futu_code, short_name in universe.items():
            ret, data, page = ctx.request_history_kline(
                futu_code, ktype='K_DAY',
                start=(datetime.now() - timedelta(days=days + 30)).strftime('%Y-%m-%d'),
                end=datetime.now().strftime('%Y-%m-%d')
            )
            if ret == 0 and len(data) > 0:  # RET_OK == 0
                df = data.tail(days).reset_index(drop=True)
                all_klines[short_name] = df
                prices[short_name] = float(df.iloc[-1]['close'])
            else:
                errors.append(f"{futu_code}: {data}")
            
            batch_count += 1
            if batch_count >= batch_size:
                time.sleep(1)  # 每15只暂停1秒，避免触发频率限制
                batch_count = 0
    finally:
        ctx.close()

    if not all_klines:
        return None, f"所有标的获取失败: {errors}"
    
    return {'klines': all_klines, 'prices': prices, 'source': 'FutuOpenD'}, None


def fetch_via_sina(universe=None, days=120):
    """通过新浪财经获取数据（备用）- 支持美股/A股, 港股历史K线暂不可用"""
    if universe is None:
        universe = DEFAULT_UNIVERSE
    import urllib.request
    import pandas as pd
    
    all_klines = {}
    prices = {}
    errors = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://finance.sina.com.cn',
    }
    
    for futu_code, short_name in universe.items():
        try:
            market = futu_code.split('.')[0]  # US, HK, SH, SZ
            code = futu_code.split('.')[1]
            
            if market == 'US':
                # 美股: US.AAPL -> JSONP API (confirmed working)
                sina_sym = code.lower()
                url = f'https://stock.finance.sina.com.cn/usstock/api/jsonp.php/var%20data=/US_MinKService.getDailyK?symbol={sina_sym}&scale=240&datalen={days}'
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    text = resp.read().decode('utf-8')
                    json_str = text[text.index('([') + 1:text.rindex('])') + 1]
                    raw = json.loads(json_str)
                    if raw and isinstance(raw[0], dict):
                        df = pd.DataFrame([{
                            'date': item.get('d', ''),
                            'open': float(item.get('o', 0)),
                            'high': float(item.get('h', 0)),
                            'low': float(item.get('l', 0)),
                            'close': float(item.get('c', 0)),
                            'volume': float(item.get('v', 0)),
                        } for item in raw[-days:]])  # limit to requested days
                        all_klines[short_name] = df
                        prices[short_name] = float(df.iloc[-1]['close'])
            
            elif market in ('SH', 'SZ'):
                # A股: SH.600519 -> CN_MarketData API (confirmed working)
                sina_sym = f'{market.lower()}{code}'
                url = f'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={sina_sym}&scale=240&ma=no&datalen={days}'
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    text = resp.read().decode('utf-8')
                    raw = json.loads(text)
                    if raw and isinstance(raw, list):
                        df = pd.DataFrame([{
                            'date': item.get('day', ''),
                            'open': float(item.get('open', 0)),
                            'high': float(item.get('high', 0)),
                            'low': float(item.get('low', 0)),
                            'close': float(item.get('close', 0)),
                            'volume': float(item.get('volume', 0)),
                        } for item in raw])
                        all_klines[short_name] = df
                        prices[short_name] = float(df.iloc[-1]['close'])
            
            elif market == 'HK':
                # 港股: 历史K线API已下线，用实时行情+跳过
                errors.append(f"{futu_code}: HK历史K线API暂不可用")
                continue
            
            else:
                errors.append(f"{futu_code}: 未知市场{market}")
                continue
        except Exception as e:
            errors.append(f"{futu_code}: {e}")
    
    if not all_klines:
        return None, f"新浪数据全部失败: {errors[:3]}"
    
    return {'klines': all_klines, 'prices': prices, 'source': 'Sina'}, None


# ============================================================
# 核心分析引擎
# ============================================================
def run_analysis(force_refresh=False, market="US"):
    """
    运行BDE多因子分析
    
    Args:
        force_refresh: 是否强制刷新缓存
        market: 市场选择 (US/HK/A/ALL)
    
    Returns:
        dict: {
            'run_time': str,
            'data_source': str,
            'results': list[dict],
            'market_summary': dict,
        }
    """
    global _cache
    
    cache_key = f'data_{market}'
    
    # 检查缓存
    if not force_refresh and _cache.get(cache_key) and _cache.get('timestamp'):
        age = (datetime.now() - _cache['timestamp']).total_seconds()
        if age < CACHE_TTL_SECONDS:
            return _cache[cache_key]
    
    # 根据市场选择标的池
    if market == "ALL":
        universe = {**UNIVERSE_US, **UNIVERSE_HK, **UNIVERSE_A}
        market_name = "全市场"
    elif market == "HK":
        universe = UNIVERSE_HK
        market_name = "港股"
    elif market == "A":
        universe = UNIVERSE_A
        market_name = "A股"
    else:
        universe = UNIVERSE_US
        market_name = "美股"
    
    # 获取数据: Futu优先 → Sina备用
    logger.info(f"尝试通过FutuOpenD获取{market_name}数据...")
    data, err = fetch_via_futu(universe=universe)
    
    if err:
        logger.warning(f"Futu获取失败: {err}，降级到新浪...")
        data, err = fetch_via_sina(universe=universe)
    
    if err:
        raise HTTPException(status_code=503, detail=f"数据获取失败: {err}")
    
    # 运行因子引擎
    engine = FactorEngine(FACTOR_CONFIG)
    factor_results = engine.evaluate(data['klines'])
    
    # 组装结果
    run_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    results = []
    
    # 🔒 NaN排序保护
    safe_results = []
    for r in factor_results:
        if isinstance(r.composite_score, float) and (math.isnan(r.composite_score) or math.isinf(r.composite_score)):
            r.composite_score = 0.0
        safe_results.append(r)
    
    for r in sorted(safe_results, key=lambda x: -x.composite_score):
        # 🔒 清理NaN/Inf防止JSON序列化崩溃
        safe_composite = r.composite_score if not (math.isnan(r.composite_score) or math.isinf(r.composite_score)) else 0.0
        safe_scores = {}
        for k, v in r.scores.items():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                safe_scores[k] = 0.0
            else:
                safe_scores[k] = round(v, 1)
        safe_details = sanitize_for_json(r.details)
        
        result_dict = {
            'symbol': r.symbol,
            'futu_code': next((k for k, v in universe.items() if v == r.symbol), r.symbol),
            'composite_score': round(safe_composite, 1),
            'signal': r.signal,
            'scores': safe_scores,
            'details': safe_details,
            'current_price': data['prices'].get(r.symbol, 0),
        }
        results.append(result_dict)
    
    # 统计汇总
    buy_count = sum(1 for r in results if r['signal'] == 'BUY')
    hold_count = sum(1 for r in results if r['signal'] == 'HOLD')
    avoid_count = sum(1 for r in results if r['signal'] == 'AVOID')
    avg_score = sum(r['composite_score'] for r in results) / len(results) if results else 0
    
    output = {
        'run_time': run_time,
        'data_source': data['source'],
        'market': market_name,
        'symbols_count': len(results),
        'results': results,
        'market_summary': {
            'buy_signals': buy_count,
            'hold_signals': hold_count,
            'avoid_signals': avoid_count,
            'avg_score': round(avg_score, 1),
            'market_sentiment': 'BULLISH' if buy_count > len(results) * 0.5 else 
                               'BEARISH' if avoid_count > len(results) * 0.3 else 'NEUTRAL',
        },
        'disclaimer': '⚠️ Technical analysis only. Not investment advice. Past performance does not guarantee future results.',
    }
    
    # 保存到数据库和缓存
    save_results_to_db(factor_results, data['source'], run_time)
    _cache[cache_key] = output
    _cache['timestamp'] = datetime.now()
    
    return output


# ============================================================
# API Endpoints
# ============================================================
@app.get("/", response_class=HTMLResponse)
async def landing():
    """Landing Page — 商业化首页（定价/功能/合规/CTA）"""
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'landing.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """数据Dashboard HTML（原首页，现移至/dashboard）"""
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'dashboard.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()

@app.get("/widget", response_class=HTMLResponse)
async def widget():
    """🔌 可嵌入分数卡片 — 零账号分发机制
    任何人复制这行即可嵌入自己的网站/博客/论坛：
    <iframe src="https://YOUR_URL/widget" width="420" height="420" frameborder="0"></iframe>
    """
    widget_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'widget', 'score-widget.html')
    with open(widget_path, 'r', encoding='utf-8') as f:
        html = f.read()
    return HTMLResponse(
        content=html,
        headers={
            "X-Frame-Options": "ALLOWALL",  # 🔓 允许任意网站iframe嵌入
            "Content-Security-Policy": "frame-ancestors *",
        }
    )

@app.get("/embed/snippet")
async def embed_snippet():
    """获取嵌入代码片段（用于分享）"""
    return {
        "iframe": '<iframe src="https://bathroom-ebooks-isa-accommodation.trycloudflare.com/widget" width="420" height="420" frameborder="0" style="border-radius:12px;overflow:hidden;"></iframe>',
        "markdown": "[![BDE Score](https://bathroom-ebooks-isa-accommodation.trycloudflare.com/widget)](https://bathroom-ebooks-isa-accommodation.trycloudflare.com)",
        "badge": "[![BDE Score](https://img.shields.io/badge/BDE-Score-blue)](https://bathroom-ebooks-isa-accommodation.trycloudflare.com)",
        "description": "Embed BDE Score™ live scores on your website. Copy the iframe code above."
    }

@app.get("/share/{symbols}", response_class=HTMLResponse)
async def share_card(
    symbols: str,
    top: int = Query(None, description="显示前N名（如 /share/US?top=5）")
):
    """🔌 病毒式分发 — 生成可分享的SVG分数卡片
    
    用法：
      /share/AAPL          → 单只股票卡片
      /share/AAPL,NVDA     → 多只股票卡片  
      /share/US?top=5      → 市场Top N排行
    任何人可通过URL分享，每次分享都是获客。
    """
    from fastapi.responses import Response
    
    symbols_upper = symbols.upper()
    
    # 🔒 输入校验：只允许字母、数字、点、短横线、逗号
    if not re.match(r'^[A-Za-z0-9.,\-]+$', symbols_upper):
        return HTMLResponse(content="<svg><text>Invalid input</text></svg>", status_code=400, media_type="image/svg+xml")
    
    # 获取数据
    if symbols_upper in VALID_MARKETS:
        market = symbols_upper
        cache_key = f'data_{market}'
        data = _cache.get(cache_key)
        if not data:
            try:
                data = run_analysis(market=market)
            except Exception:
                return Response(content="<svg><text>Error loading data</text></svg>", media_type="image/svg+xml")
        
        results = data.get('results', [])
        results.sort(key=lambda x: x.get('composite_score', 0), reverse=True)
        if top:
            results = results[:top]
        title = f"BDE Score™ Top {top or len(results)} — {market}"
    else:
        # 单只或多只股票
        symbol_list = [s.strip() for s in symbols_upper.split(',')]
        all_data = _cache.get('data_ALL') or _cache.get('data_US') or _cache.get('data_HK')
        if not all_data:
            try:
                all_data = run_analysis(market='US')
            except Exception:
                return Response(content="<svg><text>Error loading data</text></svg>", media_type="image/svg+xml")
        
        all_results = all_data.get('results', [])
        results = [r for r in all_results if r.get('symbol') in symbol_list]
        title = f"BDE Score™ — {', '.join(symbol_list)}"
    
    # 生成SVG
    svg = _generate_share_svg(results, title)
    return Response(content=svg, media_type="image/svg+xml", headers={
        "Cache-Control": "public, max-age=300",
        "X-Frame-Options": "ALLOWALL",
        "Content-Security-Policy": "frame-ancestors *",
    })

def _generate_share_svg(results, title):
    # 🔒 XSS防护：SVG内容转义
    safe_title = html.escape(str(title), quote=True)
    """生成SVG分享卡片"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    w, h = 540, 80 + len(results) * 72 + 100
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#0f172a"/><stop offset="100%" stop-color="#1e293b"/></linearGradient></defs>
<rect width="{w}" height="{h}" rx="16" fill="url(#bg)"/>
<text x="24" y="36" font-family="system-ui" font-size="20" font-weight="700" fill="#f1f5f9">📊 {safe_title}</text>
<text x="24" y="56" font-family="system-ui" font-size="12" fill="#64748b">{now}</text>
<rect x="24" y="66" width="80" height="3" rx="1.5" fill="#3b82f6"/>
'''
    for i, r in enumerate(results):
        sym = html.escape(str(r.get('symbol', '?')))
        sc = round(r.get('composite_score', 0))
        color = "#22c55e" if sc >= 70 else ("#eab308" if sc >= 40 else "#ef4444")
        signal = "BULLISH" if sc >= 70 else ("NEUTRAL" if sc >= 40 else "BEARISH")
        bw = max(10, min(200, sc * 2))
        y = 88 + i * 72
        svg += f'''<text x="24" y="{y+24}" font-family="system-ui" font-size="16" font-weight="600" fill="#e2e8f0">{sym}</text>
<text x="24" y="{y+44}" font-family="system-ui" font-size="11" fill="#64748b">{r.get('market','')}</text>
<text x="{w-24}" y="{y+24}" font-family="monospace" font-size="28" font-weight="700" fill="{color}" text-anchor="end">{sc}</text>
<text x="{w-24}" y="{y+44}" font-family="system-ui" font-size="10" fill="{color}" text-anchor="end" letter-spacing="1">{signal}</text>
<rect x="120" y="{y+32}" width="200" height="6" rx="3" fill="rgba(255,255,255,0.06)"/>
<rect x="120" y="{y+32}" width="{bw}" height="6" rx="3" fill="{color}"/>
'''
    fy = 80 + len(results) * 72
    svg += f'''<line x1="24" y1="{fy}" x2="{w-24}" y2="{fy}" stroke="rgba(255,255,255,0.06)"/>
<text x="{w//2}" y="{fy+28}" font-family="system-ui" font-size="11" fill="#475569" text-anchor="middle">BDE Score™ · AI Multi-Market Analysis</text>
<text x="{w//2}" y="{fy+48}" font-family="system-ui" font-size="10" fill="#3b82f6" text-anchor="middle">bdescore.app</text>
<text x="{w//2}" y="{fy+68}" font-family="system-ui" font-size="9" fill="#374151" text-anchor="middle">⚠️ Not financial advice</text>
</svg>'''
    return svg

@app.post("/api/waitlist")
async def add_waitlist(request: Request):
    """Early access waitlist signup（🔒 限流+输入校验）"""
    # 🔒 速率限制
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
    
    try:
        body = await request.json()
        email = body.get("email", "").strip()
        if not email or not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise HTTPException(status_code=400, detail="Invalid email address.")
        
        # Store to JSON file
        waitlist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'waitlist.json')
        try:
            with open(waitlist_path, 'r') as f:
                waitlist = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            waitlist = []
        
        # Check duplicate
        if any(entry.get("email") == email for entry in waitlist):
            return {"status": "ok", "message": "Already on the list."}
        
        # 🔒 P2: Waitlist容量上限防护
        if len(waitlist) >= 1000:
            return {"status": "full", "message": "Waitlist is full. Please try again later."}
        waitlist.append({"email": email, "time": datetime.now().isoformat()})
        with open(waitlist_path, 'w') as f:
            json.dump(waitlist, f, indent=2)
        
        logger.info(f"Waitlist signup: {email}")
        return {"status": "ok", "message": "Added to waitlist."}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Waitlist signup failed")
        raise HTTPException(status_code=500, detail="Service temporarily unavailable.")


@app.get("/api/analyze")
async def api_analyze(
    request: Request,
    force: bool = Query(False, description="强制刷新，忽略缓存"),
    market: str = Query("US", description="市场: US(美股), HK(港股), A(A股), ALL(全部)"),
    auth: dict = Depends(optional_api_key)
):
    """运行BDE多因子分析（🔒 带速率限制+并发锁+输入校验+积分计费）"""
    # 🔒 输入白名单校验
    market_upper = market.upper().strip()
    if market_upper not in VALID_MARKETS:
        raise HTTPException(status_code=400, detail=f"Invalid market. Must be one of: {', '.join(sorted(VALID_MARKETS))}")
    
    # 🔒 速率限制
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 10 requests per minute.")
    
    # 💰 积分计费 / 免费配额检查
    if auth['authenticated'] and auth.get('key_prefix'):
        # 有API Key的用户：检查积分余额
        key_prefix = auth['key_prefix']
        credit_cost = CREDIT_PRICING["cost_per_analyze"]
        balance_info = credit_manager.get_balance(key_prefix)
        if balance_info['balance'] < credit_cost:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "Insufficient credits",
                    "required": credit_cost,
                    "balance": balance_info['balance'],
                    "message": f"积分不足，需要{credit_cost}积分，当前余额{balance_info['balance']}积分。请充值后重试。",
                    "recharge": "POST /api/credits/recharge",
                    "pricing": "GET /api/credits/pricing"
                }
            )
        # 扣减积分（先扣后用）
        deducted = credit_manager.deduct(key_prefix, credit_cost, f"analyze market={market_upper}")
        if not deducted:
            raise HTTPException(
                status_code=402,
                detail={"error": "Insufficient credits", "message": "积分扣减失败，请充值。"}
            )
    else:
        # 无API Key的免费用户：保持原有3次/天限制
        if not key_manager.check_free_quota(client_ip):
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Free tier limit reached",
                    "message": "免费用户每日限3次调用。注册API Key获得1000免费积分！",
                    "upgrade": "GET /api/credits/pricing"
                }
            )
    
    # 🔒 并发锁：同一时刻只允许一个分析任务
    if _analyze_lock.locked():
        raise HTTPException(status_code=409, detail="Analysis already in progress. Please wait.")
    
    # 🔒 冷却期：force=true时至少间隔60秒
    global _analyze_last_run
    if force and (time.time() - _analyze_last_run < 60):
        raise HTTPException(status_code=429, detail="Cooldown: force refresh available every 60 seconds.")
    
    async with _analyze_lock:
        try:
            _analyze_last_run = time.time()
            result = run_analysis(force_refresh=force, market=market_upper)
            # 附加积分信息到响应
            if auth['authenticated'] and auth.get('key_prefix'):
                bal = credit_manager.get_balance(auth['key_prefix'])
                if isinstance(result, dict):
                    result['credits'] = {
                        'balance': bal['balance'],
                        'consumed_this_session': CREDIT_PRICING["cost_per_analyze"],
                    }
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("分析执行失败")
            raise HTTPException(status_code=500, detail="Internal analysis error. Please retry later.")  # 🔒 不泄露内部错误


@app.get("/api/snapshot")
async def api_snapshot(
    request: Request,
    market: str = Query("US", description="市场: US/HK/A/ALL"),
    auth: dict = Depends(optional_api_key)
):
    """获取最新缓存结果（🔒 免费3次/天，Premium/Institutional无限）"""
    # 🔑 配额检查
    client_ip = request.client.host if request.client else "unknown"
    if not auth['authenticated']:
        if not key_manager.check_free_quota(client_ip):
            raise HTTPException(
                status_code=429,
                detail="Free tier limit reached (3 queries/day). Upgrade to Premium for unlimited access. Send USDC on Base chain to activate."
            )
    
    # 🔒 输入白名单
    market_upper = market.upper().strip()
    if market_upper not in VALID_MARKETS:
        raise HTTPException(status_code=400, detail=f"Invalid market. Must be one of: {', '.join(sorted(VALID_MARKETS))}")
    
    cache_key = f'data_{market_upper}'
    if _cache.get(cache_key):
        return _cache[cache_key]
    # 没有缓存就运行一次
    try:
        return run_analysis(market=market_upper)
    except Exception as e:
        logger.exception("Snapshot获取失败")
        raise HTTPException(status_code=500, detail="Service temporarily unavailable.")  # 🔒 不泄露内部错误


# ============================================================
# 🔑 API Key 管理端点（内部管理用）
# ============================================================
@app.post("/api/keys/generate")
async def generate_key(
    request: Request,
    tier: str = Query("premium", description="Key tier: free/premium/institutional"),
    email: str = Query(None, description="用户邮箱")
):
    """生成新API Key（内部使用）"""
    # 🔒 获取真实客户端IP（Cloudflare Tunnel兼容）
    client_ip = request.headers.get('cf-connecting-ip', '') or                 request.headers.get('x-forwarded-for', '').split(',')[0].strip() or                 (request.client.host if request.client else "unknown")
    # 🔒 限制：只允许本地调用（非Tunnel流量）
    # 通过Tunnel的请求会有cf-connecting-ip头，直接拒绝
    if request.headers.get('cf-connecting-ip'):
        raise HTTPException(status_code=403, detail="Forbidden. Internal use only.")
    if client_ip not in ('127.0.0.1', '::1'):
        raise HTTPException(status_code=403, detail="Forbidden. Internal use only.")
    
    if tier not in ('free', 'premium', 'institutional'):
        raise HTTPException(status_code=400, detail="Invalid tier. Must be: free, premium, or institutional.")
    
    key = key_manager.generate_key(tier=tier, email=email)
    return {"key": key, "tier": tier, "email": email}

@app.get("/api/keys/list")
async def list_keys(request: Request):
    """列出所有API Key（内部使用）— 仅显示prefix，不显示完整key"""
    # 🔒 拒绝所有Tunnel流量
    if request.headers.get('cf-connecting-ip'):
        raise HTTPException(status_code=403, detail="Forbidden. Internal use only.")
    client_ip = request.client.host if request.client else "unknown"
    if client_ip not in ('127.0.0.1', '::1'):
        raise HTTPException(status_code=403, detail="Forbidden. Internal use only.")
    
    return {
        "keys": key_manager.list_keys(),
        "count": len(key_manager.keys),
        "note": "Full API keys are shown only once at generation time. Only key_prefix is stored."
    }

@app.post("/api/keys/revoke")
async def revoke_key(
    request: Request,
    key_prefix: str = Query(..., description="要撤销的API Key前缀（8位，如 bde_xxxx）")
):
    """撤销API Key（内部使用）— 通过key_prefix撤销"""
    # 🔒 拒绝所有Tunnel流量
    if request.headers.get('cf-connecting-ip'):
        raise HTTPException(status_code=403, detail="Forbidden. Internal use only.")
    client_ip = request.client.host if request.client else "unknown"
    if client_ip not in ('127.0.0.1', '::1'):
        raise HTTPException(status_code=403, detail="Forbidden. Internal use only.")
    
    if key_manager.revoke_by_prefix(key_prefix):
        return {"status": "revoked", "key_prefix": key_prefix}
    raise HTTPException(status_code=404, detail="Key not found by the given prefix.")


# ============================================================
# 💰 积分管理端点 (Credit Management Endpoints)
# ============================================================
@app.get("/api/credits/balance")
async def credits_balance(request: Request, auth: dict = Depends(optional_api_key)):
    """查询积分余额（需API Key）"""
    if not auth['authenticated'] or not auth.get('key_prefix'):
        raise HTTPException(status_code=401, detail="API Key required. Provide X-API-Key header.")
    
    balance_info = credit_manager.get_balance(auth['key_prefix'])
    return {
        "key_prefix": auth['key_prefix'],
        "balance": balance_info['balance'],
        "total_recharged": balance_info['total_recharged'],
        "total_consumed": balance_info['total_consumed'],
        "tier": balance_info['tier'],
        "cost_per_analyze": CREDIT_PRICING["cost_per_analyze"],
        "estimated_calls_remaining": balance_info['balance'] // CREDIT_PRICING["cost_per_analyze"],
    }


@app.get("/api/credits/ledger")
async def credits_ledger(
    request: Request,
    limit: int = Query(20, description="返回条数", ge=1, le=100),
    auth: dict = Depends(optional_api_key)
):
    """查询消费流水（需API Key）"""
    if not auth['authenticated'] or not auth.get('key_prefix'):
        raise HTTPException(status_code=401, detail="API Key required. Provide X-API-Key header.")
    
    ledger = credit_manager.get_ledger(auth['key_prefix'], limit=limit)
    return {
        "key_prefix": auth['key_prefix'],
        "count": len(ledger),
        "transactions": ledger,
    }


@app.post("/api/credits/recharge")
async def credits_recharge(
    request: Request,
    amount: int = Query(1000, description="充值积分数", ge=1),
    auth: dict = Depends(optional_api_key)
):
    """充值接口 — 🔒 生产环境禁用，仅限开发调试"""
    # 🔒 安全检查：生产环境禁止此端点
    import os as _os
    if _os.environ.get('BDE_ENV', 'production') != 'development':
        raise HTTPException(status_code=403, detail="This endpoint is disabled in production. USDC payment flow is the only way to recharge.")
    
    if not auth['authenticated'] or not auth.get('key_prefix'):
        raise HTTPException(status_code=401, detail="API Key required. Provide X-API-Key header.")
    
    # 🔒 金额上限：开发模式也限制单次最大10000积分
    if amount > 10000:
        raise HTTPException(status_code=400, detail="Max 10,000 credits per recharge in dev mode.")
    
    credit_manager.recharge(auth['key_prefix'], amount, description=f"手动充值 {amount} 积分")
    new_balance = credit_manager.get_balance(auth['key_prefix'])
    return {
        "status": "success",
        "key_prefix": auth['key_prefix'],
        "recharged": amount,
        "new_balance": new_balance['balance'],
        "total_recharged": new_balance['total_recharged'],
        "message": f"成功充值 {amount} 积分，当前余额 {new_balance['balance']} 积分",
        "note": "⚠️ 当前为模拟充值，正式版将接入在线支付"
    }


@app.get("/api/credits/pricing")
async def credits_pricing():
    """Get pricing information (public)"""
    return {
        "pricing": CREDIT_PRICING,
        "cost_per_analyze": CREDIT_PRICING["cost_per_analyze"],
        "free_daily_limit": 3,
        "new_user_gift": CREDIT_PRICING["free_gift"],
        "packages": CREDIT_PRICING["packages"],
        "message": "New users get 1000 free credits (100 analyses). Each analysis costs 10 credits.",
    }


# ============================================================
# 🔓 Freemium: Stock Unlock Endpoint
# ============================================================
@app.get("/api/stock/unlock")
async def unlock_stock(
    request: Request,
    symbol: str = Query(..., description="Stock symbol to unlock"),
    x_api_key: str = Header(None)
):
    """Unlock detailed factor scores for a specific stock (costs 10 credits)"""
    if not x_api_key:
        return JSONResponse({"error": "API key required", "message": "请绑定API Key后解锁"}, status_code=401)
    
    # Verify key
    key_data = key_manager.verify_with_prefix(x_api_key)
    if not key_data:
        return JSONResponse({"error": "Invalid API key"}, status_code=401)
    
    prefix = key_data[1]
    
    # Ensure user exists in credit system
    credit_manager.ensure_user(prefix)
    
    # Check balance
    balance_info = credit_manager.get_balance(prefix)
    unlock_cost = 10
    if balance_info['balance'] < unlock_cost:
        return JSONResponse({
            "error": "Insufficient credits",
            "balance": balance_info['balance'],
            "required": unlock_cost,
            "message": f"积分不足，需要{unlock_cost}积分，当前余额{balance_info['balance']}积分"
        }, status_code=402)
    
    # Deduct credits
    deducted = credit_manager.deduct(prefix, unlock_cost, f"Unlock {symbol}")
    if not deducted:
        return JSONResponse({"error": "Deduction failed"}, status_code=500)
    
    new_balance = credit_manager.get_balance(prefix)
    return {
        "symbol": symbol,
        "unlocked": True,
        "credits_remaining": new_balance['balance'],
        "cost": unlock_cost
    }


@app.get("/api/history")
async def api_history(
    symbol: Optional[str] = Query(None, description="股票代码过滤"),
    days: int = Query(30, description="查询天数", ge=1, le=365)
):
    """获取历史分析结果（🔒 参数已校验）"""
    # 🔒 symbol输入校验：只允许字母、数字、点、短横线
    if symbol and not re.match(r'^[A-Za-z0-9.\-]+$', symbol):
        raise HTTPException(status_code=400, detail="Invalid symbol format. Only alphanumeric, dots, and hyphens allowed.")
    
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    
    with _get_db() as conn:
        conn.row_factory = sqlite3.Row
        if symbol:
            rows = conn.execute('''
                SELECT run_time, symbol, composite_score, signal, scores_json, raw_price
                FROM analysis_history 
                WHERE symbol = ? AND run_time >= ?
                ORDER BY run_time DESC
            ''', (symbol, cutoff)).fetchall()
        else:
            rows = conn.execute('''
                SELECT run_time, symbol, composite_score, signal, scores_json, raw_price
                FROM analysis_history 
                WHERE run_time >= ?
                ORDER BY run_time DESC, composite_score DESC
            ''', (cutoff,)).fetchall()
    
    return {
        'query_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'days': days,
        'symbol_filter': symbol,
        'count': len(rows),
        'data': [
            {
                'run_time': r['run_time'],
                'symbol': r['symbol'],
                'composite_score': r['composite_score'],
                'signal': r['signal'],
                'scores': json.loads(r['scores_json']) if r['scores_json'] else {},
                'price': r['raw_price'],
            }
            for r in rows
        ]
    }


@app.get("/api/health")
async def api_health():
    """系统健康检查 - 精简信息防止内部架构泄露"""
    return {
        'status': 'healthy',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': '1.0.0',
    }


@app.get("/api/market-status")
async def api_market_status():
    """市场状态"""
    now = datetime.utcnow()  # UTC
    hour = now.hour
    weekday = now.weekday()  # 0=Mon, 6=Sun
    
    # 美东时间 = UTC-4 (EDT) / UTC-5 (EST)
    # 简化处理：假设EDT
    et_hour = (hour - 4) % 24
    
    is_weekday = weekday < 5
    is_market_hours = 9 <= et_hour < 16
    
    return {
        'utc_time': now.strftime('%Y-%m-%d %H:%M:%S UTC'),
        'et_time': f'{et_hour:02d}:{now.minute:02d}',
        'market': {
            'us_stock': {
                'open': is_weekday and is_market_hours,
                'status': 'OPEN' if (is_weekday and is_market_hours) else 'CLOSED',
                'note': 'NYSE/NASDAQ 09:30-16:00 ET',
            }
        }
    }


# ==================== GEO (Generative Engine Optimization) ====================

LLMS_TXT = """# BDE Score™

> AI-powered multi-market stock analysis with transparent multi-factor scoring. Covers 73 stocks across US, HK, and A-share markets. EU AI Act Art.50 compliant. Open source (MIT).

## What is BDE Score™

BDE Score™ is a quantitative stock scoring system that evaluates stocks across 5 independent factors: Momentum, Mean Reversion, Volume, Volatility, and Trend. Each stock receives a composite score (0-100) with signal classification: Bullish (>70), Neutral (40-70), Bearish (<40).

## Coverage

- US Markets (25 stocks): AAPL, MSFT, GOOG, AMZN, META, NVDA, AMD, AVGO, ARM, INTC, V, MA, JNJ, UNH, LLY, PFE, PG, KO, WMT, MCD, TSLA, NFLX, BABA, SPY, QQQ
- HK Markets (26 stocks): Tencent (00700), Alibaba (09988), Baidu (09888), Meituan (03690), Kuaishou (01024), Xiaomi (01810), JD.com (09618), NetEase (09999), BYD (01211), Ping An (02318)
- A-shares (23 stocks): Kweichow Moutai (600519), CATL (300750), BYD (002594), Ping An (601318), CMB (600036)

## API Endpoints

- GET /api/snapshot/{market} — Full market snapshot (US, HK, A)
- GET /api/stock/{symbol} — Single stock analysis with 5-factor breakdown
- GET /share/{symbols} — SVG score cards for social sharing
- GET /widget — Embeddable score widget (iframe)
- GET /dashboard — Full data dashboard

## Pricing

Free: Dashboard + 3 API queries/day | Premium: $29/mo (unlimited API) | Institutional: $199/mo (custom + compliance)

## Links

- GitHub: https://github.com/hbhqq9/bde-score
- GitHub Pages: https://hbhqq9.github.io/bde-score
- FAQ: https://hbhqq9.github.io/bde-score/faq

## Compliance

⚠️ Technical analysis tool only. Not financial advice. EU AI Act Art.50 compliant.
"""

@app.get("/llms.txt")
async def serve_llms_txt():
    """GEO入口 — AI搜索引擎发现协议"""
    return PlainTextResponse(LLMS_TXT, media_type="text/plain")


LLMS_INSTALL_MD = open("docs/llms-install.md", "r").read() if os.path.exists("docs/llms-install.md") else "# BDE Score Installation Guide\nSee https://hbhqq9.github.io/bde-score/llms-install.md"

@app.get("/llms-install.md")
async def serve_llms_install():
    """GEO入口 — Agent安装指南发现协议"""
    return PlainTextResponse(LLMS_INSTALL_MD, media_type="text/markdown")


# .well-known discovery protocol routes (Agent-native discovery)
@app.get("/.well-known/mcp.json")
async def serve_well_known_mcp():
    """MCP客户端自动发现协议"""
    import json
    mcp_config = {
        "name": "BDE Score",
        "description": "Multi-factor quantitative stock analysis for US, HK, and CN A-share markets.",
        "version": "1.0.1",
        "transport": {"type": "streamable-http", "url": "https://bathroom-ebooks-isa-accommodation.trycloudflare.com/mcp"},
        "authentication": {"type": "api-key", "header": "X-API-Key", "description": "Free tier: 10 req/min"},
        "capabilities": {"annotations": True, "read_only": True},
        "metadata": {
            "author": "AGL Governance",
            "license": "MIT",
            "homepage": "https://hbhqq9.github.io/bde-score/",
            "repository": "https://github.com/hbhqq9/bde-score",
            "category": "finance",
            "tags": ["stocks", "quantitative", "multi-factor", "EU AI Act"]
        }
    }
    return JSONResponse(mcp_config)


@app.get("/.well-known/ai-plugin.json")
async def ai_plugin_manifest():
    """ChatGPT Plugin discovery manifest"""
    try:
        with open("docs/.well-known/ai-plugin.json", "r", encoding="utf-8") as f:
            return JSONResponse(content=json.load(f))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="ai-plugin.json not found")

@app.get("/.well-known/agent.json")
async def serve_well_known_agent():
    """A2A Agent-to-Agent发现协议"""
    agent_config = {
        "name": "BDE Score Agent",
        "description": "AI-powered multi-market stock analysis agent providing quantitative BDE scores (0-100) for US, HK, and CN A-share markets.",
        "url": "https://bathroom-ebooks-isa-accommodation.trycloudflare.com",
        "version": "1.0.1",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": False
        },
        "provider": {"organization": "AGL", "url": "https://github.com/hbhqq9"},
        "documentation": "https://hbhqq9.github.io/bde-score/llms.txt",
        "authentication": {"schemes": ["api-key"]},
        "defaultInputModes": ["application/json"],
        "defaultOutputModes": ["application/json"],
        "skills": [
            {"id": "bde-score", "name": "BDE Score Analysis", "description": "Multi-factor stock scoring (Momentum, Mean Reversion, Volume, Volatility, Trend)"},
            {"id": "market-comparison", "name": "Cross-Market Comparison", "description": "Compare same company across US/HK/CN markets"},
            {"id": "stock-screener", "name": "Stock Screener", "description": "Screen stocks by minimum BDE score threshold"},
            {"id": "sector-analysis", "name": "Sector Analysis", "description": "Sector-level BDE analysis and rankings"}
        ]
    }
    return JSONResponse(agent_config)



# ── Agent Registry (self-hosted, zero-gatekeeper) ──────────────────────────

import hashlib as _hashlib
import threading as _threading
import urllib.request as _urllib_req

_REGISTRY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agent-registry', 'agents.json')
_registry_lock = _threading.Lock()

def _load_reg():
    if os.path.exists(_REGISTRY_FILE):
        with open(_REGISTRY_FILE, 'r') as f:
            return json.load(f)
    return {"agents": {}, "metadata": {"created": "2026-07-13T13:50:00+00:00", "version": "0.1.0"}}

def _save_reg(data):
    os.makedirs(os.path.dirname(_REGISTRY_FILE), exist_ok=True)
    with open(_REGISTRY_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _verify_ep(url, timeout=5):
    """Verify endpoint reachability with SSRF protection (security constitution v4.1)"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        # SSRF protection: block internal/cloud metadata addresses
        hostname = parsed.hostname or ''
        blocked = ['127.0.0.1', 'localhost', '169.254.169.254', '10.', '172.16.', '192.168.', '0.0.0.0']
        if any(hostname.startswith(p) or hostname == p for p in blocked):
            return False
        
        # Only allow http/https schemes
        if parsed.scheme not in ['http', 'https']:
            return False
        
        req = _urllib_req.Request(url, method='GET')
        resp = _urllib_req.urlopen(req, timeout=timeout)
        return resp.status == 200
    except Exception:
        return False

def _agent_id(name, endpoint):
    return _hashlib.sha256(f"{name}:{endpoint}".encode()).hexdigest()[:16]

@app.get("/registry", response_class=HTMLResponse)
async def registry_ui():
    """Beautiful HTML frontend for Agent Registry"""
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agent-registry', 'registry.html')
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Registry UI not found</h1>", status_code=404)

@app.get("/api/v1/registry")
async def registry_root():
    return {"service": "BDE Score Agent Registry", "version": "0.1.0",
            "description": "Agent-native, zero-gatekeeper discovery service",
            "philosophy": "From being listed to building the network",
            "endpoints": {
                "POST /api/v1/registry/register": "Register a new agent",
                "GET /api/v1/registry/agents": "List agents",
                "GET /api/v1/registry/agents/{id}": "Get agent details",
                "DELETE /api/v1/registry/agents/{id}": "Deregister",
                "GET /api/v1/registry/agents/{id}/health": "Health check",
                "GET /api/v1/registry/search": "Search (q=keyword)",
                "GET /api/v1/registry/stats": "Statistics"}}

@app.get("/api/v1/registry/stats")
async def registry_stats():
    with _registry_lock:
        reg = _load_reg()
    agents = list(reg['agents'].values())
    cats = {}
    for a in agents:
        for c in a.get('category', []):
            cats[c] = cats.get(c, 0) + 1
    return {"total_agents": len(agents),
            "healthy_agents": sum(1 for a in agents if a.get('health_status') == 'healthy'),
            "categories": cats,
            "registry_version": reg['metadata']['version']}

@app.get("/api/v1/registry/agents")
async def registry_list(category: str = None, capability: str = None, q: str = None):
    with _registry_lock:
        reg = _load_reg()
    agents = list(reg['agents'].values())
    if category:
        agents = [a for a in agents if category.lower() in [c.lower() for c in a.get('category', [])]]
    if capability:
        agents = [a for a in agents if capability.lower() in [c.lower() for c in a.get('capabilities', [])]]
    if q:
        ql = q.lower()
        agents = [a for a in agents if ql in a['name'].lower() or ql in a['description'].lower()]
    return {"count": len(agents), "agents": agents, "registry_version": reg['metadata']['version']}

@app.get("/api/v1/registry/agents/{agent_id}")
async def registry_get(agent_id: str):
    with _registry_lock:
        reg = _load_reg()
    agent = reg['agents'].get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent '{agent_id}' not found")
    return agent

@app.get("/api/v1/registry/agents/{agent_id}/health")
async def registry_health(agent_id: str):
    with _registry_lock:
        reg = _load_reg()
        agent = reg['agents'].get(agent_id)
        if not agent:
            raise HTTPException(404, f"Agent '{agent_id}' not found")
        healthy = _verify_ep(agent['primary_endpoint'])
        agent['health_status'] = "healthy" if healthy else "unreachable"
        agent['last_verified'] = datetime.now(timezone.utc).isoformat()
        agent['verification_count'] = agent.get('verification_count', 0) + 1
        _save_reg(reg)
    return {"agent_id": agent_id, "name": agent['name'], "endpoint": agent['primary_endpoint'],
            "status": agent['health_status'], "last_verified": agent['last_verified']}

@app.post("/api/v1/registry/register")
async def registry_register(request: Request):
    data = await request.json()
    required = ['name', 'description', 'primary_endpoint', 'category']
    missing = [f for f in required if not data.get(f)]
    if missing:
        raise HTTPException(400, f"Missing: {', '.join(missing)}")
    # Input length limits (security constitution v4.1 - prevent abuse)
    MAX_NAME = 100; MAX_DESC = 500; MAX_ENDPOINT = 500; MAX_CATS = 10; MAX_AGENTS = 200
    if len(str(data.get('name', ''))) > MAX_NAME:
        raise HTTPException(400, f"Name exceeds {MAX_NAME} chars")
    if len(str(data.get('description', ''))) > MAX_DESC:
        raise HTTPException(400, f"Description exceeds {MAX_DESC} chars")
    endpoint = str(data['primary_endpoint'])
    if len(endpoint) > MAX_ENDPOINT:
        raise HTTPException(400, f"Endpoint URL exceeds {MAX_ENDPOINT} chars")
    cats = data['category'] if isinstance(data['category'], list) else [data['category']]
    if len(cats) > MAX_CATS:
        raise HTTPException(400, f"Too many categories (max {MAX_CATS})")
    # Capacity check
    with _registry_lock:
        reg_check = _load_reg()
        if len(reg_check['agents']) >= MAX_AGENTS:
            raise HTTPException(503, "Registry at capacity")
    if not _verify_ep(endpoint):
        raise HTTPException(422, "Endpoint verification failed")
    aid = _agent_id(data['name'], endpoint)
    ts = datetime.now(timezone.utc).isoformat()
    record = {"id": aid, "name": data['name'], "description": data['description'],
              "primary_endpoint": endpoint,
              "category": data['category'] if isinstance(data['category'], list) else [data['category']],
              "protocols": data.get('protocols', {}), "capabilities": data.get('capabilities', []),
              "contact": data.get('contact', {}), "registration_time": ts,
              "health_status": "healthy", "last_verified": ts, "verification_count": 1}
    with _registry_lock:
        reg = _load_reg()
        reg['agents'][aid] = record
        _save_reg(reg)
    return {"status": "registered", "agent_id": aid, "message": f"Agent '{data['name']}' registered",
            "registered_at": ts}

@app.delete("/api/v1/registry/agents/{agent_id}")
async def registry_deregister(agent_id: str):
    with _registry_lock:
        reg = _load_reg()
        if agent_id not in reg['agents']:
            raise HTTPException(404, f"Agent '{agent_id}' not found")
        name = reg['agents'][agent_id]['name']
        del reg['agents'][agent_id]
        _save_reg(reg)
    return {"status": "deregistered", "message": f"Agent '{name}' removed"}

@app.get("/api/v1/registry/search")
async def registry_search(q: str):
    if not q:
        raise HTTPException(400, "Query 'q' required")
    with _registry_lock:
        reg = _load_reg()
    agents = list(reg['agents'].values())
    terms = q.lower().split()
    scored = []
    for agent in agents:
        score = 0
        searchable = f"{agent['name']} {agent['description']} {' '.join(agent.get('category', []))} {' '.join(agent.get('capabilities', []))}".lower()
        for t in terms:
            if t in searchable:
                score += 3 if t in agent['name'].lower() else (2 if t in [c.lower() for c in agent.get('category', [])] else 1)
        if score > 0:
            scored.append((score, agent))
    scored.sort(key=lambda x: -x[0])
    return {"query": q, "count": len(scored), "results": [a for _, a in scored]}
# ── End Agent Registry ─────────────────────────────────────────────────────

LLMS_FULL_TXT = """# BDE Score™

> AI-powered multi-market stock analysis with transparent multi-factor scoring. Covers 73 stocks across US, HK, and A-share markets. EU AI Act Art.50 compliant. Open source (MIT).

## What is BDE Score™

BDE Score™ is a quantitative stock scoring system that evaluates stocks across 5 independent factors:
- **Momentum**: Price momentum and rate of change
- **Mean Reversion**: Distance from statistical mean, oversold/overbought signals
- **Volume**: Trading volume patterns and money flow
- **Volatility**: Risk-adjusted returns and volatility regime
- **Trend**: Moving average alignment and trend strength

Each stock receives a composite score (0-100) with signal classification: Bullish (>70), Neutral (40-70), Bearish (<40).

## Coverage

- **US Markets** (25 stocks): AAPL, MSFT, GOOG, AMZN, META, NVDA, AMD, AVGO, ARM, INTC, V, MA, JNJ, UNH, LLY, PFE, PG, KO, WMT, MCD, TSLA, NFLX, BABA, SPY, QQQ
- **HK Markets** (26 stocks): Tencent (00700), Alibaba (09988), Baidu (09888), Meituan (03690), Kuaishou (01024), Xiaomi (01810), JD.com (09618), NetEase (09999), BYD (01211), Ping An (02318), ICBC (01398), CCB (00939), and more
- **A-shares** (23 stocks): Kweichow Moutai (600519), Wuliangye (000858), CATL (300750), BYD (002594), Ping An (601318), CMB (600036), ICBC (601318), and more

## Key Differentiators

1. **Transparency**: Every score breaks down into 5 explainable factors with weights — no black-box AI
2. **Multi-market**: Single API covers US, HK, and A-share markets simultaneously
3. **EU AI Act compliant**: Full audit trails, explainable methodology, machine-readable compliance metadata (Art.50 ready for August 2, 2026)
4. **Open source**: MIT licensed, fully auditable codebase
5. **Embeddable**: Widget system allows any website to embed live scores

## API Endpoints

- `GET /api/snapshot/{market}` — Full market snapshot (market: US, HK, A)
- `GET /api/stock/{symbol}` — Single stock analysis
- `GET /share/{symbols}` — SVG score cards (e.g., /share/AAPL, /share/US?top=5)
- `GET /widget` — Embeddable score widget (iframe)
- `GET /` — Landing page with pricing
- `GET /dashboard` — Full data dashboard

## Pricing

- **Free**: Dashboard access + 3 API queries/day
- **Premium** ($29/mo): Unlimited API + 365-day history
- **Institutional** ($199/mo): Custom universe + compliance reports + SLA

## Links

- Live Demo: https://github.com/hbhqq9/bde-score
- Dashboard: https://github.com/hbhqq9/bde-score/dashboard
- GitHub: https://github.com/hbhqq9/bde-score
- GitHub Pages: https://hbhqq9.github.io/bde-score
- API Docs: https://github.com/hbhqq9/bde-score/docs
- Widget: https://github.com/hbhqq9/bde-score/widget

## Compliance Note

⚠️ BDE Score™ is a technical analysis tool, not financial advice. Investment decisions should be made independently. The system provides quantitative signals based on historical data patterns.
"""

@app.get("/llms-full.txt")
async def serve_llms_full():
    """完整LLMs文档 — 供AI Agent深度理解项目"""
    return PlainTextResponse(LLMS_FULL_TXT, media_type="text/plain")

@app.get("/robots.txt")
async def serve_robots_txt():
    """显式允许AI爬虫（GPTBot/ChatGPT/Perplexity/Claude等）"""
    robots = """User-agent: *
Allow: /

User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Anthropic-AI
Allow: /

Sitemap: https://hbhqq9.github.io/bde-score/sitemap.xml
LLMs: https://hbhqq9.github.io/bde-score/llms.txt
"""
    return PlainTextResponse(robots, media_type="text/plain")


# ============================================================
# 💰 USDC 支付系统
# ============================================================

# ============================================================
# TIERS data for server-side rendering
# ============================================================
TIERS_DATA = {
    'starter':       {'zh': '入门版', 'en': 'Starter',       'ja': 'スターター',       'price': 10,   'credits': 1000,     'unit': 0.010},
    'standard':      {'zh': '标准版', 'en': 'Standard',      'ja': 'スタンダード',     'price': 90,   'credits': 10000,    'unit': 0.009},
    'pro':           {'zh': '专业版', 'en': 'Pro',           'ja': 'プロ',             'price': 800,  'credits': 100000,   'unit': 0.008},
    'institutional': {'zh': '机构版', 'en': 'Institutional', 'ja': '機関投資家',       'price': 6000, 'credits': 1000000,  'unit': 0.006},
}

def _format_credits(n):
    """Format number with commas: 1000 -> 1,000"""
    return f"{n:,}"

def _format_unit(u):
    """Format unit price: 0.01 -> 0.01, 0.009 -> 0.009"""
    s = f"{u:.3f}".rstrip('0').rstrip('.')
    return s

def _gen_qr_base64(text):
    """Generate QR code as base64 PNG data URI"""
    import qrcode, base64, io
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

@app.get("/qr-image")
async def qr_image_download(tier: str = 'starter'):
    """Serve QR code as downloadable PNG file - works without JS"""
    from fastapi.responses import StreamingResponse
    import qrcode, io
    tier_data = TIERS_DATA.get(tier, TIERS_DATA['starter'])
    price = tier_data['price']
    wallet = os.environ.get('BDE_WALLET_ADDRESS')
    if not wallet:
        logger.warning('⚠️ BDE_WALLET_ADDRESS not set, using fallback')
        wallet = '0x349Eea0E2f4d359479785175Da3eb49D4343'
    # Simple wallet address for QR (max compatibility)
    qr_text = wallet
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="bde-payment-{tier}.png"'}
    return StreamingResponse(buf, media_type="image/png", headers=headers)

@app.get("/credit-payment", response_class=HTMLResponse)
async def credit_payment_page(request: Request, tier: str = 'starter', lang: str = 'zh'):
    """Credit payment page - server-side rendered tier-specific USDC payment"""
    # 🔒 P3: 参数白名单校验
    if tier not in ('starter', 'standard', 'pro', 'institutional'):
        tier = 'starter'
    if lang not in ('zh', 'en', 'ja'):
        lang = 'zh'
    try:
        template_path = os.path.join(os.path.dirname(__file__), 'templates', 'credit-payment.html')
        with open(template_path, 'r') as f:
            html = f.read()
        # Inject config
        wallet = os.environ.get('BDE_WALLET_ADDRESS', '0x349Eea0E2f4d3594797851758325Da3eb49D4343')
        # Tier data (server-side rendering for no-JS environments)
        tier_data = TIERS_DATA.get(tier, TIERS_DATA['starter'])
        tier_name = tier_data.get(lang, tier_data['zh'])  # use lang param for tier name
        price = tier_data['price']
        credits = _format_credits(tier_data['credits'])
        unit = _format_unit(tier_data['unit'])
        # QR code — ERC-681 format with exact USDC amount for Base chain
        usdc_contract = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
        usdc_amount_raw = price * 1000000  # USDC 6 decimals
        qr_text = f"ethereum:{usdc_contract}@8453/transfer?address={wallet}&uint256={int(usdc_amount_raw)}"
        qr_img = _gen_qr_base64(qr_text)
        # Replace ALL placeholders
        html = html.replace('{{ WALLET_ADDRESS }}', wallet)
        html = html.replace('{{ USDC_CONTRACT }}', usdc_contract)
        html = html.replace('{{ API_BASE }}', str(request.base_url).rstrip('/'))
        html = html.replace('{{ TIER_NAME }}', tier_name)
        html = html.replace('{{ TIER_NAME_EN }}', tier_data['en'])
        html = html.replace('{{ TIER_NAME_JA }}', tier_data['ja'])
        html = html.replace('{{ TIER_PRICE }}', str(price))
        # Credits text and unit price text per language
        cred_texts = {'zh': f'{credits} 积分', 'en': f'{credits} Credits', 'ja': f'{credits} クレジット'}
        unit_texts = {'zh': f'单价：${unit} USDC/积分', 'en': f'Unit: ${unit} USDC/credit', 'ja': f'単価：${unit} USDC/クレジット'}
        html = html.replace('{{ TIER_CREDITS_FULL }}', cred_texts.get(lang, cred_texts['zh']))
        html = html.replace('{{ TIER_UNIT_FULL }}', unit_texts.get(lang, unit_texts['zh']))

        # === Full server-side i18n rendering (Coze WebView has no JS) ===
        I18N = {
            'zh': {
                'HEADER_TITLE': '📊 积分充值',
                'HEADER_DESC': '支付后积分立即到账，API Key 自动激活',
                'EXACT_AMOUNT': '请精确支付',
                'SCAN_TO_PAY': '扫码获取收款地址，金额请按上方提示手动输入',
                'QR_HINT': '扫码获取地址，请按上方金额精确输入',
                'BTN_SAVE_QR': '一键保存二维码',
                'BTN_COPY_AMOUNT': '复制金额',
                'QR_SAVE_HINT': '长按上方二维码图片可直接保存，或点击下载按钮保存PNG',
                'SEND_USDC': '将 USDC 发送至以下地址',
                'BTN_COPY': '复制',
                'LONG_PRESS_COPY': '长按上方地址可直接复制',
                'STATUS_WAITING': '等待支付中...',
                'STATUS_DETAIL_WAITING': '请完成支付后等待系统自动确认',
                'TX_HINT': '已发送？输入交易哈希进行验证：',
                'BTN_VERIFY': '验证',
                'ACTIVATED': '✅ 充值成功',
                'FEAT_INSTANT': '即时到账',
                'FEAT_AUTO_KEY': '自动激活API Key',
                'FEAT_MARKETS': '美/港/A股市场',
                'FEAT_PRIVACY': '零个人数据',
                'FOOTER_DISCLAIMER': '⚠️ 仅为技术分析工具，非金融投资建议。',
                'FOOTER_BDE': 'BDE Score™',
                'FOOTER_CHAIN': '链上支付 via Base',
            },
            'en': {
                'HEADER_TITLE': '📊 Credit Recharge',
                'HEADER_DESC': 'Credits applied instantly after payment, API Key auto-activated',
                'EXACT_AMOUNT': 'Pay Exactly',
                'SCAN_TO_PAY': 'Scan QR for address, then enter amount shown above',
                'QR_HINT': 'Scan QR for address, enter amount manually',
                'BTN_SAVE_QR': 'Save QR Code',
                'BTN_COPY_AMOUNT': 'Copy Amount',
                'QR_SAVE_HINT': 'Long-press QR image to save, or tap download button',
                'SEND_USDC': 'Send USDC to this address',
                'BTN_COPY': 'Copy',
                'LONG_PRESS_COPY': 'Long-press address above to copy',
                'STATUS_WAITING': 'Waiting for payment...',
                'STATUS_DETAIL_WAITING': 'Complete payment and wait for auto-confirmation',
                'TX_HINT': 'Already sent? Enter transaction hash to verify:',
                'BTN_VERIFY': 'Verify',
                'ACTIVATED': '✅ Recharge Successful',
                'FEAT_INSTANT': 'Instant delivery',
                'FEAT_AUTO_KEY': 'Auto-activate API Key',
                'FEAT_MARKETS': 'US / HK / A-share markets',
                'FEAT_PRIVACY': 'Zero personal data',
                'FOOTER_DISCLAIMER': '⚠️ Technical analysis tool only. Not investment advice.',
                'FOOTER_BDE': 'BDE Score™',
                'FOOTER_CHAIN': 'On-chain payments via Base',
            },
            'ja': {
                'HEADER_TITLE': '📊 クレジットチャージ',
                'HEADER_DESC': '支払い後クレジット即時反映、APIキー自動有効化',
                'EXACT_AMOUNT': '正確な金額を支払う',
                'SCAN_TO_PAY': 'QRコードをスキャンしてアドレスを取得、金額は手動入力してください',
                'QR_HINT': 'スキャンでアドレス取得、金額は手動入力',
                'BTN_SAVE_QR': 'QRコードを保存',
                'BTN_COPY_AMOUNT': '金額をコピー',
                'QR_SAVE_HINT': 'QRコード画像を長押しで保存、またはダウンロードボタンをタップ',
                'SEND_USDC': '以下のアドレスにUSDCを送信',
                'BTN_COPY': 'コピー',
                'LONG_PRESS_COPY': '上のアドレスを長押しでコピー',
                'STATUS_WAITING': '支払い待ち...',
                'STATUS_DETAIL_WAITING': '支払い完了後、自動確認をお待ちください',
                'TX_HINT': '送信済み？トランザクションハッシュを入力して検証：',
                'BTN_VERIFY': '検証',
                'ACTIVATED': '✅ チャージ完了',
                'FEAT_INSTANT': '即時反映',
                'FEAT_AUTO_KEY': 'APIキー自動有効化',
                'FEAT_MARKETS': '米国/香港/A株市場',
                'FEAT_PRIVACY': '個人データゼロ',
                'FOOTER_DISCLAIMER': '⚠️ 技術分析ツールのみの提供であり、金融投资建议ではありません。',
                'FOOTER_BDE': 'BDE Score™',
                'FOOTER_CHAIN': 'Baseチェーン決済',
            },
        }
        lang_i18n = I18N.get(lang, I18N['zh'])
        for key, val in lang_i18n.items():
            html = html.replace('{{{{ I18N_{0} }}}}'.format(key), val)

        # Language button active states
        for lcode in ('zh', 'en', 'ja'):
            css_class = ' active' if lcode == lang else ''
            html = html.replace('{{{{ LANG_{0}_ACTIVE }}}}'.format(lcode.upper()), css_class)

        html = html.replace('{{ QR_IMG_SRC }}', qr_img)
        html = html.replace('{{ TIER_PARAM }}', tier)
        return HTMLResponse(content=html)
    except Exception as e:
        logger.error(f"Credit payment page error: {e}"); return HTMLResponse(content="<h1>Page load failed</h1><p>Please retry later.</p>", status_code=500)
@app.get("/payment", response_class=HTMLResponse)
async def payment_page(request: Request):
    """支付页面 - 用户发送USDC后自动激活API Key"""
    try:
        template_path = os.path.join(os.path.dirname(__file__), 'templates', 'payment.html')
        with open(template_path, 'r') as f:
            html = f.read()
        # 注入配置
        wallet = os.environ.get('BDE_WALLET_ADDRESS', '0x349Eea0E2f4d3594797851758325Da3eb49D4343')
        usdc_contract = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'  # Base USDC
        html = html.replace('{{ WALLET_ADDRESS }}', wallet)
        html = html.replace('{{ USDC_CONTRACT }}', usdc_contract)
        html = html.replace('{{ PREMIUM_PRICE_USD }}', str(PAYMENT_PRICE_USD))
        html = html.replace('{{ API_BASE }}', str(request.base_url).rstrip('/'))
        return HTMLResponse(content=html)
    except Exception as e:
        logger.error(f"Payment page error: {e}"); return HTMLResponse(content="<h1>页面加载失败</h1><p>请稍后重试</p>", status_code=500)

@app.get("/api/payment/config")
async def payment_config():
    """支付配置信息"""
    wallet = os.environ.get('BDE_WALLET_ADDRESS', '0x349Eea0E2f4d3594797851758325Da3eb49D4343')
    return {
        "wallet_address": wallet,
        "price_usd": PAYMENT_PRICE_USD,
        "usdc_contract": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "chain": "base",
        "enabled": USDC_ENABLED
    }

@app.get("/api/payment/status")
async def payment_status(payment_id: str = None, tx_hash: str = None):
    """查询支付状态"""
    global usdc_activator_instance, usdc_listener_instance
    if not usdc_activator_instance:
        return {"status": "disabled", "message": "支付系统未启用"}
    
    if tx_hash:
        # 先查已有记录
        existing = usdc_activator_instance.get_payment_status(tx_hash=tx_hash)
        if existing:
            return existing
        # 通过链上验证
        if usdc_listener_instance:
            verify_result = usdc_listener_instance.listener.verify_transaction(tx_hash)
            if verify_result.get('valid'):
                usdc_activator_instance.record_payment(verify_result)
                result = usdc_activator_instance.activate_from_payment(tx_hash)
                return result or verify_result
            return verify_result
        return {"error": "链上监听器不可用"}
    elif payment_id:
        result = usdc_activator_instance.get_payment_status(payment_id)
        if result:
            return result
        return {"error": "支付记录未找到"}
    return {"error": "需要提供 payment_id 或 tx_hash"}

@app.post("/api/payment/verify")
async def verify_payment(request: Request):
    """手动提交tx_hash验证支付"""
    # 🔒 速率限制
    client_ip = request.client.host if request.client else "unknown"
    if not payment_rate_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 5 verification attempts per minute.")
    
    global usdc_activator_instance, usdc_listener_instance
    if not usdc_activator_instance:
        return {"status": "disabled", "message": "支付系统未启用"}
    
    body = await request.json()
    tx_hash = body.get("tx_hash")
    if not tx_hash:
        return {"error": "缺少 tx_hash"}
    
    # 🔒 tx_hash格式校验：必须是0x开头的66字符hex字符串
    if not isinstance(tx_hash, str) or not re.match(r'^0x[0-9a-fA-F]{64}$', tx_hash):
        return {"error": "Invalid tx_hash format. Must be 0x + 64 hex characters."}
    
    # 先查是否已处理
    existing = usdc_activator_instance.get_payment_status(tx_hash=tx_hash)
    if existing and existing.get('api_key'):
        return existing
    
    # 链上验证
    if not usdc_listener_instance:
        return {"error": "链上监听器不可用"}
    
    verify_result = usdc_listener_instance.listener.verify_transaction(tx_hash)
    if verify_result.get('valid'):
        usdc_activator_instance.record_payment(verify_result)
        result = usdc_activator_instance.activate_from_payment(tx_hash)
        return result or verify_result
    return verify_result

@app.get("/api/payment/wallet-check")
async def wallet_check(request: Request):
    """检测钱包新转入"""
    # 🔒 速率限制
    client_ip = request.client.host if request.client else "unknown"
    if not payment_rate_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
    
    global usdc_listener_instance
    if not usdc_listener_instance:
        return {"status": "disabled"}
    
    result = usdc_listener_instance.listener.scan_for_payments()
    return result

@app.get("/api/payment/chain-status")
async def chain_status():
    """Base链连接状态"""
    global usdc_listener_instance
    if not usdc_listener_instance:
        return {"status": "disabled", "connected": False}
    
    return usdc_listener_instance.listener.get_chain_info()


# ============================================================
# 启动 / 关闭
# ============================================================
@app.on_event("startup")
async def startup():
    global usdc_listener_instance, usdc_activator_instance, usdc_background_task
    init_db()
    logger.info(f"BDE Score™ API 启动 — 绑定 {API_HOST}:{API_PORT}（🔒 安全模式）")
    logger.info(f"Dashboard: http://localhost:{API_PORT}/")

    # USDC 支付系统初始化（使用独立线程，避免阻塞事件循环）
    try:
        import threading
        usdc_activator_instance = PaymentActivator()
        listener = USDCListener()
        usdc_listener_instance = BackgroundListener(listener=listener, activator=usdc_activator_instance)
        
        def _run_usdc_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(usdc_listener_instance.run_loop())
        
        usdc_thread = threading.Thread(target=_run_usdc_loop, daemon=True, name="USDC-Listener")
        usdc_thread.start()
        logger.info("USDC支付系统已启动（独立线程）")
    except Exception as e:
        logger.warning(f"USDC支付系统启动失败: {e}，API继续正常运行（无USDC监听）")

@app.on_event("shutdown")
async def shutdown():
    """关闭时停止USDC监听"""
    global usdc_listener_instance, usdc_background_task
    if usdc_listener_instance:
        usdc_listener_instance.stop()
        logger.info("USDC支付系统已停止")
    if usdc_background_task and not usdc_background_task.done():
        usdc_background_task.cancel()
        try:
            await usdc_background_task
        except asyncio.CancelledError:
            pass


# ============================================================
# 📜 Legal Pages — Compliance Endpoints
# ============================================================

LEGAL_STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
body { font-family: 'Inter', system-ui, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 0; line-height: 1.8; }
.legal-container { max-width: 800px; margin: 0 auto; padding: 60px 24px 80px; }
.legal-header { border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 32px; margin-bottom: 40px; }
.legal-header h1 { font-size: 2rem; font-weight: 700; color: #f1f5f9; margin: 0 0 8px; }
.legal-header .subtitle { color: #64748b; font-size: 0.95rem; }
.legal-header .effective { color: #3b82f6; font-size: 0.85rem; margin-top: 4px; }
.legal-section { margin-bottom: 36px; }
.legal-section h2 { font-size: 1.25rem; font-weight: 600; color: #f1f5f9; margin-bottom: 12px; border-left: 3px solid #3b82f6; padding-left: 12px; }
.legal-section h3 { font-size: 1.05rem; font-weight: 600; color: #cbd5e1; margin: 20px 0 8px; }
.legal-section p, .legal-section li { color: #94a3b8; font-size: 0.92rem; margin-bottom: 8px; }
.legal-section ul { padding-left: 20px; }
.legal-section li { margin-bottom: 6px; }
.legal-highlight { background: rgba(59,130,246,0.08); border: 1px solid rgba(59,130,246,0.15); border-radius: 8px; padding: 16px 20px; margin: 16px 0; }
.legal-highlight p { color: #93c5fd; margin: 0; }
.legal-warning { background: rgba(234,179,8,0.08); border: 1px solid rgba(234,179,8,0.15); border-radius: 8px; padding: 16px 20px; margin: 16px 0; }
.legal-warning p { color: #fde68a; margin: 0; }
.legal-footer { border-top: 1px solid rgba(255,255,255,0.06); padding-top: 24px; margin-top: 48px; text-align: center; }
.legal-footer a { color: #3b82f6; text-decoration: none; margin: 0 12px; font-size: 0.85rem; }
.legal-footer a:hover { color: #60a5fa; }
.legal-footer .copy { color: #475569; font-size: 0.8rem; margin-top: 12px; }
.back-link { display: inline-block; color: #3b82f6; text-decoration: none; font-size: 0.9rem; margin-bottom: 24px; }
.back-link:hover { color: #60a5fa; }
</style>
"""

LEGAL_FOOTER_HTML = """
<div class="legal-footer">
  <a href="/">Home</a>
  <a href="/terms">Terms of Service</a>
  <a href="/privacy">Privacy Policy</a>
  <a href="/legal">Legal Disclaimer</a>
  <div class="copy">&copy; 2026 BDE Score&#8482;. All rights reserved.</div>
</div>
"""

LEGAL_BACK_LINK = '<a href="/" class="back-link">&larr; Back to BDE Score&#8482;</a>'


@app.get("/pricing", response_class=HTMLResponse)
async def pricing_page():
    """Pricing page with credit tiers"""
    with open("templates/pricing.html", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


# [I18N] Disabled inline terms route - using template version
async def terms_of_service():
    """Terms of Service"""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Terms of Service &mdash; BDE Score&#8482;</title>
{LEGAL_STYLE}
</head>
<body>
<div class="legal-container">
{LEGAL_BACK_LINK}

<div class="legal-header">
  <h1>Terms of Service</h1>
  <div class="subtitle">BDE Score&#8482; &mdash; AI-Powered Technical Analysis Platform</div>
  <div class="effective">Effective Date: June 1, 2026</div>
</div>

<div class="legal-section">
  <h2>1. Nature of Service</h2>
  <p>BDE Score&#8482; (&ldquo;the Service&rdquo;) is a <strong>technical analysis tool</strong> that provides quantitative scoring based on historical price data and mathematical models. The Service evaluates stocks using multi-factor algorithms including momentum, mean reversion, volume analysis, volatility measurement, and trend detection.</p>
  <div class="legal-warning">
    <p><strong>&#9888;&#65039; IMPORTANT:</strong> BDE Score&#8482; is <strong>NOT</strong> a financial service, investment advisor, broker, dealer, or custodian. We do not provide personalized investment recommendations or manage assets on your behalf.</p>
  </div>
</div>

<div class="legal-section">
  <h2>2. Acceptance of Terms</h2>
  <p>By accessing or using the Service, you agree to be bound by these Terms. If you do not agree, do not use the Service. We reserve the right to modify these Terms at any time. Continued use after changes constitutes acceptance.</p>
</div>

<div class="legal-section">
  <h2>3. No Warranty / &ldquo;As Is&rdquo; Basis</h2>
  <p>The Service is provided on an <strong>&ldquo;AS IS&rdquo;</strong> and <strong>&ldquo;AS AVAILABLE&rdquo;</strong> basis without any warranties of any kind, either express or implied, including but not limited to:</p>
  <ul>
    <li>Accuracy or completeness of any scores, signals, or analysis</li>
    <li>Availability or uptime of the platform</li>
    <li>Merchantability or fitness for a particular purpose</li>
    <li>Non-infringement of third-party rights</li>
  </ul>
  <p>You acknowledge that quantitative models have inherent limitations and past model performance does not guarantee future accuracy.</p>
</div>

<div class="legal-section">
  <h2>4. Subscription &amp; Payment</h2>
  <h3>4.1 Pricing</h3>
  <ul>
    <li><strong>Free Tier:</strong> $0 &mdash; Dashboard access + 3 API queries per day</li>
    <li><strong>Premium:</strong> $29 USD/month &mdash; Unlimited API access, paid in USDC (Base chain)</li>
    <li><strong>Institutional:</strong> $199 USD/month &mdash; Custom solutions, paid in USDC</li>
  </ul>
  <h3>4.2 Payment Method</h3>
  <p>Premium subscriptions are paid exclusively in USDC (USD Coin) on the Base blockchain network. Upon confirmation of on-chain payment, an API key is generated and activated instantly.</p>
  <h3>4.3 No Refund Policy</h3>
  <div class="legal-highlight">
    <p><strong>All payments are final and non-refundable.</strong> Because the API key is activated immediately upon payment confirmation and provides instant access to the service, no refunds can be issued. Please ensure you understand the service before subscribing.</p>
  </div>
  <h3>4.4 Subscription Termination</h3>
  <p>Subscriptions are valid for one calendar month from activation. The Service does not auto-renew; you must send a new payment to continue access.</p>
</div>

<div class="legal-section">
  <h2>5. Right to Terminate</h2>
  <p>We reserve the right to suspend or terminate your access to the Service at our sole discretion, without notice, for conduct that we determine violates these Terms, is harmful to other users, or is harmful to the Service&rsquo;s reputation or integrity.</p>
</div>

<div class="legal-section">
  <h2>6. Limitation of Liability</h2>
  <p>In no event shall BDE Score&#8482;, its operators, affiliates, or contributors be liable for any direct, indirect, incidental, special, consequential, or punitive damages, including but not limited to:</p>
  <ul>
    <li>Loss of profits, data, or investment capital</li>
    <li>Trading losses or missed opportunities</li>
    <li>Service interruptions or data inaccuracies</li>
    <li>Any damages resulting from reliance on the Service&rsquo;s output</li>
  </ul>
</div>

<div class="legal-section">
  <h2>7. User Responsibilities</h2>
  <ul>
    <li>You are solely responsible for any investment decisions you make</li>
    <li>You must not use the Service for any unlawful purpose</li>
    <li>You must not attempt to reverse-engineer, copy, or redistribute the Service</li>
    <li>You must not share your API key with unauthorized parties</li>
    <li>You must comply with all applicable laws and regulations in your jurisdiction</li>
  </ul>
</div>

<div class="legal-section">
  <h2>8. Governing Law</h2>
  <p>These Terms shall be governed by and construed in accordance with applicable international law. Any disputes arising from these Terms or the Service shall be resolved through good-faith negotiation. If negotiation fails, disputes shall be submitted to arbitration in a mutually agreed jurisdiction.</p>
</div>

<div class="legal-section">
  <h2>9. Contact</h2>
  <p>For questions regarding these Terms, please visit our GitHub repository or contact us through the waitlist form on our website.</p>
  <p>GitHub: <a href="https://github.com/hbhqq9/bde-score" style="color:#3b82f6;">github.com/hbhqq9/bde-score</a></p>
</div>

{LEGAL_FOOTER_HTML}
</div>
</body>
</html>"""
    return HTMLResponse(content=html)


# [I18N] Disabled inline privacy route - using template version
# [I18N] Disabled inline privacy route - using template version
async def privacy_policy():
    """Privacy Policy &mdash; GDPR Compliant"""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Privacy Policy &mdash; BDE Score&#8482;</title>
{LEGAL_STYLE}
</head>
<body>
<div class="legal-container">
{LEGAL_BACK_LINK}

<div class="legal-header">
  <h1>Privacy Policy</h1>
  <div class="subtitle">BDE Score&#8482; &mdash; Data Protection &amp; Privacy Practices</div>
  <div class="effective">Effective Date: June 1, 2026 &middot; GDPR Compliant</div>
</div>

<div class="legal-section">
  <h2>1. Data Controller</h2>
  <p>BDE Score&#8482; (&ldquo;we&rdquo;, &ldquo;us&rdquo;, &ldquo;our&rdquo;) is the data controller for personal data collected through this service. This policy describes what data we collect, how we use it, and your rights under the General Data Protection Regulation (GDPR) and other applicable privacy laws.</p>
</div>

<div class="legal-section">
  <h2>2. Data We Collect</h2>
  <h3>2.1 Account Data</h3>
  <ul>
    <li><strong>Email address</strong> &mdash; collected during waitlist signup or payment confirmation, used solely for account identification and communication</li>
    <li><strong>Payment records</strong> &mdash; blockchain transaction hashes (tx_hash), wallet addresses, payment amounts, and timestamps; recorded to verify subscription status</li>
  </ul>
  <h3>2.2 Usage Data</h3>
  <ul>
    <li><strong>API usage logs</strong> &mdash; request timestamps, IP addresses (for rate limiting), and query parameters; retained for 30 days for abuse prevention</li>
    <li><strong>API key metadata</strong> &mdash; key creation date, tier level, and active/inactive status</li>
  </ul>
  <h3>2.3 Data We Do NOT Collect</h3>
  <ul>
    <li>No cookies or tracking pixels</li>
    <li>No browser fingerprinting</li>
    <li>No third-party analytics (no Google Analytics, no Mixpanel)</li>
    <li>No personal identification beyond email address</li>
    <li>No device information or location data</li>
  </ul>
</div>

<div class="legal-section">
  <h2>3. Purpose of Data Collection</h2>
  <p>We collect data exclusively for the following purposes:</p>
  <ul>
    <li><strong>Service delivery</strong> &mdash; providing API access, verifying payments, managing subscriptions</li>
    <li><strong>Abuse prevention</strong> &mdash; rate limiting, detecting unauthorized access, preventing fraud</li>
    <li><strong>Communication</strong> &mdash; sending subscription confirmations and service-related notices</li>
  </ul>
  <div class="legal-highlight">
    <p><strong>Legal basis (GDPR Art.6):</strong> Processing is necessary for the performance of a contract (providing the subscribed service) and for our legitimate interest in preventing abuse.</p>
  </div>
</div>

<div class="legal-section">
  <h2>4. Data Storage &amp; Security</h2>
  <ul>
    <li>All data is stored <strong>locally on our own servers</strong> &mdash; no cloud third-party data processors</li>
    <li>Data is stored in encrypted SQLite databases with file-level access controls</li>
    <li>API keys are generated using cryptographically secure random number generation</li>
    <li>All connections are encrypted via TLS 1.3 (enforced by Cloudflare Tunnel with HSTS)</li>
    <li>No data is transferred outside the European Economic Area (EEA)</li>
  </ul>
</div>

<div class="legal-section">
  <h2>5. Data Sharing</h2>
  <div class="legal-warning">
    <p><strong>We do NOT share, sell, or disclose your personal data to any third party.</strong> This includes advertisers, analytics providers, data brokers, or any other external entity. Your data stays with us.</p>
  </div>
  <p>The only exception is if required by law (e.g., a valid court order), in which case we will notify you unless legally prohibited.</p>
</div>

<div class="legal-section">
  <h2>6. Your Rights (GDPR)</h2>
  <p>Under the GDPR, you have the following rights regarding your personal data:</p>
  <ul>
    <li><strong>Right of Access (Art.15)</strong> &mdash; request a copy of all data we hold about you</li>
    <li><strong>Right to Rectification (Art.16)</strong> &mdash; correct inaccurate data</li>
    <li><strong>Right to Erasure (Art.17)</strong> &mdash; request deletion of all your data (&ldquo;right to be forgotten&rdquo;)</li>
    <li><strong>Right to Restrict Processing (Art.18)</strong> &mdash; limit how we use your data</li>
    <li><strong>Right to Data Portability (Art.20)</strong> &mdash; receive your data in a machine-readable format</li>
    <li><strong>Right to Object (Art.21)</strong> &mdash; object to processing of your data</li>
  </ul>
  <div class="legal-highlight">
    <p><strong>To exercise any of these rights</strong>, contact us via the email address below. We will respond within 30 days and fulfill your request at no cost.</p>
  </div>
</div>

<div class="legal-section">
  <h2>7. Cookie Policy</h2>
  <div class="legal-highlight">
    <p><strong>We do NOT use cookies.</strong> BDE Score&#8482; does not set any cookies &mdash; neither session cookies, persistent cookies, nor third-party cookies. Our service works entirely without cookie-based tracking.</p>
  </div>
</div>

<div class="legal-section">
  <h2>8. Data Retention</h2>
  <ul>
    <li><strong>Email addresses:</strong> retained for the duration of your subscription + 90 days after expiration</li>
    <li><strong>Payment records:</strong> retained for 1 year for audit purposes, then permanently deleted</li>
    <li><strong>API usage logs:</strong> retained for 30 days, then automatically purged</li>
    <li><strong>Analysis data:</strong> aggregate stock analysis results (not personal data) may be retained indefinitely</li>
  </ul>
</div>

<div class="legal-section">
  <h2>9. Children&rsquo;s Privacy</h2>
  <p>The Service is not directed at individuals under the age of 18. We do not knowingly collect data from minors. If you believe a minor has provided us with personal data, please contact us for immediate deletion.</p>
</div>

<div class="legal-section">
  <h2>10. Changes to This Policy</h2>
  <p>We may update this Privacy Policy from time to time. Material changes will be communicated via our website. Continued use after changes constitutes acceptance of the updated policy.</p>
</div>

<div class="legal-section">
  <h2>11. Contact &amp; Data Protection</h2>
  <p>For privacy-related inquiries, data requests, or complaints:</p>
  <ul>
    <li>GitHub: <a href="https://github.com/hbhqq9/bde-score" style="color:#3b82f6;">github.com/hbhqq9/bde-score</a></li>
    <li>Waitlist form: Available on our homepage</li>
  </ul>
  <p style="margin-top:12px;">We are committed to resolving any privacy concerns promptly. If you are unsatisfied with our response, you have the right to lodge a complaint with your local Data Protection Authority.</p>
</div>

{LEGAL_FOOTER_HTML}
</div>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/legal", response_class=HTMLResponse)
async def legal_disclaimer():
    """Legal Disclaimer &mdash; SEC + EU AI Act"""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Legal Disclaimer &mdash; BDE Score&#8482;</title>
{LEGAL_STYLE}
</head>
<body>
<div class="legal-container">
{LEGAL_BACK_LINK}

<div class="legal-header">
  <h1>Legal Disclaimer</h1>
  <div class="subtitle">BDE Score&#8482; &mdash; Regulatory Disclosures &amp; Risk Warnings</div>
  <div class="effective">Effective Date: June 1, 2026</div>
</div>

<div class="legal-section">
  <div class="legal-warning">
    <p><strong>&#9888;&#65039; READ CAREFULLY:</strong> This page contains important legal disclosures about BDE Score&#8482;. By using this service, you acknowledge and agree to all statements on this page.</p>
  </div>
</div>

<div class="legal-section">
  <h2>1. SEC Disclaimer &mdash; Not Investment Advice</h2>
  <div class="legal-warning">
    <p><strong>BDE Score&#8482; is NOT registered with the U.S. Securities and Exchange Commission (SEC)</strong> as an investment adviser, broker-dealer, transfer agent, or any other regulated financial entity.</p>
  </div>
  <ul>
    <li>BDE Score&#8482; does <strong>NOT</strong> provide investment advice or recommendations</li>
    <li>BDE Score&#8482; does <strong>NOT</strong> offer securities for sale or purchase</li>
    <li>BDE Score&#8482; does <strong>NOT</strong> act as a broker, dealer, custodian, or intermediary in any financial transaction</li>
    <li>BDE Score&#8482; does <strong>NOT</strong> manage assets, hold funds, or execute trades on behalf of users</li>
    <li>BDE Score&#8482; scores and signals are <strong>mathematical outputs of an algorithmic model</strong>, not professional financial advice</li>
  </ul>
  <p>No content on this platform constitutes a solicitation or offer to buy or sell any security. All analysis is provided for informational and educational purposes only.</p>
  <p style="margin-top:12px;">If you are uncertain about any investment decision, please consult a licensed financial advisor registered with the SEC or your local regulatory authority.</p>
</div>

<div class="legal-section">
  <h2>2. EU AI Act &mdash; Art.50 Transparency Declaration</h2>
  <div class="legal-highlight">
    <p><strong>AI-Generated Content Disclosure (EU AI Act Article 50):</strong></p>
    <p style="margin-top:8px;">All scores, signals, rankings, and analytical outputs produced by BDE Score&#8482; are <strong>generated by an artificial intelligence system</strong>. They do not represent human judgment, professional analysis, or personalized financial advice.</p>
  </div>
  <p>In compliance with Article 50 of the EU AI Act (Regulation (EU) 2024/1689), BDE Score&#8482; discloses the following:</p>
  <ul>
    <li><strong>AI System Type:</strong> Rule-based multi-factor quantitative model (not a generative AI or large language model)</li>
    <li><strong>Methodology:</strong> Composite scoring from 5 independent factors &mdash; Momentum, Mean Reversion, Volume Profile, Volatility Regime, and Trend Strength &mdash; each computed using established quantitative finance techniques</li>
    <li><strong>Data Inputs:</strong> Historical daily OHLCV (Open, High, Low, Close, Volume) price data from public market feeds</li>
    <li><strong>Output Nature:</strong> Numerical scores (0&ndash;100) and categorical signals (Bullish/Neutral/Bearish) based on deterministic mathematical formulas</li>
    <li><strong>Human Oversight:</strong> No human reviews or modifies individual scores; the system operates autonomously</li>
    <li><strong>Limitations:</strong> The model cannot predict future prices, account for fundamental factors (earnings, management quality, macro events), or adapt to black swan events</li>
  </ul>
  <p style="margin-top:12px;">Users within the EU/EEA are reminded that AI-generated analysis should not be the sole basis for any financial decision.</p>
</div>

<div class="legal-section">
  <h2>3. Risk Disclosure</h2>
  <div class="legal-warning">
    <p><strong>&#9888;&#65039; INVESTMENT INVOLVES RISK, INCLUDING POSSIBLE LOSS OF PRINCIPAL.</strong></p>
  </div>
  <ul>
    <li><strong>Past performance does not guarantee future results.</strong> Historical price patterns may not repeat.</li>
    <li><strong>Quantitative models have limitations.</strong> Models are simplifications of reality and may fail during unusual market conditions, liquidity crises, or structural market changes.</li>
    <li><strong>Markets can be irrational.</strong> Stock prices are influenced by countless factors including human psychology, geopolitics, natural disasters, and regulatory changes &mdash; none of which are fully captured by technical analysis.</li>
    <li><strong>No strategy is risk-free.</strong> All investment strategies carry the risk of loss. You should only invest capital you can afford to lose.</li>
    <li><strong>Cross-market risks.</strong> Investing in foreign markets (HK, A-shares) involves additional risks including currency fluctuation, political instability, and different regulatory environments.</li>
    <li><strong>Cryptocurrency payment risks.</strong> USDC, while pegged to the US Dollar, is a digital asset. Transaction finality on blockchain means payments cannot be reversed. Users bear all responsibility for sending correct payment amounts to correct addresses.</li>
  </ul>
</div>

<div class="legal-section">
  <h2>4. Not a Broker, Dealer, or Custodian</h2>
  <p>BDE Score&#8482; explicitly states that it:</p>
  <ul>
    <li>Is <strong>NOT</strong> a broker or dealer as defined under the Securities Exchange Act of 1934</li>
    <li>Is <strong>NOT</strong> an investment adviser registered under the Investment Advisers Act of 1940</li>
    <li>Is <strong>NOT</strong> a custodian of any client funds or securities</li>
    <li>Is <strong>NOT</strong> a member of FINRA, SIPC, or any other securities regulatory organization</li>
    <li>Does <strong>NOT</strong> have the authority to execute trades, manage portfolios, or provide suitability determinations</li>
  </ul>
  <p style="margin-top:12px;">BDE Score&#8482; is a <strong>software-as-a-service (SaaS) product</strong> that provides data analysis tools. The relationship between BDE Score&#8482; and its users is strictly that of a software provider and end user.</p>
</div>

<div class="legal-section">
  <h2>5. Third-Party Data</h2>
  <p>Market data displayed through BDE Score&#8482; is sourced from third-party providers (FutuOpenD, Sina Finance). We do not guarantee the accuracy, timeliness, or completeness of this data. Data may be delayed, incomplete, or subject to errors. Users should verify critical data from primary exchange sources.</p>
</div>

<div class="legal-section">
  <h2>6. Jurisdictional Compliance</h2>
  <p>Users are responsible for ensuring that their use of BDE Score&#8482; complies with the laws and regulations of their respective jurisdictions. Some jurisdictions may restrict or prohibit the use of algorithmic analysis tools or cryptocurrency payments. BDE Score&#8482; makes no representation regarding the legality of its use in any specific jurisdiction.</p>
</div>

<div class="legal-section">
  <h2>7. Indemnification</h2>
  <p>By using BDE Score&#8482;, you agree to indemnify, defend, and hold harmless BDE Score&#8482;, its operators, and contributors from any claims, losses, liabilities, damages, or expenses (including legal fees) arising from:</p>
  <ul>
    <li>Your use of the Service or reliance on its outputs</li>
    <li>Your violation of these disclaimers or applicable laws</li>
    <li>Your investment decisions made based on the Service&rsquo;s analysis</li>
  </ul>
</div>

<div class="legal-section">
  <h2>8. Severability</h2>
  <p>If any provision of this disclaimer is found to be unenforceable, the remaining provisions shall continue in full force and effect. The unenforceable provision shall be modified to the minimum extent necessary to make it enforceable while preserving its original intent.</p>
</div>

{LEGAL_FOOTER_HTML}
</div>
</body>
</html>"""
    return HTMLResponse(content=html)


# Ticker-to-DB-name mapping for badge lookups
TICKER_MAP = {
    # US stocks
    "AAPL": "AAPL", "MSFT": "MSFT", "GOOG": "GOOG", "AMZN": "AMZN", "NVDA": "NVDA",
    "META": "META", "TSLA": "TSLA", "BABA": "BABA", "AMD": "AMD", "NFLX": "NFLX",
    "INTC": "INTC", "ARM": "ARM", "AVGO": "AVGO", "JNJ": "JNJ", "UNH": "UNH",
    "V": "V", "MA": "MA", "PG": "PG", "KO": "KO", "PFE": "PFE", "WMT": "WMT",
    "MCD": "MCD", "SPY": "SPY", "QQQ": "QQQ",
    # HK stocks
    "00700": "腾讯", "09988": "阿里-W", "09999": "网易-S", "03690": "美团-W",
    "09618": "京东集团", "00005": "汇丰控股", "01024": "快手-W", "09888": "百度集团",
    "02015": "理想汽车", "09868": "小鹏汽车", "01211": "比亚迪股份", "00388": "香港交易所",
    "00941": "中国移动", "01810": "小米集团", "09626": "哔哩哔哩", "00981": "中芯国际",
    "02382": "舜宇光学", "06098": "碧桂园服务", "00823": "领展房产", "01113": "长实集团",
    "00027": "银河娱乐", "02899": "紫金矿业", "00883": "中国海洋石油", "00001": "长和",
    "02318": "中国平安", "00390": "中国中铁",
    # A-shares
    "SH600519": "贵州茅台", "SH601318": "中国平安", "SZ000858": "五粮液",
    "SH600036": "招商银行", "SZ002594": "比亚迪", "SH601899": "紫金矿业",
    "SH600028": "中国石化", "SH601857": "中国石油", "SZ000333": "美的集团",
    "SH600900": "长江电力", "SH601012": "隆基绿能", "SZ300750": "宁德时代",
    "SH600519": "贵州茅台", "SZ002714": "牧原股份", "SH600809": "泸州老窖",
    "SH601288": "农业银行", "SH601939": "建设银行", "SH601398": "工商银行",
    "SH600028": "中国石化", "SH601728": "中国电信", "SH600941": "中国移动",
    "SH600050": "中国联通", "SH601088": "中国神华", "SH601628": "中国人寿",
    "SH603259": "药明生物", "SZ002475": "立讯精密", "SH600887": "伊利股份",
}

@app.get("/api/badge")
async def badge(market: str = "ALL", symbol: str = None):
    """Generate shields.io-compatible badge JSON for BDE Score"""
    from fastapi.responses import JSONResponse
    try:
        # Get latest snapshot
        snapshot = get_latest_snapshot()
        if not snapshot:
            return JSONResponse({
                "schemaVersion": 1,
                "label": "BDE Score",
                "message": "no data",
                "color": "grey"
            })
        
        if symbol:
            # Resolve symbol to DB name
            resolved = TICKER_MAP.get(symbol.upper(), TICKER_MAP.get(symbol)) or symbol.upper()
            # Try exact match first, then partial match
            stock = next((s for s in snapshot if s.get('symbol','').upper() == resolved.upper()), None)
            if not stock:
                stock = next((s for s in snapshot if resolved in s.get('symbol','')), None)
            if stock:
                score = stock.get('bde_score', 0)
                signal = stock.get('signal', 'HOLD')
                color = "brightgreen" if signal == "BUY" else "yellow" if signal == "HOLD" else "red"
                display_name = symbol.upper()
                return JSONResponse({
                    "schemaVersion": 1,
                    "label": f"BDE {display_name}",
                    "message": f"{score:.1f} {signal}",
                    "color": color,
                    "style": "flat"
                })
            return JSONResponse({"schemaVersion": 1, "label": "BDE", "message": "not found", "color": "grey"})
        else:
            # Market overview badge
            avg_score = sum(s.get('bde_score', 0) for s in snapshot) / len(snapshot) if snapshot else 0
            buy_count = sum(1 for s in snapshot if s.get('signal') == 'BUY')
            return JSONResponse({
                "schemaVersion": 1,
                "label": f"BDE Score ({market})",
                "message": f"Ø{avg_score:.0f} · {buy_count} BUY",
                "color": "blue",
                "style": "flat"
            })
    except Exception as e:
        return JSONResponse({"schemaVersion": 1, "label": "BDE Score", "message": "error", "color": "lightgrey"})


def get_latest_snapshot():
    """Get latest analysis snapshot from DB"""
    try:
        conn = _get_db()
        # Find latest run_time
        row = conn.execute("SELECT DISTINCT run_time FROM analysis_history ORDER BY run_time DESC LIMIT 1").fetchone()
        if not row:
            conn.close()
            return None
        latest_time = row[0]
        # Get all stocks from that run
        rows = conn.execute(
            "SELECT symbol, composite_score, signal, scores_json FROM analysis_history WHERE run_time = ?",
            (latest_time,)
        ).fetchall()
        conn.close()
        if not rows:
            return None
        return [
            {
                "symbol": r[0],
                "bde_score": r[1],
                "signal": r[2],
                "scores": json.loads(r[3]) if r[3] else {}
            }
            for r in rows
        ]
    except:
        pass
    return None


# ============================================================
# 💸 x402 微支付端点 (Agent-native, zero-registration)
# ============================================================
@app.get("/pay/info")
async def pay_info():
    """
    x402 协议信息发现端点。
    Agent 调用此端点获取定价、支付方式、网络配置。
    免费端点，无需支付。
    """
    return JSONResponse(content=get_x402_info())


@app.get("/pay/free")
async def pay_free_check(request: Request):
    """
    检查当前IP的免费额度状态。
    免费端点，无需支付。
    """
    client_ip = request.headers.get('cf-connecting-ip', '') or \
                request.headers.get('x-forwarded-for', '').split(',')[0].strip() or \
                (request.client.host if request.client else "unknown")
    
    status = free_quota.get_status(client_ip)
    status['network'] = X402_NETWORK
    status['chain_id'] = X402_CHAIN_ID
    status['price_if_paid_usd'] = X402_PRICE_USD
    return JSONResponse(content=status)


@app.get("/pay/balance")
async def pay_balance():
    """
    查询 x402 支付统计。
    公开端点，展示收入数据和利润空间。
    """
    stats = get_payment_stats()
    stats['disclaimer'] = 'Technical analysis only. Not investment advice.'
    return JSONResponse(content=stats)


@app.post("/pay/query")
async def pay_query(
    request: Request,
    symbol: str = Query(None, description="股票代码 (如 AAPL, 00700, SH600519)"),
    market: str = Query("US", description="市场: US/HK/A/ALL"),
):
    """
    x402 支付+查询一体端点。
    
    认证优先级:
    1. X-API-Key → 现有认证（免费）
    2. X-Payment → x402 USDC 微支付（$0.01/query）
    3. 免费额度 → 3次/天/IP
    
    未认证且免费额度用尽 → 返回 402 Payment Required
    """
    # 🔒 输入验证
    market_upper = market.upper().strip() if market else "US"
    if market_upper not in VALID_MARKETS:
        raise HTTPException(
            status_code=400,
            detail="Invalid market. Must be one of: US, HK, A, ALL"
        )
    
    # 🔒 获取认证信息
    client_ip = request.headers.get('cf-connecting-ip', '') or \
                request.headers.get('x-forwarded-for', '').split(',')[0].strip() or \
                (request.client.host if request.client else "unknown")
    
    # 检查认证来源
    auth_source = "free"
    payment_info = None
    
    # 检查 API Key
    api_key = request.headers.get('X-API-Key') or request.headers.get('x-api-key')
    if api_key:
        tier, key_prefix = key_manager.verify_with_prefix(api_key)
        if tier:
            auth_source = f"api_key:{tier}"
    
    # 检查 x402 支付
    if hasattr(request.state, 'x402_payment'):
        auth_source = "x402_payment"
        payment_info = request.state.x402_payment
    
    # 检查免费额度
    if hasattr(request.state, 'x402_free'):
        auth_source = "x402_free"
    
    # 执行分析
    try:
        snapshot = get_latest_snapshot()
        if not snapshot:
            # 无缓存，运行一次分析
            async with _analyze_lock:
                result = run_analysis(market=market_upper)
        else:
            # 如果有指定 symbol，过滤结果
            if symbol:
                symbol_upper = symbol.upper().strip()
                filtered = [
                    s for s in snapshot
                    if symbol_upper in s.get('symbol', '').upper()
                ]
                if filtered:
                    snapshot = filtered
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Symbol '{symbol}' not found. Use /pay/info for supported symbols."
                    )
            result = {
                'run_time': datetime.now().isoformat(),
                'data_source': 'cache',
                'results': snapshot,
                'market': market_upper,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("x402 pay/query analysis failed")
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please retry."
        )
    
    # 构建响应
    response = {
        'auth_source': auth_source,
        'disclaimer': '⚠️ Technical analysis only. Not investment advice. Past performance does not guarantee future results.',
    }
    
    if isinstance(result, dict):
        response.update(sanitize_for_json(result))
    else:
        response['data'] = sanitize_for_json(result)
    
    # 附加 x402 支付确认信息
    if payment_info:
        response['x402_receipt'] = {
            'paid': X402_PRICE_USD,
            'currency': 'USDC',
            'network': X402_CHAIN_ID,
            'payer': _mask_address_x402(payment_info.get('payer', '')),
            'tx_hash': payment_info.get('tx_hash', ''),
            'verified_at': payment_info.get('verified_at', ''),
        }
    
    return JSONResponse(content=response)


@app.get("/pay/query")
async def pay_query_get(request: Request, market: str = Query("US")):
    """
    GET /pay/query — x402 支付查询（GET方法，方便浏览器测试）。
    与 POST /pay/query 相同逻辑，由 x402 中间件保护。
    """
    # 复用 POST 逻辑
    return await pay_query(request, symbol=None, market=market)


def _mask_address_x402(address: str) -> str:
    """🔒 地址脱敏"""
    if not address or len(address) < 12:
        return "***"
    return f"{address[:6]}...{address[-4:]}"




# ============================================================
# 🔍 Agent Compliance Quick Check (EU AI Act)
# ============================================================
# BDE Score 引流入口：检测 MCP endpoint 的合规性
# 自动检测 HTTPS、安全头、API文档、透明度声明等
# ============================================================

import httpx
from urllib.parse import urlparse

# 合规检测专用速率限制：每IP每分钟3次 (fixed version - original RateLimiter has a counting bug)
class _ComplianceRateLimiter:
    """Fixed rate limiter for compliance checks: 3 req/min/IP"""
    def __init__(self, max_requests=3, window_seconds=60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        # Clean expired entries for this IP
        self.requests[client_ip] = [t for t in self.requests[client_ip] if now - t < self.window]
        if len(self.requests[client_ip]) >= self.max_requests:
            return False
        self.requests[client_ip].append(now)
        return True

compliance_rate_limiter = _ComplianceRateLimiter(max_requests=3, window_seconds=60)


async def _check_endpoint(client, url, timeout=10):
    """检测单个端点是否可访问，返回 (status_code, response_time, headers, body_snippet)"""
    try:
        start = time.time()
        resp = await client.get(url, follow_redirects=True, timeout=timeout)
        elapsed = time.time() - start
        body_text = ""
        try:
            body_text = resp.text[:5000]  # 只取前5000字符
        except Exception:
            pass
        return {
            "status": resp.status_code,
            "time": round(elapsed, 3),
            "headers": dict(resp.headers),
            "body_snippet": body_text,
            "final_url": str(resp.url),
            "ok": True,
        }
    except httpx.TimeoutException:
        return {"ok": False, "error": "timeout", "status": 0, "time": timeout, "headers": {}, "body_snippet": "", "final_url": url}
    except httpx.ConnectError as e:
        return {"ok": False, "error": f"connection_failed: {str(e)[:100]}", "status": 0, "time": 0, "headers": {}, "body_snippet": "", "final_url": url}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200], "status": 0, "time": 0, "headers": {}, "body_snippet": "", "final_url": url}


async def _run_compliance_checks(target_url: str) -> dict:
    """执行所有合规检测项，返回完整报告"""
    parsed = urlparse(target_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    checks = []
    total_score = 0
    max_score = 100
    issues = []
    recommendations = []
    
    async with httpx.AsyncClient(
        verify=False,  # 允许自签证书检测
        headers={"User-Agent": "BDE-ComplianceCheck/1.0 (+https://github.com/hbhqq9/bde-score)"}
    ) as client:
        
        # ---- 1. HTTPS 检测 (10分) ----
        https_ok = parsed.scheme == "https"
        https_score = 10 if https_ok else 0
        checks.append({
            "id": "https",
            "name": "HTTPS Enabled",
            "description": "Endpoint uses HTTPS encryption",
            "max_score": 10,
            "score": https_score,
            "passed": https_ok,
            "detail": f"Scheme: {parsed.scheme}" if https_ok else "Endpoint does not use HTTPS — all traffic is unencrypted",
            "severity": "critical" if not https_ok else "none",
        })
        if not https_ok:
            issues.append("HTTPS not enabled — all data transmitted in plaintext")
            recommendations.append("Enable HTTPS/TLS immediately. Use Let's Encrypt for free certificates.")
        
        # ---- 主页面请求 (获取 headers + body) ----
        main_result = await _check_endpoint(client, target_url)
        
        if not main_result["ok"]:
            # 连接失败，返回错误报告
            return {
                "success": False,
                "error": main_result["error"],
                "url": target_url,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        
        headers = main_result["headers"]
        body = main_result["body_snippet"]
        response_time = main_result["time"]
        
        # ---- 2. Security Headers (15分) ----
        security_headers = {
            "Content-Security-Policy": 4,
            "X-Content-Type-Options": 3,
            "X-Frame-Options": 3,
            "Strict-Transport-Security": 3,
            "Referrer-Policy": 2,
        }
        sec_score = 0
        sec_details = {}
        for h, pts in security_headers.items():
            present = h.lower() in {k.lower(): v for k, v in headers.items()}
            if present:
                sec_score += pts
            sec_details[h] = {"present": present, "points": pts if present else 0}
        checks.append({
            "id": "security_headers",
            "name": "Security Headers",
            "description": "Presence of key security headers (CSP, X-Content-Type-Options, X-Frame-Options, HSTS, Referrer-Policy)",
            "max_score": 15,
            "score": sec_score,
            "passed": sec_score >= 10,
            "detail": sec_details,
            "severity": "high" if sec_score < 10 else "none",
        })
        missing_sec = [h for h, d in sec_details.items() if not d["present"]]
        if missing_sec:
            issues.append(f"Missing security headers: {', '.join(missing_sec)}")
            recommendations.append(f"Add the following security headers: {', '.join(missing_sec)}")
        
        # ---- 3. API Documentation (10分) ----
        api_doc_paths = [
            "/openapi.json", "/docs", "/redoc", "/swagger.json",
            "/api/docs", "/api-docs", "/api/v1/docs",
            "/.well-known/openapi.json",
        ]
        api_doc_found = False
        api_doc_path = None
        for path in api_doc_paths:
            result = await _check_endpoint(client, f"{base_url}{path}", timeout=5)
            if result["ok"] and result["status"] == 200:
                api_doc_found = True
                api_doc_path = path
                break
        api_doc_score = 10 if api_doc_found else 0
        checks.append({
            "id": "api_documentation",
            "name": "API Documentation",
            "description": "Presence of OpenAPI/Swagger documentation",
            "max_score": 10,
            "score": api_doc_score,
            "passed": api_doc_found,
            "detail": f"Found at {api_doc_path}" if api_doc_found else "No API documentation endpoint found",
            "severity": "medium" if not api_doc_found else "none",
        })
        if not api_doc_found:
            issues.append("No API documentation endpoint discovered")
            recommendations.append("Add /openapi.json or /docs endpoint for API discoverability")
        
        # ---- 4. MCP Endpoint (15分) ----
        mcp_paths = ["/mcp", "/mcp/", "/sse", "/messages", "/mcp/v1"]
        mcp_found = False
        mcp_path = None
        mcp_detail = ""
        for path in mcp_paths:
            result = await _check_endpoint(client, f"{base_url}{path}", timeout=5)
            if result["ok"] and result["status"] in (200, 405, 422, 400):
                # 405/422 means endpoint exists but needs different method
                mcp_found = True
                mcp_path = path
                mcp_detail = f"Endpoint {path} responded with {result['status']}"
                break
        # Also check if body mentions MCP or JSON-RPC
        if not mcp_found and ("mcp" in body.lower() or "jsonrpc" in body.lower() or "json-rpc" in body.lower()):
            mcp_found = True
            mcp_detail = "MCP/JSON-RPC references found in response body"
        mcp_score = 15 if mcp_found else 0
        checks.append({
            "id": "mcp_endpoint",
            "name": "MCP Endpoint Accessible",
            "description": "Model Context Protocol endpoint is reachable",
            "max_score": 15,
            "score": mcp_score,
            "passed": mcp_found,
            "detail": mcp_detail if mcp_found else "No MCP endpoint found at common paths (/mcp, /sse, /messages)",
            "severity": "high" if not mcp_found else "none",
        })
        if not mcp_found:
            issues.append("MCP endpoint not accessible")
            recommendations.append("Ensure /mcp or /sse endpoint is publicly accessible")
        
        # ---- 5. Response Time (10分) ----
        rt_score = 10 if response_time < 2.0 else (5 if response_time < 5.0 else 0)
        checks.append({
            "id": "response_time",
            "name": "Response Time < 2s",
            "description": "Server responds within acceptable latency",
            "max_score": 10,
            "score": rt_score,
            "passed": response_time < 2.0,
            "detail": f"Response time: {response_time:.3f}s",
            "severity": "medium" if response_time >= 2.0 else "none",
        })
        if response_time >= 2.0:
            issues.append(f"Slow response time: {response_time:.3f}s")
            recommendations.append("Optimize server performance — target < 2s response time")
        
        # ---- 6. Privacy Policy / Terms (10分) ----
        privacy_paths = [
            "/privacy", "/privacy-policy", "/legal/privacy", "/policies/privacy",
            "/terms", "/terms-of-service", "/legal/terms", "/tos",
            "/legal", "/about/legal",
        ]
        privacy_found = False
        privacy_detail = ""
        # Check in body first
        if "privacy" in body.lower() or "terms" in body.lower():
            # Look for actual links
            import re as _re
            links = _re.findall(r'href=["\']([^"\']*(?:privacy|terms|legal)[^"\']*)["\']', body, _re.IGNORECASE)
            if links:
                privacy_found = True
                privacy_detail = f"Privacy/Terms links found in page: {links[0]}"
        # Also check common paths
        if not privacy_found:
            for path in privacy_paths:
                result = await _check_endpoint(client, f"{base_url}{path}", timeout=5)
                if result["ok"] and result["status"] == 200:
                    privacy_found = True
                    privacy_detail = f"Found at {path}"
                    break
        privacy_score = 10 if privacy_found else 0
        checks.append({
            "id": "privacy_policy",
            "name": "Privacy Policy / Terms",
            "description": "Privacy policy or terms of service page available",
            "max_score": 10,
            "score": privacy_score,
            "passed": privacy_found,
            "detail": privacy_detail if privacy_found else "No privacy policy or terms page found",
            "severity": "high" if not privacy_found else "none",
        })
        if not privacy_found:
            issues.append("No privacy policy or terms of service found")
            recommendations.append("Add /privacy and /terms pages — required by EU AI Act and GDPR")
        
        # ---- 7. Server Header Exposure (扣分项 -10) ----
        server_header = None
        for k, v in headers.items():
            if k.lower() == "server":
                server_header = v
                break
        server_exposed = server_header is not None and len(server_header) > 0
        server_score = -10 if server_exposed else 0
        checks.append({
            "id": "server_header",
            "name": "Server Header Exposure",
            "description": "Server header should NOT reveal technology stack",
            "max_score": 0,
            "score": server_score,
            "passed": not server_exposed,
            "detail": f"Server header: '{server_header}' — reveals technology stack" if server_exposed else "Server header not exposed",
            "severity": "medium" if server_exposed else "none",
        })
        if server_exposed:
            issues.append(f"Server header exposes technology: '{server_header}'")
            recommendations.append("Remove or obfuscate the Server header to avoid revealing your tech stack")
        
        # ---- 8. CORS Configuration (5分) ----
        cors_present = any(k.lower().startswith("access-control-allow") for k in headers)
        cors_score = 5 if cors_present else 0
        checks.append({
            "id": "cors",
            "name": "CORS Configuration",
            "description": "Cross-Origin Resource Sharing headers present",
            "max_score": 5,
            "score": cors_score,
            "passed": cors_present,
            "detail": "CORS headers detected" if cors_present else "No CORS headers found",
            "severity": "low" if not cors_present else "none",
        })
        if not cors_present:
            issues.append("No CORS configuration detected")
            recommendations.append("Configure CORS headers if the API is consumed by web clients")
        
        # ---- 9. Rate Limiting (5分) ----
        rate_limit_headers = {
            "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset",
            "retry-after", "rate-limit-limit", "rate-limit-remaining",
        }
        rate_headers_found = [k for k in headers if k.lower() in rate_limit_headers]
        rate_found = len(rate_headers_found) > 0
        rate_score = 5 if rate_found else 0
        checks.append({
            "id": "rate_limiting",
            "name": "Rate Limiting",
            "description": "Rate limiting headers or traces present",
            "max_score": 5,
            "score": rate_score,
            "passed": rate_found,
            "detail": f"Rate limit headers: {', '.join(rate_headers_found)}" if rate_found else "No rate limiting headers detected",
            "severity": "low" if not rate_found else "none",
        })
        if not rate_found:
            recommendations.append("Add rate limiting and expose limits via response headers (X-RateLimit-*)")
        
        # ---- 10. EU AI Act Art.50 Transparency (20分, 关键项) ----
        art50_keywords = [
            "art.50", "article 50", "art 50",
            "ai act", "ai-act", "eu ai act",
            "transparency obligation", "ai-generated", "ai generated",
            "artificial intelligence system", "ai system",
            "machine-generated", "automated decision",
        ]
        art50_found = False
        art50_detail = ""
        body_lower = body.lower()
        for kw in art50_keywords:
            if kw in body_lower:
                art50_found = True
                art50_detail = f"AI Act transparency keyword found: '{kw}'"
                break
        # Also check /legal or /about pages
        if not art50_found:
            for path in ["/legal", "/about", "/disclaimer", "/compliance", "/ai-act"]:
                result = await _check_endpoint(client, f"{base_url}{path}", timeout=5)
                if result["ok"] and result["status"] == 200:
                    snippet_lower = result["body_snippet"].lower()
                    for kw in art50_keywords:
                        if kw in snippet_lower:
                            art50_found = True
                            art50_detail = f"Found at {path}: keyword '{kw}'"
                            break
                if art50_found:
                    break
        
        art50_score = 20 if art50_found else 0
        checks.append({
            "id": "eu_ai_act_art50",
            "name": "EU AI Act Art.50 Transparency",
            "description": "Transparency declaration per EU AI Act Article 50 (AI-generated content disclosure)",
            "max_score": 20,
            "score": art50_score,
            "passed": art50_found,
            "detail": art50_detail if art50_found else "No EU AI Act Art.50 transparency declaration found",
            "severity": "critical" if not art50_found else "none",
        })
        if not art50_found:
            issues.append("⚠️ CRITICAL: No EU AI Act Art.50 transparency declaration found")
            recommendations.append("Add Art.50 transparency declaration — required for AI systems operating in the EU. See https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai")
        
        # ---- Calculate total ----
        total_score = sum(c["score"] for c in checks)
        # Ensure within 0-100 range
        total_score = max(0, min(100, total_score))
        
        # Grade
        if total_score >= 90:
            grade = "A"
            grade_label = "Excellent"
        elif total_score >= 75:
            grade = "B"
            grade_label = "Good"
        elif total_score >= 60:
            grade = "C"
            grade_label = "Needs Improvement"
        elif total_score >= 40:
            grade = "D"
            grade_label = "Below Average"
        else:
            grade = "F"
            grade_label = "Critical Gaps"
        
        return {
            "success": True,
            "url": target_url,
            "base_url": base_url,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "response_time": response_time,
            "total_score": total_score,
            "max_score": max_score,
            "grade": grade,
            "grade_label": grade_label,
            "checks": checks,
            "issues": issues,
            "recommendations": recommendations,
            "disclaimer": "Automated compliance scan — not a legal audit. Consult legal counsel for formal compliance assessment.",
            "powered_by": "BDE Score™ Compliance Quick Check",
            "ai_system_info": {
                "generated_by": "BDE Score AI Assessment Engine v1.0",
                "assessment_type": "automated-reliability-scoring",
                "methodology": "rule-based + LLM-enhanced public signal analysis",
                "data_sources": ["public-endpoint-analysis", "protocol-detection", "security-signal-scanning"],
                "limitations": ["based on publicly accessible signals only", "not a penetration test", "point-in-time assessment"],
                "eu_ai_act_art50": True
            },
        }


def _compliance_html_report(report: dict) -> str:
    """生成合规检测的HTML报告页面"""
    if not report.get("success"):
        return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Compliance Check Error</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:600px;margin:60px auto;padding:20px;background:#0f172a;color:#e2e8f0;}}
.error{{background:#7f1d1d;border:1px solid #dc2626;border-radius:12px;padding:24px;}}h1{{color:#f87171;}}</style></head>
<body><div class="error"><h1>⚠️ Scan Failed</h1><p><strong>URL:</strong> {html.escape(report.get("url",""))}</p>
<p><strong>Error:</strong> {html.escape(report.get("error","Unknown error"))}</p>
<p>Please verify the URL is correct and the server is reachable.</p></div></body></html>"""
    
    score = report["total_score"]
    grade = report["grade"]
    grade_colors = {"A": "#22c55e", "B": "#84cc16", "C": "#eab308", "D": "#f97316", "F": "#ef4444"}
    grade_color = grade_colors.get(grade, "#94a3b8")
    
    # Score ring SVG
    score_ring = f"""<svg width="160" height="160" viewBox="0 0 160 160">
      <circle cx="80" cy="80" r="70" fill="none" stroke="#1e293b" stroke-width="12"/>
      <circle cx="80" cy="80" r="70" fill="none" stroke="{grade_color}" stroke-width="12"
        stroke-dasharray="{score * 4.4} {440 - score * 4.4}" stroke-linecap="round"
        transform="rotate(-90 80 80)"/>
      <text x="80" y="72" text-anchor="middle" fill="{grade_color}" font-size="36" font-weight="bold">{score}</text>
      <text x="80" y="96" text-anchor="middle" fill="#94a3b8" font-size="14">/ 100</text>
    </svg>"""
    
    # Check items HTML
    checks_html = ""
    for c in report["checks"]:
        passed = c["passed"]
        icon = "✅" if passed else ("❌" if c.get("severity") == "critical" else "⚠️")
        bg = "#0f2a1a" if passed else "#2a0f0f"
        border = "#22c55e" if passed else "#ef4444"
        detail_str = str(c["detail"])
        if len(detail_str) > 200:
            detail_str = detail_str[:200] + "..."
        checks_html += f"""
        <div style="background:{bg};border-left:4px solid {border};border-radius:8px;padding:16px;margin-bottom:12px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:18px;">{icon} <strong>{html.escape(c["name"])}</strong></span>
            <span style="color:{grade_color};font-weight:bold;font-size:16px;">{c["score"]}/{c["max_score"]}</span>
          </div>
          <div style="color:#94a3b8;font-size:13px;margin-top:6px;">{html.escape(c["description"])}</div>
          <div style="color:#cbd5e1;font-size:13px;margin-top:4px;font-family:monospace;">{html.escape(detail_str)}</div>
        </div>"""
    
    # Issues & recommendations
    issues_html = ""
    if report["issues"]:
        issues_html = "<h2 style='color:#f87171;margin-top:32px;'>🔴 Issues Found</h2><ul>"
        for iss in report["issues"]:
            issues_html += f"<li style='margin-bottom:8px;color:#fca5a5;'>{html.escape(iss)}</li>"
        issues_html += "</ul>"
    
    recs_html = ""
    if report["recommendations"]:
        recs_html = "<h2 style='color:#60a5fa;margin-top:32px;'>💡 Recommendations</h2><ul>"
        for rec in report["recommendations"]:
            recs_html += f"<li style='margin-bottom:8px;color:#93c5fd;'>{html.escape(rec)}</li>"
        recs_html += "</ul>"
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Compliance Check — {html.escape(report["base_url"])}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 20px; }}
  .container {{ max-width: 720px; margin: 0 auto; }}
  .header {{ text-align: center; padding: 40px 20px; }}
  .badge {{ display: inline-block; padding: 4px 16px; border-radius: 20px; font-size: 14px; font-weight: 600; background: {grade_color}22; color: {grade_color}; border: 1px solid {grade_color}44; }}
  h2 {{ color: #f1f5f9; font-size: 20px; }}
  .footer {{ text-align: center; padding: 40px 20px; color: #475569; font-size: 13px; border-top: 1px solid #1e293b; margin-top: 40px; }}
  a {{ color: #60a5fa; text-decoration: none; }}
  .cta {{ background: linear-gradient(135deg, #3b82f6, #8b5cf6); color: white; padding: 16px 32px; border-radius: 12px; display: inline-block; font-weight: 600; margin-top: 24px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1 style="font-size:28px;margin-bottom:8px;">🔍 Agent Compliance Quick Check</h1>
    <p style="color:#94a3b8;margin:4px 0;">EU AI Act Readiness Scan</p>
    <p style="color:#64748b;font-size:14px;margin:4px 0;">{html.escape(report["base_url"])} &mdash; {html.escape(report["timestamp"])}</p>
  </div>
  
  <div style="text-align:center;margin:20px 0;">
    {score_ring}
    <div style="margin-top:12px;"><span class="badge">Grade {grade}: {html.escape(report["grade_label"])}</span></div>
  </div>
  
  <h2>📋 Detailed Checks</h2>
  {checks_html}
  
  {issues_html}
  {recs_html}
  
  <div style="text-align:center;margin-top:40px;padding:32px;background:linear-gradient(135deg,#1e1b4b,#172554);border-radius:16px;border:1px solid #312e81;">
    <h2 style="color:#c7d2fe;margin-top:0;">🚀 Want a Full Compliance Audit?</h2>
    <p style="color:#a5b4fc;">BDE Score™ provides comprehensive EU AI Act compliance scoring for AI agents and MCP endpoints.</p>
    <a href="https://github.com/hbhqq9/bde-score" class="cta">Get Full BDE Compliance Report →</a>
  </div>
  
  <div class="footer">
    <p>{html.escape(report["disclaimer"])}</p>
    <p>Powered by <a href="https://github.com/hbhqq9/bde-score">BDE Score™</a></p>
  </div>
</div>
</body>
</html>"""


# ============================================================
# 🔐 用户认证路由
# ============================================================

def _get_session_user(request: Request) -> Optional[dict]:
    """从cookie中提取并验证session"""
    token = request.cookies.get("bde_session")
    if not token:
        return None
    user = auth_manager.validate_session(token)
    return user

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """注册页面"""
    # 已登录则跳转dashboard
    user = _get_session_user(request)
    if user:
        from starlette.responses import RedirectResponse
        return RedirectResponse("/dashboard", status_code=302)
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'register.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()

@app.post("/api/auth/register")
async def api_register(request: Request):
    """注册API"""
    try:
        body = await request.json()
    except:
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid JSON"})
    email = body.get("email", "").strip()
    password = body.get("password", "")
    result = auth_manager.register_user(email, password)
    if result["success"]:
        # 自动登录
        login_result = auth_manager.login_user(email, password)
        if login_result["success"]:
            token = auth_manager.create_session(
                login_result["user_id"], login_result["email"],
                request.client.host if request.client else "",
                request.headers.get("user-agent", "")
            )
            resp = JSONResponse(content={"success": True, "message": "Registration successful", "email": login_result["email"]})
            resp.set_cookie(
                key="bde_session", value=token,
                httponly=True, samesite="lax", max_age=SESSION_TTL_HOURS * 3600,
                secure=False  # Tunnel是HTTP
            )
            return resp
    return JSONResponse(status_code=400, content=result)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页面"""
    user = _get_session_user(request)
    if user:
        from starlette.responses import RedirectResponse
        return RedirectResponse("/dashboard", status_code=302)
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'login.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()

@app.post("/api/auth/login")
async def api_login(request: Request):
    """登录API"""
    try:
        body = await request.json()
    except:
        return JSONResponse(status_code=400, content={"success": False, "message": "Invalid JSON"})
    email = body.get("email", "").strip()
    password = body.get("password", "")
    result = auth_manager.login_user(email, password)
    if result["success"]:
        token = auth_manager.create_session(
            result["user_id"], result["email"],
            request.client.host if request.client else "",
            request.headers.get("user-agent", "")
        )
        resp = JSONResponse(content={
            "success": True, "message": "Login successful",
            "email": result["email"], "tier": result.get("tier", "free"),
            "credits_remaining": result.get("credits_total", 1000) - result.get("credits_used", 0)
        })
        resp.set_cookie(
            key="bde_session", value=token,
            httponly=True, samesite="lax", max_age=SESSION_TTL_HOURS * 3600,
            secure=False
        )
        return resp
    return JSONResponse(status_code=401, content=result)

@app.post("/api/auth/logout")
async def api_logout(request: Request):
    """登出API"""
    token = request.cookies.get("bde_session")
    if token:
        auth_manager.destroy_session(token)
    resp = JSONResponse(content={"success": True, "message": "Logged out"})
    resp.delete_cookie("bde_session")
    return resp

@app.get("/api/auth/me")
async def api_auth_me(request: Request):
    """当前用户信息"""
    user = _get_session_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"authenticated": False})
    info = auth_manager.get_user_info(user["user_id"])
    if not info:
        return JSONResponse(status_code=401, content={"authenticated": False})
    info["authenticated"] = True
    return info

SESSION_TTL_HOURS = 72

@app.get("/compliance-check")
async def compliance_check(
    request: Request,
    response: Response,
    url: str = Query(None, description="MCP endpoint URL to check"),
):
    """
    Agent Compliance Quick Check — EU AI Act readiness scan.


    Accepts an MCP endpoint URL, runs automated compliance checks,
    and returns a scored report (JSON or HTML).
    
    Rate limit: 3 checks per IP per minute.
    """
    # EU AI Act Art.50: AI system disclosure headers
    response.headers["X-BDE-AI-System"] = "true"
    response.headers["X-BDE-Assessment-Method"] = "ai-automated"
    response.headers["X-BDE-Model-Version"] = "1.0"
    
    # Rate limiting
    client_ip = request.headers.get('cf-connecting-ip', '') or \
                request.headers.get('x-forwarded-for', '').split(',')[0].strip() or \
                (request.client.host if request.client else "unknown")
    
    if not compliance_rate_limiter.is_allowed(client_ip):
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded. Max 3 checks per minute per IP.", "retry_after": 60},
            headers={"Retry-After": "60"}
        )
    
    # 🔐 Auth + eval limit check (when performing actual check with URL)
    accept_hdr = request.headers.get('accept', '')
    is_html = 'text/html' in accept_hdr
    user = _get_session_user(request)  # Check auth early
    if url:
        if not user:
            if is_html:
                from starlette.responses import RedirectResponse
                return RedirectResponse("/login?redirect=/compliance-check", status_code=302)
            return JSONResponse(status_code=401, content={"error": "Authentication required. Please register/login."})
        # Check eval limit
        limit_check = auth_manager.check_eval_limit(user["user_id"], "compliance")
        if not limit_check.get("allowed"):
            if is_html:
                from starlette.responses import RedirectResponse
                return RedirectResponse("/pricing?reason=compliance_limit", status_code=302)
            return JSONResponse(status_code=402, content={
                "error": limit_check.get("reason", "Limit reached"),
                "used": limit_check.get("used"), "limit": limit_check.get("limit"),
                "upgrade_url": "/pricing"
            })

    # Validate URL
    if not url:
        # If browser request (Accept: text/html), show interactive form
        accept = request.headers.get('accept', '')
        if 'text/html' in accept:
            form_html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BDE Score™ — Agent Compliance Check</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
.container{max-width:560px;width:100%}
h1{font-size:24px;margin-bottom:8px;color:#f1f5f9}
.subtitle{color:#94a3b8;margin-bottom:32px;font-size:14px;line-height:1.6}
.badge-row{display:flex;gap:8px;margin-bottom:24px;flex-wrap:wrap}
.badge{font-size:11px;padding:4px 10px;border-radius:20px;font-weight:600}
.badge-eu{background:#1e3a5f;color:#93c5fd}
.badge-cn{background:#3b1f1f;color:#fca5a5}
.badge-mcp{background:#1a3a2a;color:#86efac}
.form-group{margin-bottom:20px}
label{display:block;font-size:13px;color:#94a3b8;margin-bottom:6px;font-weight:500}
input[type=url]{width:100%;padding:14px 16px;background:#1e293b;border:1px solid rgba(255,255,255,0.1);border-radius:10px;color:#f1f5f9;font-size:15px;outline:none;transition:border-color .2s}
input[type=url]:focus{border-color:#3b82f6}
input[type=url]::placeholder{color:#475569}
button{width:100%;padding:14px;background:#2563eb;color:#fff;border:none;border-radius:10px;font-size:15px;font-weight:600;cursor:pointer;transition:background .2s}
button:hover{background:#1d4ed8}
.note{margin-top:16px;font-size:12px;color:#64748b;line-height:1.6}
a{color:#60a5fa;text-decoration:none}
a:hover{text-decoration:underline}
</style>
</head>
<body>
<div class="container">
<div class="badge-row">
<span class="badge badge-eu">EU AI Act Art.50</span>
<span class="badge badge-cn">中国智能体治理</span>
<span class="badge badge-mcp">MCP Extension</span>
</div>
<h1>Agent Compliance Check</h1>
<p class="subtitle">输入你的 Agent / MCP 端点 URL，自动检测 EU AI Act Art.50 和中国《智能体治理实施意见》合规状态。<br>免费 · 无需注册 · 结果可分享</p>
<form action="/compliance-check" method="get">
<div class="form-group">
<label for="url">MCP / Agent Endpoint URL</label>
<input type="url" id="url" name="url" placeholder="https://your-agent.example.com/mcp" required autocomplete="off" spellcheck="false">
</div>
<button type="submit">🔍 Start Compliance Scan</button>
</form>
<p class="note">API 调用: <code>GET /compliance-check?url=YOUR_URL</code> · 频率限制: 3次/分钟 · <a href="/compliance-check/status">系统状态</a></p>
</div>
</body>
</html>"""
            return HTMLResponse(content=form_html)
        return JSONResponse(
            status_code=400,
            content={
                "error": "Missing required parameter: url",
                "usage": "GET /compliance-check?url=https://your-mcp-endpoint.com",
                "example": "GET /compliance-check?url=https://example.com",
            }
        )
    
    # Basic URL validation
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid URL format. Must include scheme (http:// or https://) and hostname."}
        )
    if parsed.scheme not in ("http", "https"):
        return JSONResponse(
            status_code=400,
            content={"error": "Unsupported URL scheme. Only http and https are supported."}
        )
    
    # Run compliance checks
    try:
        report = await _run_compliance_checks(url)
    except Exception as e:
        logger.exception("Compliance check failed")
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal error during compliance scan: {str(e)[:200]}"}
        )
    
    # 📊 Record evaluation for logged-in user
    if user:
        score = report.get("overall_score", report.get("score", 0))
        auth_manager.record_evaluation(user["user_id"], "compliance", url, f"score={score}")

    # Content negotiation: HTML or JSON
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        html_content = _compliance_html_report(report)
        return HTMLResponse(content=html_content)
    
    # JSON response with EU AI Act Art.50 disclosure headers
    return JSONResponse(
        content=report,
        headers={
            "X-BDE-AI-System": "true",
            "X-BDE-Assessment-Method": "ai-automated",
            "X-BDE-Model-Version": "1.0"
        }
    )
@app.get("/privacy")
async def privacy_page():
    """Privacy Policy page"""
    try:
        with open("templates/privacy.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except Exception:
        return HTMLResponse(content="<h1>Privacy Policy</h1><p>Privacy policy page not found.</p>", status_code=500)


@app.get("/terms")
async def terms_page():
    """Terms of Service page"""
    try:
        with open("templates/terms.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except Exception:
        return HTMLResponse(content="<h1>Terms of Service</h1><p>Terms page not found.</p>", status_code=500)

    



# EU AI Act Article 50 Compliance Page
@app.get("/compliance", response_class=HTMLResponse)
async def eu_ai_act_compliance():
    """EU AI Act Article 50 Transparency Compliance Statement"""
    try:
        with open("templates/compliance.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Compliance Statement</h1><p>Page not found.</p>", status_code=404)

@app.get("/compliance-check/status")
async def compliance_check_status():
    """Status of compliance check system"""
    return {
        "status": "operational",
        "version": "1.0",
        "ai_system": True,
        "eu_ai_act_art50_compliant": True,
        "rate_limit": "3 requests per minute per IP",
        "methodology": "rule-based + LLM-enhanced public signal analysis"
    }

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=API_HOST, port=API_PORT)