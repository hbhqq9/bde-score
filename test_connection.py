"""
BDE-Stock 连接测试工具
支持 IBKR (主用) 和 Alpaca (备用) 连接测试

用法:
  python test_connection.py              # 测试当前配置的券商连接
  python test_connection.py --ibkr       # 测试 IBKR 连接
  python test_connection.py --alpaca     # 测试 Alpaca 连接
  python test_connection.py --offline    # 离线测试（不连接券商，仅验证代码）
"""

import sys
import os
import argparse
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def print_banner():
    print("=" * 60)
    print("  BDE-Stock 连接测试工具")
    print("  Interactive Brokers 架构 v1.0")
    print("=" * 60)
    print()


def test_offline():
    """
    离线测试 - 不连接任何券商
    仅验证:
    1. 所有模块可正常导入
    2. 类定义正确
    3. 配置加载正常
    4. 段永平框架约束存在
    """
    print("[离线测试] 开始验证模块完整性...")
    print()

    errors = []
    warnings = []
    passed = 0

    # 测试1: 导入 broker_adapter
    print("  [1/8] 导入 broker_adapter...", end=" ")
    try:
        from broker_adapter import (
            BrokerAdapter, BarData, QuoteData, PositionData, OrderData, AccountData
        )
        # 验证抽象方法
        abstract_methods = [
            'connect', 'disconnect', 'is_connected',
            'get_account', 'get_buying_power', 'get_portfolio_value',
            'get_positions', 'get_position',
            'get_latest_bar', 'get_bars', 'get_latest_quote',
            'submit_order', 'get_order', 'cancel_order', 'get_open_orders',
            'get_clock', 'get_name'
        ]
        for method in abstract_methods:
            assert hasattr(BrokerAdapter, method), f"缺少方法: {method}"
        print("PASS")
        passed += 1
    except Exception as e:
        print(f"FAIL - {e}")
        errors.append(f"broker_adapter: {e}")

    # 测试2: 导入 ibkr_adapter
    print("  [2/8] 导入 ibkr_adapter...", end=" ")
    try:
        from ibkr_adapter import IBKRAdapter, IB_INSYNC_AVAILABLE
        if not IB_INSYNC_AVAILABLE:
            warnings.append("ib_insync 未安装，IBKR 适配器不可用")
            print("WARN (ib_insync 未安装)")
        else:
            print("PASS")
        passed += 1
    except Exception as e:
        print(f"FAIL - {e}")
        errors.append(f"ibkr_adapter: {e}")

    # 测试3: 导入 alpaca_adapter
    print("  [3/8] 导入 alpaca_adapter...", end=" ")
    try:
        from alpaca_adapter import AlpacaAdapter, ALPACA_AVAILABLE
        if not ALPACA_AVAILABLE:
            warnings.append("alpaca-py 未安装，Alpaca 适配器不可用（预期行为）")
            print("WARN (alpaca-py 未安装)")
        else:
            print("PASS")
        passed += 1
    except Exception as e:
        print(f"FAIL - {e}")
        errors.append(f"alpaca_adapter: {e}")

    # 测试4: 导入 config
    print("  [4/8] 导入 config...", end=" ")
    try:
        from config import (
            ACTIVE_BROKER, IBKR_CONFIG, ALPACA_CONFIG,
            DUAN_RULES, FACTOR_WEIGHTS, STOCK_UNIVERSE,
            STRATEGY_PARAMS, FEISHU_CONFIG, RISK_PARAMS,
            get_broker_adapter
        )
        # 验证段永平规则
        assert DUAN_RULES['no_short_selling'] is True, "做空约束缺失"
        assert DUAN_RULES['no_leverage'] is True, "杠杆约束缺失"
        assert DUAN_RULES['long_only'] is True, "做多约束缺失"
        # 验证飞书配置
        assert FEISHU_CONFIG['base_token'] == 'EMGtbCVY0auttWsnorTcjqbZnSf', "飞书配置错误"
        # 验证券商选择
        assert ACTIVE_BROKER in ('ibkr', 'alpaca'), f"无效券商: {ACTIVE_BROKER}"
        print("PASS")
        passed += 1
    except Exception as e:
        print(f"FAIL - {e}")
        errors.append(f"config: {e}")

    # 测试5: 导入 factor_engine
    print("  [5/8] 导入 factor_engine...", end=" ")
    try:
        from factor_engine import FactorEngine
        print("PASS")
        passed += 1
    except Exception as e:
        print(f"FAIL - {e}")
        errors.append(f"factor_engine: {e}")

    # 测试6: 导入 paper_trader
    print("  [6/8] 导入 paper_trader...", end=" ")
    try:
        from paper_trader import PaperTrader
        print("PASS")
        passed += 1
    except Exception as e:
        print(f"FAIL - {e}")
        errors.append(f"paper_trader: {e}")

    # 测试7: 导入 stock_screener
    print("  [7/8] 导入 stock_screener...", end=" ")
    try:
        from stock_screener import StockScreener
        print("PASS")
        passed += 1
    except Exception as e:
        print(f"FAIL - {e}")
        errors.append(f"stock_screener: {e}")

    # 测试8: 导入 risk_manager
    print("  [8/8] 导入 risk_manager...", end=" ")
    try:
        from risk_manager import RiskManager
        print("PASS")
        passed += 1
    except Exception as e:
        print(f"FAIL - {e}")
        errors.append(f"risk_manager: {e}")

    # 测试9: IBKRAdapter 实例化（不连接）
    print()
    print("  [额外] IBKRAdapter 实例化测试...", end=" ")
    try:
        from ibkr_adapter import IBKRAdapter, IB_INSYNC_AVAILABLE
        if IB_INSYNC_AVAILABLE:
            adapter = IBKRAdapter(host='127.0.0.1', port=7497, client_id=99)
            assert adapter.get_name() == "Interactive Brokers (IBKR)"
            assert adapter.paper_trading is True
            assert adapter.is_connected() is False
            print("PASS")
            passed += 1
        else:
            print("SKIP (ib_insync 未安装)")
    except Exception as e:
        print(f"FAIL - {e}")
        errors.append(f"IBKRAdapter实例化: {e}")

    # 测试结果汇总
    print()
    print("=" * 60)
    print(f"  离线测试结果: {passed}/8 模块通过")
    if errors:
        print(f"  错误: {len(errors)}")
        for err in errors:
            print(f"    - {err}")
    if warnings:
        print(f"  警告: {len(warnings)}")
        for w in warnings:
            print(f"    - {w}")
    if not errors:
        print("  状态: ALL MODULES LOADED SUCCESSFULLY")
    print("=" * 60)

    return len(errors) == 0


def test_ibkr_connection():
    """测试 IBKR 连接"""
    from config import IBKR_CONFIG, get_broker_adapter

    print("[IBKR] 测试 Interactive Brokers 连接...")
    print(f"  主机: {IBKR_CONFIG['host']}")
    print(f"  端口: {IBKR_CONFIG['port']} ({'Paper' if IBKR_CONFIG['port'] == 7497 else 'Live'})")
    print(f"  Client ID: {IBKR_CONFIG['client_id']}")
    print()

    try:
        broker = get_broker_adapter()
    except Exception as e:
        print(f"  创建适配器失败: {e}")
        return False

    # 连接测试
    print("  正在连接...", end=" ")
    connected = broker.connect()
    if connected:
        print("OK")
    else:
        print("FAILED")
        print("  请确保 IB Gateway 正在运行:")
        print("    bash deploy_ib_gateway.sh    # 安装并启动")
        return False

    # 获取账户信息
    print("  获取账户信息...", end=" ")
    account = broker.get_account()
    if account:
        print("OK")
        print(f"    净资产: ${account.portfolio_value:,.2f}")
        print(f"    现金:   ${account.cash:,.2f}")
        print(f"    购买力: ${account.buying_power:,.2f}")
    else:
        print("FAILED")

    # 获取持仓
    print("  获取持仓...", end=" ")
    positions = broker.get_positions()
    print(f"{len(positions)} 只持仓")
    for pos in positions:
        print(f"    {pos.symbol}: {pos.qty}股 @ ${pos.avg_entry_price:.2f}")

    # 获取市场数据
    print("  获取市场数据 (AAPL)...", end=" ")
    bar = broker.get_latest_bar('AAPL')
    if bar:
        print(f"OK - 收盘 ${bar.close:.2f}")
    else:
        print("FAILED (可能需要订阅市场数据)")

    # 获取市场时钟
    print("  获取市场时钟...", end=" ")
    clock = broker.get_clock()
    status = "OPEN" if clock.get('is_open') else "CLOSED"
    print(f"{status}")

    broker.disconnect()
    print()
    print("  IBKR 连接测试完成")
    return True


def test_alpaca_connection():
    """测试 Alpaca 连接（预期失败 - 账户已停用）"""
    from config import ALPACA_CONFIG

    print("[Alpaca] 测试 Alpaca 连接（备用）...")
    print("  注意: Alpaca 账户已停用")
    print()

    if not ALPACA_CONFIG['api_key']:
        print("  未配置 API Key，跳过测试")
        return False

    try:
        from alpaca_adapter import AlpacaAdapter
        broker = AlpacaAdapter(
            api_key=ALPACA_CONFIG['api_key'],
            api_secret=ALPACA_CONFIG['api_secret'],
            paper=ALPACA_CONFIG['paper']
        )
        connected = broker.connect()
        if connected:
            print("  Alpaca 连接成功")
            broker.disconnect()
        else:
            print("  Alpaca 连接失败（预期 - 账户已停用）")
    except Exception as e:
        print(f"  Alpaca 测试异常: {e}")

    return False


def main():
    parser = argparse.ArgumentParser(description='BDE-Stock 连接测试工具')
    parser.add_argument('--ibkr', action='store_true', help='测试 IBKR 连接')
    parser.add_argument('--alpaca', action='store_true', help='测试 Alpaca 连接')
    parser.add_argument('--offline', action='store_true', help='离线测试（不连接券商）')
    args = parser.parse_args()

    print_banner()

    if args.offline:
        success = test_offline()
        sys.exit(0 if success else 1)
    elif args.ibkr:
        test_ibkr_connection()
    elif args.alpaca:
        test_alpaca_connection()
    else:
        # 默认：先离线测试，再尝试连接当前配置的券商
        print("[默认] 先执行离线测试...")
        print()
        success = test_offline()
        if success:
            from config import ACTIVE_BROKER
            print()
            print(f"当前券商配置: {ACTIVE_BROKER}")
            if ACTIVE_BROKER == 'ibkr':
                test_ibkr_connection()
            elif ACTIVE_BROKER == 'alpaca':
                test_alpaca_connection()


if __name__ == '__main__':
    main()
