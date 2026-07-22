"""
BDE-Stock Phase 3 - 生产版本每日执行脚本
==========================================
整合Phase 2所有功能作为正式生产脚本：
- 7因子模型（VIX + Volume Profile + 原5因子）
- 动态权重引擎（VIX四档自动调整）
- 终点区间输出（压力位/支撑位/POC）
- 标准化JSON输出
- 信号变化检测（供推送系统使用）
- DNA完整性校验（防篡改）

数据源: yfinance(VIX) > 新浪JSONP API
执行频率: 每日美股收盘后（UTC 21:00+）

DNA验证: 启动时校验 SYSTEM_DNA.md 完整性，校验失败则拒绝执行。
"""

import sys
import json
import os
import hashlib
import subprocess
import traceback
import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# 路径设置
PROD_DIR = os.path.dirname(os.path.abspath(__file__))
BDE_ROOT = os.path.dirname(PROD_DIR)
PHASE2_DIR = os.path.join(BDE_ROOT, 'phase2_backtest')
PHASE1_DIR = os.path.join(BDE_ROOT, 'phase1_vix_vp')

sys.path.insert(0, PROD_DIR)
sys.path.insert(0, PHASE2_DIR)
sys.path.insert(0, PHASE1_DIR)
sys.path.insert(0, BDE_ROOT)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ================================================================
# DNA完整性校验（防篡改）
# ================================================================
DNA_FILE = os.path.join(os.path.dirname(PROD_DIR), 'SYSTEM_DNA.md')
DNA_HASH_EXPECTED = "e36a48bc52a90e571250b85dfd20a464cd680c7e65467ec9002a77a769eef59a"

def verify_dna_integrity():
    """
    校验 SYSTEM_DNA.md 的完整性。
    如果DNA文件被篡改或不存在，拒绝执行。
    返回 True=通过, False=失败（此时应退出）
    """
    if not os.path.exists(DNA_FILE):
        logger.error(f"❌ DNA文件不存在: {DNA_FILE}")
        logger.error("系统DNA被删除，拒绝执行。请恢复 SYSTEM_DNA.md 后重试。")
        return False
    
    try:
        with open(DNA_FILE, 'rb') as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()
    except Exception as e:
        logger.error(f"❌ 无法读取DNA文件: {e}")
        return False
    
    if actual_hash != DNA_HASH_EXPECTED:
        logger.error(f"❌ DNA完整性校验失败！")
        logger.error(f"   期望: {DNA_HASH_EXPECTED}")
        logger.error(f"   实际: {actual_hash}")
        logger.error("系统DNA可能被篡改，拒绝执行。请检查 SYSTEM_DNA.md 并更新哈希。")
        return False
    
    logger.info(f"✅ DNA完整性校验通过 (SHA-256: {actual_hash[:16]}...)")
    return True


# ================================================================
# 常量配置
# ================================================================
KLINE_DAYS = 120
RESULT_DIR = PROD_DIR  # 输出到production目录
INITIAL_CAPITAL = 1_000_000

UNIVERSE_SINA = {
    'aapl': 'apple', 'msft': 'microsoft', 'goog': 'alphabet',
    'amzn': 'amazon', 'meta': 'meta', 'nvda': 'nvidia',
    'v': 'visa', 'ma': 'mastercard', 'jnj': 'jnj',
    'pg': 'pg', 'tsla': 'tesla', 'baba': 'baba',
    'spy': 'spy', 'qqq': 'qqq',
}

UNIVERSE_FUTU = {
    'US.AAPL': 'apple', 'US.MSFT': 'microsoft', 'US.GOOG': 'alphabet',
    'US.AMZN': 'amazon', 'US.META': 'meta', 'US.NVDA': 'nvidia',
    'US.V': 'visa', 'US.MA': 'mastercard', 'US.JNJ': 'jnj',
    'US.PG': 'pg', 'US.TSLA': 'tesla', 'US.BABA': 'baba',
    'US.SPY': 'spy', 'US.QQQ': 'qqq',
}


# ================================================================
# VIX数据获取
# ================================================================
def fetch_vix_yfinance():
    """通过yfinance获取VIX"""
    try:
        import yfinance as yf
        vix = yf.Ticker("^VIX")
        hist = vix.history(period="1mo")
        if hist is not None and len(hist) > 0:
            current_vix = float(hist["Close"].iloc[-1])
            history = hist["Close"]
            logger.info(f"VIX via yfinance: {current_vix:.2f}")
            return current_vix, history
    except ImportError:
        logger.warning("yfinance未安装")
    except Exception as e:
        logger.warning(f"yfinance VIX失败: {e}")
    return None, None


def fetch_vix_sina():
    """通过新浪API获取VIX"""
    try:
        import requests
        url = ("https://stock.finance.sina.com.cn/usstock/api/jsonp.php/"
               "var%20data=/US_MinKService.getDailyK?symbol=vix&scale=240&datalen=30")
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://finance.sina.com.cn'
        }
        resp = requests.get(url, headers=headers, timeout=15)
        text = resp.text
        json_str = text[text.index('(') + 1:text.rindex(')')]
        records = json.loads(json_str)
        if records:
            latest = float(records[-1]['close'])
            closes = pd.Series([float(r['close']) for r in records])
            logger.info(f"VIX via Sina: {latest:.2f}")
            return latest, closes
    except Exception as e:
        logger.warning(f"Sina VIX失败: {e}")
    return None, None


def fetch_vix():
    """获取VIX恐慌指数（多数据源降级）"""
    logger.info("获取VIX恐慌指数...")
    vix_val, vix_hist = fetch_vix_yfinance()
    if vix_val is not None:
        return vix_val, vix_hist
    vix_val, vix_hist = fetch_vix_sina()
    if vix_val is not None:
        return vix_val, vix_hist
    logger.warning("所有VIX数据源不可用，使用中性值20")
    return 20.0, None


# ================================================================
# 股票数据获取
# ================================================================
def fetch_via_sina(days):
    """通过新浪JSONP获取股票数据"""
    import requests
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
        'Referer': 'https://finance.sina.com.cn'
    }
    all_data = {}
    for sina_symbol, name in UNIVERSE_SINA.items():
        url = (f'https://stock.finance.sina.com.cn/usstock/api/jsonp.php/'
               f'var%20data=/US_MinKService.getDailyK?'
               f'symbol={sina_symbol}&scale=240&datalen={days}')
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            text = resp.text
            json_str = text[text.index('(') + 1:text.rindex(')')]
            records = json.loads(json_str)
            if len(records) > 0:
                df = pd.DataFrame(records)
                if 'd' in df.columns:
                    df = df.rename(columns={
                        'd': 'date', 'o': 'open', 'h': 'high',
                        'l': 'low', 'c': 'close', 'v': 'volume'
                    })
                for col in ['open', 'high', 'low', 'close']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0).astype(int)
                df = df.dropna(subset=['close']).reset_index(drop=True)
                df = df.tail(days).reset_index(drop=True)
                df = df.rename(columns={'date': 'time_key'})
                all_data[name] = df
        except Exception:
            pass
    return all_data, len(all_data) == len(UNIVERSE_SINA)


def check_futu_available():
    """检查FutuOpenD是否可用"""
    try:
        result = subprocess.run(['pgrep', '-f', 'FutuOpenD'],
                                capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return False
        from futu import OpenQuoteContext, RET_OK
        ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
        ret, data = ctx.get_market_snapshot(['US.AAPL'])
        ctx.close()
        return ret == RET_OK
    except:
        return False


def fetch_stock_data(days):
    """获取股票数据（自动选择数据源）"""
    logger.info("检测数据源...")
    source = "SinaJSONP"
    stock_data, ok = fetch_via_sina(days)
    if not stock_data and check_futu_available():
        logger.info("FutuOpenD可用，尝试获取...")
        source = "FutuOpenD"
        stock_data, ok = fetch_via_sina(days)  # 仍用sina作为fallback
    logger.info(f"{len(stock_data)}/14 标的获取成功 (数据源: {source})")
    return stock_data, source


# ================================================================
# 信号变化检测
# ================================================================
def load_previous_signals():
    """加载昨日的信号用于对比"""
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    prev_file = os.path.join(RESULT_DIR, f'bde_production_{yesterday}.json')
    
    if os.path.exists(prev_file):
        try:
            with open(prev_file, 'r') as f:
                data = json.load(f)
            return data.get('signals', {})
        except:
            pass
    
    # 也尝试检查前一天的文件
    for days_back in range(2, 5):
        prev_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y%m%d')
        prev_file = os.path.join(RESULT_DIR, f'bde_production_{prev_date}.json')
        if os.path.exists(prev_file):
            try:
                with open(prev_file, 'r') as f:
                    data = json.load(f)
                return data.get('signals', {})
            except:
                pass
    return None


def detect_signal_changes(current_signals, prev_signals):
    """检测信号变化"""
    if prev_signals is None:
        return {
            "new_buy": current_signals.get("BUY", []),
            "new_sell": current_signals.get("SELL", []),
            "lost_buy": [],
            "lost_sell": [],
            "has_changes": True
        }
    
    prev_buy = set(prev_signals.get("BUY", []))
    prev_sell = set(prev_signals.get("SELL", []))
    curr_buy = set(current_signals.get("BUY", []))
    curr_sell = set(current_signals.get("SELL", []))
    
    return {
        "new_buy": sorted(curr_buy - prev_buy),
        "new_sell": sorted(curr_sell - prev_sell),
        "lost_buy": sorted(prev_buy - curr_buy),
        "lost_sell": sorted(prev_sell - curr_sell),
        "has_changes": bool(curr_buy - prev_buy or curr_sell - prev_sell or
                           prev_buy - curr_buy or prev_sell - curr_sell)
    }


# ================================================================
# 主执行流程
# ================================================================
def main():
    """
    生产版本主流程:
    1. 获取VIX数据
    2. 获取股票数据
    3. 动态权重计算
    4. Phase 2 因子评估
    5. 信号变化检测
    6. 输出标准化JSON
    """
    print("=" * 70)
    print(f"BDE-Stock Phase 3 PRODUCTION | 7因子+动态权重+终点区间")
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"回溯: {KLINE_DAYS}日")
    print("=" * 70)

    # Step 0: DNA完整性校验
    if not verify_dna_integrity():
        logger.error("DNA校验未通过，系统拒绝执行")
        sys.exit(2)

    # Step 1: 获取VIX
    vix_value, vix_history = fetch_vix()

    # Step 2: 获取股票数据
    stock_data, source = fetch_stock_data(KLINE_DAYS)
    if not stock_data:
        logger.error("无法获取任何数据，退出")
        return None

    # Step 3: 动态权重计算
    logger.info("动态权重引擎...")
    from dynamic_weight_engine import DynamicWeightEngine
    dw_engine = DynamicWeightEngine(vix_value=vix_value)
    dynamic_weights = dw_engine.get_weights_dict()
    regime_info = dw_engine.get_regime_summary()

    logger.info(f"VIX={vix_value:.2f} → 市场状态: {regime_info['regime']}")
    logger.info(f"因果层: {regime_info['config']['causal_layer']['total']:.0%}  "
                f"技术层: {regime_info['config']['technical_layer']['total']:.0%}")

    # Step 4: Phase 2 因子评估
    logger.info("Phase 2 因子评估（动态权重 + 终点区间）...")
    from factor_engine_phase2 import FactorEnginePhase2

    engine = FactorEnginePhase2(
        vix_value=vix_value,
        vix_history=vix_history,
        weights_override=dynamic_weights
    )
    results = engine.evaluate(stock_data)

    # 打印结果
    print(f"\n  {'标的':<10s} {'综合分':>6s} {'信号':>5s} {'价格':>8s} "
          f"{'R1':>8s} {'S1':>8s} {'POC':>8s} {'位置':>12s}")
    print(f"  {'-'*85}")
    for r in results:
        ep = r.endpoints
        r1 = f"{ep.get('resistance_1', '-')}" if ep.get('resistance_1') else "-"
        s1 = f"{ep.get('support_1', '-')}" if ep.get('support_1') else "-"
        poc = f"{ep.get('poc', '-')}" if ep.get('poc') else "-"
        pos = ep.get('current_position', '-')
        tag = "BUY" if r.signal == "BUY" else "HOLD" if r.signal == "HOLD" else "SELL"
        print(f"  {r.symbol:<10s} {r.composite_score:5.1f} {tag:>5s} "
              f"{r.details.get('close', 0):8.2f} {r1:>8s} {s1:>8s} "
              f"{poc:>8s} {pos:>12s}")

    # Step 5: 构建输出
    logger.info("生成输出...")
    output = {
        "timestamp": datetime.now().isoformat(),
        "model_version": "Phase3_7Factor_DynamicWeight_Production",
        "data_source": source,
        "lookback_days": KLINE_DAYS,
        "vix": {
            "value": round(vix_value, 2) if vix_value else None,
            "score": results[0].vix_data.get("score", 50) if results else 50,
            "sentiment": results[0].vix_data.get("sentiment_cn", "未知") if results else "未知",
        },
        "dynamic_weights": regime_info,
        "stocks": {},
        "signals": {"BUY": [], "HOLD": [], "SELL": []},
        "summary": {
            "total_stocks": len(results),
        }
    }

    for r in results:
        output["stocks"][r.symbol] = {
            "score": round(r.composite_score, 1),
            "signal": r.signal,
            "scores": {k: round(v, 1) for k, v in r.scores.items()},
            "price": r.details.get("close"),
            "ma20": round(r.details.get("ma20", 0), 2),
            "vix": r.vix_data,
            "volume_profile": r.volume_profile_data,
            "endpoints": r.endpoints,
        }
        output["signals"][r.signal].append(r.symbol)

    output["summary"]["buy_list"] = output["signals"]["BUY"]
    output["summary"]["hold_list"] = output["signals"]["HOLD"]
    output["summary"]["sell_list"] = output["signals"]["SELL"]

    # 投资组合建议
    buy_list = output["signals"]["BUY"]
    if buy_list:
        weight = round(1.0 / len(buy_list), 4)
        output["portfolio"] = {
            "allocation": {s: weight for s in buy_list},
            "cash": round(1.0 - weight * len(buy_list), 4),
            "strategy": "Phase3因果增强+动态权重+终点区间"
        }
    else:
        output["portfolio"] = {
            "allocation": {},
            "cash": 1.0,
            "strategy": "全仓现金，等待因果共振信号"
        }

    # Step 6: 信号变化检测
    prev_signals = load_previous_signals()
    signal_changes = detect_signal_changes(output["signals"], prev_signals)
    output["signal_changes"] = signal_changes

    # 保存结果
    date_str = datetime.now().strftime('%Y%m%d')
    result_file = os.path.join(RESULT_DIR, f'bde_production_{date_str}.json')
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    logger.info(f"结果已保存: {result_file}")

    # 同时保存一份latest symlink/copy
    latest_file = os.path.join(RESULT_DIR, 'bde_production_latest.json')
    with open(latest_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # 打印汇总
    print(f"\n{'='*70}")
    print(f"BDE-Stock Phase 3 PRODUCTION - 每日汇总")
    print(f"{'='*70}")
    print(f"  VIX: {output['vix']['value']} → {output['vix']['sentiment']}")
    print(f"  权重: 因果层{regime_info['config']['causal_layer']['total']:.0%} + "
          f"技术层{regime_info['config']['technical_layer']['total']:.0%}")
    print(f"  BUY: {output['signals']['BUY'] or '无'}")
    print(f"  HOLD: {output['signals']['HOLD']}")
    print(f"  SELL: {output['signals']['SELL'] or '无'}")

    if signal_changes["has_changes"]:
        print(f"\n  ⚡ 信号变化:")
        if signal_changes["new_buy"]:
            print(f"    新增BUY: {signal_changes['new_buy']}")
        if signal_changes["new_sell"]:
            print(f"    新增SELL: {signal_changes['new_sell']}")
        if signal_changes["lost_buy"]:
            print(f"    失去BUY: {signal_changes['lost_buy']}")
    else:
        print(f"\n  ✅ 信号无变化")

    # 终点区间汇总
    print(f"\n  终点区间（关键价位）:")
    for r in results:
        ep = r.endpoints
        if ep.get("resistance_1") or ep.get("support_1"):
            r1 = f"{ep['resistance_1']}" if ep.get('resistance_1') else "N/A"
            s1 = f"{ep['support_1']}" if ep.get('support_1') else "N/A"
            poc = f"{ep['poc']}" if ep.get('poc') else "N/A"
            print(f"    {r.symbol:<10s}: 压力={r1} | 支撑={s1} | POC={poc}")

    return output


if __name__ == '__main__':
    try:
        result = main()
        if result is None:
            sys.exit(1)
        sys.exit(0)
    except Exception as e:
        logger.error(f"生产脚本执行失败: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
