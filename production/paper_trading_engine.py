"""
BDE-Stock Phase 3 - 模拟盘交易引擎
======================================
基于每日信号自动执行模拟交易：
- 初始资金: $1,000,000
- BUY信号: 等权分配可用资金
- SELL信号: 清仓该标的
- HOLD信号: 保持现有仓位
- 记录所有交易
- 计算持仓市值、收益率、最大回撤

输出: paper_trading_state.json (持久化状态)
      paper_trading_report.json (每日报告)
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
import math

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

PROD_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(PROD_DIR, 'paper_trading_state.json')
SIGNAL_FILE = os.path.join(PROD_DIR, 'bde_production_latest.json')
REPORT_FILE = os.path.join(PROD_DIR, 'paper_trading_report.json')

INITIAL_CAPITAL = 1_000_000.0


class PaperTradingState:
    """模拟盘状态管理"""

    def __init__(self):
        self.initial_capital = INITIAL_CAPITAL
        self.cash = INITIAL_CAPITAL
        self.positions: Dict[str, Dict] = {}  # symbol -> {shares, avg_cost, current_price}
        self.trades: List[Dict] = []
        self.daily_snapshots: List[Dict] = []
        self.peak_value = INITIAL_CAPITAL
        self.start_date = datetime.now().strftime('%Y-%m-%d')
        self.last_update = None

    def to_dict(self):
        return {
            'initial_capital': self.initial_capital,
            'cash': self.cash,
            'positions': self.positions,
            'trades': self.trades,
            'daily_snapshots': self.daily_snapshots,
            'peak_value': self.peak_value,
            'start_date': self.start_date,
            'last_update': self.last_update,
        }

    @classmethod
    def from_dict(cls, data):
        state = cls()
        state.initial_capital = data.get('initial_capital', INITIAL_CAPITAL)
        state.cash = data.get('cash', INITIAL_CAPITAL)
        state.positions = data.get('positions', {})
        state.trades = data.get('trades', [])
        state.daily_snapshots = data.get('daily_snapshots', [])
        state.peak_value = data.get('peak_value', INITIAL_CAPITAL)
        state.start_date = data.get('start_date', datetime.now().strftime('%Y-%m-%d'))
        state.last_update = data.get('last_update')
        return state

    def save(self):
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"状态已保存: {STATE_FILE}")

    @classmethod
    def load(cls):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(" 加载状态")
            return cls.from_dict(data)
        except FileNotFoundError:
            logger.info("无历史状态，使用新状态")
            return cls()
        except Exception as e:
            logger.warning(f"加载状态失败: {e}，使用新状态")
            return cls()


class PaperTradingEngine:
    """模拟盘交易引擎"""

    def __init__(self, state: PaperTradingState):
        self.state = state

    def get_total_value(self) -> float:
        """计算当前总资产"""
        position_value = sum(
            pos['shares'] * pos.get('current_price', pos['avg_cost'])
            for pos in self.state.positions.values()
        )
        return self.state.cash + position_value

    def get_current_return(self) -> float:
        """计算当前收益率"""
        total = self.get_total_value()
        return (total - self.state.initial_capital) / self.state.initial_capital

    def get_max_drawdown(self) -> float:
        """计算最大回撤"""
        peak = self.state.peak_value
        current = self.get_total_value()
        if peak > 0:
            return (peak - current) / peak
        return 0.0

    def update_prices(self, signal_data: Dict):
        """根据最新行情更新持仓价格"""
        stocks = signal_data.get('stocks', {})
        for symbol, pos in self.state.positions.items():
            if symbol in stocks:
                price = stocks[symbol].get('price')
                if price:
                    pos['current_price'] = price

    def execute_signals(self, signal_data: Dict):
        """
        根据信号执行交易
        
        逻辑：
        - SELL信号：清仓该标的
        - BUY信号：等权分配可用资金（买入）
        - HOLD信号：保持不动
        """
        signals = signal_data.get('signals', {})
        stocks = signal_data.get('stocks', {})
        buy_list = signals.get('BUY', [])
        sell_list = signals.get('SELL', [])
        hold_list = signals.get('HOLD', [])
        now = datetime.now().isoformat()

        # Step 1: 执行SELL - 清仓
        for symbol in sell_list:
            if symbol in self.state.positions:
                pos = self.state.positions[symbol]
                shares = pos['shares']
                price = pos.get('current_price', pos['avg_cost'])
                proceeds = shares * price
                pnl = proceeds - (shares * pos['avg_cost'])
                self.state.cash += proceeds

                trade = {
                    'date': now,
                    'action': 'signal_sell',
                    'symbol': symbol,
                    'shares': shares,
                    'price': price,
                    'pnl': round(pnl, 2),
                }
                self.state.trades.append(trade)
                logger.info(f"SELL {symbol} {shares}股 @ ${price:.2f} (PnL: ${pnl:+.2f})")
                del self.state.positions[symbol]
            elif symbol in stocks:
                # 没有持仓但收到SELL信号，仅记录
                price = stocks[symbol].get('price', 0)
                trade = {
                    'date': now,
                    'action': 'signal_neutral',
                    'symbol': symbol,
                    'shares': 0,
                    'price': price,
                    'note': 'CLEAN SELL - 无持仓',
                }
                self.state.trades.append(trade)

        # Step 2: 执行BUY - 等权分配
        if buy_list:
            # 计算可用于买入的总资金
            total_value = self.get_total_value()
            target_per_stock = total_value / len(buy_list)

            for symbol in buy_list:
                if symbol not in stocks:
                    continue
                price = stocks[symbol].get('price', 0)
                if price <= 0:
                    continue

                if symbol in self.state.positions:
                    # 已有持仓 - 调整到目标权重
                    pos = self.state.positions[symbol]
                    current_shares = pos['shares']
                    current_value = current_shares * price
                    target_shares = int(target_per_stock / price)
                    add_shares = target_shares - current_shares

                    if add_shares > 0:
                        cost = add_shares * price
                        if cost <= self.state.cash:
                            old_cost = current_shares * pos['avg_cost']
                            new_total = old_cost + cost
                            pos['avg_cost'] = new_total / (current_shares + add_shares)
                            pos['shares'] = current_shares + add_shares
                            self.state.cash -= cost

                            trade = {
                                'date': now,
                                'action': 'signal_buy_add',
                                'symbol': symbol,
                                'shares': add_shares,
                                'price': price,
                            }
                            self.state.trades.append(trade)
                            logger.info(f"BUY ADD {symbol} {add_shares}股 @ ${price:.2f} (总额: ${new_total:.2f})")
                    elif add_shares < 0:
                        # 需要减仓（目标小于当前持仓），卖出多余部分
                        sell_shares = abs(add_shares)
                        proceeds = sell_shares * price
                        self.state.cash += proceeds
                        pos['shares'] = current_shares - sell_shares

                        trade = {
                            'date': now,
                            'action': 'signal_buy_reduce',
                            'symbol': symbol,
                            'shares': -sell_shares,
                            'price': price,
                        }
                        self.state.trades.append(trade)
                        logger.info(f"REDUCE {symbol} {sell_shares}股 @ ${price:.2f}")
                else:
                    # 新买入
                    target_shares = int(target_per_stock / price)
                    if target_shares > 0:
                        cost = target_shares * price
                        if cost <= self.state.cash:
                            self.state.positions[symbol] = {
                                'shares': target_shares,
                                'avg_cost': price,
                                'current_price': price,
                            }
                            self.state.cash -= cost

                            trade = {
                                'date': now,
                                'action': 'signal_buy_new',
                                'symbol': symbol,
                                'shares': target_shares,
                                'price': price,
                            }
                            self.state.trades.append(trade)
                            logger.info(f"BUY {symbol} {target_shares}股 @ ${price:.2f}")

    def take_snapshot(self):
        """记录每日快照"""
        total = self.get_total_value()
        if total > self.state.peak_value:
            self.state.peak_value = total

        snapshot = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'total_value': round(total, 2),
            'cash': round(self.state.cash, 2),
            'return_pct': round(self.get_current_return() * 100, 2),
            'drawdown_pct': round(self.get_max_drawdown() * 100, 2),
            'positions_count': len(self.state.positions),
        }
        self.state.daily_snapshots.append(snapshot)
        self.state.last_update = datetime.now().isoformat()
        logger.info("记录每日快照")

    def generate_report(self) -> Dict:
        """生成模拟盘报告"""
        total = self.get_total_value()
        positions_list = []
        for symbol, pos in self.state.positions.items():
            shares = pos['shares']
            avg_cost = pos['avg_cost']
            current_price = pos.get('current_price', avg_cost)
            market_value = shares * current_price
            pnl = market_value - (shares * avg_cost)
            pnl_pct = (pnl / (shares * avg_cost) * 100) if avg_cost > 0 else 0

            positions_list.append({
                'symbol': symbol,
                'shares': shares,
                'avg_cost': round(avg_cost, 2),
                'current_price': round(current_price, 2),
                'market_value': round(market_value, 2),
                'pnl': round(pnl, 2),
                'pnl_pct': round(pnl_pct, 1),
            })

        report = {
            'timestamp': datetime.now().isoformat(),
            'initial_capital': self.state.initial_capital,
            'current_value': round(total, 2),
            'cash': round(self.state.cash, 2),
            'positions_value': round(total - self.state.cash, 2),
            'total_return': round(self.get_current_return() * 100, 2),
            'max_drawdown': round(self.get_max_drawdown() * 100, 2),
            'trades_count': len(self.state.trades),
            'positions': positions_list,
            'recent_trades': self.state.trades[-10:],
            'daily_snapshots': self.state.daily_snapshots[-30:],
        }
        return report


def main():
    print("=" * 60)
    print("BDE-Stock Phase 3 - 模拟盘引擎")
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"初始资金: ${INITIAL_CAPITAL:,.0f}")
    print("=" * 60)

    # 加载信号文件
    if not os.path.exists(SIGNAL_FILE):
        logger.error(f"信号文件不存在: {SIGNAL_FILE}")
        logger.error("请先运行 bde_production_daily.py 生成信号")
        return None

    with open(SIGNAL_FILE, 'r', encoding='utf-8') as f:
        signal_data = json.load(f)

    # 加载或初始化状态
    state = PaperTradingState.load()
    engine = PaperTradingEngine(state)

    # [1/4] 更新持仓价格
    print("\n📄 初始化报告已保存: " if not state.last_update else "")
    print("\n[1/4] 更新持仓价格...")
    engine.update_prices(signal_data)

    # [2/4] 执行交易信号
    print("[2/4] 执行交易信号...")
    engine.execute_signals(signal_data)

    # [3/4] 记录每日快照
    print("[3/4] 记录每日快照...")
    engine.take_snapshot()

    # [4/4] 生成报告
    print("[4/4] 生成报告...")
    report = engine.generate_report()

    # 保存状态
    state.save()

    # 保存报告
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # 打印报告
    print(f"\n📊 模拟盘状态报告")
    print(f"  初始资金: ${report['initial_capital']:>12,.2f}")
    print(f"  当前净值: ${report['current_value']:>12,.2f}")
    print(f"  现金:     ${report['cash']:>12,.2f}")
    print(f"  持仓市值: ${report['positions_value']:>12,.2f}")
    print(f"  总收益率: {report['total_return']:>+11.2f}%")
    print(f"  最大回撤: {report['max_drawdown']:>11.2f}%")
    print(f"  交易次数: {report['trades_count']:>12d}")

    if report['positions']:
        print(f"\n  持仓明细:")
        for pos in report['positions']:
            print(f"    {pos['symbol']:<10s} {pos['shares']:>6d}股 成本${pos['avg_cost']:>8.2f} "
                  f"现价${pos['current_price']:>8.2f} PnL ${pos['pnl']:>+10,.2f} ({pos['pnl_pct']:>+.1f}%)")

    if report['recent_trades']:
        print(f"\n  最近交易:")
        for trade in report['recent_trades'][-5:]:
            print(f"    {trade['date'][:10]} {trade['action']:<15s} {trade['symbol']:<10s} "
                  f"{abs(trade.get('shares', 0)):>6d}股 @ ${trade.get('price', 0):>8.2f}")

    print(f"\n📄 报告已保存: {REPORT_FILE}")
    return report


if __name__ == '__main__':
    try:
        result = main()
        if result is None:
            exit(1)
        exit(0)
    except Exception as e:
        logger.error(f"模拟盘引擎执行失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        exit(1)
