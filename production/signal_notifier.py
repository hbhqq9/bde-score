"""
BDE-Stock Phase 3 - 信号变化通知器
======================================
对比昨日信号，如有BUY/SELL变化则格式化通知消息。
输出变化摘要供飞书推送或主Agent通知使用。

输出: signal_changes.json (变化详情)
"""

import json
import os
import logging
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

PROD_DIR = os.path.dirname(os.path.abspath(__file__))
LATEST_FILE = os.path.join(PROD_DIR, 'bde_production_latest.json')
CHANGES_FILE = os.path.join(PROD_DIR, 'signal_changes.json')


SYMBOL_NAMES = {
    'aapl': 'Apple', 'msft': 'Microsoft', 'goog': 'Alphabet',
    'amzn': 'Amazon', 'meta': 'Meta', 'nvda': 'NVIDIA',
    'v': 'Visa', 'ma': 'Mastercard', 'jnj': 'J&J',
    'pg': 'P&G', 'tsla': 'Tesla', 'baba': 'BABA',
    'spy': 'SPY', 'qqq': 'QQQ',
}


def load_latest():
    """加载最新信号"""
    if not os.path.exists(LATEST_FILE):
        logger.error(f"信号文件不存在: {LATEST_FILE}")
        return None
    with open(LATEST_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_previous(date_str=None):
    """加载前一交易日信号"""
    if date_str is None:
        dt = datetime.now() - timedelta(days=1)
    else:
        dt = datetime.strptime(date_str, '%Y%m%d')
    
    # 尝试最近5天
    for days_back in range(0, 5):
        check_dt = dt - timedelta(days=days_back)
        check_str = check_dt.strftime('%Y%m%d')
        path = os.path.join(PROD_DIR, f'bde_production_{check_str}.json')
        if os.path.exists(path) and path != LATEST_FILE:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    return None


def format_notification(current_data, prev_data):
    """格式化信号变化通知"""
    curr_signals = current_data.get('signals', {})
    curr_stocks = current_data.get('stocks', {})
    vix = current_data.get('vix', {})
    
    prev_signals = prev_data.get('signals', {}) if prev_data else {}
    
    prev_buy = set(prev_signals.get('BUY', []))
    prev_sell = set(prev_signals.get('SELL', []))
    curr_buy = set(curr_signals.get('BUY', []))
    curr_sell = set(curr_signals.get('SELL', []))
    
    new_buy = sorted(curr_buy - prev_buy)
    new_sell = sorted(curr_sell - prev_sell)
    lost_buy = sorted(prev_buy - curr_buy)
    lost_sell = sorted(prev_sell - curr_sell)
    
    has_changes = bool(new_buy or new_sell or lost_buy or lost_sell)
    
    if not has_changes:
        return {
            'has_changes': False,
            'message': '✅ BDE-Stock 每日信号 - 无变化',
            'detail': f"BUY: {sorted(curr_buy)} | HOLD: {sorted(set(curr_signals.get('HOLD', [])))} | SELL: {sorted(curr_sell)}"
        }
    
    # 构建变化详情
    lines = []
    lines.append("⚡ BDE-Stock 信号变化通知")
    lines.append(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"📊 VIX: {vix.get('value', 'N/A')} → {vix.get('sentiment', 'N/A')}")
    lines.append("")
    
    if new_buy:
        lines.append("🟢 新增BUY:")
        for s in new_buy:
            name = SYMBOL_NAMES.get(s, s.upper())
            score = curr_stocks.get(s, {}).get('score', 0)
            price = curr_stocks.get(s, {}).get('price', 0)
            lines.append(f"  • {name} ({s.upper()}) 评分{score:.1f} 价格${price:.2f}")
        lines.append("")
    
    if lost_buy:
        lines.append("🟡 失去BUY:")
        for s in lost_buy:
            name = SYMBOL_NAMES.get(s, s.upper())
            score = curr_stocks.get(s, {}).get('score', 0)
            lines.append(f"  • {name} ({s.upper()}) 评分{score:.1f}")
        lines.append("")
    
    if new_sell:
        lines.append("🔴 新增SELL:")
        for s in new_sell:
            name = SYMBOL_NAMES.get(s, s.upper())
            score = curr_stocks.get(s, {}).get('score', 0)
            price = curr_stocks.get(s, {}).get('price', 0)
            lines.append(f"  • {name} ({s.upper()}) 评分{score:.1f} 价格${price:.2f}")
        lines.append("")
    
    if lost_sell:
        lines.append("🟢 解除SELL:")
        for s in lost_sell:
            name = SYMBOL_NAMES.get(s, s.upper())
            lines.append(f"  • {name} ({s.upper()})")
        lines.append("")
    
    # 当前完整信号
    lines.append("─── 当前信号 ───")
    lines.append(f"🟢 BUY: {sorted(curr_buy) or '无'}")
    lines.append(f"⚪ HOLD: {sorted(curr_signals.get('HOLD', []))}")
    lines.append(f"🔴 SELL: {sorted(curr_sell) or '无'}")
    
    # 组合建议
    portfolio = current_data.get('portfolio', {})
    if portfolio.get('allocation'):
        lines.append("")
        lines.append("─── 组合建议 ───")
        for sym, weight in portfolio['allocation'].items():
            name = SYMBOL_NAMES.get(sym, sym.upper())
            lines.append(f"  {name}: {weight:.0%}")
    
    message = '\n'.join(lines)
    
    return {
        'has_changes': True,
        'new_buy': new_buy,
        'new_sell': new_sell,
        'lost_buy': lost_buy,
        'lost_sell': lost_sell,
        'message': message,
    }


def main():
    print("=" * 60)
    print("BDE-Stock Phase 3 - 信号变化检测")
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    current_data = load_latest()
    if not current_data:
        return None
    
    prev_data = load_previous()
    
    result = format_notification(current_data, prev_data)
    
    # 保存变化详情
    with open(CHANGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    # 打印通知
    print(f"\n{result['message']}")
    
    if result['has_changes']:
        print(f"\n⚡ 存在信号变化，需要通知")
    else:
        print(f"\n✅ 信号无变化")
    
    return result


if __name__ == '__main__':
    try:
        result = main()
        if result is None:
            exit(1)
        exit(0)
    except Exception as e:
        logger.error(f"信号通知器执行失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        exit(1)
