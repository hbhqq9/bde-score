"""
BDE-Stock 统一每日执行脚本
数据源优先级: FutuOpenD (本地) > 新浪JSONP API (远程)
自动检测可用数据源，执行完整BDE五因子评估，输出信号
"""

import sys
import json
import os
import subprocess
from datetime import datetime

sys.path.insert(0, '/app/data/所有对话/主对话/BDE-Stock')
sys.path.insert(0, '/app/data/所有对话/主对话/BDE-Stock')

KLINE_DAYS = 120
RESULT_DIR = '/app/data/所有对话/主对话/BDE-Stock'


def check_futu_available():
    """检查FutuOpenD是否可用"""
    try:
        result = subprocess.run(['pgrep', '-f', 'FutuOpenD'], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return False
        # 尝试连接
        from futu import OpenQuoteContext, RET_OK
        ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
        ret, data = ctx.get_market_snapshot(['US.AAPL'])
        ctx.close()
        return ret == RET_OK
    except:
        return False


def fetch_via_futu(days):
    """通过FutuOpenD获取数据"""
    from futu import OpenQuoteContext, RET_OK
    
    UNIVERSE = {
        'US.AAPL': 'apple', 'US.MSFT': 'microsoft', 'US.GOOG': 'alphabet',
        'US.AMZN': 'amazon', 'US.META': 'meta', 'US.NVDA': 'nvidia',
        'US.V': 'visa', 'US.MA': 'mastercard', 'US.JNJ': 'jnj',
        'US.PG': 'pg', 'US.TSLA': 'tesla', 'US.BABA': 'baba',
        'US.SPY': 'spy', 'US.QQQ': 'qqq',
    }
    
    from datetime import timedelta
    ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days + 30)).strftime('%Y-%m-%d')
    
    all_data = {}
    try:
        for futu_code, name in UNIVERSE.items():
            ret, data, _ = ctx.request_history_kline(
                futu_code, ktype='K_DAY', start=start_date, end=end_date
            )
            if ret == RET_OK and len(data) > 0:
                df = data.tail(days).reset_index(drop=True)
                all_data[name] = df
    finally:
        ctx.close()
    
    return all_data, len(all_data) == len(UNIVERSE)


def fetch_via_sina(days):
    """通过新浪JSONP获取数据（备用）"""
    import requests
    import pandas as pd
    
    UNIVERSE = {
        'aapl': 'apple', 'msft': 'microsoft', 'goog': 'alphabet',
        'amzn': 'amazon', 'meta': 'meta', 'nvda': 'nvidia',
        'v': 'visa', 'ma': 'mastercard', 'jnj': 'jnj',
        'pg': 'pg', 'tsla': 'tesla', 'baba': 'baba',
        'spy': 'spy', 'qqq': 'qqq',
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
        'Referer': 'https://finance.sina.com.cn'
    }
    
    all_data = {}
    for sina_symbol, name in UNIVERSE.items():
        url = f'https://stock.finance.sina.com.cn/usstock/api/jsonp.php/var%20data=/US_MinKService.getDailyK?symbol={sina_symbol}&scale=240&datalen={days}'
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            # Parse JSONP response
            text = resp.text
            json_str = text[text.index('(') + 1 : text.rindex(')')]
            records = json.loads(json_str)
            
            if len(records) > 0:
                df = pd.DataFrame(records)
                df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
                # Convert types
                for col in ['open', 'high', 'low', 'close']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0).astype(int)
                df = df.tail(days).reset_index(drop=True)
                # Rename for FactorEngine
                df = df.rename(columns={'date': 'time_key'})
                all_data[name] = df
        except Exception as e:
            pass
    
    return all_data, len(all_data) == len(UNIVERSE)


def run_bde_engine(stock_data):
    """运行BDE五因子引擎"""
    from factor_engine import FactorEngine
    
    engine = FactorEngine()
    results = engine.evaluate(stock_data)
    return results


def main():
    print("=" * 60)
    print(f"BDE-Stock 每日信号 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"回溯: {KLINE_DAYS}日")
    print("=" * 60)
    
    # Step 1: 选择数据源
    print("\n[1/4] 检测数据源...")
    if check_futu_available():
        print("  🟢 FutuOpenD可用，使用官方数据")
        source = "FutuOpenD"
        stock_data, ok = fetch_via_futu(KLINE_DAYS)
    else:
        print("  🟡 FutuOpenD不可用，尝试启动...")
        # Try to start FutuOpenD
        manager_path = os.path.join(RESULT_DIR, 'futu_opend_manager.py')
        if os.path.exists(manager_path):
            subprocess.run([sys.executable, manager_path, 'ensure'], 
                         capture_output=True, timeout=40)
            if check_futu_available():
                print("  🟢 FutuOpenD启动成功，使用官方数据")
                source = "FutuOpenD"
                stock_data, ok = fetch_via_futu(KLINE_DAYS)
            else:
                print("  🔴 FutuOpenD启动失败，回退到新浪数据")
                source = "SinaJSONP"
                stock_data, ok = fetch_via_sina(KLINE_DAYS)
        else:
            print("  🔴 直接回退到新浪数据")
            source = "SinaJSONP"
            stock_data, ok = fetch_via_sina(KLINE_DAYS)
    
    if not stock_data:
        print("❌ 无法获取任何数据，退出")
        return
    
    print(f"\n  ✅ {len(stock_data)}/14 标的获取成功 (数据源: {source})")
    
    # Step 2: 五因子评估
    print(f"\n[2/4] 五因子评估...")
    results = run_bde_engine(stock_data)
    
    for r in results:
        tag = "🟢" if r.signal == "BUY" else "🟡" if r.signal == "HOLD" else "🔴"
        print(f"  {tag} {r.symbol:12s}: {r.composite_score:5.1f} → {r.signal}")
    
    # Step 3: 生成信号
    print(f"\n[3/4] 生成交易信号...")
    output = {
        "timestamp": datetime.now().isoformat(),
        "data_source": source,
        "lookback_days": KLINE_DAYS,
        "stocks": {},
        "signals": {"BUY": [], "HOLD": [], "AVOID": [], "SELL": []},
        "portfolio": {}
    }
    
    for r in results:
        output["stocks"][r.symbol] = {
            "score": round(r.composite_score, 1),
            "signal": r.signal,
            "scores": {k: round(v, 1) for k, v in r.scores.items()},
            "price": r.details.get("close"),
            "ma20": round(r.details.get("ma20", 0), 2)
        }
        output["signals"][r.signal].append(r.symbol)
    
    buy_list = output["signals"]["BUY"]
    if buy_list:
        weight = round(1.0 / len(buy_list), 4)
        output["portfolio"] = {
            "allocation": {s: weight for s in buy_list},
            "cash": round(1.0 - weight * len(buy_list), 4),
            "strategy": "段永平框架: 集中持有，宁缺毋滥"
        }
    else:
        output["portfolio"] = {
            "allocation": {},
            "cash": 1.0,
            "strategy": "全仓现金，等待信号"
        }
    
    # Step 4: 保存结果
    print(f"\n[4/4] 保存结果...")
    date_str = datetime.now().strftime('%Y%m%d')
    result_file = os.path.join(RESULT_DIR, f'bde_daily_{date_str}.json')
    with open(result_file, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"  📄 {result_file}")
    
    # 打印汇总
    print(f"\n{'='*60}")
    print(f"📊 BDE每日信号汇总")
    print(f"{'='*60}")
    print(f"  数据源: {source}")
    print(f"  🟢 买入: {output['signals']['BUY'] or '无'}")
    print(f"  🟡 持有: {output['signals']['HOLD']}")
    print(f"  🔴 卖出: {output['signals']['SELL'] or '无'}")
    print(f"  🔴 回避: {output['signals']['AVOID']}")
    print(f"  💰 仓位: 现金 {output['portfolio']['cash']*100:.0f}%")
    
    return output


if __name__ == '__main__':
    main()
