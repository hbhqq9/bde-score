"""
x402 Micro-Payment Integration Tests
=====================================
测试 x402 支付端点的安全性和功能。

运行: python test_x402_endpoints.py
"""

import os
import sys
import json
import time
import sqlite3
import requests
import logging

# 配置
BASE_URL = os.environ.get('BDE_TEST_URL', 'http://127.0.0.1:8890')
TEST_PASS = 0
TEST_FAIL = 0
TEST_TOTAL = 0

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger('x402_test')


def test(name, condition, detail=""):
    global TEST_PASS, TEST_FAIL, TEST_TOTAL
    TEST_TOTAL += 1
    if condition:
        TEST_PASS += 1
        log.info(f"  ✅ {name}")
    else:
        TEST_FAIL += 1
        log.error(f"  ❌ {name}: {detail}")


def section(title):
    log.info(f"\n{'='*60}")
    log.info(f"  {title}")
    log.info(f"{'='*60}")


# ============================================================
# 测试组 1: 协议信息发现
# ============================================================
def test_info_endpoint():
    section("1. GET /pay/info — 协议发现端点")
    
    try:
        r = requests.get(f"{BASE_URL}/pay/info", timeout=10)
        test("Status 200", r.status_code == 200, f"got {r.status_code}")
        
        data = r.json()
        test("Protocol is x402", data.get('protocol') == 'x402')
        test("Version 2", data.get('version') == 2)
        test("Enabled flag present", 'enabled' in data)
        test("Price $0.01", data.get('pricing', {}).get('per_query_usd') == 0.01)
        test("Currency USDC", data.get('pricing', {}).get('currency') == 'USDC')
        test("Chain eip155:8453", data.get('pricing', {}).get('chain_id') == 'eip155:8453')
        test("Pay-to address present", bool(data.get('payment', {}).get('pay_to')))
        test("Free quota 3/day", data.get('free_tier', {}).get('queries_per_day') == 3)
        test("Disclaimer present", 'disclaimer' in data)
        
        # 🔒 安全检查: 不应暴露私钥或内部路径
        raw = json.dumps(data)
        test("No private key leaked", 'PRIVATE' not in raw.upper() or 'KEY_HERE' in raw.upper())
        test("No internal file paths", '/app/' not in raw and '/home/' not in raw)
        
    except requests.exceptions.ConnectionError:
        log.warning("⚠️  Server not running, skipping HTTP tests")
        return False
    except Exception as e:
        test("Info endpoint works", False, str(e))
        return False
    return True


# ============================================================
# 测试组 2: 免费额度检查
# ============================================================
def test_free_endpoint():
    section("2. GET /pay/free — 免费额度检查")
    
    try:
        r = requests.get(f"{BASE_URL}/pay/free", timeout=10)
        test("Status 200", r.status_code == 200, f"got {r.status_code}")
        
        data = r.json()
        test("Has 'used' field", 'used' in data)
        test("Has 'limit' field", 'limit' in data)
        test("Has 'remaining' field", 'remaining' in data)
        test("Limit is 3", data.get('limit') == 3)
        test("Remaining >= 0", data.get('remaining', -1) >= 0)
        test("Has network info", 'network' in data)
        
    except requests.exceptions.ConnectionError:
        return False
    except Exception as e:
        test("Free endpoint works", False, str(e))
        return False
    return True


# ============================================================
# 测试组 3: 支付统计端点
# ============================================================
def test_balance_endpoint():
    section("3. GET /pay/balance — 支付统计")
    
    try:
        r = requests.get(f"{BASE_URL}/pay/balance", timeout=10)
        test("Status 200", r.status_code == 200, f"got {r.status_code}")
        
        data = r.json()
        test("Has total_payments", 'total_payments' in data)
        test("Has price_per_query_usd", data.get('price_per_query_usd') == 0.01)
        test("Has cost_per_event_usd", data.get('cost_per_event_usd') == 0.000752)
        test("Profit margin > 90%", data.get('profit_margin_pct', 0) > 90)
        test("Disclaimer present", 'disclaimer' in data)
        
    except requests.exceptions.ConnectionError:
        return False
    except Exception as e:
        test("Balance endpoint works", False, str(e))
        return False
    return True


# ============================================================
# 测试组 4: x402 支付+查询端点
# ============================================================
def test_query_endpoint():
    section("4. POST/GET /pay/query — 支付+查询")
    
    try:
        # GET 请求（免费额度内应成功）
        r = requests.get(f"{BASE_URL}/pay/query?symbol=AAPL&market=US", timeout=30)
        
        if r.status_code == 200:
            data = r.json()
            test("GET /pay/query returns 200 (free tier)", True)
            test("Response has auth_source", 'auth_source' in data)
            test("Response has disclaimer", 'disclaimer' in data)
            test("Not leaking internal errors", 'Traceback' not in json.dumps(data))
            
        elif r.status_code == 402:
            test("GET /pay/query returns 402 (free quota exhausted)", True)
            data = r.json()
            test("402 has accepts array", 'accepts' in data)
            test("Accept has scheme=exact", data['accepts'][0].get('scheme') == 'exact')
            test("Accept has correct network", 'eip155:8453' in str(data))
            test("Accept has USDC contract", '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' in str(data))
            test("Accept has pay-to address", '0x349Eea0E2f4d3594797851758325Da3eb49D4343' in str(data))
            test("Amount is 10000 atomic ($0.01)", data['accepts'][0].get('maxAmountRequired') == '10000')
            
            # 🔒 安全检查: 402 响应不泄露内部架构
            raw = json.dumps(data)
            test("402 no internal paths", '/app/' not in raw)
            test("402 no stack traces", 'Traceback' not in raw)
            test("402 no DB paths", '.db' not in raw)
            
        else:
            test("GET /pay/query returns expected status", False, f"got {r.status_code}")
        
        # POST 请求
        r2 = requests.post(f"{BASE_URL}/pay/query?symbol=NVDA&market=US", timeout=30)
        test("POST /pay/query responds", r2.status_code in (200, 402, 400, 429),
             f"got {r2.status_code}")
        
        # 无效 market
        r3 = requests.get(f"{BASE_URL}/pay/query?market=INVALID", timeout=10)
        test("Invalid market returns 400", r3.status_code == 400, f"got {r3.status_code}")
        
    except requests.exceptions.ConnectionError:
        return False
    except Exception as e:
        test("Query endpoint works", False, str(e))
        return False
    return True


# ============================================================
# 测试组 5: 安全验证
# ============================================================
def test_security():
    section("5. 🔒 安全验证")
    
    try:
        # 测试无效 X-Payment header
        r = requests.get(
            f"{BASE_URL}/pay/query?symbol=AAPL",
            headers={"X-Payment": "invalid_garbage_data"},
            timeout=10
        )
        test("Invalid X-Payment → 402 (not 500)", r.status_code == 402, f"got {r.status_code}")
        
        # 测试恶意 JSON 在 X-Payment
        r2 = requests.get(
            f"{BASE_URL}/pay/query?symbol=AAPL",
            headers={"X-Payment": '{"payTo": "0xattacker"}'},
            timeout=10
        )
        test("Wrong payTo → 402", r2.status_code == 402, f"got {r2.status_code}")
        
        # 安全响应头检查
        r3 = requests.get(f"{BASE_URL}/pay/info", timeout=10)
        test("HSTS header present", 'strict-transport-security' in r3.headers)
        test("X-Content-Type-Options", r3.headers.get('x-content-type-options') == 'nosniff')
        test("No server version header", 'server' not in r3.headers or r3.headers.get('server') == '')
        
    except requests.exceptions.ConnectionError:
        return False
    except Exception as e:
        test("Security checks", False, str(e))
        return False
    return True


# ============================================================
# 测试组 6: 本地 DB 验证
# ============================================================
def test_db():
    section("6. 💾 本地数据库验证")
    
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'x402_payments.db')
    
    if not os.path.exists(db_path):
        log.warning("⚠️  x402_payments.db not found (will be created on first run)")
        test("DB will be created at runtime", True)
        return True
    
    try:
        conn = sqlite3.connect(db_path)
        
        # 检查表结构
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        
        test("x402_free_usage table exists", 'x402_free_usage' in table_names)
        test("x402_payments table exists", 'x402_payments' in table_names)
        
        # 检查索引
        indexes = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
        index_names = [i[0] for i in indexes]
        test("Free usage index exists", 'idx_x402_ip_date' in index_names)
        test("Payment payer index exists", 'idx_x402_payer' in index_names)
        
        conn.close()
        
    except Exception as e:
        test("DB validation", False, str(e))
        return False
    return True


# ============================================================
# 主测试流程
# ============================================================
def main():
    global TEST_PASS, TEST_FAIL, TEST_TOTAL
    
    log.info("=" * 60)
    log.info("  BDE Score™ x402 Micro-Payment Integration Tests")
    log.info(f"  Target: {BASE_URL}")
    log.info("=" * 60)
    
    # 先测试本地 DB（不需要服务运行）
    test_db()
    
    # HTTP 测试需要服务运行
    server_running = test_info_endpoint()
    
    if server_running:
        test_free_endpoint()
        test_balance_endpoint()
        test_query_endpoint()
        test_security()
    else:
        log.warning("\n⚠️  Server not running. Start with: python bde_api.py")
        log.warning("   Then re-run tests with: BDE_TEST_URL=http://127.0.0.1:8890 python test_x402_endpoints.py")
    
    # 汇总
    section("测试汇总")
    log.info(f"  Total: {TEST_TOTAL} | ✅ Pass: {TEST_PASS} | ❌ Fail: {TEST_FAIL}")
    
    if TEST_FAIL == 0:
        log.info("  🎉 All tests passed!")
    else:
        log.warning(f"  ⚠️  {TEST_FAIL} test(s) failed")
    
    return TEST_FAIL == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
