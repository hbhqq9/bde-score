#!/usr/bin/env python3
"""
BDE-Stock 每日分析脚本
======================
段永平风格五因子决策引擎 - 自动化数据管道版本

架构设计：
  模块A (主路径): 预填充历史数据 JSON 文件 (由主Agent通过fetch_web从stockanalysis.com获取)
  模块B (补充):   新浪实时行情API (Python requests直连)

数据流：
  1. 加载历史OHLCV数据 (从JSON文件)
  2. 获取实时行情 (新浪API)
  3. 计算五因子评分
  4. 生成交易信号 + 模拟盘配置
  5. 输出JSON结果 + 终端摘要

使用方法：
  # 方式1: 使用预填充历史数据文件运行
  python3 bde_stock_daily.py --history history_data.json

  # 方式2: 独立运行 (需要网络可用)
  python3 bde_stock_daily.py

  # 方式3: 指定输出路径
  python3 bde_stock_daily.py --history history_data.json --output /path/to/output.json
"""

import json
import sys
import os
import argparse
import logging
import math
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

import requests

# ============================================================
# 配置
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 股票池 (14只)
STOCK_UNIVERSE = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA',
    'V', 'MA', 'JNJ', 'PG', 'TSLA', 'BABA',
    'SPY', 'QQQ'
]

# stockanalysis.com URL模板
STOCKANALYSIS_URL_TPL = "https://stockanalysis.com/stocks/{symbol}/history/"

# 新浪实时行情API
SINA_API_URL = "https://hq.sinajs.cn/list={symbols}"
SINA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://finance.sina.com.cn/"
}

# 五因子权重
FACTOR_WEIGHTS = {
    'momentum': 0.30,
    'mean_reversion': 0.20,
    'volume': 0.20,
    'volatility': 0.15,
    'trend': 0.15,
}

# 信号阈值
BUY_THRESHOLD = 65
HOLD_THRESHOLD = 50

# 段永平风格模拟盘参数
PORTFOLIO_CONFIG = {
    'initial_capital': 1_000_000,
    'max_positions': 5,
    'max_single_pct': 0.25,  # 单只最大25%
}

# 日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('bde_daily')


# ============================================================
# 数据结构
# ============================================================

@dataclass
class StockHistory:
    """单只股票的历史OHLCV数据"""
    symbol: str
    dates: List[str] = field(default_factory=list)
    opens: List[float] = field(default_factory=list)
    highs: List[float] = field(default_factory=list)
    lows: List[float] = field(default_factory=list)
    closes: List[float] = field(default_factory=list)
    volumes: List[float] = field(default_factory=list)

    def __len__(self):
        return len(self.closes)

    def to_dict(self):
        return {
            'symbol': self.symbol,
            'dates': self.dates,
            'opens': self.opens,
            'highs': self.highs,
            'lows': self.lows,
            'closes': self.closes,
            'volumes': self.volumes,
        }


@dataclass
class SinaQuote:
    """新浪实时行情数据"""
    symbol: str
    name: str = ""
    price: float = 0.0
    change_pct: float = 0.0
    timestamp: str = ""
    change_amt: float = 0.0
    open_price: float = 0.0
    high: float = 0.0
    low: float = 0.0
    high_52w: float = 0.0
    low_52w: float = 0.0
    volume: float = 0.0


@dataclass
class FactorScores:
    """五因子评分结果"""
    symbol: str
    momentum: float = 0.0
    mean_reversion: float = 0.0
    volume_factor: float = 0.0
    volatility: float = 0.0
    trend: float = 0.0
    composite: float = 0.0
    signal: str = "HOLD"

    def to_dict(self):
        return {
            'momentum': round(self.momentum, 2),
            'mean_reversion': round(self.mean_reversion, 2),
            'volume': round(self.volume_factor, 2),
            'volatility': round(self.volatility, 2),
            'trend': round(self.trend, 2),
        }


# ============================================================
# 模块A: 历史数据加载
# ============================================================

def load_history_from_json(filepath: str) -> Dict[str, StockHistory]:
    """
    从预填充的JSON文件加载历史数据。

    JSON格式支持两种：
    1. { "AAPL": { "dates": [...], "opens": [...], ... }, ... }
    2. { "AAPL": [ {"date":"...", "open":..., "high":..., "low":..., "close":..., "volume":...}, ... ], ... }

    Args:
        filepath: JSON文件路径

    Returns:
        Dict[str, StockHistory]: 每只股票的历史数据
    """
    logger.info(f"加载历史数据: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    result = {}

    for symbol, data in raw.items():
        symbol = symbol.upper()

        if isinstance(data, dict):
            # 格式1: 已经是列式结构
            if 'closes' in data and len(data.get('closes', [])) > 0:
                history = StockHistory(
                    symbol=symbol,
                    dates=data.get('dates', []),
                    opens=[float(x) for x in data.get('opens', [])],
                    highs=[float(x) for x in data.get('highs', [])],
                    lows=[float(x) for x in data.get('lows', [])],
                    closes=[float(x) for x in data['closes']],
                    volumes=[float(x) for x in data.get('volumes', [])],
                )
                if len(history) >= 10:
                    result[symbol] = history
                    logger.info(f"  {symbol}: {len(history)} 条数据")
            # 格式2: 行式结构 [{"date":..., "open":..., ...}, ...]
            elif 'rows' in data:
                rows = data['rows']
                history = StockHistory(symbol=symbol)
                for row in rows:
                    history.dates.append(row.get('date', ''))
                    history.opens.append(float(row.get('open', 0)))
                    history.highs.append(float(row.get('high', 0)))
                    history.lows.append(float(row.get('low', 0)))
                    history.closes.append(float(row.get('close', 0)))
                    history.volumes.append(float(row.get('volume', 0)))
                if len(history) >= 10:
                    result[symbol] = history
                    logger.info(f"  {symbol}: {len(history)} 条数据 (rows)")
            else:
                # 尝试从 OHLCV 对象列表解析
                try:
                    rows_list = data.get('data', data.get('history', []))
                    if isinstance(rows_list, list) and len(rows_list) > 0:
                        history = StockHistory(symbol=symbol)
                        for row in rows_list:
                            history.dates.append(str(row.get('date', row.get('Date', ''))))
                            history.opens.append(float(row.get('open', row.get('Open', 0))))
                            history.highs.append(float(row.get('high', row.get('High', 0))))
                            history.lows.append(float(row.get('low', row.get('Low', 0))))
                            history.closes.append(float(row.get('close', row.get('Close', 0))))
                            history.volumes.append(float(row.get('volume', row.get('Volume', 0))))
                        if len(history) >= 10:
                            result[symbol] = history
                            logger.info(f"  {symbol}: {len(history)} 条数据 (auto)")
                except Exception as e:
                    logger.warning(f"  {symbol}: 解析失败 - {e}")

        elif isinstance(data, list):
            # 格式3: 直接是行列表
            history = StockHistory(symbol=symbol)
            for row in data:
                if isinstance(row, dict):
                    history.dates.append(str(row.get('date', row.get('Date', ''))))
                    history.opens.append(float(row.get('open', row.get('Open', 0))))
                    history.highs.append(float(row.get('high', row.get('High', 0))))
                    history.lows.append(float(row.get('low', row.get('Low', 0))))
                    history.closes.append(float(row.get('close', row.get('Close', 0))))
                    history.volumes.append(float(row.get('volume', row.get('Volume', 0))))
            if len(history) >= 10:
                result[symbol] = history
                logger.info(f"  {symbol}: {len(history)} 条数据 (list)")

    logger.info(f"成功加载 {len(result)}/{len(raw)} 只股票的历史数据")
    return result


def parse_stockanalysis_text(text: str, symbol: str) -> Optional[StockHistory]:
    """
    解析 stockanalysis.com 返回的文本中的历史数据表格。

    表格格式:
    | Date | Open | High | Low | Close | Adj. Close | Change | Volume |
    | Jul 9, 2026 | 310.51 | 316.53 | 308.16 | 316.22 | 316.22 | 0.90% | 48,095,310 |

    Args:
        text: stockanalysis.com 页面的文本内容
        symbol: 股票代码

    Returns:
        StockHistory 或 None
    """
    history = StockHistory(symbol=symbol)

    # 匹配表格行: | date | open | high | low | close | adj_close | change | volume |
    # 使用正则匹配每一行数据
    table_pattern = re.compile(
        r'\|\s*'
        r'(\w+\s+\d{1,2},\s+\d{4})\s*\|\s*'   # Date: Jul 9, 2026
        r'([\d,.]+)\s*\|\s*'                      # Open
        r'([\d,.]+)\s*\|\s*'                      # High
        r'([\d,.]+)\s*\|\s*'                      # Low
        r'([\d,.]+)\s*\|\s*'                      # Close
        r'([\d,.]+)\s*\|\s*'                      # Adj. Close
        r'([-\d,.]+%)\s*\|\s*'                    # Change
        r'([\d,.]+)\s*\|'                          # Volume
    )

    for match in table_pattern.finditer(text):
        try:
            date_str = match.group(1)
            open_p = float(match.group(2).replace(',', ''))
            high_p = float(match.group(3).replace(',', ''))
            low_p = float(match.group(4).replace(',', ''))
            close_p = float(match.group(5).replace(',', ''))
            # adj_close = match.group(6)  # 暂不使用
            # change = match.group(7)  # 暂不使用
            volume = float(match.group(8).replace(',', ''))

            history.dates.append(date_str)
            history.opens.append(open_p)
            history.highs.append(high_p)
            history.lows.append(low_p)
            history.closes.append(close_p)
            history.volumes.append(volume)
        except (ValueError, IndexError):
            continue

    if len(history) >= 10:
        logger.info(f"  解析 {symbol}: {len(history)} 条OHLCV数据")
        return history
    else:
        logger.warning(f"  解析 {symbol}: 仅 {len(history)} 条数据，不足")
        return None


def load_fetched_data(filepath: str) -> Dict[str, StockHistory]:
    """
    加载fetch_web获取并解析后的数据文件。

    这是主Agent用fetch_web获取stockanalysis.com页面后，
    解析成标准格式保存的JSON文件。

    格式: { "AAPL": {"dates":[...], "opens":[...], "highs":[...], "lows":[...], "closes":[...], "volumes":[...]}, ... }
    """
    logger.info(f"加载fetch_web预解析数据: {filepath}")
    return load_history_from_json(filepath)


# ============================================================
# 模块B: 新浪实时行情
# ============================================================

def fetch_sina_quotes(symbols: List[str]) -> Dict[str, SinaQuote]:
    """
    从新浪API获取实时行情数据。

    URL格式: https://hq.sinajs.cn/list=gb_aapl,gb_msft,...
    返回格式: var hq_str_gb_aapl="名称,当前价,涨跌%,..."

    Args:
        symbols: 股票代码列表

    Returns:
        Dict[str, SinaQuote]: 实时行情数据
    """
    # 构造新浪API的股票代码 (前缀 gb_)
    sina_symbols = ','.join([f"gb_{s.lower()}" for s in symbols])
    url = SINA_API_URL.format(symbols=sina_symbols)

    logger.info(f"获取新浪实时行情: {len(symbols)} 只股票")

    try:
        resp = requests.get(url, headers=SINA_HEADERS, timeout=15)
        resp.encoding = 'gbk'
        text = resp.text
    except Exception as e:
        logger.error(f"新浪API请求失败: {e}")
        return {}

    result = {}

    # 解析返回数据
    # 格式: var hq_str_gb_aapl="Apple,220.50,1.23,..."
    pattern = re.compile(r'var hq_str_gb_(\w+)="([^"]*)"')

    for match in pattern.finditer(text):
        try:
            symbol = match.group(1).upper()
            data_str = match.group(2)

            if not data_str:
                continue

            parts = data_str.split(',')
            if len(parts) < 11:
                continue

            quote = SinaQuote(
                symbol=symbol,
                name=parts[0],
                price=float(parts[1]) if parts[1] else 0.0,
                change_pct=float(parts[2]) if parts[2] else 0.0,
                timestamp=parts[3],
                change_amt=float(parts[4]) if parts[4] else 0.0,
                open_price=float(parts[5]) if parts[5] else 0.0,
                high=float(parts[6]) if parts[6] else 0.0,
                low=float(parts[7]) if parts[7] else 0.0,
                high_52w=float(parts[8]) if parts[8] else 0.0,
                low_52w=float(parts[9]) if parts[9] else 0.0,
                volume=float(parts[10]) if parts[10] else 0.0,
            )

            result[symbol] = quote
        except (ValueError, IndexError) as e:
            logger.warning(f"  解析 {match.group(1)} 失败: {e}")
            continue

    logger.info(f"成功获取 {len(result)}/{len(symbols)} 只股票的实时行情")
    return result


# ============================================================
# 五因子计算引擎
# ============================================================

def calc_momentum(history: StockHistory) -> float:
    """
    动量因子 (30%)
    逻辑: 20日收益率，归一化到0-100
    收益率越高 → 分数越高
    """
    closes = history.closes
    if len(closes) < 21:
        return 50.0

    # 20日收益率
    ret_20d = (closes[-1] / closes[-21] - 1) * 100

    # 5日收益率 (辅助确认)
    ret_5d = (closes[-1] / closes[-6] - 1) * 100 if len(closes) >= 6 else 0

    # 映射到0-100: -15%→10分, 0%→50分, +15%→90分
    score_20d = 50 + ret_20d * (40 / 15)
    score_5d = 50 + ret_5d * (40 / 15)

    # 综合: 20日为主(70%)，5日为辅(30%)
    composite = score_20d * 0.7 + score_5d * 0.3

    return max(0, min(100, composite))


def calc_mean_reversion(history: StockHistory, sina_quote: Optional[SinaQuote] = None) -> float:
    """
    均值回归因子 (20%)
    逻辑: 52周区间位置(越低越安全)，归一化到0-100
    价格越接近52周低点 → 分数越高 (安全边际)
    """
    closes = history.closes

    # 尝试用新浪的52周高低点
    if sina_quote and sina_quote.high_52w > 0 and sina_quote.low_52w > 0:
        high_52w = sina_quote.high_52w
        low_52w = sina_quote.low_52w
    elif len(closes) >= 50:
        # 用历史数据估算52周 (约252个交易日，取可用的最长)
        available = closes[-min(252, len(closes)):]
        high_52w = max(available)
        low_52w = min(available)
    else:
        high_52w = max(closes)
        low_52w = min(closes)

    current = closes[-1]

    if high_52w == low_52w:
        return 50.0

    # 在52周区间中的位置: 0=最低点, 100=最高点
    position = (current - low_52w) / (high_52w - low_52w) * 100

    # 反转: 越低越安全 → 分数越高
    # position=0 (在52周低点) → 100分
    # position=50 → 50分
    # position=100 (在52周高点) → 0分
    score = 100 - position

    return max(0, min(100, score))


def calc_volume_factor(history: StockHistory, sina_quote: Optional[SinaQuote] = None) -> float:
    """
    量能因子 (20%)
    逻辑: 当日成交量/20日平均成交量，归一化到0-100
    量比越高 → 分数越高 (资金关注度)
    """
    volumes = history.volumes
    if len(volumes) < 5:
        return 50.0

    # 20日平均成交量
    vol_20d = volumes[-min(20, len(volumes)):]
    avg_vol = sum(vol_20d) / len(vol_20d)

    # 当日成交量 (优先用新浪实时数据)
    if sina_quote and sina_quote.volume > 0:
        current_vol = sina_quote.volume
    else:
        current_vol = volumes[-1]

    if avg_vol == 0:
        return 50.0

    volume_ratio = current_vol / avg_vol

    # 映射到0-100:
    # ratio < 0.3 → 10分 (极度缩量)
    # ratio = 0.5 → 30分
    # ratio = 1.0 → 50分 (正常)
    # ratio = 1.5 → 70分
    # ratio = 2.0 → 85分
    # ratio >= 3.0 → 100分 (极度活跃)
    if volume_ratio < 0.3:
        score = 10
    elif volume_ratio < 1.0:
        score = 10 + (volume_ratio - 0.3) / 0.7 * 40
    elif volume_ratio < 2.0:
        score = 50 + (volume_ratio - 1.0) / 1.0 * 35
    elif volume_ratio < 3.0:
        score = 85 + (volume_ratio - 2.0) / 1.0 * 10
    else:
        score = 95 + min((volume_ratio - 3.0) / 2.0, 1) * 5

    return max(0, min(100, score))


def calc_volatility(history: StockHistory) -> float:
    """
    波动率因子 (15%)
    逻辑: 20日收益率标准差(越低越好)，归一化到0-100
    波动率越低 → 分数越高 (稳定性)
    """
    closes = history.closes
    if len(closes) < 21:
        return 50.0

    # 计算20日对数收益率
    returns = []
    for i in range(-20, 0):
        if closes[i - 1] > 0 and closes[i] > 0:
            r = math.log(closes[i] / closes[i - 1])
            returns.append(r)

    if len(returns) < 5:
        return 50.0

    # 标准差
    mean_r = sum(returns) / len(returns)
    variance = sum((r - mean_r) ** 2 for r in returns) / len(returns)
    std_dev = math.sqrt(variance)

    # 年化波动率
    annual_vol = std_dev * math.sqrt(252)

    # 映射到0-100: 波动率越低 → 分数越高
    # annual_vol < 0.10 → 90分 (非常稳定)
    # annual_vol = 0.20 → 70分
    # annual_vol = 0.35 → 50分
    # annual_vol = 0.50 → 30分
    # annual_vol > 0.70 → 10分 (极度波动)
    if annual_vol < 0.10:
        score = 90
    elif annual_vol < 0.20:
        score = 90 - (annual_vol - 0.10) / 0.10 * 20
    elif annual_vol < 0.35:
        score = 70 - (annual_vol - 0.20) / 0.15 * 20
    elif annual_vol < 0.50:
        score = 50 - (annual_vol - 0.35) / 0.15 * 20
    elif annual_vol < 0.70:
        score = 30 - (annual_vol - 0.50) / 0.20 * 20
    else:
        score = max(10, 10 - (annual_vol - 0.70) * 20)

    return max(0, min(100, score))


def calc_trend(history: StockHistory) -> float:
    """
    趋势因子 (15%)
    逻辑: 价格vs20日均线的位置，归一化到0-100
    价格在均线上方越多 → 分数越高
    """
    closes = history.closes
    if len(closes) < 20:
        return 50.0

    # 20日均线
    ma20 = sum(closes[-20:]) / 20

    current = closes[-1]

    if ma20 == 0:
        return 50.0

    # 偏离度: (当前价 - MA20) / MA20
    deviation = (current - ma20) / ma20

    # 映射到0-100:
    # deviation < -10% → 20分 (远低于均线，趋势弱)
    # deviation = -5% → 35分
    # deviation = 0% → 50分 (在均线上)
    # deviation = +5% → 70分
    # deviation = +10% → 85分
    # deviation > +15% → 95分
    if deviation < -0.10:
        score = 10 + max(deviation + 0.10, -0.20) / 0.20 * 10
    elif deviation < 0:
        score = 20 + (deviation + 0.10) / 0.10 * 30
    elif deviation < 0.05:
        score = 50 + deviation / 0.05 * 20
    elif deviation < 0.10:
        score = 70 + (deviation - 0.05) / 0.05 * 15
    elif deviation < 0.15:
        score = 85 + (deviation - 0.10) / 0.05 * 10
    else:
        score = min(100, 95 + (deviation - 0.15) / 0.10 * 5)

    return max(0, min(100, score))


def calculate_factors(
    history: StockHistory,
    sina_quote: Optional[SinaQuote] = None
) -> FactorScores:
    """
    计算单只股票的五因子综合评分

    Args:
        history: 历史OHLCV数据
        sina_quote: 新浪实时行情 (可选)

    Returns:
        FactorScores: 五因子评分结果
    """
    scores = FactorScores(symbol=history.symbol)

    scores.momentum = calc_momentum(history)
    scores.mean_reversion = calc_mean_reversion(history, sina_quote)
    scores.volume_factor = calc_volume_factor(history, sina_quote)
    scores.volatility = calc_volatility(history)
    scores.trend = calc_trend(history)

    # 加权合成
    scores.composite = (
        scores.momentum * FACTOR_WEIGHTS['momentum'] +
        scores.mean_reversion * FACTOR_WEIGHTS['mean_reversion'] +
        scores.volume_factor * FACTOR_WEIGHTS['volume'] +
        scores.volatility * FACTOR_WEIGHTS['volatility'] +
        scores.trend * FACTOR_WEIGHTS['trend']
    )

    # 生成信号
    if scores.composite > BUY_THRESHOLD:
        scores.signal = "BUY"
    elif scores.composite >= HOLD_THRESHOLD:
        scores.signal = "HOLD"
    else:
        scores.signal = "SELL"

    return scores


# ============================================================
# 模拟盘管理
# ============================================================

def build_portfolio(
    all_scores: List[FactorScores],
    sina_quotes: Dict[str, SinaQuote]
) -> dict:
    """
    构建段永平风格模拟盘

    规则:
    - 只买入BUY信号的股票
    - 最多5只持仓
    - 每只最多25%仓位
    - 按综合评分排序分配资金
    - 初始资金 $1,000,000

    Args:
        all_scores: 所有股票的五因子评分
        sina_quotes: 实时行情

    Returns:
        dict: 模拟盘配置
    """
    initial_capital = PORTFOLIO_CONFIG['initial_capital']
    max_positions = PORTFOLIO_CONFIG['max_positions']
    max_single_pct = PORTFOLIO_CONFIG['max_single_pct']

    # 筛选BUY信号的股票，按评分排序
    buy_candidates = sorted(
        [s for s in all_scores if s.signal == "BUY"],
        key=lambda x: -x.composite
    )

    # 最多取前max_positions只
    selected = buy_candidates[:max_positions]

    if not selected:
        return {
            'initial': initial_capital,
            'total': initial_capital,
            'return_pct': 0.0,
            'cash': initial_capital,
            'positions': {},
            'trades': [],
            'selected': [],
        }

    # 等权分配，但不超过单只25%
    n = len(selected)
    alloc_pct = min(1.0 / n, max_single_pct)
    alloc_amount = initial_capital * alloc_pct

    positions = {}
    trades = []
    total_invested = 0.0

    for score in selected:
        symbol = score.symbol
        # 获取当前价格
        if symbol in sina_quotes and sina_quotes[symbol].price > 0:
            price = sina_quotes[symbol].price
        else:
            # 没有实时价格，跳过
            continue

        qty = int(alloc_amount / price)
        if qty <= 0:
            continue

        cost = qty * price
        positions[symbol] = {
            'qty': qty,
            'avg': round(price, 4),
            'cost': round(cost, 2),
            'score': round(score.composite, 2),
        }
        trades.append({
            'action': 'BUY',
            'symbol': symbol,
            'qty': qty,
            'price': round(price, 4),
            'cost': round(cost, 2),
        })
        total_invested += cost

    cash = initial_capital - total_invested
    total_value = initial_capital  # 初始时 total = initial
    return_pct = 0.0

    return {
        'initial': initial_capital,
        'total': round(total_value, 2),
        'return_pct': round(return_pct, 4),
        'cash': round(cash, 2),
        'positions': positions,
        'trades': trades,
        'selected': [s.symbol for s in selected],
    }


# ============================================================
# 主流程
# ============================================================

def run_analysis(
    history_data: Dict[str, StockHistory],
    sina_quotes: Dict[str, SinaQuote]
) -> dict:
    """
    运行完整的五因子分析流程

    Args:
        history_data: 历史OHLCV数据
        sina_quotes: 实时行情

    Returns:
        dict: 完整分析结果
    """
    now = datetime.now(timezone(timedelta(hours=-4)))  # EST
    timestamp = now.isoformat()

    all_scores = []
    results = []

    for symbol in STOCK_UNIVERSE:
        if symbol not in history_data:
            logger.warning(f"{symbol}: 无历史数据，跳过")
            continue

        history = history_data[symbol]
        sina_q = sina_quotes.get(symbol)

        # 计算五因子
        scores = calculate_factors(history, sina_q)
        all_scores.append(scores)

        # 构建结果
        result = {
            'symbol': symbol,
            'score': round(scores.composite, 2),
            'scores': scores.to_dict(),
            'signal': scores.signal,
        }

        # 附加实时数据
        if sina_q:
            result['realtime'] = {
                'price': sina_q.price,
                'change_pct': sina_q.change_pct,
                'volume': sina_q.volume,
                'high_52w': sina_q.high_52w,
                'low_52w': sina_q.low_52w,
            }

        results.append(result)

    # 按综合评分排序
    results.sort(key=lambda x: -x['score'])

    # 构建模拟盘
    portfolio = build_portfolio(all_scores, sina_quotes)

    # 组装最终结果
    output = {
        'timestamp': timestamp,
        'mode': 'daily_analysis',
        'data_source': 'stockanalysis.com + sina',
        'universe': STOCK_UNIVERSE,
        'results': results,
        'portfolio': portfolio,
        'selected': portfolio['selected'],
    }

    return output


def print_summary(output: dict):
    """打印终端摘要"""
    print("\n" + "=" * 70)
    print("  BDE-Stock 每日分析报告 (段永平风格)")
    print(f"  {output['timestamp'][:19]}")
    print("=" * 70)

    # 五因子评分表
    print(f"\n{'股票':<8} {'综合':>6} {'信号':>6} │ {'动量':>5} {'回归':>5} {'量能':>5} {'波动':>5} {'趋势':>5}")
    print("-" * 70)

    for r in output['results']:
        signal = r['signal']
        signal_icon = {'BUY': '🟢', 'HOLD': '🟡', 'SELL': '🔴'}.get(signal, '⚪')

        print(
            f"{r['symbol']:<8} {r['score']:>6.1f} {signal_icon}{signal:>4} │ "
            f"{r['scores']['momentum']:>5.1f} "
            f"{r['scores']['mean_reversion']:>5.1f} "
            f"{r['scores']['volume']:>5.1f} "
            f"{r['scores']['volatility']:>5.1f} "
            f"{r['scores']['trend']:>5.1f}"
        )

    # 模拟盘
    pf = output['portfolio']
    print(f"\n{'=' * 70}")
    print(f"  模拟盘配置 (初始资金 ${pf['initial']:,.0f})")
    print("-" * 70)

    if pf['positions']:
        for symbol, pos in pf['positions'].items():
            pct = pos['cost'] / pf['initial'] * 100
            print(f"  {symbol:<8} {pos['qty']:>6}股 × ${pos['avg']:>9.2f} = ${pos['cost']:>12,.2f} ({pct:.1f}%)")
        print(f"\n  现金: ${pf['cash']:,.2f}")
        print(f"  已选: {', '.join(pf['selected'])}")
    else:
        print("  无BUY信号股票，全仓现金")

    print(f"\n  信号统计: ", end='')
    buy_count = sum(1 for r in output['results'] if r['signal'] == 'BUY')
    hold_count = sum(1 for r in output['results'] if r['signal'] == 'HOLD')
    sell_count = sum(1 for r in output['results'] if r['signal'] == 'SELL')
    print(f"BUY={buy_count}  HOLD={hold_count}  SELL={sell_count}")
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(description='BDE-Stock 每日分析脚本')
    parser.add_argument('--history', type=str, help='历史数据JSON文件路径')
    parser.add_argument('--output', type=str, help='输出JSON文件路径')
    parser.add_argument('--sina-only', action='store_true', help='仅使用新浪数据(无历史数据)')
    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info("BDE-Stock 每日分析启动")
    logger.info("=" * 50)

    # Step 1: 加载历史数据
    history_data = {}

    if args.history and os.path.exists(args.history):
        # 从预填充文件加载
        history_data = load_history_from_json(args.history)
    else:
        # 查找默认的历史数据文件
        default_paths = [
            os.path.join(BASE_DIR, 'history_data.json'),
            os.path.join(BASE_DIR, 'bde_history.json'),
        ]
        for path in default_paths:
            if os.path.exists(path):
                logger.info(f"发现默认历史数据: {path}")
                history_data = load_history_from_json(path)
                break

    if not history_data and not args.sina_only:
        logger.warning("未找到历史数据文件。")
        logger.warning("请使用 --history 参数指定数据文件，或先通过fetch_web获取数据。")
        logger.warning("示例: python3 bde_stock_daily.py --history history_data.json")

        # 如果新浪可用，仅用实时数据生成简要报告
        sina_quotes = fetch_sina_quotes(STOCK_UNIVERSE)
        if sina_quotes:
            logger.info("使用新浪实时数据生成简要报告...")
            # 生成最小化结果
            results = []
            for symbol in STOCK_UNIVERSE:
                if symbol in sina_quotes:
                    q = sina_quotes[symbol]
                    results.append({
                        'symbol': symbol,
                        'price': q.price,
                        'change_pct': q.change_pct,
                        'note': '仅实时数据，无历史因子评分',
                    })
            output = {
                'timestamp': datetime.now().isoformat(),
                'mode': 'realtime_only',
                'results': results,
                'portfolio': {'initial': 1000000, 'cash': 1000000, 'positions': {}, 'trades': [], 'selected': []},
            }
        else:
            logger.error("无任何可用数据源，退出")
            sys.exit(1)

    else:
        # Step 2: 获取新浪实时行情
        sina_quotes = fetch_sina_quotes(STOCK_UNIVERSE)

        # Step 3: 运行分析
        output = run_analysis(history_data, sina_quotes)

    # Step 4: 打印摘要
    print_summary(output)

    # Step 5: 保存JSON
    if args.output:
        output_path = args.output
    else:
        date_str = datetime.now().strftime('%Y%m%d')
        output_path = os.path.join(BASE_DIR, f'bde_result_{date_str}.json')

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    logger.info(f"结果已保存: {output_path}")

    return output


if __name__ == '__main__':
    main()
