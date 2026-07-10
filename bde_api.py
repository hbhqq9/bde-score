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
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn


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

# ============================================================
# 🔒 安全中间件
# ============================================================
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """注入安全响应头，防止XSS/Clickjacking/Sniffing等攻击"""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        # CORS: 仅允许同源 + Cloudflare
        response.headers["Access-Control-Allow-Origin"] = "*"  # Dashboard需要跨域; 生产环境应限制
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
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
    """通过新浪财经获取数据（备用）- 支持美股/港股/A股"""
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
                # 美股: US.AAPL -> aapl
                sina_sym = code.lower()
                url = f'https://stock.finance.sina.com.cn/usstock/api/jsonp.php/var%20data=/US_MinKService.getDailyK?symbol={sina_sym}&scale=240&datalen={days}'
            elif market == 'HK':
                # 港股: HK.00700 -> rt_hk00700
                sina_sym = f'rt_hk{code}'
                url = f'https://stock.finance.sina.com.cn/hkstock/api/jsonp.php/var%20data=/HK_KlineService.getDailyK?symbol={code}&scale=240&datalen={days}'
            elif market in ('SH', 'SZ'):
                # A股: SH.600519 -> sh600519
                sina_sym = f'{market.lower()}{code}'
                url = f'https://stock.finance.sina.com.cn/usstock/api/jsonp.php/var%20data=/CN_MinKService.getDailyK?symbol={sina_sym}&scale=240&datalen={days}'
            else:
                errors.append(f"{futu_code}: 未知市场{market}")
                continue
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                text = resp.read().decode('utf-8')
                # 解析 JSONP
                json_str = text[text.index('([') + 1:text.rindex('])') + 1]
                raw = json.loads(json_str)
                
                if raw:
                    df = pd.DataFrame(raw, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
                    for col in ['open', 'high', 'low', 'close']:
                        df[col] = df[col].astype(float)
                    df['volume'] = df['volume'].astype(float)
                    all_klines[short_name] = df
                    prices[short_name] = float(df.iloc[-1]['close'])
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
async def api_snapshot(market: str = Query("US", description="市场: US/HK/A/ALL")):
    """获取最新缓存结果（不重新计算）"""
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
    """系统健康检查"""
    import subprocess
    
    # FutuOpenD状态
    result = subprocess.run(['pgrep', '-f', 'FutuOpenD'], capture_output=True, text=True)
    futu_running = result.returncode == 0
    
    # 数据库状态
    db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
    
    # 缓存状态
    cache_age = None
    if _cache['timestamp']:
        cache_age = round((datetime.now() - _cache['timestamp']).total_seconds())
    
    return {
        'status': 'healthy',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'futu_opend': 'running' if futu_running else 'stopped',
        'database': {'exists': os.path.exists(DB_PATH), 'size_bytes': db_size},
        'cache': {'valid': _cache['data'] is not None, 'age_seconds': cache_age},
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


# ============================================================
# 启动
# ============================================================
@app.on_event("startup")
async def startup():
    init_db()
    logger.info(f"BDE Score™ API 启动 — 绑定 {API_HOST}:{API_PORT}（🔒 安全模式）")
    logger.info(f"Dashboard: http://localhost:{API_PORT}/")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=API_HOST, port=API_PORT)
