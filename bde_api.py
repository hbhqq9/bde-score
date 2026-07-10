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
from datetime import datetime, timedelta
from typing import Optional
from contextlib import contextmanager
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn
from usdc_listener import USDCListener, PaymentActivator, BackgroundListener


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
    openapi_url=None,    # 🔒 禁用OpenAPI JSON
)

# USDC 支付系统全局实例
usdc_listener_instance = None
usdc_activator_instance = None
usdc_background_task = None

# ============================================================
# 🔒 安全中间件
# ============================================================
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """注入安全响应头，防止XSS/Clickjacking/Sniffing等攻击"""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        # 🔌 /widget 和 /embed 路径允许iframe嵌入（零账号分发机制）
        if request.url.path in ('/widget', '/embed/snippet'):
            response.headers["X-Frame-Options"] = "ALLOWALL"
            response.headers["Content-Security-Policy"] = "frame-ancestors *"
        else:
            response.headers["X-Frame-Options"] = "DENY"
        # 🔒 CORS 白名单（仅允许已知域名嵌入）
        allowed_origins = {
            "https://hbhqq9.github.io",
            "https://atlantic-remains-atomic-floor.trycloudflare.com",
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
        # 🔒 Inject disclaimer into all JSON analysis responses
        if (request.url.path.startswith('/api/')
                and 'application/json' in response.headers.get('content-type', '')
                and request.url.path not in ('/api/health', '/api/keys/list', '/api/payment/config', '/api/payment/chain-status')):
            try:
                # Read the streamed body
                body_chunks = []
                async for chunk in response.body_iterator:
                    body_chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode('utf-8'))
                raw_body = b''.join(body_chunks)
                
                body = json.loads(raw_body)
                if isinstance(body, dict) and 'disclaimer' not in body:
                    body['disclaimer'] = '⚠️ Technical analysis only. Not investment advice. Past performance does not guarantee future results.'
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

# ============================================================
# 🔒 速率限制器（内存级，防DoS）
# ============================================================
class RateLimiter:
    """简单滑动窗口速率限制"""
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        # 清理过期记录
        self.requests[client_ip] = [t for t in self.requests[client_ip] if now - t < self.window]
        if len(self.requests[client_ip]) >= self.max_requests:
            return False
        self.requests[client_ip].append(now)
        return True

rate_limiter = RateLimiter(max_requests=10, window_seconds=60)  # 每IP每分钟10次

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

key_manager = KeyManager()

# 🔑 API Key验证依赖
from fastapi import Header, Depends

async def optional_api_key(x_api_key: str = Header(None)):
    """可选API Key验证：有key走付费通道，无key走免费配额"""
    if x_api_key:
        tier = key_manager.verify(x_api_key)
        if tier:
            return {'authenticated': True, 'tier': tier}
    return {'authenticated': False, 'tier': 'free'}

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
    with sqlite3.connect(DB_PATH) as conn:
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
    with sqlite3.connect(DB_PATH) as conn:
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
        "iframe": '<iframe src="https://atlantic-remains-atomic-floor.trycloudflare.com/widget" width="420" height="420" frameborder="0" style="border-radius:12px;overflow:hidden;"></iframe>',
        "markdown": "[![BDE Score](https://atlantic-remains-atomic-floor.trycloudflare.com/widget)](https://atlantic-remains-atomic-floor.trycloudflare.com)",
        "badge": "[![BDE Score](https://img.shields.io/badge/BDE-Score-blue)](https://atlantic-remains-atomic-floor.trycloudflare.com)",
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
    """生成SVG分享卡片"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    w, h = 540, 80 + len(results) * 72 + 100
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#0f172a"/><stop offset="100%" stop-color="#1e293b"/></linearGradient></defs>
<rect width="{w}" height="{h}" rx="16" fill="url(#bg)"/>
<text x="24" y="36" font-family="system-ui" font-size="20" font-weight="700" fill="#f1f5f9">📊 {title}</text>
<text x="24" y="56" font-family="system-ui" font-size="12" fill="#64748b">{now}</text>
<rect x="24" y="66" width="80" height="3" rx="1.5" fill="#3b82f6"/>
'''
    for i, r in enumerate(results):
        sym = r.get('symbol', '?')
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
    market: str = Query("US", description="市场: US(美股), HK(港股), A(A股), ALL(全部)")
):
    """运行BDE多因子分析（🔒 带速率限制+并发锁+输入校验）"""
    # 🔒 输入白名单校验
    market_upper = market.upper().strip()
    if market_upper not in VALID_MARKETS:
        raise HTTPException(status_code=400, detail=f"Invalid market. Must be one of: {', '.join(sorted(VALID_MARKETS))}")
    
    # 🔒 速率限制
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 10 requests per minute.")
    
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
    client_ip = request.client.host if request.client else "unknown"
    # 🔒 限制：只允许本地调用
    if client_ip not in ('127.0.0.1', '::1'):
        raise HTTPException(status_code=403, detail="Forbidden. Internal use only.")
    
    if tier not in ('free', 'premium', 'institutional'):
        raise HTTPException(status_code=400, detail="Invalid tier. Must be: free, premium, or institutional.")
    
    key = key_manager.generate_key(tier=tier, email=email)
    return {"key": key, "tier": tier, "email": email}

@app.get("/api/keys/list")
async def list_keys(request: Request):
    """列出所有API Key（内部使用）— 仅显示prefix，不显示完整key"""
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
    client_ip = request.client.host if request.client else "unknown"
    if client_ip not in ('127.0.0.1', '::1'):
        raise HTTPException(status_code=403, detail="Forbidden. Internal use only.")
    
    if key_manager.revoke_by_prefix(key_prefix):
        return {"status": "revoked", "key_prefix": key_prefix}
    raise HTTPException(status_code=404, detail="Key not found by the given prefix.")

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
    
    with sqlite3.connect(DB_PATH) as conn:
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

@app.get("/payment", response_class=HTMLResponse)
async def payment_page(request: Request):
    """支付页面 - 用户发送USDC后自动激活API Key"""
    try:
        template_path = os.path.join(os.path.dirname(__file__), 'templates', 'payment.html')
        with open(template_path, 'r') as f:
            html = f.read()
        # 注入配置
        wallet = os.environ.get('BDE_WALLET_ADDRESS', '0x349Eea0E2f4d3594797851758325Da3eb49D4343')
        html = html.replace('{{ WALLET_ADDRESS }}', wallet)
        html = html.replace('{{ USDC_CONTRACT }}', '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913')
        html = html.replace('{{ PREMIUM_PRICE_USD }}', str(PAYMENT_PRICE_USD))
        html = html.replace('{{ API_BASE }}', str(request.base_url).rstrip('/'))
        return HTMLResponse(content=html)
    except Exception as e:
        return HTMLResponse(content=f"<h1>支付页面加载失败</h1><p>{str(e)}</p>", status_code=500)

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
    global usdc_activator_instance, usdc_listener_instance
    if not usdc_activator_instance:
        return {"status": "disabled", "message": "支付系统未启用"}
    
    body = await request.json()
    tx_hash = body.get("tx_hash")
    if not tx_hash:
        return {"error": "缺少 tx_hash"}
    
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
async def wallet_check():
    """检测钱包新转入"""
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


@app.get("/terms", response_class=HTMLResponse)
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


@app.get("/privacy", response_class=HTMLResponse)
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


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=API_HOST, port=API_PORT)