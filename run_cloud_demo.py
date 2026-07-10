"""
BDE-Stock 云端演示版
====================
不依赖任何外部券商，在云端完整运行：
数据获取 → BDE五因子评分 → 信号生成 → 内部模拟盘 → 结果输出

用法: python run_cloud_demo.py [--top 5] [--universe AAPL,MSFT,...]
"""

import sys
import re
import json
import logging
import requests
import argparse
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional

import numpy as np
import pandas as pd

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('BDE-Cloud')

# ============================================================
# 配置
# ============================================================
DEFAULT_UNIVERSE = [
    # 科技龙头
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA',
    # 巴菲特/段永平持仓
    'BRK-B', 'V', 'MA', 'JNJ', 'PG', 'KO', 'CVX', 'AAPL',
    # 中概
    'BABA', 'JD', 'PDD', 'BIDU', 'NIO',
    # ETF
    'SPY', 'QQQ', 'ARKK',
]

FACTOR_WEIGHTS = {
    'momentum': 0.30,
    'mean_reversion': 0.20,
    'volume': 0.20,
    'volatility': 0.15,
    'trend': 0.15,
}

RISK_LIMITS = {
    'max_position_pct': 0.25,
    'max_positions': 5,
    'stop_loss_pct': 0.03,
    'max_drawdown_pct': 0.15,
    'min_score_buy': 55,
}

INITIAL_CAPITAL = 1_000_000  # 100万美元模拟资金


# ============================================================
# 数据获取
# ============================================================
def fetch_stock_data(symbols: List[str], days: int = 120) -> Dict[str, pd.DataFrame]:
    """用新浪财经API获取股票历史数据"""
    import requests
    
    data = {}
    logger.info(f"获取 {len(symbols)} 只股票数据 (新浪财经API)...")
    
    for sym in symbols:
        try:
            # 新浪财经API
            url = f"https://quotes.sina.cn/usstock/api/jsonp.php/data/US_MinKService.getDailyK?symbol={sym}&scale=240&datalen={days}"
            headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn"}
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code != 200:
                logger.warning(f"  ✗ {sym}: HTTP {resp.status_code}")
                continue
            
            # 解析JSONP响应
            text = resp.text
            json_str = re.search(r'\((.+)\)', text)
            if not json_str:
                # 尝试直接解析
                json_str = text
            
            import json
            json_text = json_str.group(1) if hasattr(json_str, 'group') else text
            records = json.loads(json_text)
            
            if not records:
                logger.warning(f"  ✗ {sym}: 无数据")
                continue
            
            # 构建DataFrame
            df = pd.DataFrame(records)
            # 重命名列
            col_map = {'day': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}
            df = df.rename(columns=col_map)
            
            for col in ['Open', 'High', 'Low', 'Close']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            if 'Volume' in df.columns:
                df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce')
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
                df = df.set_index('Date')
            
            if len(df) > 20:
                data[sym] = df
                logger.info(f"  ✓ {sym}: {len(df)} 条数据")
            else:
                logger.warning(f"  ✗ {sym}: 数据不足({len(df)}条)，跳过")
                
        except Exception as e:
            logger.warning(f"  ✗ {sym}: {str(e)[:80]}")
    
    logger.info(f"成功获取 {len(data)}/{len(symbols)} 只股票数据")
    return data


# ============================================================
# BDE五因子评分
# ============================================================
@dataclass
class FactorResult:
    symbol: str
    scores: Dict[str, float] = field(default_factory=dict)
    composite_score: float = 0.0
    signal: str = "HOLD"
    price: float = 0.0
    change_pct: float = 0.0

def compute_factors(data: Dict[str, pd.DataFrame]) -> List[FactorResult]:
    """计算五因子评分"""
    results = []
    
    for sym, df in data.items():
        close = df['Close'].values
        volume = df['Volume'].values
        high = df['High'].values
        low = df['Low'].values
        
        if len(close) < 20:
            continue
        
        scores = {}
        
        # 1. 动量因子 (30%) - 20日收益率排名
        ret_20d = (close[-1] / close[-20] - 1) * 100 if len(close) >= 20 else 0
        scores['momentum'] = max(0, min(100, 50 + ret_20d * 3))
        
        # 2. 均值回归因子 (20%) - 偏离MA20程度
        ma20 = np.mean(close[-20:])
        deviation = (close[-1] / ma20 - 1) * 100
        scores['mean_reversion'] = max(0, min(100, 50 - deviation * 5))
        
        # 3. 成交量因子 (20%) - 量比
        vol_avg = np.mean(volume[-20:])
        vol_ratio = volume[-1] / vol_avg if vol_avg > 0 else 1
        scores['volume'] = max(0, min(100, vol_ratio * 50))
        
        # 4. 波动率因子 (15%) - ATR
        tr = np.maximum(high[-20:] - low[-20:], 
               np.maximum(np.abs(high[-20:] - close[-21:-1]),
                         np.abs(low[-20:] - close[-21:-1])))
        atr = np.mean(tr) if len(tr) > 0 else 0
        atr_pct = atr / close[-1] * 100 if close[-1] > 0 else 0
        scores['volatility'] = max(0, min(100, 100 - atr_pct * 20))
        
        # 5. 趋势因子 (15%) - EMA交叉
        ema5 = pd.Series(close).ewm(span=5).mean().iloc[-1]
        ema20 = pd.Series(close).ewm(span=20).mean().iloc[-1]
        trend_signal = 1 if ema5 > ema20 else -1
        scores['trend'] = 70 if trend_signal > 0 else 30
        
        # 加权综合分
        composite = sum(scores[k] * FACTOR_WEIGHTS[k] for k in FACTOR_WEIGHTS)
        
        # 交易信号
        signal = "BUY" if composite >= RISK_LIMITS['min_score_buy'] else "HOLD"
        
        # 价格和涨跌幅
        price = close[-1]
        change_pct = (close[-1] / close[-2] - 1) * 100 if len(close) >= 2 else 0
        
        result = FactorResult(
            symbol=sym,
            scores=scores,
            composite_score=composite,
            signal=signal,
            price=price,
            change_pct=change_pct
        )
        results.append(result)
    
    # 按综合分排序
    results.sort(key=lambda x: -x.composite_score)
    return results


# ============================================================
# 内部模拟盘
# ============================================================
@dataclass
class Position:
    symbol: str
    qty: int
    avg_price: float
    entry_date: str

class InternalPaperTrader:
    """内部模拟盘 - 不依赖任何外部券商"""
    
    def __init__(self, initial_capital: float = INITIAL_CAPITAL):
        self.cash = initial_capital
        self.initial_capital = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Dict] = []
        self.daily_values: List[Dict] = []
    
    def execute_buy(self, symbol: str, price: float, target_amount: float) -> bool:
        """执行买入"""
        qty = int(target_amount / price)
        if qty <= 0:
            return False
        
        cost = qty * price
        if cost > self.cash:
            qty = int(self.cash / price)
            cost = qty * price
        
        if qty <= 0:
            return False
        
        self.cash -= cost
        
        if symbol in self.positions:
            pos = self.positions[symbol]
            total_cost = pos.avg_price * pos.qty + cost
            pos.qty += qty
            pos.avg_price = total_cost / pos.qty
        else:
            self.positions[symbol] = Position(symbol, qty, price, datetime.now().strftime('%Y-%m-%d'))
        
        self.trades.append({
            'action': 'BUY',
            'symbol': symbol,
            'qty': qty,
            'price': price,
            'cost': cost,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        logger.info(f"  📈 BUY {symbol} x{qty} @ ${price:.2f} = ${cost:,.0f}")
        return True
    
    def execute_sell(self, symbol: str, price: float) -> bool:
        """执行卖出"""
        if symbol not in self.positions:
            return False
        
        pos = self.positions[symbol]
        revenue = pos.qty * price
        pnl = (price - pos.avg_price) * pos.qty
        pnl_pct = (price / pos.avg_price - 1) * 100
        
        self.cash += revenue
        
        self.trades.append({
            'action': 'SELL',
            'symbol': symbol,
            'qty': pos.qty,
            'price': price,
            'revenue': revenue,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        logger.info(f"  📉 SELL {symbol} x{pos.qty} @ ${price:.2f} = ${revenue:,.0f} (PnL: ${pnl:,.0f} / {pnl_pct:+.1f}%)")
        
        del self.positions[symbol]
        return True
    
    def get_portfolio_value(self, prices: Dict[str, float]) -> float:
        """计算组合总价值"""
        position_value = sum(
            pos.qty * prices.get(pos.symbol, pos.avg_price)
            for pos in self.positions.values()
        )
        return self.cash + position_value
    
    def print_summary(self, prices: Dict[str, float]):
        """打印组合摘要"""
        total_value = self.get_portfolio_value(prices)
        total_return = (total_value / self.initial_capital - 1) * 100
        
        print("\n" + "="*60)
        print(f"📊 BDE-Stock 模拟盘组合摘要")
        print(f"="*60)
        print(f"初始资金:    ${self.initial_capital:>12,.0f}")
        print(f"当前总值:    ${total_value:>12,.0f}")
        print(f"总收益率:    {total_return:>11.2f}%")
        print(f"现金余额:    ${self.cash:>12,.0f}")
        print(f"持仓数量:    {len(self.positions)}")
        print(f"交易次数:    {len(self.trades)}")
        
        if self.positions:
            print(f"\n{'─'*60}")
            print(f"{'股票':<8} {'数量':>6} {'成本':>10} {'现价':>10} {'盈亏':>12} {'盈亏%':>8}")
            print(f"{'─'*60}")
            for sym, pos in self.positions.items():
                current_price = prices.get(sym, pos.avg_price)
                pnl = (current_price - pos.avg_price) * pos.qty
                pnl_pct = (current_price / pos.avg_price - 1) * 100
                print(f"{sym:<8} {pos.qty:>6} ${pos.avg_price:>9.2f} ${current_price:>9.2f} ${pnl:>11,.0f} {pnl_pct:>7.1f}%")
        
        print(f"{'='*60}")


# ============================================================
# 主流程
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='BDE-Stock 云端演示版')
    parser.add_argument('--top', type=int, default=5, help='买入前N只股票')
    parser.add_argument('--universe', type=str, default=None, help='股票池(逗号分隔)')
    parser.add_argument('--capital', type=float, default=INITIAL_CAPITAL, help='初始资金')
    args = parser.parse_args()
    
    universe = args.universe.split(',') if args.universe else DEFAULT_UNIVERSE
    top_n = min(args.top, RISK_LIMITS['max_positions'])
    
    print("\n" + "🔷"*20)
    print("  BDE-Stock 云端演示版 - 段永平价值投资框架")
    print("  数据获取 → 五因子评分 → 信号生成 → 模拟交易")
    print("🔷"*20)
    
    # Step 1: 获取数据
    logger.info("\n" + "="*40)
    logger.info("Step 1: 获取行情数据")
    logger.info("="*40)
    stock_data = fetch_stock_data(universe)
    
    if not stock_data:
        logger.error("没有获取到任何数据，退出")
        sys.exit(1)
    
    # Step 2: BDE五因子评分
    logger.info("\n" + "="*40)
    logger.info("Step 2: BDE五因子评分")
    logger.info("="*40)
    results = compute_factors(stock_data)
    
    print(f"\n{'─'*80}")
    print(f"{'排名':>4} {'股票':<8} {'综合分':>8} {'动量':>6} {'回归':>6} {'量能':>6} {'波动':>6} {'趋势':>6} {'信号':>6} {'价格':>10}")
    print(f"{'─'*80}")
    for i, r in enumerate(results, 1):
        emoji = "🟢" if r.signal == "BUY" else "⚪"
        print(f"{i:>4} {r.symbol:<8} {r.composite_score:>7.1f} {r.scores['momentum']:>5.0f} {r.scores['mean_reversion']:>5.0f} {r.scores['volume']:>5.0f} {r.scores['volatility']:>5.0f} {r.scores['trend']:>5.0f} {emoji}{r.signal:>5} ${r.price:>9.2f}")
    print(f"{'─'*80}")
    
    # Step 3: 信号生成 + 风控
    logger.info("\n" + "="*40)
    logger.info("Step 3: 信号生成 + 风控检查")
    logger.info("="*40)
    
    buy_signals = [r for r in results if r.signal == "BUY"][:top_n]
    
    if not buy_signals:
        logger.warning("没有产生BUY信号的股票，市场可能处于弱势")
        buy_signals = results[:3]  # 至少选前3只
        logger.info(f"选取综合分最高的 {len(buy_signals)} 只股票")
    
    logger.info(f"选中 {len(buy_signals)} 只股票: {[r.symbol for r in buy_signals]}")
    
    # Step 4: 模拟交易
    logger.info("\n" + "="*40)
    logger.info("Step 4: 执行模拟交易")
    logger.info("="*40)
    
    trader = InternalPaperTrader(args.capital)
    
    # 等权分配到选中的股票
    per_stock_amount = args.capital * RISK_LIMITS['max_position_pct']
    
    for r in buy_signals:
        trader.execute_buy(r.symbol, r.price, per_stock_amount)
    
    # Step 5: 组合摘要
    current_prices = {r.symbol: r.price for r in results}
    trader.print_summary(current_prices)
    
    # 保存结果
    result_file = f"bde_stock_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    result_data = {
        'timestamp': datetime.now().isoformat(),
        'universe': universe,
        'factor_results': [
            {
                'symbol': r.symbol,
                'composite_score': r.composite_score,
                'scores': r.scores,
                'signal': r.signal,
                'price': r.price,
            }
            for r in results
        ],
        'selected': [r.symbol for r in buy_signals],
        'portfolio': {
            'initial_capital': args.capital,
            'total_value': trader.get_portfolio_value(current_prices),
            'cash': trader.cash,
            'positions': {
                sym: {'qty': pos.qty, 'avg_price': pos.avg_price}
                for sym, pos in trader.positions.items()
            },
            'trades': trader.trades
        }
    }
    
    with open(result_file, 'w') as f:
        json.dump(result_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n✅ 结果已保存到: {result_file}")
    print(f"\n🎯 BDE-Stock 云端演示完成！")


if __name__ == '__main__':
    main()
