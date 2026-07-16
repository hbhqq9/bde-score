"""
BDE Score™ - AI-Powered Multi-Market Stock Analysis MCP Server
Copyright (C) 2026 BDE Score™ (https://github.com/hbhqq9/bde-score)

Licensed under AGPL-3.0 with commercial option.
If you run a modified version on a network server, you must make
the complete source code available. See LICENSE for details.
Commercial licensing available: nnhbh@foxmail.com
"""

"""
BDE-Stock IBKR Adapter - Interactive Brokers 适配器
使用 ib_insync 库通过 Socket 连接 IB Gateway / TWS
"""

import time
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

try:
    from ib_insync import IB, Stock, Option, Index, Forex, Crypto
    from ib_insync import Order as IBOrder
    from ib_insync.contract import Contract
    IB_INSYNC_AVAILABLE = True
except ImportError:
    IB_INSYNC_AVAILABLE = False
    logger.warning("ib_insync 未安装，IBKR 适配器不可用。请运行: pip install ib_insync")

from broker_adapter import (
    BrokerAdapter, BarData, QuoteData, PositionData, OrderData, AccountData
)


class IBKRAdapter(BrokerAdapter):
    """
    Interactive Brokers 适配器
    
    通过 ib_insync 库连接 IB Gateway 或 TWS:
    - Paper Trading: host='127.0.0.1', port=7497, clientId=1
    - Live Trading:  host='127.0.0.1', port=7496, clientId=1
    
    段永平框架约束（硬编码，不可修改）:
    - 绝对不做空
    - 绝对不加杠杆
    - 只做多，现金买入
    """

    # IBKR timeframe 映射
    TIMEFRAME_MAP = {
        '1Min':  ('1 min',  '1 D'),
        '5Min':  ('5 mins', '1 D'),
        '15Min': ('15 mins', '1 D'),
        '1Hour': ('1 hour', '1 M'),
        '4Hour': ('4 hours', '6 M'),
        '1Day':  ('1 day',  '1 Y'),
        '1Week': ('1 week', '2 Y'),
    }

    def __init__(self, host: str = '127.0.0.1', port: int = 7497,
                 client_id: int = 1, readonly: bool = False,
                 account: str = '', timeout: int = 20):
        if not IB_INSYNC_AVAILABLE:
            raise ImportError("ib_insync 未安装，请运行: pip install ib_insync")

        self._host = host
        self._port = port
        self._client_id = client_id
        self._readonly = readonly
        self._account = account
        self._timeout = timeout
        self._ib = IB()
        self._connected = False
        self._paper_trading = (port == 7497)
        self._account_id = account
        self._order_id_counter = 0

        # 缓存 - 持仓/账户信息
        self._position_cache = {}
        self._account_cache = None

    # ====== 连接管理 ======

    def connect(self) -> bool:
        try:
            if self._ib.isConnected():
                self._connected = True
                logger.info("IBKR 已连接")
                return True

            logger.info(f"连接 IBKR: {self._host}:{self._port} clientId={self._client_id}")
            self._ib.connect(
                host=self._host,
                port=self._port,
                clientId=self._client_id,
                readonly=self._readonly,
                account=self._account,
                timeout=self._timeout
            )
            self._connected = True
            
            # 获取账户ID
            if not self._account_id:
                accounts = self._ib.manageAccounts()
                if accounts:
                    self._account_id = accounts[0]
            
            mode = "Paper" if self._paper_trading else "Live"
            logger.info(f"IBKR 连接成功 [{mode}] account={self._account_id}")
            return True
        except Exception as e:
            self._connected = False
            logger.error(f"IBKR 连接失败: {e}")
            return False

    def disconnect(self):
        try:
            if self._ib.isConnected():
                self._ib.disconnect()
            self._connected = False
            logger.info("IBKR 已断开连接")
        except Exception as e:
            logger.error(f"IBKR 断开连接异常: {e}")

    def is_connected(self) -> bool:
        return self._connected and self._ib.isConnected()

    # ====== 辅助方法 ======

    def _make_contract(self, symbol: str, currency: str = 'USD',
                       exchange: str = 'SMART') -> Contract:
        """创建股票合约"""
        return Stock(symbol, exchange, currency)

    def _resolve_contract(self, symbol: str) -> Optional[Contract]:
        """解析合约（确保合约有效）"""
        contract = self._make_contract(symbol)
        try:
            self._ib.qualifyContracts(contract)
            return contract
        except Exception as e:
            logger.error(f"合约解析失败 {symbol}: {e}")
            return None

    def _ensure_connected(self) -> bool:
        if not self.is_connected():
            logger.error("IBKR 未连接")
            return False
        return True

    # ====== 账户信息 ======

    def get_account(self) -> Optional[AccountData]:
        if not self._ensure_connected():
            return None
        try:
            summary = self._ib.accountSummary(self._account_id)
            cash = 0.0
            nav = 0.0
            buying_power = 0.0
            day_trade_count = 0

            for item in summary:
                tag = item.tag
                val = float(item.value) if item.value and item.value.replace('.', '').replace('-', '').replace('E', '').replace('+', '').isdigit() else 0.0
                if tag == 'TotalCashValue':
                    cash = val
                elif tag == 'NetLiquidation':
                    nav = val
                elif tag == 'BuyingPower':
                    buying_power = val
                elif tag == 'DayTradesRemaining':
                    day_trade_count = int(float(item.value)) if item.value else 0

            acct = AccountData(
                cash=cash,
                portfolio_value=nav,
                buying_power=buying_power,
                day_trade_count=day_trade_count,
                status='ACTIVE'
            )
            self._account_cache = acct
            return acct
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
            positions = self._ib.positions(self._account_id)
            result = []
            for pos in positions:
                symbol = pos.contract.symbol
                qty = float(pos.position)
                if qty == 0:
                    continue

                # 段永平框架：检查是否为做空仓位（不应该存在）
                if qty < 0:
                    logger.warning(f"段永平框架警告：发现做空仓位 {symbol} qty={qty}，系统不应做空！")
                    continue  # 跳过空头仓位

                avg_cost = float(pos.avgCost) if pos.avgCost else 0.0
                market_value = float(pos.position) * avg_cost

                result.append(PositionData(
                    symbol=symbol,
                    qty=abs(qty),
                    avg_entry_price=avg_cost,
                    side='long',
                    market_value=market_value
                ))
            self._position_cache = {p.symbol: p for p in result}
            return result
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return list(self._position_cache.values())

    def get_position(self, symbol: str) -> Optional[PositionData]:
        positions = self.get_positions()
        for p in positions:
            if p.symbol == symbol:
                return p
        return None

    # ====== 行情数据 ======

    def get_latest_bar(self, symbol: str) -> Optional[BarData]:
        bars = self.get_bars(symbol, timeframe='1Day', limit=1)
        if bars:
            return bars[-1]
        return None

    def get_bars(self, symbol: str, timeframe: str = "1Day",
                 limit: int = 200, start: str = None, end: str = None) -> List[BarData]:
        if not self._ensure_connected():
            return []
        try:
            contract = self._resolve_contract(symbol)
            if not contract:
                return []

            # 映射 timeframe
            bar_size, duration = self.TIMEFRAME_MAP.get(timeframe, ('1 day', '1 Y'))
            
            # 根据 limit 和 timeframe 调整 duration
            if timeframe == '1Day' and limit <= 5:
                duration = '1 M'
            elif timeframe == '1Day' and limit <= 30:
                duration = '3 M'
            
            end_dt = None
            if end:
                try:
                    end_dt = datetime.strptime(end, '%Y-%m-%d')
                except Exception:
                    end_dt = None
            if not end_dt:
                end_dt = datetime.now()

            bars = self._ib.reqHistoricalData(
                contract,
                endDateTime=end_dt,
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow='TRADES',
                useRTH=True,
                formatDate=1,
                timeout=30
            )

            result = []
            for b in bars:
                result.append(BarData(
                    timestamp=b.date,
                    open=float(b.open),
                    high=float(b.high),
                    low=float(b.low),
                    close=float(b.close),
                    volume=int(b.volume) if b.volume >= 0 else 0,
                    vwap=float(b.wap) if hasattr(b, 'wap') and b.wap else 0,
                    trade_count=int(b.barCount) if hasattr(b, 'barCount') and b.barCount >= 0 else 0
                ))

            return result[-limit:] if limit and len(result) > limit else result

        except Exception as e:
            logger.error(f"获取K线数据失败 {symbol}: {e}")
            return []

    def get_latest_quote(self, symbol: str) -> Optional[QuoteData]:
        """
        获取最新报价
        注意：IBKR 的实时行情需要订阅市场数据
        如果无实时行情，回退到最新交易价格
        """
        if not self._ensure_connected():
            return None
        try:
            contract = self._resolve_contract(symbol)
            if not contract:
                return None

            # 尝试获取实时 tick 数据
            ticker = self._ib.reqTickers(contract)
            if ticker and ticker.contract:
                bid = float(ticker.bid) if ticker.bid and ticker.bid > 0 else 0.0
                ask = float(ticker.ask) if ticker.ask and ticker.ask > 0 else 0.0
                last = float(ticker.last) if ticker.last and ticker.last > 0 else 0.0
                bid_size = int(ticker.bidSize) if ticker.bidSize and ticker.bidSize > 0 else 0
                ask_size = int(ticker.askSize) if ticker.askSize and ticker.askSize > 0 else 0

                # 如果 bid/ask 无效，使用 last price
                if bid <= 0 and ask <= 0 and last > 0:
                    bid = last
                    ask = last

                return QuoteData(
                    bid_price=bid,
                    bid_size=bid_size,
                    ask_price=ask,
                    ask_size=ask_size,
                    timestamp=datetime.now(),
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
        提交订单
        
        段永平框架约束:
        - 绝对不做空: side 必须为 'buy'
        - 绝对不加杠杆: 必须全额现金支付
        - 只做多，现金买入
        """
        if not self._ensure_connected():
            return None

        # ===== 段永平框架：禁止做空 =====
        if side.lower() != 'buy':
            logger.error(f"段永平框架约束：禁止做空/卖出开仓！symbol={symbol} side={side}")
            return None

        try:
            contract = self._resolve_contract(symbol)
            if not contract:
                return None

            # 构建订单
            action = 'BUY'
            tif = 'DAY' if time_in_force.lower() == 'day' else 'GTC'

            if order_type == 'limit' and limit_price is not None:
                order = self._ib.limitOrder(action, int(qty), limit_price)
            elif order_type == 'stop' and stop_price is not None:
                order = self._ib.stopOrder(action, int(qty), stop_price)
            elif order_type == 'stop_limit' and stop_price is not None and limit_price is not None:
                order = IBOrder()
                order.action = action
                order.totalQuantity = int(qty)
                order.orderType = 'STP LMT'
                order.auxPrice = stop_price
                order.lmtPrice = limit_price
            else:
                order = self._ib.marketOrder(action, int(qty))

            order.tif = tif

            # 提交订单
            trade = self._ib.placeOrder(contract, order)
            self._ib.sleep(1)  # 等待订单确认

            # 构建返回数据
            order_data = OrderData(
                order_id=str(trade.order.orderId),
                symbol=symbol,
                side=side.lower(),
                qty=int(qty),
                order_type=order_type,
                limit_price=limit_price,
                stop_price=stop_price,
                status=trade.orderStatus.status,
                filled_qty=int(trade.orderStatus.filled),
                filled_avg_price=float(trade.orderStatus.avgFillPrice) if trade.orderStatus.avgFillPrice else None,
                created_at=datetime.now(),
                raw_order=trade
            )

            logger.info(f"订单已提交: {order_data}")
            return order_data

        except Exception as e:
            logger.error(f"提交订单失败 {symbol}: {e}")
            return None

    def get_order(self, order_id: str) -> Optional[OrderData]:
        if not self._ensure_connected():
            return None
        try:
            trades = self._ib.openTrades()
            for trade in trades:
                if str(trade.order.orderId) == str(order_id):
                    return self._trade_to_order_data(trade)
            
            # 查找已完成的订单
            fills = self._ib.fills()
            for fill in fills:
                if str(fill.contract.symbol):
                    return self._fill_to_order_data(fill)
            
            return None
        except Exception as e:
            logger.error(f"查询订单失败 {order_id}: {e}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        if not self._ensure_connected():
            return False
        try:
            trades = self._ib.openTrades()
            for trade in trades:
                if str(trade.order.orderId) == str(order_id):
                    self._ib.cancelOrder(trade.order)
                    logger.info(f"订单已取消: {order_id}")
                    return True
            logger.warning(f"未找到活跃订单: {order_id}")
            return False
        except Exception as e:
            logger.error(f"取消订单失败 {order_id}: {e}")
            return False

    def get_open_orders(self, symbol: str = None) -> List[OrderData]:
        if not self._ensure_connected():
            return []
        try:
            trades = self._ib.openTrades()
            result = []
            for trade in trades:
                if symbol and trade.contract.symbol != symbol:
                    continue
                result.append(self._trade_to_order_data(trade))
            return result
        except Exception as e:
            logger.error(f"获取活跃订单失败: {e}")
            return []

    # ====== 市场状态 ======

    def get_clock(self) -> Dict[str, Any]:
        """
        获取市场时钟
        IBKR 通过 reqMarketRule 或手动判断
        美东时间 9:30-16:00 为交易时段
        """
        if not self._ensure_connected():
            return {
                'is_open': False,
                'next_open': '',
                'next_close': '',
                'timestamp': datetime.now().isoformat()
            }
        try:
            # 使用 reqMarketDataType 判断市场状态
            # 1=Live, 2=Frozen, 3=Delayed, 4=Delayed-Frozen
            market_data_type = self._ib.reqMarketDataType()
            
            # 简单判断：工作日 + 美东时间
            now = datetime.now()
            hour = now.hour  # UTC
            est_hour = (hour - 5) % 24  # 粗略 EST
            
            is_open = (9 <= est_hour < 16) and now.weekday() < 5
            
            return {
                'is_open': is_open or market_data_type == 1,
                'next_open': '',
                'next_close': '',
                'timestamp': now.isoformat(),
                'market_data_type': market_data_type
            }
        except Exception as e:
            logger.error(f"获取市场时钟失败: {e}")
            return {
                'is_open': False,
                'next_open': '',
                'next_close': '',
                'timestamp': datetime.now().isoformat()
            }

    # ====== 期权支持 ======

    def get_option_contracts(self, underlying: str, expiration: str = None,
                             option_type: str = None) -> List[Dict]:
        """获取期权合约链"""
        if not self._ensure_connected():
            return []
        try:
            stock = self._make_contract(underlying)
            self._ib.qualifyContracts(stock)

            # 获取期权链
            chains = self._ib.reqSecDefOptParams(underlying, '', 'STK', stock.conId)
            if not chains:
                return []

            chain = chains[0]
            result = []
            
            for exp in chain.expirations[:5]:  # 取前5个到期日
                for strike in chain.strikes[:20]:  # 取前20个行权价
                    for right in (['C', 'P'] if not option_type else [option_type.upper()[0]]):
                        option = Option(underlying, exp, strike, right, 'SMART', 'USD')
                        result.append({
                            'symbol': underlying,
                            'expiration': exp,
                            'strike': strike,
                            'type': 'call' if right == 'C' else 'put',
                            'contract': option
                        })

            return result
        except Exception as e:
            logger.error(f"获取期权合约失败 {underlying}: {e}")
            return []

    def get_option_quotes(self, contracts: List) -> Dict:
        """获取期权报价"""
        if not self._ensure_connected():
            return {}
        try:
            tickers = self._ib.reqTickers(*contracts[:10])
            result = {}
            for t in tickers:
                key = f"{t.contract.symbol}_{t.contract.lastTradeDateOrContractMonth}_{t.contract.strike}_{t.contract.right}"
                result[key] = {
                    'bid': float(t.bid) if t.bid else 0,
                    'ask': float(t.ask) if t.ask else 0,
                    'last': float(t.last) if t.last else 0,
                    'model': float(t.modelGreeks) if t.modelGreeks else None
                }
            return result
        except Exception as e:
            logger.error(f"获取期权报价失败: {e}")
            return {}

    # ====== 内部转换方法 ======

    def _trade_to_order_data(self, trade) -> OrderData:
        """将 ib_insync Trade 转换为 OrderData"""
        return OrderData(
            order_id=str(trade.order.orderId),
            symbol=trade.contract.symbol,
            side='buy' if trade.order.action == 'BUY' else 'sell',
            qty=int(trade.order.totalQuantity),
            order_type=trade.order.orderType,
            limit_price=float(trade.order.lmtPrice) if trade.order.lmtPrice and trade.order.lmtPrice != 0 else None,
            stop_price=float(trade.order.auxPrice) if trade.order.auxPrice and trade.order.auxPrice != 0 else None,
            status=trade.orderStatus.status,
            filled_qty=int(trade.orderStatus.filled),
            filled_avg_price=float(trade.orderStatus.avgFillPrice) if trade.orderStatus.avgFillPrice else None,
            raw_order=trade
        )

    def _fill_to_order_data(self, fill) -> OrderData:
        """将 ib_insync Fill 转换为 OrderData"""
        return OrderData(
            order_id=str(fill.execution.orderId),
            symbol=fill.contract.symbol,
            side='buy' if fill.execution.side == 'BOT' else 'sell',
            qty=int(fill.execution.shares),
            status='Filled',
            filled_qty=int(fill.execution.shares),
            filled_avg_price=float(fill.execution.price),
            raw_order=fill
        )

    # ====== 属性 ======

    def get_name(self) -> str:
        return "Interactive Brokers (IBKR)"

    @property
    def paper_trading(self) -> bool:
        return self._paper_trading
