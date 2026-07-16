"""
BDE Score™ - AI-Powered Multi-Market Stock Analysis MCP Server
Copyright (C) 2026 BDE Score™ (https://github.com/hbhqq9/bde-score)

Licensed under AGPL-3.0 with commercial option.
If you run a modified version on a network server, you must make
the complete source code available. See LICENSE for details.
Commercial licensing available: nnhbh@foxmail.com
"""

"""
BDE-Stock Paper Trader - 模拟交易引擎
通过 BrokerAdapter 接口与券商交互（支持 IBKR / Alpaca）
"""

import logging
import time
from typing import Optional, Dict, List
from datetime import datetime

from broker_adapter import BrokerAdapter, OrderData

logger = logging.getLogger(__name__)


class PaperTrader:
    """
    模拟交易引擎
    
    通过 broker adapter 接口执行交易，与具体券商解耦。
    段永平框架约束:
    - 绝对不做空
    - 绝对不加杠杆
    - 只做多，现金买入
    """

    def __init__(self, broker: BrokerAdapter):
        self.broker = broker
        self._trade_history = []

    def place_market_buy(self, symbol: str, qty: int) -> Optional[OrderData]:
        """
        市价买入 - 只做多，现金买入
        """
        if qty <= 0:
            logger.error(f"买入数量必须为正数: {symbol} qty={qty}")
            return None

        # 段永平框架：禁止做空（buy 是合法的，但防御性检查）
        logger.info(f"市价买入: {symbol} 数量={qty}")

        try:
            order = self.broker.submit_order(
                symbol=symbol,
                qty=qty,
                side='buy',
                order_type='market',
                time_in_force='day'
            )
            if order:
                self._record_trade('BUY', symbol, qty, order)
                logger.info(f"买入订单已提交: {order}")
                return order
        except Exception as e:
            logger.error(f"买入失败 {symbol}: {e}")

        return None

    def place_market_sell(self, symbol: str, qty: int) -> Optional[OrderData]:
        """
        市价卖出 - 段永平框架: 仅允许卖出已有持仓（平仓），不允许卖出开仓（做空）
        """
        if qty <= 0:
            logger.error(f"卖出数量必须为正数: {symbol} qty={qty}")
            return None

        # 段永平框架：检查是否持有该股票
        position = self.broker.get_position(symbol)
        if not position or position.qty < qty:
            available = position.qty if position else 0
            logger.error(f"段永平框架约束：无法卖出 - 持仓不足 {symbol} "
                        f"需要={qty} 可用={available}，禁止做空！")
            return None

        logger.info(f"市价卖出(平仓): {symbol} 数量={qty}")

        try:
            order = self.broker.submit_order(
                symbol=symbol,
                qty=qty,
                side='sell',
                order_type='market',
                time_in_force='day'
            )
            if order:
                self._record_trade('SELL', symbol, qty, order)
                logger.info(f"卖出订单已提交: {order}")
                return order
        except Exception as e:
            logger.error(f"卖出失败 {symbol}: {e}")

        return None

    def place_limit_buy(self, symbol: str, qty: int,
                        limit_price: float) -> Optional[OrderData]:
        """限价买入"""
        if qty <= 0 or limit_price <= 0:
            logger.error(f"限价买入参数无效: {symbol} qty={qty} price={limit_price}")
            return None

        logger.info(f"限价买入: {symbol} 数量={qty} 价格={limit_price}")

        try:
            order = self.broker.submit_order(
                symbol=symbol,
                qty=qty,
                side='buy',
                order_type='limit',
                limit_price=limit_price,
                time_in_force='day'
            )
            if order:
                self._record_trade('LIMIT_BUY', symbol, qty, order, limit_price=limit_price)
                logger.info(f"限价买入订单已提交: {order}")
                return order
        except Exception as e:
            logger.error(f"限价买入失败 {symbol}: {e}")

        return None

    def get_portfolio_summary(self) -> Dict:
        """获取投资组合摘要"""
        try:
            account = self.broker.get_account()
            positions = self.broker.get_positions()

            if not account:
                return {'error': '无法获取账户信息'}

            position_details = []
            for pos in positions:
                position_details.append({
                    'symbol': pos.symbol,
                    'qty': pos.qty,
                    'avg_entry': pos.avg_entry_price,
                    'market_value': pos.market_value,
                    'side': pos.side,
                })

            return {
                'timestamp': datetime.now().isoformat(),
                'portfolio_value': account.portfolio_value,
                'cash': account.cash,
                'buying_power': account.buying_power,
                'positions_count': len(positions),
                'positions': position_details,
                'broker': self.broker.get_name(),
                'paper_trading': self.broker.paper_trading,
            }
        except Exception as e:
            logger.error(f"获取投资组合摘要失败: {e}")
            return {'error': str(e)}

    def cancel_all_orders(self) -> int:
        """取消所有未成交订单"""
        try:
            open_orders = self.broker.get_open_orders()
            cancelled = 0
            for order in open_orders:
                if self.broker.cancel_order(order.order_id):
                    cancelled += 1
            logger.info(f"已取消 {cancelled} 个订单")
            return cancelled
        except Exception as e:
            logger.error(f"取消订单失败: {e}")
            return 0

    def _record_trade(self, action: str, symbol: str, qty: int,
                      order: OrderData, limit_price: float = None):
        """记录交易"""
        record = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'symbol': symbol,
            'qty': qty,
            'order_id': order.order_id,
            'status': order.status,
            'limit_price': limit_price,
            'broker': self.broker.get_name(),
        }
        self._trade_history.append(record)
        logger.info(f"交易记录: {record}")

    def get_trade_history(self) -> List[Dict]:
        """获取交易历史"""
        return self._trade_history.copy()
