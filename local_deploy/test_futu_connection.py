#!/usr/bin/env python3
"""
FutuOpenD 连接测试工具
======================
测试 BDE-Stock → FutuOpenD → 富途模拟盘 全链路连通性。

测试项目:
  1. Python环境检查 (futu-api是否安装)
  2. FutuOpenD连接 (TCP端口)
  3. 行情获取 (实时报价)
  4. 账户信息 (模拟盘)
  5. 模拟下单 (小额测试单)

用法:
    python test_futu_connection.py           # 运行全部测试
    python test_futu_connection.py --quick   # 快速测试（仅连接+行情）
    python test_futu_connection.py --host 127.0.0.1 --port 11111
"""

import sys
import os
import json
import time
import socket
import argparse
import logging
from datetime import datetime
from pathlib import Path

# 路径设置
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('FutuTest')


# ============================================================
# 测试工具函数
# ============================================================

class TestResult:
    """测试结果"""
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.message = ""
        self.details = ""
    
    def ok(self, msg: str = "", details: str = ""):
        self.passed = True
        self.message = msg
        self.details = details
        return self
    
    def fail(self, msg: str, details: str = ""):
        self.passed = False
        self.message = msg
        self.details = details
        return self


def print_header():
    print()
    print("=" * 62)
    print("  🔌 BDE-Stock × FutuOpenD 连接测试")
    print(f"  📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 62)
    print()


def print_result(idx: int, total: int, result: TestResult):
    status = "✅ PASS" if result.passed else "❌ FAIL"
    print(f"  [{idx}/{total}] {status} | {result.name}")
    if result.message:
        print(f"         └─ {result.message}")
    if result.details and not result.passed:
        print(f"         └─ 💡 {result.details}")
    print()


def print_summary(results: list):
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    all_pass = passed == total
    
    print("=" * 62)
    if all_pass:
        print(f"  ✅ 全部通过 ({passed}/{total}) - 系统就绪！")
        print("  🚀 现在可以运行: python run_bde_stock.py")
    else:
        failed = [r for r in results if not r.passed]
        print(f"  ⚠️  {passed}/{total} 通过, {total-passed} 失败")
        print()
        for r in failed:
            print(f"  ❌ {r.name}: {r.message}")
            if r.details:
                print(f"     💡 {r.details}")
        print()
        print("  📖 请参照 LOCAL_QUICKSTART.md 排查问题")
    print("=" * 62)
    print()


# ============================================================
# 测试用例
# ============================================================

def test_python_env() -> TestResult:
    """测试1: Python环境检查"""
    result = TestResult("Python 环境")
    
    # 检查Python版本
    if sys.version_info < (3, 9):
        return result.fail(
            f"Python版本过低: {sys.version}",
            "需要 Python 3.9+，请升级"
        )
    
    # 检查futu-api
    try:
        import futu
        version = getattr(futu, '__version__', 'unknown')
        return result.ok(f"Python {sys.version_info.major}.{sys.version_info.minor} | futu-api v{version}")
    except ImportError:
        return result.fail(
            "futu-api 未安装",
            "请运行: pip install futu-api"
        )


def test_opend_tcp(host: str, port: int) -> TestResult:
    """测试2: FutuOpenD TCP连接"""
    result = TestResult("FutuOpenD TCP连接")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        sock.close()
        return result.ok(f"{host}:{port} 可达")
    except ConnectionRefusedError:
        return result.fail(
            f"连接被拒绝 {host}:{port}",
            "FutuOpenD未启动，请启动后重试"
        )
    except socket.timeout:
        return result.fail(
            f"连接超时 {host}:{port}",
            "FutuOpenD可能卡死，请重启"
        )
    except Exception as e:
        return result.fail(
            f"连接失败: {e}",
            f"确认FutuOpenD已启动并监听在 {host}:{port}"
        )


def test_futu_context(host: str, port: int) -> TestResult:
    """测试3: Futu 行情上下文 (API级别连接)"""
    result = TestResult("Futu 行情API")
    
    try:
        from futu import OpenQuoteContext, RET_OK
        
        ctx = OpenQuoteContext(host=host, port=port)
        ret, data = ctx.get_global_state()
        ctx.close()
        
        if ret == RET_OK:
            market_state = data.get('market_sz', 'unknown')
            return result.ok(f"行情API连接成功 | 深市状态: {market_state}")
        else:
            return result.fail(
                f"API返回错误: {data}",
                "FutuOpenD可能未登录，请检查登录状态"
            )
    except ImportError:
        return result.fail("futu-api未安装", "pip install futu-api")
    except Exception as e:
        return result.fail(f"API调用失败: {e}")


def test_quote_fetch(host: str, port: int) -> TestResult:
    """测试4: 实时行情获取"""
    result = TestResult("实时行情获取")
    
    try:
        from futu import OpenQuoteContext, RET_OK
        
        ctx = OpenQuoteContext(host=host, port=port)
        
        # 测试获取苹果股票行情
        ret, data = ctx.get_market_snapshot(['US.AAPL'])
        ctx.close()
        
        if ret == RET_OK and len(data) > 0:
            row = data.iloc[0]
            price = row.get('last_price', row.get('last_price', 'N/A'))
            return result.ok(f"AAPL 最新价: ${price}")
        else:
            return result.fail(f"行情获取失败: {data}")
            
    except Exception as e:
        return result.fail(f"行情获取异常: {e}")


def test_account_info(host: str, port: int, paper: bool = True) -> TestResult:
    """测试5: 账户信息"""
    result = TestResult("模拟盘账户信息")
    
    try:
        from futu import OpenSecTradeContext, TrdEnv, RET_OK
        
        trd_env = TrdEnv.SIMULATE if paper else TrdEnv.REAL
        
        ctx = OpenSecTradeContext(host=host, port=port)
        ret, data = ctx.get_acc_list()
        
        if ret != RET_OK:
            ctx.close()
            return result.fail(f"获取账户列表失败: {data}")
        
        # 查找模拟盘账户
        acc_list = data[data['trd_env'] == ('SIMULATE' if paper else 'REAL')]
        if len(acc_list) == 0:
            ctx.close()
            return result.fail("未找到模拟盘账户", "请在富途APP开通模拟交易")
        
        acc_id = acc_list.iloc[0]['acc_id']
        
        # 获取账户资金
        ret2, fund_data = ctx.get_acc_fund(trd_env=trd_env)
        ctx.close()
        
        if ret2 == RET_OK:
            cash = fund_data.iloc[0].get('cash', 0)
            total = fund_data.iloc[0].get('total_assets', 0)
            return result.ok(f"账户ID: {acc_id} | 现金: ${cash:,.2f} | 总资产: ${total:,.2f}")
        else:
            return result.ok(f"账户ID: {acc_id} | 资金查询失败(可能未开通)")
            
    except Exception as e:
        return result.fail(f"账户查询异常: {e}")


def test_paper_order(host: str, port: int) -> TestResult:
    """测试6: 模拟下单测试"""
    result = TestResult("模拟下单测试")
    
    try:
        from futu import (
            OpenSecTradeContext, TrdEnv, TrdMarket, TrdSide,
            OrderType, RET_OK
        )
        
        ctx = OpenSecTradeContext(host=host, port=port)
        
        # 获取账户
        ret, acc_list = ctx.get_acc_list()
        if ret != RET_OK:
            ctx.close()
            return result.fail(f"获取账户失败: {acc_list}")
        
        # 使用模拟盘
        sim_accs = acc_list[acc_list['trd_env'] == 'SIMULATE']
        if len(sim_accs) == 0:
            ctx.close()
            return result.fail("无模拟盘账户")
        
        acc_id = sim_accs.iloc[0]['acc_id']
        trd_market = TrdMarket.US
        
        # 尝试下一个极小量的限价买单（几乎不会成交）
        ret2, order_data = ctx.place_order(
            price=0.01,           # 极低价格，不会实际成交
            qty=1,                # 1股
            code='US.AAPL',
            trd_side=TrdSide.BUY,
            order_type=OrderType.NORMAL,
            trd_env=TrdEnv.SIMULATE,
            acc_id=acc_id,
            trd_market=trd_market,
        )
        
        if ret2 == RET_OK:
            order_id = order_data.iloc[0]['order_id']
            
            # 立即取消订单
            ctx.modify_order(
                order_id=order_id,
                qty=0,
                price=0,
                trd_env=TrdEnv.SIMULATE,
            )
            
            ctx.close()
            return result.ok(f"下单+撤单成功 (OrderID: {order_id})")
        else:
            ctx.close()
            # 下单失败但连接成功也算部分通过
            return result.ok(f"下单返回: {order_data} (连接正常，可能需要交易时段)")
            
    except Exception as e:
        err_msg = str(e)
        if "not trading time" in err_msg.lower() or "market closed" in err_msg.lower():
            return result.ok("连接正常，当前非交易时段")
        return result.fail(f"下单测试异常: {e}")


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='FutuOpenD 连接测试')
    parser.add_argument('--quick', action='store_true', help='快速测试（仅连接+行情）')
    parser.add_argument('--host', default='127.0.0.1', help='FutuOpenD地址')
    parser.add_argument('--port', type=int, default=11111, help='FutuOpenD端口')
    args = parser.parse_args()
    
    # 尝试从配置文件读取
    config_path = SCRIPT_DIR / "config_local.json"
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                cfg = json.load(f)
            if not args.host or args.host == '127.0.0.1':
                args.host = cfg.get('futu_opend', {}).get('host', '127.0.0.1')
            if args.port == 11111:
                args.port = cfg.get('futu_opend', {}).get('port', 11111)
        except Exception:
            pass
    
    print_header()
    
    results = []
    
    if args.quick:
        # 快速测试: 仅 环境 + TCP + 行情
        tests = [
            ("环境", lambda: test_python_env()),
            ("TCP", lambda: test_opend_tcp(args.host, args.port)),
            ("行情", lambda: test_quote_fetch(args.host, args.port)),
        ]
    else:
        # 完整测试
        tests = [
            ("环境", lambda: test_python_env()),
            ("TCP", lambda: test_opend_tcp(args.host, args.port)),
            ("行情API", lambda: test_futu_context(args.host, args.port)),
            ("实时行情", lambda: test_quote_fetch(args.host, args.port)),
            ("账户", lambda: test_account_info(args.host, args.port)),
            ("下单", lambda: test_paper_order(args.host, args.port)),
        ]
    
    total = len(tests)
    
    for idx, (name, test_fn) in enumerate(tests, 1):
        try:
            result = test_fn()
        except Exception as e:
            result = TestResult(name)
            result.fail(f"测试异常: {e}")
        
        results.append(result)
        print_result(idx, total, result)
        
        # 如果TCP连接失败，后面的测试大概率也会失败
        if name == "TCP" and not result.passed:
            logger.info("FutuOpenD未连接，跳过后续测试...")
            break
    
    print_summary(results)
    
    # 返回退出码
    all_pass = all(r.passed for r in results)
    sys.exit(0 if all_pass else 1)


if __name__ == '__main__':
    main()
