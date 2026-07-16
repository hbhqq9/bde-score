"""
BDE Score™ - AI-Powered Multi-Market Stock Analysis MCP Server
Copyright (C) 2026 BDE Score™ (https://github.com/hbhqq9/bde-score)

Licensed under AGPL-3.0 with commercial option.
If you run a modified version on a network server, you must make
the complete source code available. See LICENSE for details.
Commercial licensing available: nnhbh@foxmail.com
"""

"""
BDE-Stock 配置文件
集中管理所有系统参数

券商架构:
  - 支持 IBKR (主用) 和 Alpaca (备用)
  - 通过 BrokerAdapter 统一接口切换
"""

import os
from dataclasses import dataclass, field
from datetime import timedelta
from typing import List
import logging

# ============================================================
# 日志配置
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# ============================================================
# 段永平价值投资框架 - 硬编码约束（不可修改）
# ============================================================
DUAN_RULES = {
    'no_short_selling': True,     # 绝对不做空
    'no_leverage': True,          # 绝对不加杠杆
    'long_only': True,            # 只做多，现金买入
    'cash_purchase_only': True,   # 必须全额现金支付
}

# ============================================================
# 券商选择配置
# ============================================================
# 可选值: 'ibkr', 'alpaca', 'futu'
ACTIVE_BROKER = os.environ.get('BDE_BROKER', 'ibkr').lower()

# ============================================================
# IBKR 配置 (主用)
# ============================================================
# 连接方式: 通过 IB Gateway 或 TWS 的 Socket 端口
# Paper Trading: host='127.0.0.1', port=7497
# Live Trading:  host='127.0.0.1', port=7496
IBKR_CONFIG = {
    'host': os.environ.get('IB_HOST', '127.0.0.1'),
    'port': int(os.environ.get('IB_PORT', '7497')),  # 7497=paper, 7496=live
    'client_id': int(os.environ.get('IB_CLIENT_ID', '1')),
    'readonly': False,
    'account': os.environ.get('IB_ACCOUNT', ''),
    'timeout': 20,
    'reconnect': True,
    'reconnect_interval': 30,  # 重连间隔（秒）
}

# ============================================================
# Alpaca 配置 (备用 - 暂不可用)
# Alpaca 账户信息（备用）:
#   邮箱: nnhbh@foxmail.com
#   密码: Nnhbhqqq@999
#   MFA:  4PMLBWWPYR5SPHSK35M7R2GIM3M5LSG45OHYMFEQAAYBKE5XTVBA
# ============================================================
ALPACA_CONFIG = {
    'api_key': os.environ.get('ALPACA_API_KEY', ''),
    'api_secret': os.environ.get('ALPACA_API_SECRET', ''),
    'paper': True,  # True=模拟盘, False=实盘
    'base_url': 'https://paper-api.alpaca.markets',  # 已停用
}

# ============================================================
# Futu (富途证券) 配置 (备选 - 对中国用户友好)
# ============================================================
# 连接方式: 通过 FutuOpenD 本地网关代理
#   1. 先安装 FutuOpenD: https://openapi.futunn.com/futu-api-doc/opend/opend-cmd.html
#   2. 启动 FutuOpenD，登录富途账号
#   3. 本系统通过 Socket 连接 FutuOpenD
# 默认端口: 11111
# 支持模拟交易(Paper Trading)
# 支持市场: 美股(US.xxx), 港股(HK.xxxx), A股(SH.xxxxxx/SZ.xxxxxx)
FUTU_CONFIG = {
    'host': os.environ.get('FUTU_HOST', '127.0.0.1'),
    'port': int(os.environ.get('FUTU_PORT', '11111')),
    'paper': True,                        # True=模拟盘, False=实盘
    'trd_market': os.environ.get('FUTU_TRD_MARKET', 'US'),  # 交易市场
    'security_firm': 'FUTUSECURITIES',    # 券商机构
}

# ============================================================
# 五因子模型权重（不可修改）
# ============================================================
FACTOR_WEIGHTS = {
    'momentum': 0.30,         # 动量因子 - 14日涨幅
    'mean_reversion': 0.20,   # 均值回归因子 - RSI超卖信号
    'volume': 0.20,           # 成交量因子 - 资金流入信号
    'volatility': 0.15,       # 波动率因子 - 低波动率优先
    'trend': 0.15,            # 趋势因子 - 均线趋势
}

# ============================================================
# 选股池（不可修改）
# ============================================================
STOCK_UNIVERSE = [
    # 消费/科技龙头
    'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'META', 'NVDA', 'TSLA',
    'PLNT', 'COST', 'ORCL', 'NKE', 'GM', 'LULU',
    # BDE核心持仓关注
    'BABA', 'TSM', 'BIDU',  # 中概股
    'BRK.B', 'BAC',          # 巴菲特/金融
    'BAC', 'JPM', 'AXP', 'V', 'KO', 'WMT', 'PG', 'DIS',
    # 中概ETF
    'MCHI', 'KWEB', 'CQQQ',
    # 指数ETF（用于趋势参考）
    'SPY', 'QQQ', 'IWM', 'DIA',
]

# ============================================================
# 交易参数
# ============================================================
TRADING_PARAMS = {
    'data_feed': 'ibkr',              # IBKR
    'default_timeframe': '1Day',
    'screener_lookback_days': 200,    # 历史数据回溯天数
    'rate_limit_sleep': 0.3,          # API调用间隔(秒)
    'market_open_hour': 9,            # 美股开盘时间(EST)
    'market_close_hour': 16,          # 美股收盘时间(EST)
}

# ============================================================
# 飞书推送配置（不可修改）
# ============================================================
FEISHU_CONFIG = {
    'base_token': 'EMGtbCVY0auttWsnorTcjqbZnSf',
    'enabled': True,
    'push_on_signal': True,
    'push_on_trade': True,
    'push_on_alert': True,
}

# ============================================================
# 风控参数（不可修改）
# ============================================================
RISK_PARAMS = {
    'max_sector_exposure': 0.40,      # 单行业最大40%
    'min_cash_ratio': 0.05,           # 最低保留5%现金
    'daily_loss_limit': -0.05,        # 单日亏损-5%停止交易
    'max_options_per_trade': 100,     # 单笔期权合约上限
    'position_scaling': 'equal',      # 仓位分配: equal | kelly | confidence
}

# ============================================================
# 策略核心参数
# ============================================================
STRATEGY_PARAMS = {
    'initial_capital': 20000,       # 初始资金 $20,000
    'max_positions': 5,             # 最大同时持仓5只
    'max_single_position_pct': 0.25,# 单只最大仓位25%
    'stop_loss_pct': -0.03,         # 硬性止损 -3%
    'max_drawdown_pct': -0.15,      # 最大回撤 -15% 触发全部清仓
    'min_confidence': 55,           # 最低置信度门槛
}


# ============================================================
# 兼容层 - 供 factor_engine / stock_screener / risk_manager 使用
# 这些 dataclass 保持与原 config 的接口兼容
# ============================================================

@dataclass
class FactorConfig:
    """因子引擎配置 - factor_engine.py 使用"""
    weights: dict = field(default_factory=lambda: {
        'momentum': 0.30,
        'mean_reversion': 0.20,
        'volume': 0.20,
        'volatility': 0.15,
        'trend': 0.15,
    })
    momentum_periods: list = field(default_factory=lambda: [5, 10, 20, 60])
    mean_reversion_window: int = 20
    mean_reversion_threshold: float = 0.05
    volume_lookback: int = 20
    volume_spike_threshold: float = 1.5
    atr_period: int = 14
    volatility_window: int = 20
    ema_short: int = 10
    ema_long: int = 50


@dataclass
class TradingConfig:
    """交易参数配置 - stock_screener.py 使用"""
    watchlist: list = field(default_factory=lambda: [
        'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'META', 'NVDA', 'TSLA',
        'PLNT', 'COST', 'ORCL', 'NKE', 'GM', 'LULU',
        'BABA', 'TSM', 'BIDU', 'BRK.B', 'BAC',
        'JPM', 'AXP', 'V', 'KO', 'WMT', 'PG', 'DIS',
        'MCHI', 'KWEB', 'CQQQ', 'SPY', 'QQQ', 'IWM', 'DIA',
    ])
    default_lookback_days: int = 200
    default_timeframe: str = '1Day'
    rate_limit_sleep: float = 0.3
    min_volume: int = 100000
    min_market_cap: float = 1e9
    min_price: float = 5.0
    max_price: float = 10000.0


@dataclass
class RiskLimits:
    """风控限制 - risk_manager.py / stock_screener.py 使用
    
    段永平铁律:
    1. 不做空 short_allowed = False
    2. 不加杠杆 leverage_max = 1.0
    """
    # 段永平铁律
    short_allowed: bool = False
    leverage_max: float = 1.0
    
    # 仓位限制
    max_position_pct: float = 0.25        # 单只最大25%
    max_total_position_pct: float = 0.95  # 总仓位最大95%
    min_cash_reserve_pct: float = 0.05    # 现金保留5%
    
    # 日限制
    max_daily_trades: int = 10
    max_daily_loss_pct: float = 0.05      # 日亏损5%止损
    max_single_loss_pct: float = 0.03     # 单笔亏损3%止损
    
    # 价格保护
    no_chase_limit: bool = True
    max_price_change_pct: float = 0.05    # 5%涨跌停不追
    min_price: float = 5.0
    max_price: float = 10000.0


# 全局配置实例（供 factor_engine / stock_screener / risk_manager 导入）
FACTOR_CONFIG = FactorConfig()
RISK_LIMITS = RiskLimits()

# 让 TRADING_PARAMS 同时支持 dict 和属性访问
class TradingParamsNS:
    """交易参数 - 同时支持 dict 风格和属性访问"""
    def __init__(self):
        self.watchlist = [
            'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'META', 'NVDA', 'TSLA',
            'PLNT', 'COST', 'ORCL', 'NKE', 'GM', 'LULU',
            'BABA', 'TSM', 'BIDU', 'BRK.B', 'BAC',
            'JPM', 'AXP', 'V', 'KO', 'WMT', 'PG', 'DIS',
            'MCHI', 'KWEB', 'CQQQ', 'SPY', 'QQQ', 'IWM', 'DIA',
        ]
        self.default_lookback_days = 200
        self.default_timeframe = '1Day'
        self.rate_limit_sleep = 0.3
        self.min_volume = 100000
        self.min_market_cap = 1e9
        self.min_price = 5.0
        self.max_price = 10000.0

# 覆盖 TRADING_PARAMS 为支持属性访问的对象
TRADING_PARAMS = TradingParamsNS()


# ============================================================
# 券商适配器工厂
# ============================================================
def get_broker_adapter():
    """
    根据配置获取券商适配器实例
    返回 BrokerAdapter 实例
    """
    if ACTIVE_BROKER == 'ibkr':
        from ibkr_adapter import IBKRAdapter
        return IBKRAdapter(
            host=IBKR_CONFIG['host'],
            port=IBKR_CONFIG['port'],
            client_id=IBKR_CONFIG['client_id'],
            readonly=IBKR_CONFIG['readonly'],
            account=IBKR_CONFIG['account'],
            timeout=IBKR_CONFIG['timeout']
        )
    elif ACTIVE_BROKER == 'alpaca':
        from alpaca_adapter import AlpacaAdapter
        return AlpacaAdapter(
            api_key=ALPACA_CONFIG['api_key'],
            api_secret=ALPACA_CONFIG['api_secret'],
            paper=ALPACA_CONFIG['paper']
        )
    elif ACTIVE_BROKER == 'futu':
        from futu_adapter import FutuAdapter
        return FutuAdapter(
            host=FUTU_CONFIG['host'],
            port=FUTU_CONFIG['port'],
            paper_trading=FUTU_CONFIG['paper'],
            trd_market=FUTU_CONFIG['trd_market'],
            security_firm=FUTU_CONFIG['security_firm']
        )
    else:
        raise ValueError(f"不支持的券商: {ACTIVE_BROKER}，可选: ibkr, alpaca, futu")
