"""
BDE-Stock Futu Adapter - 富途证券适配器
通过 FutuOpenD 网关连接富途证券，支持美股/港股/A股

连接方式:
  - FutuOpenD 是富途本地代理服务，需先启动
  - 默认端口: 11111
  - API文档: https://openapi.futunn.com

段永平框架约束（硬编码，不可修改）:
  - 绝对不做空
  - 绝对不加杠杆
  - 只做多，现金买入
"""

import time
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

try:
    from futu import (
        OpenQuoteContext, OpenSecTradeContext,
        TrdMarket, SecurityFirm, TrdSide, OrderType,
        KLType, KL_FIELD, RET_OK, RET_ERROR,
        Market, SysConfig,
        TrdEnv, TrdMarket as TrdMkt,
    )
    FUTU_AVAILABLE = True
except ImportError:
    FUTU_AVAILABLE = False
    logger.warning("futu-api 未安装，Futu 适配器不可用。请运行: pip install futu-api")

from broker_adapter import (
    BrokerAdapter, BarData, QuoteData, PositionData, OrderData, AccountData
)


class FutuAdapter(BrokerAdapter):
    """
    富途证券适配器

    通过 FutuOpenD 网关连接:
    - 默认地址: 127.0.0.1:11111
    - 支持模拟交易(Paper Trading)
    - 支持美股(US.xxx)、港股(HK.xxxx)、A股(SH.xxxxxx/SZ.xxxxxx)

    段永平框架约束（硬编码，不可修改）:
    - 绝对不做空
    - 绝对不加杠杆
    - 只做多，现金买入
    """

    # ===== Timeframe 映射 =====
    # BDE统一格式 -> Futu KLType
    TIMEFRAME_MAP = {
        '1Min':  KLType.K_1M,
        '5Min':  KLType.K_5M,
        '15Min': KLType.K_15M,
        '30Min': KLType.K_30M,
        '1Hour': KLType.K_60M,
        '1Day':  KLType.K_DAY,
        '1Week': KLType.K_WEEK,
        '1Mon':  KLType.K_MON,
    }

    # 订单状态映射
    ORDER_STATUS_MAP = {
        '':          'Pending',
        'NONE':      'Pending',
        'NORMAL':    'Submitted',
        'SUBMITTED': 'Submitted',
        'WAITING':   'Pending',
        'SUBMITTING':'Pending',
        'FILLED_ALL':       'Filled',
        'FILLED_PART':      'PartiallyFilled',
        'CANCELLED_ALL':    'Cancelled',
        'CANCELLED_PART':   'Cancelled',
        'FAILED':           'Rejected',
        'DISABLED':         'Cancelled',
        'DELETED':          'Cancelled',
    }

    def __init__(self, host: str = '127.0.0.1', port: int = 11111,
                 paper_trading: bool = True,
                 trd_market: str = 'US',
                 security_firm: str = 'FUTUSECURITIES'):
        """
        初始化富途适配器
        :param host: FutuOpenD 地址，默认 127.0.0.1
        :param port: FutuOpenD 端口，默认 11111
        :param paper_trading: True=模拟盘, False=实盘
        :param trd_market: 交易市场 ('US', 'HK', 'SH', 'SZ')
        :param security_firm: 券商机构 ('FUTUSECURITIES', 'FUTUSECURITIES_HK')
        """
        if not FUTU_AVAILABLE:
            raise ImportError("futu-api 未安装，请运行: pip install futu-api")

        self._host = host
        self._port = port
        self._paper = paper_trading
        self._trd_market = trd_market
        self._security_firm = security_firm

        self._quote_ctx = None   # 行情上下文
        self._trade_ctx = None   # 交易上下文
        self._connected = False

        # 缓存
        self._position_cache = {}
        self._account_cache = None

        # 交易环境
        self._trd_env = TrdEnv.SIMULATE if paper_trading else TrdEnv.REAL

    # ====== 连接管理 ======

    def connect(self) -> bool:
        """连接到 FutuOpenD 网关"""
        try:
            logger.info(f"连接 FutuOpenD: {self._host}:{self._port} "
                        f"[{'模拟' if self._paper else '实盘'}]")

            # 创建行情上下文
            self._quote_ctx = OpenQuoteContext(
                host=self._host, port=self._port
            )

            # 创建交易上下文
            sec_firm = (SecurityFirm.FUTUSECURITIES
                        if self._security_firm == 'FUTUSECURITIES'
                        else SecurityFirm.FUTUSECURITIES_HK)

            self._trade_ctx = OpenSecTradeContext(
                filter_trdmarket=TrdMarket.NONE,
                host=self._host,
                port=self._port,
                security_firm=sec_firm
            )

            # 测试连接 - 获取账户列表
            ret, data = self._trade_ctx.acc_list()
            if ret != RET_OK:
                logger.error(f"获取账户列表失败: {data}")
                self._safe_close()
                return False

            self._connected = True
            mode = "模拟盘" if self._paper else "实盘"
            logger.info(f"Futu 连接成功 [{mode}] 账户数={len(data)}")
            return True

        except Exception as e:
            self._connected = False
            logger.error(f"Futu 连接失败: {e}")
            self._safe_close()
            return False

    def disconnect(self):
        """断开连接"""
        try:
            self._safe_close()
            self._connected = False
            logger.info("Futu 已断开连接")
        except Exception as e:
            logger.error(f"Futu 断开连接异常: {e}")

    def is_connected(self) -> bool:
        return self._connected

    def _safe_close(self):
        """安全关闭上下文"""
        try:
            if self._quote_ctx:
                self._quote_ctx.close()
        except Exception:
            pass
        try:
            if self._trade_ctx:
                self._trade_ctx.close()
        except Exception:
            pass
        self._quote_ctx = None
        self._trade_ctx = None

    def _ensure_connected(self) -> bool:
        if not self.is_connected():
            logger.error("Futu 未连接")
            return False
        return True

    # ====== Symbol 转换 ======

    def _to_futu_symbol(self, symbol: str) -> str:
        """
        将标准 symbol 转为 Futu 格式
        AAPL -> US.AAPL
        0700 -> HK.00700
        600519 -> SH.600519
        """
        # 如果已经包含市场前缀，直接返回
        if '.' in symbol and symbol.split('.')[0] in ('US', 'HK', 'SH', 'SZ'):
            return symbol

        # 默认添加 US 前缀
        return f"US.{symbol}"

    def _to_standard_symbol(self, futu_symbol: str) -> str:
        """
        将 Futu symbol 转为标准格式
        US.AAPL -> AAPL
        HK.00700 -> 0700
        SH.600519 -> 600519
        """
        if '.' in futu_symbol:
            parts = futu_symbol.split('.', 1)
            return parts[1]
        return futu_symbol

    # ====== 账户信息 ======

    def get_account(self) -> Optional[AccountData]:
        if not self._ensure_connected():
            return None
        try:
            # 获取账户列表
            ret, acc_list = self._trade_ctx.acc_list()
            if ret != RET_OK:
                logger.error(f"获取账户列表失败: {acc_list}")
                return self._account_cache

            # 取第一个账户
            trd_acc = acc_list.iloc[0] if len(acc_list) > 0 else None
            if trd_acc is None:
                logger.error("无可用交易账户")
                return self._account_cache

            acc_id = trd_acc['acc_id']

            # 获取账户资金
            ret, acc_funds = self._trade_ctx.acc_funds_query(
                trd_env=self._trd_env,
                acc_id=acc_id
            )
            if ret != RET_OK:
                logger.error(f"获取账户资金失败: {acc_funds}")
                return self._account_cache

            fund = acc_funds.iloc[0] if len(acc_funds) > 0 else None
            if fund is None:
                return self._account_cache

            cash = float(fund.get('cash', 0) or 0)
            total_assets = float(fund.get('total_assets', 0) or 0)
            max_power = float(fund.get('max_power_short', 0) or 0)
            market_val = float(fund.get('market_val', 0) or 0)

            acct = AccountData(
                cash=cash,
                portfolio_value=total_assets,
                buying_power=cash,  # 富途的 buying_power 即现金余额（不加杠杆）
                day_trade_count=0,  # 富途不追踪 PDT
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
            ret, data = self._trade_ctx.position_list(
                trd_env=self._trd_env,
                filter_conditions=None
            )
            if ret != RET_OK:
                logger.error(f"获取持仓失败: {data}")
                return list(self._position_cache.values())

            result = []
            if data is not None and len(data) > 0:
                for _, row in data.iterrows():
                    qty = float(row.get('qty', 0) or 0)
                    if qty == 0:
                        continue

                    # 段永平框架：检查做空仓位
                    position_side = str(row.get('position_side', 'LONG')).upper()
                    if position_side == 'SHORT':
                        logger.warning(
                            f"段永平框架警告：发现做空仓位 "
                            f"{row.get('code', '')} qty={qty}，系统不应做空！"
                        )
                        continue

                    symbol = self._to_standard_symbol(str(row.get('code', '')))
                    avg_price = float(row.get('cost_price', 0) or 0)
                    market_value = float(row.get('market_val', 0) or 0)
                    unrealized_pl = float(row.get('unrealized_pl', 0) or 0)
                    unrealized_plpc = float(row.get('unrealized_pl_ratio', 0) or 0)

                    result.append(PositionData(
                        symbol=symbol,
                        qty=abs(qty),
                        avg_entry_price=avg_price,
                        side='long',
                        market_value=market_value,
                        unrealized_pl=unrealized_pl,
                        unrealized_plpc=unrealized_plpc
                    ))

            self._position_cache = {p.symbol: p for p in result}
            return result

        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return list(self._position_cache.values())

    def get_position(self, symbol: str) -> Optional[PositionData]:
        positions = self.get_positions()
        futu_code = self._to_futu_symbol(symbol)
        std_symbol = self._to_standard_symbol(futu_code)
        for p in positions:
            if p.symbol == std_symbol or p.symbol == symbol:
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
            futu_code = self._to_futu_symbol(symbol)
            kl_type = self.TIMEFRAME_MAP.get(timeframe, KLType.K_DAY)

            # Futu get_cur_kline 最多返回 1000 条
            num = min(limit, 1000)

            ret, data, _ = self._quote_ctx.request_history_kline(
                code=futu_code,
                ktype=kl_type,
                max_count=num,
                fields=[
                    KL_FIELD.TIME_HIGH,
                    KL_FIELD.OPEN,
                    KL_FIELD.HIGH,
                    KL_FIELD.LOW,
                    KL_FIELD.CLOSE,
                    KL_FIELD.VOLUME,
                    KL_FIELD.TURNOVER,
                ]
            )

            if ret != RET_OK:
                logger.error(f"获取K线失败 {symbol}: {data}")
                return []

            result = []
            if data is not None and len(data) > 0:
                for _, row in data.iterrows():
                    ts = row.get('time_key', None)
                    # 解析时间戳
                    if isinstance(ts, str):
                        try:
                            ts = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
                        except Exception:
                            ts = datetime.now()

                    result.append(BarData(
                        timestamp=ts,
                        open=float(row.get('open', 0) or 0),
                        high=float(row.get('high', 0) or 0),
                        low=float(row.get('low', 0) or 0),
                        close=float(row.get('close', 0) or 0),
                        volume=int(row.get('volume', 0) or 0),
                        vwap=0,
                        trade_count=0
                    ))

            return result[-limit:] if limit and len(result) > limit else result

        except Exception as e:
            logger.error(f"获取K线数据失败 {symbol}: {e}")
            return []

    def get_latest_quote(self, symbol: str) -> Optional[QuoteData]:
        if not self._ensure_connected():
            return None
        try:
            futu_code = self._to_futu_symbol(symbol)

            ret, data = self._quote_ctx.get_market_snapshot([futu_code])
            if ret != RET_OK:
                logger.error(f"获取报价失败 {symbol}: {data}")
                return None

            if data is None or len(data) == 0:
                return None

            row = data.iloc[0]
            bid_price = float(row.get('cur_price', 0) or 0)
            ask_price = bid_price  # snapshot 不直接区分 bid/ask
            last_price = float(row.get('last_close', 0) or 0)

            # 优先使用最新价
            if bid_price <= 0:
                bid_price = last_price
            if ask_price <= 0:
                ask_price = last_price

            return QuoteData(
                bid_price=bid_price,
                bid_size=int(row.get('volume', 0) or 0),
                ask_price=ask_price,
                ask_size=0,
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
            logger.error(
                f"段永平框架约束：禁止做空/卖出开仓！"
                f"symbol={symbol} side={side}"
            )
            return None

        try:
            futu_code = self._to_futu_symbol(symbol)

            # 映射订单类型
            if order_type == 'limit' and limit_price is not None:
                futu_order_type = OrderType.NORMAL  # 限价单
                order_price = limit_price
            elif order_type == 'market':
                futu_order_type = OrderType.MARKET  # 市价单
                # 富途市价单需要指定价格（用最新价的 110%）
                quote = self.get_latest_quote(symbol)
                order_price = limit_price or (
                    (quote.bid_price * 1.1) if quote and quote.bid_price > 0 else 0
                )
            else:
                futu_order_type = OrderType.NORMAL
                order_price = limit_price or stop_price or 0

            if order_price <= 0:
                logger.error(f"订单价格无效: {order_price}")
                return None

            # 提交订单
            ret, data = self._trade_ctx.place_order(
                price=order_price,
                qty=int(qty),
                code=futu_code,
                trd_side=TrdSide.BUY,
                order_type=futu_order_type,
                trd_env=self._trd_env,
                time_in_force='Day' if time_in_force.lower() == 'day' else 'GTC'
            )

            if ret != RET_OK:
                logger.error(f"下单失败 {symbol}: {data}")
                return None

            order_row = data.iloc[0] if len(data) > 0 else None
            if order_row is None:
                return None

            order_id = str(order_row.get('order_id', ''))
            status = str(order_row.get('order_status', ''))

            order_data = OrderData(
                order_id=order_id,
                symbol=symbol,
                side='buy',
                qty=int(qty),
                order_type=order_type,
                limit_price=limit_price,
                stop_price=stop_price,
                status=self.ORDER_STATUS_MAP.get(status, status),
                filled_qty=0,
                filled_avg_price=None,
                created_at=datetime.now(),
                raw_order=data
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
            ret, data = self._trade_ctx.order_list_query(
                trd_env=self._trd_env,
                status_filter_list=None,  # 所有状态
                code=''
            )
            if ret != RET_OK:
                logger.error(f"查询订单失败 {order_id}: {data}")
                return None

            if data is None or len(data) == 0:
                return None

            for _, row in data.iterrows():
                if str(row.get('order_id', '')) == str(order_id):
                    return self._row_to_order_data(row)

            return None

        except Exception as e:
            logger.error(f"查询订单失败 {order_id}: {e}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        if not self._ensure_connected():
            return False
        try:
            ret, data = self._trade_ctx.modify_order(
                modify_order_op='CANCEL',
                order_id=order_id,
                qty=0,
                price=0,
                trd_env=self._trd_env,
                for_all_orders=False
            )
            if ret != RET_OK:
                logger.error(f"取消订单失败 {order_id}: {data}")
                return False

            logger.info(f"订单已取消: {order_id}")
            return True

        except Exception as e:
            logger.error(f"取消订单失败 {order_id}: {e}")
            return False

    def get_open_orders(self, symbol: str = None) -> List[OrderData]:
        if not self._ensure_connected():
            return []
        try:
            # 查询活跃订单（Submitted / FilledPart / Waiting）
            from futu import OrderStatus
            active_statuses = [
                OrderStatus.SUBMITTED,
                OrderStatus.WAITING,
                OrderStatus.SUBMITTING,
                OrderStatus.FILLED_PART,
            ]

            code = self._to_futu_symbol(symbol) if symbol else ''

            ret, data = self._trade_ctx.order_list_query(
                trd_env=self._trd_env,
                status_filter_list=active_statuses,
                code=code
            )
            if ret != RET_OK:
                logger.error(f"获取活跃订单失败: {data}")
                return []

            result = []
            if data is not None and len(data) > 0:
                for _, row in data.iterrows():
                    result.append(self._row_to_order_data(row))

            return result

        except Exception as e:
            logger.error(f"获取活跃订单失败: {e}")
            return []

    # ====== 市场状态 ======

    def get_clock(self) -> Dict[str, Any]:
        """
        获取市场时钟
        富途通过 get_global_state 获取市场状态
        """
        try:
            if not self._ensure_connected():
                return {
                    'is_open': False,
                    'next_open': '',
                    'next_close': '',
                    'timestamp': datetime.now().isoformat()
                }

            # 尝试获取全局状态
            ret, data = self._quote_ctx.get_global_state()
            if ret != RET_OK:
                # 回退到时间判断
                return self._time_based_clock()

            # 判断美股市场状态
            us_market = data.get('us_market_state', 0) if isinstance(data, dict) else 0
            # 0=未开盘, 1=交易中, 2=已收盘

            now = datetime.now()
            return {
                'is_open': us_market == 1,
                'next_open': '',
                'next_close': '',
                'timestamp': now.isoformat(),
                'us_market_state': us_market
            }

        except Exception as e:
            logger.error(f"获取市场时钟失败: {e}")
            return self._time_based_clock()

    def _time_based_clock(self) -> Dict[str, Any]:
        """基于时间判断市场状态（回退方案）"""
        now = datetime.utcnow()
        # 美东时间 = UTC - 5 (EST) 或 UTC - 4 (EDT)
        est_hour = (now.hour - 5) % 24
        is_weekday = now.weekday() < 5
        is_trading_hours = 9 <= est_hour < 16

        return {
            'is_open': is_weekday and is_trading_hours,
            'next_open': '',
            'next_close': '',
            'timestamp': now.isoformat()
        }

    # ====== 内部转换方法 ======

    def _row_to_order_data(self, row) -> OrderData:
        """将 Futu 订单行数据转换为 OrderData"""
        code = str(row.get('code', ''))
        symbol = self._to_standard_symbol(code)
        trd_side = str(row.get('trd_side', '')).upper()
        status = str(row.get('order_status', ''))
        order_type_val = str(row.get('order_type', 'NORMAL'))

        return OrderData(
            order_id=str(row.get('order_id', '')),
            symbol=symbol,
            side='buy' if trd_side == 'BUY' else 'sell',
            qty=int(row.get('qty', 0) or 0),
            order_type=order_type_val.lower(),
            limit_price=float(row.get('price', 0) or 0) or None,
            stop_price=None,
            status=self.ORDER_STATUS_MAP.get(status, status),
            filled_qty=int(row.get('filled_qty', 0) or 0),
            filled_avg_price=(
                float(row.get('filled_avg_price', 0) or 0) or None
            ),
            created_at=(
                datetime.strptime(
                    str(row.get('create_time', '')), '%Y-%m-%d %H:%M:%S'
                ) if row.get('create_time') else None
            ),
            raw_order=row
        )

    # ====== 属性 ======

    def get_name(self) -> str:
        return "Futu (富途证券)"

    @property
    def paper_trading(self) -> bool:
        return self._paper
