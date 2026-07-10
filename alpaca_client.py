"""
Alpaca API 客户端封装
=====================
封装 Alpaca REST API v2，提供行情、交易、持仓、账户等核心功能。
支持 paper trading 与 live trading 环境切换。

核心功能：
- 账户信息查询
- 历史K线数据获取
- 实时行情快照
- 订单提交/取消/查询
- 持仓管理
- WebSocket 实时数据流

依赖：alpaca-py SDK + requests（REST直连兜底）
"""

import time
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional, Any
from dataclasses import dataclass

import pandas as pd
import numpy as np

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest, StockLatestTradeRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest, LimitOrderRequest,
    GetOrdersRequest, ClosePositionRequest
)
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus

from config import ALPACA_CONFIG

logger = logging.getLogger(__name__)


class AlpacaClientError(Exception):
    """Alpaca 客户端异常基类"""
    pass


class AuthenticationError(AlpacaClientError):
    """认证失败"""
    pass


class RateLimitError(AlpacaClientError):
    """触发速率限制"""
    pass


class DataFetchError(AlpacaClientError):
    """数据获取失败"""
    pass


@dataclass
class QuoteSnapshot:
    """行情快照数据"""
    symbol: str
    bid_price: float
    ask_price: float
    last_price: float
    timestamp: datetime


class AlpacaClient:
    """
    Alpaca API 统一客户端
    
    封装行情数据客户端 + 交易客户端，提供统一的调用接口。
    内置重试机制和错误处理。
    
    Usage:
        client = AlpacaClient()
        account = client.get_account()
        bars = client.get_bars("AAPL", days=100)
    """
    
    def __init__(self, config=None):
        """
        初始化 Alpaca 客户端
        
        Args:
            config: AlpacaConfig 实例，默认使用全局配置
        """
        self.config = config or ALPACA_CONFIG
        
        if not self.config.validate():
            raise AuthenticationError(
                "API 凭证未配置。请设置环境变量 ALPACA_API_KEY 和 ALPACA_SECRET_KEY，"
                "或在 config.py 中填入。"
            )
        
        # 行情数据客户端（使用 alpaca-py SDK）
        self._data_client: Optional[StockHistoricalDataClient] = None
        # 交易客户端（使用 alpaca-py SDK）
        self._trading_client: Optional[TradingClient] = None
        
        # REST API 直连（作为兜底方案）
        self._session = requests.Session()
        self._session.headers.update({
            "APCA-API-KEY-ID": self.config.api_key,
            "APCA-API-SECRET-KEY": self.config.api_secret,
        })
        
        # 重试配置
        self.max_retries: int = 3
        self.retry_delay: float = 1.0  # 秒，指数退避基数
        
        logger.info(f"AlpacaClient 初始化完成 | Paper={self.config.paper}")
    
    # ================================================================
    # 属性 & 懒加载
    # ================================================================
    
    @property
    def data_client(self) -> StockHistoricalDataClient:
        """懒加载行情数据客户端"""
        if self._data_client is None:
            self._data_client = StockHistoricalDataClient(
                api_key=self.config.api_key,
                secret_key=self.config.api_secret,
            )
        return self._data_client
    
    @property
    def trading_client(self) -> TradingClient:
        """懒加载交易客户端"""
        if self._trading_client is None:
            self._trading_client = TradingClient(
                api_key=self.config.api_key,
                secret_key=self.config.api_secret,
                paper=self.config.paper,
            )
        return self._trading_client
    
    # ================================================================
    # 重试机制
    # ================================================================
    
    def _retry(self, func, *args, **kwargs) -> Any:
        """
        带指数退避的重试装饰器
        
        Args:
            func: 要执行的函数
            *args, **kwargs: 函数参数
            
        Returns:
            函数返回值
            
        Raises:
            AlpacaClientError: 所有重试失败后抛出
        """
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                wait = self.retry_delay * (2 ** attempt)
                logger.warning(
                    f"请求失败 (尝试 {attempt+1}/{self.max_retries}): {e} | "
                    f"等待 {wait:.1f}s 后重试"
                )
                time.sleep(wait)
        
        raise AlpacaClientError(f"重试 {self.max_retries} 次后仍然失败: {last_error}")
    
    # ================================================================
    # 账户信息
    # ================================================================
    
    def get_account(self) -> dict:
        """
        获取账户信息
        
        Returns:
            dict: 包含 cash, portfolio_value, buying_power, status 等字段
        """
        def _fetch():
            account = self.trading_client.get_account()
            return {
                "id": account.id,
                "account_number": account.account_number,
                "status": str(account.status),
                "cash": float(account.cash),
                "portfolio_value": float(account.portfolio_value),
                "buying_power": float(account.buying_power),
                "equity": float(account.equity),
                "long_market_value": float(account.long_market_value),
                "short_market_value": float(account.short_market_value),
                "daytrade_count": int(account.daytrade_count),
                "created_at": str(account.created_at),
                "pattern_day_trader": bool(account.pattern_day_trader),
                "trading_blocked": bool(account.trading_blocked),
                "currency": str(account.currency),
            }
        
        return self._retry(_fetch)
    
    # ================================================================
    # 行情数据
    # ================================================================
    
    def get_bars(
        self,
        symbols: list[str] | str,
        days: int = 100,
        timeframe: str = "1Day",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        获取历史K线数据
        
        Args:
            symbols: 股票代码，单个或列表
            days: 回看天数（与start/end二选一）
            timeframe: K线周期，如 "1Day", "1Hour", "5Min"
            start: 起始时间
            end: 结束时间
            
        Returns:
            pd.DataFrame: 包含 open, high, low, close, volume 列
                         单只股票返回扁平 DataFrame
                         多只股票返回 MultiIndex DataFrame
        """
        if isinstance(symbols, str):
            symbols = [symbols]
        
        # 解析时间框架
        tf = self._parse_timeframe(timeframe)
        
        # 计算时间范围
        if start is None:
            start = datetime.now() - timedelta(days=days)
        if end is None:
            end = datetime.now()
        
        def _fetch():
            request = StockBarsRequest(
                symbol_or_symbols=symbols,
                timeframe=tf,
                start=start,
                end=end,
            )
            bars = self.data_client.get_stock_bars(request)
            return bars.df
        
        try:
            df = self._retry(_fetch)
            
            # 单只股票时扁平化
            if len(symbols) == 1:
                if isinstance(df.index, pd.MultiIndex):
                    df = df.xs(symbols[0], level=0)
            
            logger.info(f"获取K线数据成功 | {symbols} | {len(df)} 条记录")
            return df
            
        except Exception as e:
            logger.error(f"获取K线数据失败: {symbols} | {e}")
            raise DataFetchError(f"K线数据获取失败: {e}")
    
    def get_latest_quote(self, symbols: list[str] | str) -> dict[str, QuoteSnapshot]:
        """
        获取最新报价快照
        
        Args:
            symbols: 股票代码
            
        Returns:
            dict: {symbol: QuoteSnapshot}
        """
        if isinstance(symbols, str):
            symbols = [symbols]
        
        def _fetch():
            request = StockLatestQuoteRequest(symbol_or_symbols=symbols)
            quotes = self.data_client.get_stock_latest_quote(request)
            return quotes
        
        try:
            quotes = self._retry(_fetch)
            result = {}
            for sym in symbols:
                if sym in quotes:
                    q = quotes[sym]
                    result[sym] = QuoteSnapshot(
                        symbol=sym,
                        bid_price=float(q.bid_price or 0),
                        ask_price=float(q.ask_price or 0),
                        last_price=float((q.bid_price + q.ask_price) / 2) if q.bid_price and q.ask_price else 0,
                        timestamp=q.timestamp,
                    )
            return result
        except Exception as e:
            logger.error(f"获取最新报价失败: {symbols} | {e}")
            raise DataFetchError(f"报价数据获取失败: {e}")
    
    def get_latest_trade(self, symbols: list[str] | str) -> dict[str, float]:
        """
        获取最新成交价
        
        Args:
            symbols: 股票代码
            
        Returns:
            dict: {symbol: last_price}
        """
        if isinstance(symbols, str):
            symbols = [symbols]
        
        def _fetch():
            request = StockLatestTradeRequest(symbol_or_symbols=symbols)
            trades = self.data_client.get_stock_latest_trade(request)
            return trades
        
        try:
            trades = self._retry(_fetch)
            return {sym: float(trades[sym].price) for sym in symbols if sym in trades}
        except Exception as e:
            logger.error(f"获取最新成交价失败: {symbols} | {e}")
            raise DataFetchError(f"成交数据获取失败: {e}")
    
    # ================================================================
    # 交易操作
    # ================================================================
    
    def submit_market_order(
        self,
        symbol: str,
        qty: float,
        side: str = "buy",
        time_in_force: str = "day",
    ) -> dict:
        """
        提交市价单
        
        Args:
            symbol: 股票代码
            qty: 数量（支持小数，表示碎股）
            side: "buy" 或 "sell"
            time_in_force: 有效期，day/gtc/ioc/fok
            
        Returns:
            dict: 订单信息
        """
        if not self.config.paper and side == "sell":
            logger.warning("Live 环境下卖出操作需要确认")
        
        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        tif = self._parse_tif(time_in_force)
        
        def _fetch():
            order = MarketOrderRequest(
                symbol_or_id=symbol,
                qty=qty,
                side=order_side,
                time_in_force=tif,
            )
            result = self.trading_client.submit_order(order)
            return self._order_to_dict(result)
        
        result = self._retry(_fetch)
        logger.info(f"市价单提交成功 | {side.upper()} {qty} {symbol} | ID={result['id']}")
        return result
    
    def submit_limit_order(
        self,
        symbol: str,
        qty: float,
        limit_price: float,
        side: str = "buy",
        time_in_force: str = "day",
    ) -> dict:
        """
        提交限价单
        
        Args:
            symbol: 股票代码
            qty: 数量
            limit_price: 限价
            side: "buy" 或 "sell"
            time_in_force: 有效期
            
        Returns:
            dict: 订单信息
        """
        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        tif = self._parse_tif(time_in_force)
        
        def _fetch():
            order = LimitOrderRequest(
                symbol_or_id=symbol,
                qty=qty,
                limit_price=limit_price,
                side=order_side,
                time_in_force=tif,
            )
            result = self.trading_client.submit_order(order)
            return self._order_to_dict(result)
        
        result = self._retry(_fetch)
        logger.info(f"限价单提交成功 | {side.upper()} {qty} {symbol} @ ${limit_price} | ID={result['id']}")
        return result
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        try:
            self.trading_client.cancel_order_by_id(order_id)
            logger.info(f"订单取消成功 | ID={order_id}")
            return True
        except Exception as e:
            logger.error(f"订单取消失败 | ID={order_id} | {e}")
            return False
    
    def get_orders(self, status: str = "open", limit: int = 50) -> list[dict]:
        """
        查询订单列表
        
        Args:
            status: "open", "closed", "all"
            limit: 返回数量限制
            
        Returns:
            list[dict]: 订单列表
        """
        status_map = {
            "open": QueryOrderStatus.OPEN,
            "closed": QueryOrderStatus.CLOSED,
            "all": QueryOrderStatus.ALL,
        }
        
        def _fetch():
            request = GetOrdersRequest(
                status=status_map.get(status, QueryOrderStatus.OPEN),
                limit=limit,
            )
            orders = self.trading_client.get_orders(request)
            return [self._order_to_dict(o) for o in orders]
        
        return self._retry(_fetch)
    
    # ================================================================
    # 持仓管理
    # ================================================================
    
    def get_positions(self) -> list[dict]:
        """
        获取当前持仓列表
        
        Returns:
            list[dict]: 持仓信息列表
        """
        def _fetch():
            positions = self.trading_client.get_all_positions()
            return [self._position_to_dict(p) for p in positions]
        
        return self._retry(_fetch)
    
    def get_position(self, symbol: str) -> Optional[dict]:
        """获取单个标的持仓"""
        try:
            position = self.trading_client.get_open_position(symbol)
            return self._position_to_dict(position)
        except Exception:
            return None
    
    def close_position(self, symbol: str) -> dict:
        """
        平仓指定标的
        
        Args:
            symbol: 股票代码
            
        Returns:
            dict: 平仓订单信息
        """
        def _fetch():
            result = self.trading_client.close_position(symbol)
            return self._order_to_dict(result)
        
        result = self._retry(_fetch)
        logger.info(f"平仓成功 | {symbol}")
        return result
    
    def close_all_positions(self) -> list[dict]:
        """平掉所有持仓"""
        def _fetch():
            result = self.trading_client.close_all_positions()
            return [self._order_to_dict(o) for o in result]
        
        results = self._retry(_fetch)
        logger.info(f"全部平仓完成 | 共 {len(results)} 笔")
        return results
    
    # ================================================================
    # REST API 直连（兜底方案）
    # ================================================================
    
    def rest_get(self, endpoint: str, params: dict = None) -> dict:
        """
        REST GET 直连请求
        
        Args:
            endpoint: API 路径，如 "/v2/account"
            params: 查询参数
            
        Returns:
            dict: 响应数据
        """
        url = f"{self.config.base_url}{endpoint}"
        response = self._session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def rest_post(self, endpoint: str, data: dict = None) -> dict:
        """
        REST POST 直连请求
        
        Args:
            endpoint: API 路径
            data: 请求体
            
        Returns:
            dict: 响应数据
        """
        url = f"{self.config.base_url}{endpoint}"
        response = self._session.post(url, json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    
    # ================================================================
    # 辅助方法
    # ================================================================
    
    @staticmethod
    def _parse_timeframe(tf_str: str) -> TimeFrame:
        """解析时间框架字符串为 TimeFrame 对象"""
        mapping = {
            "1Min": TimeFrame(1, TimeFrameUnit.Minute),
            "5Min": TimeFrame(5, TimeFrameUnit.Minute),
            "15Min": TimeFrame(15, TimeFrameUnit.Minute),
            "1Hour": TimeFrame(1, TimeFrameUnit.Hour),
            "1Day": TimeFrame(1, TimeFrameUnit.Day),
            "1Week": TimeFrame(1, TimeFrameUnit.Week),
            "1Month": TimeFrame(1, TimeFrameUnit.Month),
        }
        return mapping.get(tf_str, TimeFrame(1, TimeFrameUnit.Day))
    
    @staticmethod
    def _parse_tif(tif_str: str) -> TimeInForce:
        """解析订单有效期"""
        mapping = {
            "day": TimeInForce.DAY,
            "gtc": TimeInForce.GTC,
            "ioc": TimeInForce.IOC,
            "fok": TimeInForce.FOK,
        }
        return mapping.get(tif_str.lower(), TimeInForce.DAY)
    
    @staticmethod
    def _order_to_dict(order) -> dict:
        """将 Alpaca 订单对象转为 dict"""
        try:
            return {
                "id": str(order.id),
                "symbol": str(order.symbol),
                "side": str(order.side),
                "type": str(order.type),
                "qty": str(order.qty),
                "filled_qty": str(order.filled_qty),
                "status": str(order.status),
                "submitted_at": str(order.submitted_at),
                "filled_at": str(order.filled_at) if order.filled_at else None,
                "filled_avg_price": str(order.filled_avg_price) if order.filled_avg_price else None,
            }
        except Exception:
            return {"raw": str(order)}
    
    @staticmethod
    def _position_to_dict(pos) -> dict:
        """将 Alpaca 持仓对象转为 dict"""
        try:
            return {
                "symbol": str(pos.symbol),
                "qty": str(pos.qty),
                "side": str(pos.side),
                "market_value": str(pos.market_value),
                "cost_basis": str(pos.cost_basis),
                "avg_entry_price": str(pos.avg_entry_price),
                "unrealized_pl": str(pos.unrealized_pl),
                "unrealized_plpc": str(pos.unrealized_plpc),
                "current_price": str(pos.current_price),
                "lastday_price": str(pos.lastday_price),
                "change_today": str(pos.change_today),
            }
        except Exception:
            return {"raw": str(pos)}
    
    def __repr__(self) -> str:
        return f"AlpacaClient(paper={self.config.paper}, configured={self.config.validate()})"
