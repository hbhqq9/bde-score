"""
BDE Score™ - AI-Powered Multi-Market Stock Analysis MCP Server
Copyright (C) 2026 BDE Score™ (https://github.com/hbhqq9/bde-score)

Licensed under AGPL-3.0 with commercial option.
If you run a modified version on a network server, you must make
the complete source code available. See LICENSE for details.
Commercial licensing available: nnhbh@foxmail.com
"""

"""
BDE-Stock Alpaca Adapter - Alpaca 适配器
将原 alpaca_client.py 功能封装到统一 BrokerAdapter 接口中
保留代码备用，暂不可用（账户已停用）

Alpaca 账户信息（备用）:
  邮箱: nnhbh@foxmail.com
  密码: Nnhbhqqq@999
  MFA:  4PMLBWWPYR5SPHSK35M7R2GIM3M5LSG45OHYMFEQAAYBKE5XTVBA
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from alpaca.trading.client import TradingClient
    from alpaca.data.timeframe import TimeFrame
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.trading.requests import (
        MarketOrderRequest, LimitOrderRequest,
        StopOrderRequest, StopLimitOrderRequest, GetAssetsRequest
    )
    from alpaca.data.historical.stock import StockHistoricalDataClient
    from alpaca.data.requests import (
        StockBarsRequest, StockLatestQuoteRequest, StockLatestBarRequest
    )
    from alpaca.data.models import Quote, Bar
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    logger.warning("alpaca-py 未安装，Alpaca 适配器不可用")

from broker_adapter import (
    BrokerAdapter, BarData, QuoteData, PositionData, OrderData, AccountData
)


class AlpacaAdapter(BrokerAdapter):
    """
    Alpaca 适配器 - 封装 alpaca-py SDK
    将原 alpaca_client.py 的功能适配到统一接口
    
    段永平框架约束（硬编码，不可修改）:
    - 绝对不做空
    - 绝对不加杠杆
    - 只做多，现金买入
    """

    # Alpaca TimeFrame 映射
    TIMEFRAME_MAP = {
        '1Min':  ('Minute', 1),
        '5Min':  ('Minute', 5),
        '15Min': ('Minute', 15),
        '1Hour': ('Hour', 1),
        '1Day':  ('Day', 1),
        '1Week': ('Week', 1),
    }

    def __init__(self, api_key: str, api_secret: str, paper: bool = True):
        """
        初始化 Alpaca 适配器
        :param api_key: API Key
        :param api_secret: API Secret
        :param paper: True=模拟盘, False=实盘
        """
        if not ALPACA_AVAILABLE:
            raise ImportError("alpaca-py 未安装，请运行: pip install alpaca-py")

        self._api_key = api_key
        self._api_secret = api_secret
        self._paper = paper
        self._connected = False

        self._trading_client = None
        self._data_client = None
        self._account_cache = None
        self._position_cache = {}

    # ====== 连接管理 ======

    def connect(self) -> bool:
        try:
            self._trading_client = TradingClient(
                api_key=self._api_key,
                secret_key=self._api_secret,
                paper=self._paper
            )
            self._data_client = StockHistoricalDataClient(
                api_key=self._api_key,
                secret_key=self._api_secret
            )
            # 测试连接
            self._trading_client.get_account()
            self._connected = True
            mode = "Paper" if self._paper else "Live"
            logger.info(f"Alpaca 连接成功 [{mode}]")
            return True
        except Exception as e:
            self._connected = False
            logger.error(f"Alpaca 连接失败: {e}")
            return False

    def disconnect(self):
        self._trading_client = None
        self._data_client = None
        self._connected = False
        logger.info("Alpaca 已断开连接")

    def is_connected(self) -> bool:
        return self._connected and self._trading_client is not None

    def _ensure_connected(self) -> bool:
        if not self.is_connected():
            logger.error("Alpaca 未连接")
            return False
        return True

    # ====== 账户信息 ======

    def get_account(self) -> Optional[AccountData]:
        if not self._ensure_connected():
            return None
        try:
            acct = self._trading_client.get_account()
            self._account_cache = AccountData(
                cash=float(acct.cash),
                portfolio_value=float(acct.portfolio_value),
                buying_power=float(acct.buying_power),
                day_trade_count=getattr(acct, 'daytrade_count', 0) or 0,
                status=str(acct.status) if hasattr(acct, 'status') else 'ACTIVE'
            )
            return self._account_cache
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            return self._account_cache

    def get_buying_power(self) -> float:
        acct = self.get_account()
        if acct:
            return acct.buying_power
        return 0.0

    def get_portfolio_value(self) -> float:
        acct = self.get_account()
        if acct:
            return acct.portfolio_value
        return 0.0

    # ====== 持仓管理 ======

    def get_positions(self) -> List[PositionData]:
        if not self._ensure_connected():
            return []
        try:
            positions = self._trading_client.get_all_positions()
            result = []
            for pos in positions:
                qty = float(pos.qty)
                if qty == 0:
                    continue

                # 段永平框架：检查做空仓位
                if qty < 0:
                    logger.warning(f"段永平框架警告：发现做空仓位 {pos.symbol} qty={qty}")
                    continue

                result.append(PositionData(
                    symbol=pos.symbol,
                    qty=abs(qty),
                    avg_entry_price=float(pos.avg_entry_price),
                    side='long',
                    market_value=float(pos.market_value) if hasattr(pos, 'market_value') else 0,
                    unrealized_pl=float(pos.unrealized_pl) if hasattr(pos, 'unrealized_pl') else 0,
                    unrealized_plpc=float(pos.unrealized_plpc) if hasattr(pos, 'unrealized_plpc') else 0,
                ))
            self._position_cache = {p.symbol: p for p in result}
            return result
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return list(self._position_cache.values())

    def get_position(self, symbol: str) -> Optional[PositionData]:
        if not self._ensure_connected():
            return None
        try:
            pos = self._trading_client.get_open_position(symbol)
            qty = float(pos.qty)
            if qty == 0:
                return None
            return PositionData(
                symbol=pos.symbol,
                qty=abs(qty),
                avg_entry_price=float(pos.avg_entry_price),
                side='long' if qty > 0 else 'short',
                market_value=float(pos.market_value) if hasattr(pos, 'market_value') else 0,
                unrealized_pl=float(pos.unrealized_pl) if hasattr(pos, 'unrealized_pl') else 0,
                unrealized_plpc=float(pos.unrealized_plpc) if hasattr(pos, 'unrealized_plpc') else 0,
            )
        except Exception as e:
            if 'position_not_found' in str(e).lower() or 'no position' in str(e).lower():
                return None
            logger.error(f"获取持仓失败 {symbol}: {e}")
            return None

    # ====== 行情数据 ======

    def get_latest_bar(self, symbol: str) -> Optional[BarData]:
        if not self._ensure_connected():
            return None
        try:
            request = StockLatestBarRequest(symbol_or_symbols=symbol, feed='iex')
            data = self._data_client.get_stock_latest_bar(request)
            if symbol in data:
                b = data[symbol]
                return BarData(
                    timestamp=b.timestamp,
                    open=float(b.open),
                    high=float(b.high),
                    low=float(b.low),
                    close=float(b.close),
                    volume=int(b.volume)
                )
        except Exception as e:
            logger.error(f"获取最新K线失败 {symbol}: {e}")
        return None

    def get_bars(self, symbol: str, timeframe: str = "1Day",
                 limit: int = 200, start: str = None, end: str = None) -> List[BarData]:
        if not self._ensure_connected():
            return []
        try:
            unit, value = self.TIMEFRAME_MAP.get(timeframe, ('Day', 1))
            if unit == 'Minute':
                tf = TimeFrame(value, TimeFrame.Unit.Minute)
            elif unit == 'Hour':
                tf = TimeFrame(value, TimeFrame.Unit.Hour)
            elif unit == 'Day':
                tf = TimeFrame(value, TimeFrame.Unit.Day)
            elif unit == 'Week':
                tf = TimeFrame(value, TimeFrame.Unit.Week)
            else:
                tf = TimeFrame(1, TimeFrame.Unit.Day)

            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=tf,
                start=start,
                end=end,
                limit=limit,
                feed='iex'
            )
            data = self._data_client.get_stock_bars(request)
            if symbol not in data:
                return []

            bars = data[symbol]
            result = []
            for b in bars:
                result.append(BarData(
                    timestamp=b.timestamp,
                    open=float(b.open),
                    high=float(b.high),
                    low=float(b.low),
                    close=float(b.close),
                    volume=int(b.volume)
                ))
            return result
        except Exception as e:
            logger.error(f"获取K线失败 {symbol}: {e}")
            return []

    def get_latest_quote(self, symbol: str) -> Optional[QuoteData]:
        if not self._ensure_connected():
            return None
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol, feed='iex')
            data = self._data_client.get_stock_latest_quote(request)
            if symbol in data:
                q = data[symbol]
                return QuoteData(
                    bid_price=float(q.bid_price) if q.bid_price else 0,
                    bid_size=int(q.bid_size) if q.bid_size else 0,
                    ask_price=float(q.ask_price) if q.ask_price else 0,
                    ask_size=int(q.ask_size) if q.ask_size else 0,
                    timestamp=q.timestamp,
                    symbol=symbol
                )
        except Exception as e:
            logger.error(f"获取报价失败 {symbol}: {e}")
        return None

    # ====== 订单管理 ======

    def submit_order(self, symbol: str, qty: float, side: str,
                     order_type: str = "market", limit_price: float = None,
                     stop_price: float = None, time_in_force: str = "day") -> Optional[OrderData]:
        """
        提交订单 - 段永平框架: 只做多
        """
        if not self._ensure_connected():
            return None

        # ===== 段永平框架：禁止做空 =====
        if side.lower() != 'buy':
            logger.error(f"段永平框架约束：禁止做空/卖出开仓！symbol={symbol} side={side}")
            return None

        try:
            tif = TimeInForce.DAY if time_in_force.lower() == 'day' else TimeInForce.GTC

            if order_type == 'limit' and limit_price is not None:
                req = LimitOrderRequest(
                    symbol=symbol, qty=int(qty), side=OrderSide.BUY,
                    limit_price=limit_price, time_in_force=tif
                )
            elif order_type == 'stop' and stop_price is not None:
                req = StopOrderRequest(
                    symbol=symbol, qty=int(qty), side=OrderSide.BUY,
                    stop_price=stop_price, time_in_force=tif
                )
            elif order_type == 'stop_limit' and stop_price is not None and limit_price is not None:
                req = StopLimitOrderRequest(
                    symbol=symbol, qty=int(qty), side=OrderSide.BUY,
                    stop_price=stop_price, limit_price=limit_price, time_in_force=tif
                )
            else:
                req = MarketOrderRequest(
                    symbol=symbol, qty=int(qty), side=OrderSide.BUY,
                    time_in_force=tif
                )

            order = self._trading_client.submit_order(req)
            logger.info(f"订单已提交: {order.id} {symbol} buy {qty}")

            return OrderData(
                order_id=str(order.id),
                symbol=symbol,
                side='buy',
                qty=int(qty),
                order_type=order_type,
                limit_price=limit_price,
                stop_price=stop_price,
                status=str(order.status),
                filled_qty=int(order.filled_qty) if order.filled_qty else 0,
                filled_avg_price=float(order.filled_avg_price) if order.filled_avg_price else None,
                raw_order=order
            )
        except Exception as e:
            logger.error(f"提交订单失败 {symbol}: {e}")
            return None

    def get_order(self, order_id: str) -> Optional[OrderData]:
        if not self._ensure_connected():
            return None
        try:
            order = self._trading_client.get_order_by_id(order_id)
            return OrderData(
                order_id=str(order.id),
                symbol=order.symbol,
                side=order.side.value if hasattr(order.side, 'value') else str(order.side),
                qty=int(order.qty),
                order_type=order.type if hasattr(order, 'type') else 'market',
                status=str(order.status),
                filled_qty=int(order.filled_qty) if order.filled_qty else 0,
                filled_avg_price=float(order.filled_avg_price) if order.filled_avg_price else None,
                raw_order=order
            )
        except Exception as e:
            logger.error(f"查询订单失败 {order_id}: {e}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        if not self._ensure_connected():
            return False
        try:
            self._trading_client.cancel_order_by_id(order_id)
            logger.info(f"订单已取消: {order_id}")
            return True
        except Exception as e:
            logger.error(f"取消订单失败 {order_id}: {e}")
            return False

    def get_open_orders(self, symbol: str = None) -> List[OrderData]:
        if not self._ensure_connected():
            return []
        try:
            orders = self._trading_client.get_orders()
            result = []
            for order in orders:
                if symbol and order.symbol != symbol:
                    continue
                result.append(OrderData(
                    order_id=str(order.id),
                    symbol=order.symbol,
                    side=order.side.value if hasattr(order.side, 'value') else str(order.side),
                    qty=int(order.qty),
                    order_type=order.type if hasattr(order, 'type') else 'market',
                    status=str(order.status),
                    filled_qty=int(order.filled_qty) if order.filled_qty else 0,
                    filled_avg_price=float(order.filled_avg_price) if order.filled_avg_price else None,
                    raw_order=order
                ))
            return result
        except Exception as e:
            logger.error(f"获取活跃订单失败: {e}")
            return []

    # ====== 市场状态 ======

    def get_clock(self) -> Dict[str, Any]:
        if not self._ensure_connected():
            return {'is_open': False, 'next_open': '', 'next_close': '',
                    'timestamp': datetime.now().isoformat()}
        try:
            clock = self._trading_client.get_clock()
            return {
                'is_open': clock.is_open,
                'next_open': str(clock.next_open) if hasattr(clock, 'next_open') else '',
                'next_close': str(clock.next_close) if hasattr(clock, 'next_close') else '',
                'timestamp': str(clock.timestamp) if hasattr(clock, 'timestamp') else datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"获取市场时钟失败: {e}")
            return {'is_open': False, 'next_open': '', 'next_close': '',
                    'timestamp': datetime.now().isoformat()}

    # ====== 属性 ======

    def get_name(self) -> str:
        return "Alpaca"

    @property
    def paper_trading(self) -> bool:
        return self._paper
