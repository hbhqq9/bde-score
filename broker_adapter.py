"""
BDE Score™ - AI-Powered Multi-Market Stock Analysis MCP Server
Copyright (C) 2026 BDE Score™ (https://github.com/hbhqq9/bde-score)

Licensed under AGPL-3.0 with commercial option.
If you run a modified version on a network server, you must make
the complete source code available. See LICENSE for details.
Commercial licensing available: nnhbh@foxmail.com
"""

"""
BDE-Stock Broker Adapter - 抽象基类
定义统一券商接口，支持多券商切换（IBKR / Alpaca / 未来扩展）
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================
# 数据类 - 统一返回格式
# ============================================================

class BarData:
    """K线数据统一封装"""
    def __init__(self, timestamp=None, open=0, high=0, low=0, close=0,
                 volume=0, vwap=0, trade_count=0):
        self.timestamp = timestamp
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.vwap = vwap
        self.trade_count = trade_count

    def __repr__(self):
        return f"BarData(ts={self.timestamp}, O={self.open}, H={self.high}, L={self.low}, C={self.close}, V={self.volume})"


class QuoteData:
    """报价数据统一封装"""
    def __init__(self, bid_price=0, bid_size=0, ask_price=0, ask_size=0,
                 timestamp=None, symbol=""):
        self.bid_price = bid_price
        self.bid_size = bid_size
        self.ask_price = ask_price
        self.ask_size = ask_size
        self.timestamp = timestamp
        self.symbol = symbol

    @property
    def mid_price(self):
        if self.bid_price > 0 and self.ask_price > 0:
            return (self.bid_price + self.ask_price) / 2
        return self.ask_price or self.bid_price or 0

    def __repr__(self):
        return f"QuoteData({self.symbol} bid={self.bid_price} ask={self.ask_price})"


class PositionData:
    """持仓数据统一封装"""
    def __init__(self, symbol="", qty=0, avg_entry_price=0, side="long",
                 market_value=0, unrealized_pl=0, unrealized_plpc=0):
        self.symbol = symbol
        self.qty = qty
        self.avg_entry_price = avg_entry_price
        self.side = side
        self.market_value = market_value
        self.unrealized_pl = unrealized_pl
        self.unrealized_plpc = unrealized_plpc

    def __repr__(self):
        return f"Position({self.symbol} qty={self.qty} avg={self.avg_entry_price})"


class OrderData:
    """订单数据统一封装"""
    def __init__(self, order_id="", symbol="", side="", qty=0, order_type="market",
                 limit_price=None, stop_price=None, status="", filled_qty=0,
                 filled_avg_price=None, created_at=None, filled_at=None,
                 raw_order=None):
        self.order_id = order_id
        self.symbol = symbol
        self.side = side
        self.qty = qty
        self.order_type = order_type
        self.limit_price = limit_price
        self.stop_price = stop_price
        self.status = status
        self.filled_qty = filled_qty
        self.filled_avg_price = filled_avg_price
        self.created_at = created_at
        self.filled_at = filled_at
        self.raw_order = raw_order

    def __repr__(self):
        return f"Order({self.order_id} {self.side} {self.qty} {self.symbol} {self.status})"


class AccountData:
    """账户数据统一封装"""
    def __init__(self, cash=0, portfolio_value=0, buying_power=0,
                 day_trade_count=0, status=""):
        self.cash = cash
        self.portfolio_value = portfolio_value
        self.buying_power = buying_power
        self.day_trade_count = day_trade_count
        self.status = status

    def __repr__(self):
        return f"Account(cash={self.cash:.2f} pv={self.portfolio_value:.2f} bp={self.buying_power:.2f})"


# ============================================================
# 抽象基类 - BrokerAdapter
# ============================================================

class BrokerAdapter(ABC):
    """
    券商适配器抽象基类
    所有券商适配器必须实现这些方法
    """

    # ------ 连接管理 ------

    @abstractmethod
    def connect(self) -> bool:
        """连接到券商API，返回是否成功"""
        pass

    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """检查是否已连接"""
        pass

    # ------ 账户信息 ------

    @abstractmethod
    def get_account(self) -> Optional[AccountData]:
        """获取账户信息"""
        pass

    @abstractmethod
    def get_buying_power(self) -> float:
        """获取购买力"""
        pass

    @abstractmethod
    def get_portfolio_value(self) -> float:
        """获取投资组合总价值"""
        pass

    # ------ 持仓管理 ------

    @abstractmethod
    def get_positions(self) -> List[PositionData]:
        """获取所有持仓"""
        pass

    @abstractmethod
    def get_position(self, symbol: str) -> Optional[PositionData]:
        """获取指定股票持仓"""
        pass

    # ------ 行情数据 ------

    @abstractmethod
    def get_latest_bar(self, symbol: str) -> Optional[BarData]:
        """获取最新一根K线"""
        pass

    @abstractmethod
    def get_bars(self, symbol: str, timeframe: str = "1Day",
                 limit: int = 200, start: str = None, end: str = None) -> List[BarData]:
        """
        获取历史K线数据
        timeframe: '1Min', '5Min', '1Hour', '1Day' 等
        """
        pass

    @abstractmethod
    def get_latest_quote(self, symbol: str) -> Optional[QuoteData]:
        """获取最新报价"""
        pass

    # ------ 订单管理 ------

    @abstractmethod
    def submit_order(self, symbol: str, qty: float, side: str,
                     order_type: str = "market", limit_price: float = None,
                     stop_price: float = None, time_in_force: str = "day") -> Optional[OrderData]:
        """
        提交订单
        side: 'buy' / 'sell'
        order_type: 'market', 'limit', 'stop', 'stop_limit'
        """
        pass

    @abstractmethod
    def get_order(self, order_id: str) -> Optional[OrderData]:
        """查询订单状态"""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        pass

    @abstractmethod
    def get_open_orders(self, symbol: str = None) -> List[OrderData]:
        """获取所有未成交订单"""
        pass

    # ------ 市场状态 ------

    @abstractmethod
    def get_clock(self) -> Dict[str, Any]:
        """
        获取市场时钟
        返回: {'is_open': bool, 'next_open': str, 'next_close': str, 'timestamp': str}
        """
        pass

    # ------ 期权（可选，部分券商不支持） ------

    def get_option_contracts(self, underlying: str, expiration: str = None,
                             option_type: str = None) -> List[Dict]:
        """获取期权合约列表（可选实现）"""
        return []

    def get_option_quotes(self, contracts: List[str]) -> Dict:
        """获取期权报价（可选实现）"""
        return {}

    # ------ 辅助方法 ------

    @abstractmethod
    def get_name(self) -> str:
        """返回券商名称"""
        pass

    @property
    @abstractmethod
    def paper_trading(self) -> bool:
        """是否为模拟交易模式"""
        pass
