"""
BDE-Stock Futu Data Adapter
通过本地FutuOpenD获取官方行情数据，替代新浪数据源
架构: bde_futu_adapter → 127.0.0.1:11111 → FutuOpenD → HTTPS(443) → 富途服务器
"""

import sys
import json
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, '/app/data/所有对话/主对话/BDE-Stock')
from factor_engine import FactorEngine

FUTU_HOST = '127.0.0.1'
FUTU_PORT = 11111
KLINE_DAYS = 120

BDE_UNIVERSE = {
    'US.AAPL': 'apple', 'US.MSFT': 'microsoft', 'US.GOOG': 'alphabet',
    'US.AMZN': 'amazon', 'US.META': 'meta', 'US.NVDA': 'nvidia',
    'US.V': 'visa', 'US.MA': 'mastercard', 'US.JNJ': 'jnj',
    'US.PG': 'pg', 'US.TSLA': 'tesla', 'US.BABA': 'baba',
    'US.SPY': 'spy', 'US.QQQ': 'qqq',
}


def check_futu_opend_alive():
    import subprocess
    result = subprocess.run(['pgrep', '-f', 'FutuOpenD'], capture_output=True, text=True)
    return result.returncode == 0


def fetch_all_klines(days=KLINE_DAYS):
    """通过futu-api获取所有14只标的的日K线，返回 DataFrame dict"""
    from futu import OpenQuoteContext, RET_OK

    if not check_futu_opend_alive():
        return None, "FutuOpenD未运行"

    ctx = OpenQuoteContext(host=FUTU_HOST, port=FUTU_PORT)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days + 30)).strftime('%Y-%m-%d')

    all_klines = {}
    errors = []

    try:
        for futu_code, name in BDE_UNIVERSE.items():
            ret, data, page = ctx.request_history_kline(
                futu_code, ktype='K_DAY',
                start=start_date, end=end_date
            )
            if ret == RET_OK and len(data) > 0:
                df = data.tail(days).reset_index(drop=True)
                # FactorEngine需要 open, high, low, close, volume 列
                all_klines[name] = df
                print(f"  ✅ {futu_code} ({name}): {len(df)}条, 最新 ${df.iloc[-1]['close']:.2f}")
            else:
                errors.append(f"  ❌ {futu_code}: {data}")
    finally:
        ctx.close()

    if errors:
        print("\n".join(errors))
    return all_klines, None if not errors else f"{len(errors)}个标的失败"


def run_bde_with_futu(days=KLINE_DAYS):
    """使用Futu数据运行完整BDE引擎"""
    print("=" * 60)
    print("BDE-Stock 富途数据版 — 完整引擎运行")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"回溯: {days}日 | 数据源: FutuOpenD (127.0.0.1:{FUTU_PORT})")
    print("=" * 60)

    # Step 1: 获取K线
    print("\n[1/3] 获取K线数据...")
    all_klines, err = fetch_all_klines(days)
    if err:
        return {"status": "ERROR", "error": err}
    print(f"\n✅ {len(all_klines)}/14 标的获取成功")

    # Step 2: 五因子评估
    print("\n[2/3] 五因子评估...")
    engine = FactorEngine()
    results = engine.evaluate(all_klines)

    for r in results:
        tag = "🟢" if r.signal == "BUY" else "🟡" if r.signal == "HOLD" else "🔴"
        print(f"  {tag} {r.symbol:12s}: {r.composite_score:5.1f} → {r.signal}  (动量:{r.scores.get('momentum',0):.0f} 均值回归:{r.scores.get('mean_reversion',0):.0f} 量价:{r.scores.get('volume',0):.0f} 波动:{r.scores.get('volatility',0):.0f} 趋势:{r.scores.get('trend',0):.0f})")

    # Step 3: 生成信号
    print("\n[3/3] 生成交易信号...")
    output = {
        "timestamp": datetime.now().isoformat(),
        "data_source": "FutuOpenD",
        "lookback_days": days,
        "stocks": {},
        "signals": {"BUY": [], "HOLD": [], "AVOID": []},
        "portfolio": {}
    }

    for r in results:
        output["stocks"][r.symbol] = {
            "score": round(r.composite_score, 1),
            "signal": r.signal,
            "scores": {k: round(v, 1) for k, v in r.scores.items()},
            "price": r.details.get("close"),
            "ma20": round(r.details.get("ma20", 0), 2),
            "volume_ratio": round(r.details.get("volume_ratio", 0) or 0, 2)
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

    # 汇总
    print("\n" + "=" * 60)
    print("📊 BDE信号汇总（富途数据版）")
    print("=" * 60)
    print(f"  🟢 买入: {output['signals']['BUY'] or '无'}")
    print(f"  🟡 持有: {output['signals']['HOLD']}")
    print(f"  🔴 回避: {output['signals']['AVOID']}")
    print(f"\n  💰 仓位: 现金 {output['portfolio']['cash']*100:.0f}%")
    if output['portfolio']['allocation']:
        for s, w in output['portfolio']['allocation'].items():
            print(f"    {s}: {w*100:.1f}%")

    return output


if __name__ == '__main__':
    result = run_bde_with_futu()
    output_path = '/app/data/所有对话/主对话/BDE-Stock/bde_futu_result.json'
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n结果已保存: {output_path}")
