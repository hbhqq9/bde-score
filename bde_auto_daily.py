#!/usr/bin/env python3
"""
BDE-Stock 自动化每日运行脚本
=============================
完全自动化，不依赖任何外部服务（fetch_web/yfinance等）。

数据源：
  - 历史K线: 新浪财经 stock.finance.sina.com.cn (JSONP)
  - 实时行情: 新浪财经 hq.sinajs.cn (已确认可用)

功能：
  1. 自动获取14只股票50+日历史收盘价
  2. 自动获取14只股票实时行情
  3. 计算BDE五因子评分（动量30%+均值回归20%+量能20%+波动率15%+趋势15%）
  4. 生成BUY/HOLD/SELL信号
  5. 输出段永平风格模拟盘配置（$1M, 最多5只, 每只≤25%）
  6. 保存JSON结果

用法：
  python bde_auto_daily.py
  python bde_auto_daily.py --universe AAPL,MSFT,GOOGL
  python bde_auto_daily.py --days 60
  python bde_auto_daily.py --capital 2000000
"""

import sys
import os
import re
import json
import time
import logging
import argparse
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import requests

# ============================================================
# 日志配置
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('BDE-Auto')

# ============================================================
# 默认配置
# ============================================================
DEFAULT_UNIVERSE = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'V', 'MA',
    'JNJ', 'PG', 'TSLA', 'BABA', 'SPY', 'QQQ'
]

FACTOR_WEIGHTS = {
    'momentum': 0.30,
    'mean_reversion': 0.20,
    'volume': 0.20,
    'volatility': 0.15,
    'trend': 0.15,
}

# 段永平铁律
INITIAL_CAPITAL = 1_000_000
MAX_POSITIONS = 5
MAX_POSITION_PCT = 0.25
STOP_LOSS_PCT = -0.03
MAX_DRAWDOWN_PCT = -0.15
MIN_SCORE_BUY = 55

# 因子引擎参数（与 factor_engine.py 的 FactorConfig 一致）
MOMENTUM_PERIODS = [5, 10, 20, 60]
MEAN_REVERSION_WINDOW = 20
VOLUME_LOOKBACK = 20
VOLUME_SPIKE_THRESHOLD = 1.5
ATR_PERIOD = 14
VOLATILITY_WINDOW = 20
EMA_SHORT = 10
EMA_LONG = 50

# 网络配置
REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://finance.sina.com.cn',
}
REQUEST_TIMEOUT = 20
RATE_LIMIT_SLEEP = 0.3


# ============================================================
# 数据获取层
# ============================================================

def fetch_historical_kline(symbol: str, min_days: int = 120) -> Optional[pd.DataFrame]:
    """
    从新浪财经获取美股历史日K线数据。
    
    API: https://stock.finance.sina.com.cn/usstock/api/jsonp.php/var%20data=/US_MinKService.getDailyK
    返回: DataFrame with columns: date, open, high, low, close, volume
          index: date (DatetimeIndex)
    """
    sym_lower = symbol.lower()
    url = (
        f"https://stock.finance.sina.com.cn/usstock/api/jsonp.php/"
        f"var%20data=/US_MinKService.getDailyK"
        f"?symbol={sym_lower}&scale=240&datalen={min_days}"
    )
    
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            logger.warning(f"  {symbol}: HTTP {resp.status_code}")
            return None
        
        # 解析 JSONP: var data=([...])
        text = resp.text
        match = re.search(r'var data=\((.+)\)', text)
        if not match:
            # 尝试更宽松的解析
            match = re.search(r'\((\[.+\])\)', text)
        if not match:
            logger.warning(f"  {symbol}: JSONP解析失败")
            return None
        
        records = json.loads(match.group(1))
        if not records or len(records) == 0:
            logger.warning(f"  {symbol}: 无数据")
            return None
        
        # 取最后 min_days 条（API返回全部历史）
        records = records[-min_days:] if len(records) > min_days else records
        
        # 构建 DataFrame
        df = pd.DataFrame(records)
        df = df.rename(columns={
            'd': 'date', 'o': 'open', 'h': 'high',
            'l': 'low', 'c': 'close', 'v': 'volume'
        })
        
        # 类型转换
        for col in ['open', 'high', 'low', 'close']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        
        # 如果存在 'a' 列（调整后收盘价），可以忽略
        if 'a' in df.columns:
            df = df.drop(columns=['a'])
        
        # 确保列顺序
        df = df[['open', 'high', 'low', 'close', 'volume']]
        
        # 去除可能的NaN行
        df = df.dropna()
        
        return df
        
    except Exception as e:
        logger.warning(f"  {symbol}: {str(e)[:100]}")
        return None


def fetch_realtime_quotes(symbols: List[str]) -> Dict[str, dict]:
    """
    从新浪实时行情API获取报价。
    
    API: https://hq.sinajs.cn/list=gb_aapl,gb_msft,...
    返回: {symbol: {name, price, change, change_pct, volume, open, high, low, prev_close, timestamp}}
    """
    if not symbols:
        return {}
    
    # 构建symbol列表
    sina_symbols = ','.join([f'gb_{s.lower()}' for s in symbols])
    url = f"https://hq.sinajs.cn/list={sina_symbols}"
    
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            logger.warning(f"  实时行情请求失败: HTTP {resp.status_code}")
            return {}
        
        results = {}
        # 解析: var hq_str_gb_aapl="字段1,字段2,...";
        pattern = r'var hq_str_gb_(\w+)="(.+?)";'
        matches = re.findall(pattern, resp.text)
        
        for sym_lower, data_str in matches:
            fields = data_str.split(',')
            if len(fields) < 30:
                continue
            
            # 找到对应的原始symbol
            orig_sym = None
            for s in symbols:
                if s.lower() == sym_lower:
                    orig_sym = s
                    break
            if not orig_sym:
                orig_sym = sym_lower.upper()
            
            try:
                results[orig_sym] = {
                    'name': fields[0],
                    'price': float(fields[1]) if fields[1] else 0,
                    'change_pct': float(fields[2]) if fields[2] else 0,
                    'timestamp': fields[3],
                    'change': float(fields[4]) if fields[4] else 0,
                    'open': float(fields[5]) if fields[5] else 0,
                    'high': float(fields[6]) if fields[6] else 0,
                    'low': float(fields[7]) if fields[7] else 0,
                    'prev_close': float(fields[8]) if fields[8] else 0,
                    'volume': int(float(fields[10])) if fields[10] else 0,
                    'market_cap': float(fields[12]) if fields[12] else 0,
                    'eps': float(fields[13]) if fields[13] else 0,
                    'pe': float(fields[14]) if fields[14] else 0,
                }
            except (ValueError, IndexError) as e:
                logger.debug(f"  {orig_sym} 解析实时数据异常: {e}")
                continue
        
        return results
        
    except Exception as e:
        logger.warning(f"  实时行情获取失败: {str(e)[:100]}")
        return {}


def fetch_all_data(symbols: List[str], min_days: int = 120) -> Tuple[Dict[str, pd.DataFrame], Dict[str, dict]]:
    """
    获取所有股票的历史K线和实时行情。
    
    Returns:
        (historical_data, realtime_quotes)
    """
    logger.info(f"📊 获取 {len(symbols)} 只股票历史K线数据 (至少{min_days}天)...")
    historical = {}
    
    for i, sym in enumerate(symbols):
        df = fetch_historical_kline(sym, min_days)
        if df is not None and len(df) >= 30:
            historical[sym] = df
            logger.info(f"  ✅ {sym}: {len(df)}天 ({df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')})")
        else:
            n = len(df) if df is not None else 0
            logger.warning(f"  ❌ {sym}: 数据不足({n}天)")
        
        if i < len(symbols) - 1:
            time.sleep(RATE_LIMIT_SLEEP)
    
    logger.info(f"历史数据: {len(historical)}/{len(symbols)} 只股票可用")
    
    # 获取实时行情
    logger.info(f"📈 获取实时行情...")
    realtime = fetch_realtime_quotes(symbols)
    logger.info(f"实时行情: {len(realtime)}/{len(symbols)} 只股票可用")
    
    return historical, realtime


# ============================================================
# BDE 五因子计算引擎
# ============================================================

@dataclass
class FactorResult:
    """单只股票的因子评估结果"""
    symbol: str
    scores: Dict[str, float] = field(default_factory=dict)
    composite_score: float = 0.0
    signal: str = "HOLD"
    price: float = 0.0
    change_pct: float = 0.0
    details: Dict = field(default_factory=dict)


def calc_momentum(close: np.ndarray) -> float:
    """
    动量因子 (0~100)
    多周期收益率加权，近期权重更高。
    """
    scores = []
    for period in MOMENTUM_PERIODS:
        if len(close) < period + 1:
            scores.append(50.0)
            continue
        ret = (close[-1] / close[-period - 1] - 1) * 100
        score = np.clip(50 + ret * 4, 0, 100)
        scores.append(score)
    
    weights = [0.3, 0.3, 0.2, 0.2][:len(scores)]
    total_weight = sum(weights)
    return float(np.clip(
        sum(s * w for s, w in zip(scores, weights)) / total_weight, 0, 100
    ))


def calc_mean_reversion(close: np.ndarray) -> float:
    """
    均值回归因子 (0~100)
    价格偏离MA20的程度。偏离负向越大（跌多了）→ 分越高。
    """
    window = MEAN_REVERSION_WINDOW
    if len(close) < window:
        return 50.0
    
    ma = pd.Series(close).rolling(window).mean().iloc[-1]
    if ma == 0 or np.isnan(ma):
        return 50.0
    
    current = close[-1]
    deviation = (current - ma) / ma  # 偏离度
    # 偏离 -10% → 90分, 0% → 50分, +10% → 10分
    score = 50 - deviation * 400
    return float(np.clip(score, 0, 100))


def calc_volume(volume: np.ndarray) -> float:
    """
    成交量因子 (0~100)
    量比异常检测，衡量资金关注度。
    """
    lookback = VOLUME_LOOKBACK
    spike_threshold = VOLUME_SPIKE_THRESHOLD
    
    if len(volume) < lookback + 1:
        return 50.0
    
    avg_volume = np.mean(volume[-lookback - 1:-1])
    if avg_volume == 0:
        return 50.0
    
    volume_ratio = volume[-1] / avg_volume
    
    if volume_ratio < 0.5:
        score = 20 + volume_ratio * 60
    elif volume_ratio <= spike_threshold:
        score = 50 + (volume_ratio - 1) / (spike_threshold - 1) * 30
    else:
        score = 80 + min((volume_ratio - spike_threshold) / spike_threshold, 1) * 15
    
    return float(np.clip(score, 0, 100))


def calc_volatility(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> float:
    """
    波动率因子 (0~100)
    ATR + 收益率波动率。适度波动=高分，极端波动=低分。
    """
    if len(close) < max(ATR_PERIOD, VOLATILITY_WINDOW) + 1:
        return 50.0
    
    # 计算 True Range
    tr_list = []
    for i in range(1, len(close)):
        tr = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1])
        )
        tr_list.append(tr)
    
    atr = np.mean(tr_list[-ATR_PERIOD:]) if len(tr_list) >= ATR_PERIOD else (np.mean(tr_list) if tr_list else 0)
    atr_pct = atr / close[-1] if close[-1] > 0 else 0
    
    # 评分
    if atr_pct < 0.01:
        score = 60
    elif atr_pct < 0.03:
        score = 60 + (atr_pct - 0.01) / 0.02 * 20
    elif atr_pct < 0.05:
        score = 80 - (atr_pct - 0.03) / 0.02 * 30
    else:
        score = max(20, 50 - (atr_pct - 0.05) * 300)
    
    return float(np.clip(score, 0, 100))


def calc_trend(close_arr: np.ndarray) -> float:
    """
    趋势因子 (0~100)
    EMA交叉系统判断趋势方向和强度。
    """
    close = pd.Series(close_arr)
    
    if len(close) < EMA_LONG + 5:
        return 50.0
    
    ema_s = close.ewm(span=EMA_SHORT, adjust=False).mean()
    ema_l = close.ewm(span=EMA_LONG, adjust=False).mean()
    
    current = close.iloc[-1]
    es = ema_s.iloc[-1]
    el = ema_l.iloc[-1]
    es_prev = ema_s.iloc[-3]
    el_prev = ema_l.iloc[-3]
    
    # 趋势判断
    if current > es > el:
        score = 80
        if es_prev <= el_prev:
            score = 95  # 金叉
    elif current > el and es < el:
        score = 60  # 回调未破位
    elif current < es < el:
        score = 20
        if es_prev >= el_prev:
            score = 10  # 死叉
    elif current < el:
        score = 35
    else:
        score = 50
    
    # 趋势强度修正
    ema_spread = abs(es - el) / el if el > 0 else 0
    if ema_spread > 0.05:
        if es > el:
            score = min(100, score + 5)
        else:
            score = max(0, score - 5)
    
    return float(np.clip(score, 0, 100))


def generate_signal(composite: float, scores: dict) -> str:
    """
    根据综合得分生成交易信号。
    BUY: composite >= 70 AND trend >= 50
    SELL: composite <= 30 OR trend <= 15
    HOLD: otherwise
    """
    if composite >= 70 and scores.get('trend', 0) >= 50:
        return "BUY"
    elif composite <= 30 or scores.get('trend', 0) <= 15:
        return "SELL"
    else:
        return "HOLD"


def evaluate_all(historical: Dict[str, pd.DataFrame], realtime: Dict[str, dict]) -> List[FactorResult]:
    """
    对所有股票计算五因子评分。
    """
    results = []
    
    for symbol, df in historical.items():
        close = df['close'].values
        volume = df['volume'].values
        high = df['high'].values
        low = df['low'].values
        
        if len(close) < 30:
            logger.warning(f"  {symbol}: 数据不足30天，跳过")
            continue
        
        try:
            scores = {
                'momentum': calc_momentum(close),
                'mean_reversion': calc_mean_reversion(close),
                'volume': calc_volume(volume),
                'volatility': calc_volatility(high, low, close),
                'trend': calc_trend(close),
            }
            
            composite = sum(scores[k] * FACTOR_WEIGHTS[k] for k in FACTOR_WEIGHTS)
            signal = generate_signal(composite, scores)
            
            # 价格和涨跌幅
            price = close[-1]
            change_pct = (close[-1] / close[-2] - 1) * 100 if len(close) >= 2 else 0
            
            # 补充实时数据
            if symbol in realtime:
                rt = realtime[symbol]
                if rt['price'] > 0:
                    price = rt['price']
                if rt['change_pct'] != 0:
                    # change_pct from sina is already a percentage value (e.g., 0.90 means 0.90%)
                    change_pct = rt['change_pct']
            
            # 详细信息
            details = {
                'close': float(close[-1]),
                'ma20': float(pd.Series(close).rolling(20).mean().iloc[-1]),
                'volume_ratio': float(volume[-1] / pd.Series(volume).rolling(20).mean().iloc[-1])
                    if pd.Series(volume).rolling(20).mean().iloc[-1] > 0 else None,
                'ema10': float(pd.Series(close).ewm(span=10, adjust=False).mean().iloc[-1]),
                'ema50': float(pd.Series(close).ewm(span=50, adjust=False).mean().iloc[-1]) if len(close) >= 50 else None,
                'date_range': f"{df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}",
                'data_points': len(df),
            }
            
            result = FactorResult(
                symbol=symbol,
                scores=scores,
                composite_score=composite,
                signal=signal,
                price=price,
                change_pct=change_pct,
                details=details,
            )
            results.append(result)
            
        except Exception as e:
            logger.error(f"  {symbol} 因子计算失败: {e}")
            continue
    
    # 按综合得分排序
    results.sort(key=lambda x: -x.composite_score)
    return results


# ============================================================
# 段永平风格模拟盘
# ============================================================

@dataclass
class PortfolioPosition:
    symbol: str
    weight: float  # 0~1
    shares: int
    cost_basis: float
    score: float
    signal: str


def build_portfolio(
    results: List[FactorResult],
    realtime: Dict[str, dict],
    capital: float = INITIAL_CAPITAL,
    max_positions: int = MAX_POSITIONS,
    max_pct: float = MAX_POSITION_PCT,
) -> Dict:
    """
    构建段永平风格模拟盘：
    - 只做多，不做空
    - 不加杠杆
    - 最多5只
    - 每只最多25%
    - 选择综合分>=MIN_SCORE_BUY的信号为BUY的股票
    """
    # 筛选可买入的
    candidates = [r for r in results if r.signal == "BUY" and r.composite_score >= MIN_SCORE_BUY]
    
    if not candidates:
        logger.info("⚠️ 没有满足买入条件的股票，保持空仓")
        return {
            'positions': [],
            'cash': capital,
            'total_value': capital,
            'invested_pct': 0.0,
        }
    
    # 按综合分排序，取前max_positions只
    candidates = sorted(candidates, key=lambda x: -x.composite_score)[:max_positions]
    
    # 等权重分配（但不超过max_pct）
    n = len(candidates)
    weight = min(max_pct, 1.0 / n) if n > 0 else 0
    # 确保不超过100%
    total_weight = weight * n
    if total_weight > 0.95:  # 至少保留5%现金
        weight = 0.95 / n
    
    positions = []
    total_invested = 0
    
    for c in candidates:
        price = c.price
        if price <= 0:
            continue
        
        allocated = capital * weight
        shares = int(allocated / price)  # 美股可以买整股
        cost = shares * price
        
        positions.append(PortfolioPosition(
            symbol=c.symbol,
            weight=cost / capital if capital > 0 else 0,
            shares=shares,
            cost_basis=price,
            score=c.composite_score,
            signal=c.signal,
        ))
        total_invested += cost
    
    cash = capital - total_invested
    
    return {
        'positions': [
            {
                'symbol': p.symbol,
                'shares': p.shares,
                'weight_pct': round(p.weight * 100, 2),
                'cost_basis': round(p.cost_basis, 2),
                'amount': round(p.shares * p.cost_basis, 2),
                'score': round(p.score, 1),
                'signal': p.signal,
            }
            for p in positions
        ],
        'cash': round(cash, 2),
        'total_value': capital,
        'invested_pct': round(total_invested / capital * 100, 2) if capital > 0 else 0,
    }


# ============================================================
# 输出与保存
# ============================================================

def format_report(results: List[FactorResult], portfolio: Dict, realtime: Dict[str, dict]) -> str:
    """生成文本报告"""
    lines = []
    lines.append("=" * 70)
    lines.append("  BDE-Stock 五因子决策引擎 - 每日报告")
    lines.append(f"  运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)
    
    # 汇总表
    lines.append("")
    lines.append("📊 五因子评分汇总")
    lines.append("-" * 70)
    lines.append(f"{'Symbol':<8} {'综合分':>6} {'信号':>6} {'动量':>6} {'回归':>6} {'量能':>6} {'波动':>6} {'趋势':>6} {'价格':>10} {'涨跌%':>8}")
    lines.append("-" * 70)
    
    for r in results:
        signal_emoji = {'BUY': '🟢', 'HOLD': '🟡', 'SELL': '🔴'}.get(r.signal, '⚪')
        lines.append(
            f"{r.symbol:<8} {r.composite_score:>6.1f} {signal_emoji}{r.signal:>4} "
            f"{r.scores.get('momentum', 0):>6.1f} {r.scores.get('mean_reversion', 0):>6.1f} "
            f"{r.scores.get('volume', 0):>6.1f} {r.scores.get('volatility', 0):>6.1f} "
            f"{r.scores.get('trend', 0):>6.1f} "
            f"${r.price:>9.2f} {r.change_pct:>+7.2f}%"
        )
    
    # 模拟盘
    lines.append("")
    lines.append("💰 段永平风格模拟盘 ($1,000,000)")
    lines.append("-" * 70)
    
    if portfolio['positions']:
        lines.append(f"{'Symbol':<8} {'股数':>8} {'权重%':>8} {'成本':>10} {'金额':>14} {'评分':>6}")
        lines.append("-" * 70)
        for pos in portfolio['positions']:
            lines.append(
                f"{pos['symbol']:<8} {pos['shares']:>8} {pos['weight_pct']:>7.1f}% "
                f"${pos['cost_basis']:>9.2f} ${pos['amount']:>13,.2f} {pos['score']:>6.1f}"
            )
        lines.append("-" * 70)
        lines.append(f"  已投资: {portfolio['invested_pct']:.1f}%  |  现金: ${portfolio['cash']:,.2f}")
    else:
        lines.append("  （空仓 - 无满足买入条件的股票）")
        lines.append(f"  现金: ${portfolio['cash']:,.2f}")
    
    # 段永平投资原则提醒
    lines.append("")
    lines.append("📝 段永平投资原则提醒")
    lines.append("  • 买股票就是买公司，买公司就是买其未来现金流的折现值")
    lines.append("  • 不懂不做，能力圈之外的不碰")
    lines.append("  • 不做空、不加杠杆、不追涨")
    lines.append("  • 好公司、好价格、长期持有")
    
    lines.append("")
    lines.append("=" * 70)
    
    return "\n".join(lines)


def save_results(results: List[FactorResult], portfolio: Dict, realtime: Dict, 
                 historical_meta: Dict, output_dir: str) -> str:
    """保存JSON结果"""
    output = {
        'run_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'run_timestamp': datetime.now().isoformat(),
        'engine': 'BDE-Stock 五因子决策引擎',
        'version': '2.0-auto',
        'data_source': {
            'historical': '新浪财经 stock.finance.sina.com.cn',
            'realtime': '新浪财经 hq.sinajs.cn',
        },
        'factor_weights': FACTOR_WEIGHTS,
        'parameters': {
            'initial_capital': INITIAL_CAPITAL,
            'max_positions': MAX_POSITIONS,
            'max_position_pct': MAX_POSITION_PCT,
            'min_score_buy': MIN_SCORE_BUY,
            'momentum_periods': MOMENTUM_PERIODS,
            'ema_short': EMA_SHORT,
            'ema_long': EMA_LONG,
        },
        'stock_results': [],
        'portfolio': portfolio,
    }
    
    for r in results:
        stock_entry = {
            'symbol': r.symbol,
            'composite_score': round(r.composite_score, 2),
            'signal': r.signal,
            'price': round(r.price, 2),
            'change_pct': round(r.change_pct, 2),
            'factor_scores': {k: round(v, 2) for k, v in r.scores.items()},
            'details': r.details,
        }
        # 添加实时数据（如果有）
        if r.symbol in realtime:
            rt = realtime[r.symbol]
            stock_entry['realtime'] = {
                'name': rt.get('name', ''),
                'price': rt.get('price', 0),
                'change_pct': rt.get('change_pct', 0),
                'pe': rt.get('pe', 0),
                'market_cap': rt.get('market_cap', 0),
                'timestamp': rt.get('timestamp', ''),
            }
        # 添加历史数据摘要
        if r.symbol in historical_meta:
            stock_entry['historical'] = historical_meta[r.symbol]
        
        output['stock_results'].append(stock_entry)
    
    filepath = os.path.join(output_dir, 'bde_auto_result.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    
    logger.info(f"✅ 结果已保存: {filepath}")
    return filepath


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='BDE-Stock 自动化每日运行')
    parser.add_argument('--universe', type=str, default=None,
                        help='股票代码列表，逗号分隔。默认: AAPL,MSFT,GOOGL,AMZN,META,NVDA,V,MA,JNJ,PG,TSLA,BABA,SPY,QQQ')
    parser.add_argument('--days', type=int, default=120,
                        help='历史数据天数（默认120）')
    parser.add_argument('--capital', type=float, default=INITIAL_CAPITAL,
                        help=f'模拟盘资金（默认{INITIAL_CAPITAL:,.0f}）')
    parser.add_argument('--max-positions', type=int, default=MAX_POSITIONS,
                        help=f'最大持仓数（默认{MAX_POSITIONS}）')
    parser.add_argument('--output-dir', type=str, default=None,
                        help='输出目录（默认: 脚本所在目录）')
    
    args = parser.parse_args()
    
    # 解析股票列表
    if args.universe:
        symbols = [s.strip().upper() for s in args.universe.split(',')]
    else:
        symbols = DEFAULT_UNIVERSE
    
    # 输出目录
    output_dir = args.output_dir or os.path.dirname(os.path.abspath(__file__))
    
    logger.info("=" * 60)
    logger.info("  BDE-Stock 五因子决策引擎 - 自动化运行")
    logger.info(f"  股票池: {', '.join(symbols)}")
    logger.info(f"  历史天数: {args.days}")
    logger.info(f"  模拟资金: ${args.capital:,.0f}")
    logger.info("=" * 60)
    
    # Step 1: 获取数据
    historical, realtime = fetch_all_data(symbols, args.days)
    
    if not historical:
        logger.error("❌ 无法获取任何历史数据，退出")
        sys.exit(1)
    
    # 记录历史数据摘要
    historical_meta = {}
    for sym, df in historical.items():
        historical_meta[sym] = {
            'date_range': f"{df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}",
            'data_points': len(df),
            'last_close': float(df['close'].iloc[-1]),
            'last_date': df.index[-1].strftime('%Y-%m-%d'),
        }
    
    # Step 2: 计算五因子
    logger.info("🧮 计算五因子评分...")
    results = evaluate_all(historical, realtime)
    logger.info(f"完成: {len(results)} 只股票已评分")
    
    # Step 3: 构建模拟盘
    logger.info("💰 构建段永平风格模拟盘...")
    portfolio = build_portfolio(results, realtime, capital=args.capital, max_positions=args.max_positions)
    
    # Step 4: 输出报告
    report = format_report(results, portfolio, realtime)
    print("\n" + report)
    
    # Step 5: 保存结果
    filepath = save_results(results, portfolio, realtime, historical_meta, output_dir)
    
    # 同时保存文本报告
    report_path = os.path.join(output_dir, 'bde_auto_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    logger.info(f"✅ 报告已保存: {report_path}")
    
    return results, portfolio


if __name__ == '__main__':
    main()
