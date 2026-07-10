#!/usr/bin/env python3
"""
BDE-Stock 一键启动脚本
=====================
从行情获取 → 因子评分 → 交易信号 → 富途模拟盘下单 → 飞书推送，全链路自动化。

使用方法:
    python run_bde_stock.py              # 完整运行（行情→评分→下单→推送）
    python run_bde_stock.py --dry-run    # 干跑模式（只评分不下单）
    python run_bde_stock.py --top 3      # 只交易前3只

依赖:
    pip install futu-api yfinance pandas numpy requests

前提:
    FutuOpenD 已启动并登录（默认 127.0.0.1:11111）
"""

import sys
import os
import json
import logging
import warnings
import argparse
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# 抑制 yfinance 警告
warnings.filterwarnings('ignore')

# ============================================================
# 路径设置
# ============================================================
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent  # BDE-Stock 根目录
sys.path.insert(0, str(PROJECT_DIR))

# 加载本地配置
CONFIG_PATH = SCRIPT_DIR / "config_local.json"
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    LOCAL_CONFIG = json.load(f)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('BDE-Run')


# ============================================================
# 第1部分：行情数据获取（yfinance + 新浪备用）
# ============================================================

def fetch_stock_data_yfinance(symbols: list, lookback_days: int = 200) -> dict:
    """
    从 yfinance 批量获取历史K线数据
    
    Args:
        symbols: 股票代码列表
        lookback_days: 回溯天数
    
    Returns:
        dict: {symbol: pd.DataFrame} 每个DataFrame含 open/high/low/close/volume
    """
    import yfinance as yf
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days + 30)  # 多取一些防止节假日不够
    
    logger.info(f"正在从 Yahoo Finance 获取 {len(symbols)} 只股票数据...")
    
    data = {}
    # 分批获取，每批10只
    batch_size = 10
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        batch_str = ' '.join(batch)
        
        try:
            df = yf.download(batch_str, start=start_date.strftime('%Y-%m-%d'),
                           end=end_date.strftime('%Y-%m-%d'), progress=False,
                           group_by='ticker', threads=True)
            
            for symbol in batch:
                try:
                    if len(batch) == 1:
                        sdf = df.copy()
                    else:
                        sdf = df[symbol].copy() if symbol in df.columns.get_level_values(0) else None
                    
                    if sdf is not None and len(sdf) > 50:
                        # 处理多层索引
                        if isinstance(sdf.columns, pd.MultiIndex):
                            sdf.columns = sdf.columns.droplevel(0)
                        
                        sdf = sdf.dropna(subset=['Close'])
                        # 统一列名为小写
                        sdf.columns = [c.lower() for c in sdf.columns]
                        data[symbol] = sdf
                    else:
                        logger.warning(f"  {symbol}: 数据不足，跳过")
                except Exception as e:
                    logger.warning(f"  {symbol}: 解析失败 ({e})")
                    
        except Exception as e:
            logger.error(f"  批次 {batch} 获取失败: {e}")
    
    logger.info(f"成功获取 {len(data)}/{len(symbols)} 只股票数据")
    return data


def fetch_stock_data_sina_fallback(symbol: str, lookback_days: int = 200) -> pd.DataFrame:
    """
    新浪行情备用接口（单只股票）
    当 yfinance 不可用时使用
    """
    import requests
    
    logger.info(f"尝试从新浪财经获取 {symbol} 数据...")
    
    # 新浪财经实时行情API
    # 美股代码格式: gb_aapl
    sina_code = f"gb_{symbol.lower().replace('-', '_').replace('.', '_')}"
    url = f"https://hq.sinajs.cn/list={sina_code}"
    
    try:
        resp = requests.get(url, timeout=10, headers={
            'Referer': 'https://finance.sina.com.cn'
        })
        if resp.status_code == 200 and 'var hq_str' in resp.text:
            parts = resp.text.split('"')[1].split(',')
            if len(parts) > 5:
                logger.info(f"  {symbol} 实时价格: ${parts[1]}")
                return parts  # 返回原始数据
    except Exception as e:
        logger.warning(f"  新浪接口失败: {e}")
    
    return None


# ============================================================
# 第2部分：BDE因子评分引擎
# ============================================================

def run_factor_scoring(stock_data: dict) -> list:
    """
    运行BDE五因子评分
    
    因子体系:
    - 动量因子 (30%) - 14日涨幅
    - 均值回归 (20%) - RSI超卖信号
    - 成交量 (20%) - 资金流入信号
    - 波动率 (15%) - 低波动优先
    - 趋势因子 (15%) - 均线趋势
    
    Returns:
        list: [(symbol, score, signal), ...] 按分数降序排列
    """
    from factor_engine import FactorEngine, FactorResult
    from config import FACTOR_CONFIG
    
    engine = FactorEngine(FACTOR_CONFIG)
    
    logger.info("正在运行BDE五因子评分引擎...")
    
    # FactorEngine.evaluate 接受 dict[str, pd.DataFrame]
    results = engine.evaluate(stock_data)
    
    # 按综合分数降序排列
    ranked = sorted(results, key=lambda x: -x.composite_score)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"  BDE因子评分结果 (Top 10)")
    logger.info(f"{'='*60}")
    
    for i, r in enumerate(ranked[:10]):
        emoji = "🟢" if r.signal == "BUY" else ("🔴" if r.signal == "SELL" else "⚪")
        logger.info(
            f"  #{i+1:2d} {emoji} {r.symbol:6s} | "
            f"综合={r.composite_score:5.1f} | "
            f"信号={r.signal:4s} | "
            f"动量={r.scores.get('momentum',0):.0f} "
            f"回归={r.scores.get('mean_reversion',0):.0f} "
            f"量能={r.scores.get('volume',0):.0f} "
            f"波动={r.scores.get('volatility',0):.0f} "
            f"趋势={r.scores.get('trend',0):.0f}"
        )
    
    return ranked


# ============================================================
# 第3部分：交易信号生成 + 风控检查
# ============================================================

def generate_trade_signals(ranked_results: list, top_n: int = 5) -> list:
    """
    从因子评分结果生成交易信号
    
    规则（段永平框架）:
    - 只做多，不做空
    - 不加杠杆
    - 单只最大25%仓位
    - 最多5只持仓
    - 综合评分 >= 55 才出BUY信号
    """
    config = LOCAL_CONFIG
    
    signals = []
    min_confidence = config['trading']['min_confidence']
    max_positions = config['trading']['max_positions']
    
    for r in ranked_results:
        if len(signals) >= max_positions:
            break
        
        # 只接受BUY信号且置信度达标
        if r.signal == "BUY" and r.composite_score >= min_confidence:
            signals.append({
                'symbol': r.symbol,
                'score': r.composite_score,
                'confidence': r.composite_score,
                'action': 'BUY',
                'position_pct': min(
                    config['trading']['max_single_position_pct'],
                    1.0 / max_positions  # 等权分配
                ),
            })
    
    logger.info(f"\n交易信号: {len(signals)} 只股票")
    for s in signals:
        logger.info(f"  📈 {s['symbol']:6s} | 评分={s['score']:.1f} | 仓位={s['position_pct']*100:.0f}%")
    
    return signals


# ============================================================
# 第4部分：富途模拟盘交易执行
# ============================================================

def execute_trades(signals: list, dry_run: bool = False) -> list:
    """
    通过FutuOpenD连接富途模拟盘执行交易
    
    Args:
        signals: 交易信号列表
        dry_run: 是否为干跑模式（不实际下单）
    
    Returns:
        list: 订单执行结果
    """
    if dry_run:
        logger.info("\n🏃 干跑模式 - 不实际下单")
        return [{'symbol': s['symbol'], 'status': 'DRY_RUN', 'qty': 0} for s in signals]
    
    futu_cfg = LOCAL_CONFIG['futu_opend']
    account_cfg = LOCAL_CONFIG['futu_account']
    
    logger.info(f"\n正在连接富途模拟盘 ({futu_cfg['host']}:{futu_cfg['port']})...")
    
    try:
        from futu_adapter import FutuAdapter
        
        broker = FutuAdapter(
            host=futu_cfg['host'],
            port=futu_cfg['port'],
            paper_trading=account_cfg['paper_trading'],
            trd_market=account_cfg['trd_market'],
            security_firm=account_cfg['security_firm']
        )
        
        # 连接
        if not broker.connect():
            logger.error("❌ 无法连接FutuOpenD！请确认：")
            logger.error("   1. FutuOpenD已启动")
            logger.error("   2. 已登录富途账号")
            logger.error("   3. 端口 {}:{} 可访问".format(futu_cfg['host'], futu_cfg['port']))
            return []
        
        logger.info("✅ FutuOpenD 连接成功")
        
        # 获取账户信息
        account = broker.get_account()
        if account:
            logger.info(f"  账户总资产: ${account.portfolio_value:,.2f}")
            logger.info(f"  可用资金:   ${account.cash:,.2f}")
            logger.info(f"  购买力:     ${account.buying_power:,.2f}")
        
        # 执行交易
        results = []
        total_capital = account.portfolio_value if account else LOCAL_CONFIG['trading']['initial_capital']
        
        for signal in signals:
            symbol = signal['symbol']
            target_value = total_capital * signal['position_pct']
            
            # 获取当前价格计算股数
            latest = broker.get_latest_bar(symbol)
            if not latest or latest.close <= 0:
                logger.warning(f"  {symbol}: 无法获取价格，跳过")
                continue
            
            qty = int(target_value / latest.close)
            if qty <= 0:
                logger.warning(f"  {symbol}: 计算股数为0，跳过")
                continue
            
            logger.info(f"  📤 下单: {symbol} × {qty}股 @ ~${latest.close:.2f} = ${qty*latest.close:,.2f}")
            
            order = broker.submit_order(
                symbol=symbol,
                qty=qty,
                side='buy',
                order_type='market',
                time_in_force='day'
            )
            
            if order:
                logger.info(f"  ✅ 订单成功: {order.order_id} 状态={order.status}")
                results.append({
                    'symbol': symbol,
                    'order_id': order.order_id,
                    'qty': qty,
                    'price': latest.close,
                    'status': order.status,
                    'value': qty * latest.close,
                })
            else:
                logger.warning(f"  ❌ 订单失败: {symbol}")
                results.append({
                    'symbol': symbol,
                    'order_id': None,
                    'qty': qty,
                    'price': latest.close,
                    'status': 'FAILED',
                    'value': 0,
                })
        
        # 断开连接
        broker.disconnect()
        return results
        
    except ImportError:
        logger.error("❌ futu-api 未安装！请运行: pip install futu-api")
        return []
    except Exception as e:
        logger.error(f"❌ 交易执行异常: {e}")
        return []


# ============================================================
# 第5部分：飞书推送
# ============================================================

def push_to_feishu(signals: list, results: list):
    """将交易结果推送到飞书"""
    feishu_cfg = LOCAL_CONFIG.get('feishu', {})
    webhook_url = feishu_cfg.get('webhook_url', '')
    
    if not feishu_cfg.get('enabled', False) or not webhook_url:
        logger.info("飞书推送未配置，跳过")
        return
    
    try:
        import requests
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        # 构建消息
        lines = [f"📊 BDE-Stock 交易报告 {now}", ""]
        
        if results:
            lines.append("📈 执行结果:")
            for r in results:
                status_emoji = "✅" if r['status'] in ['Filled', 'Submitted', 'DRY_RUN'] else "❌"
                lines.append(
                    f"  {status_emoji} {r['symbol']} | "
                    f"数量={r['qty']} | "
                    f"价格=${r.get('price', 0):.2f} | "
                    f"状态={r['status']}"
                )
        else:
            lines.append("⚪ 无交易信号或执行失败")
        
        lines.append("")
        lines.append(f"🎯 信号来源: BDE五因子模型")
        lines.append(f"📋 段永平框架: 只做多 | 不做空 | 不加杠杆")
        
        # 飞书卡片消息
        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": "🤖 BDE-Stock 自动交易报告"},
                    "template": "blue"
                },
                "elements": [
                    {"tag": "markdown", "content": "\n".join(lines)}
                ]
            }
        }
        
        resp = requests.post(webhook_url, json=card, timeout=10)
        if resp.status_code == 200:
            logger.info("✅ 飞书推送成功")
        else:
            logger.warning(f"飞书推送失败: {resp.status_code}")
    
    except Exception as e:
        logger.warning(f"飞书推送异常: {e}")


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='BDE-Stock 一键启动')
    parser.add_argument('--dry-run', action='store_true', help='干跑模式（只评分不下单）')
    parser.add_argument('--top', type=int, default=5, help='交易Top N只股票')
    parser.add_argument('--no-feishu', action='store_true', help='不推送飞书')
    parser.add_argument('--universe', type=str, default='', help='自定义股票池(逗号分隔)')
    args = parser.parse_args()
    
    print()
    print("=" * 60)
    print("  🤖 BDE-Stock 段永平价值因子量化系统")
    print("  📡 行情: Yahoo Finance → 因子评分 → 富途模拟盘")
    print(f"  📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    
    # ---- 确定股票池 ----
    if args.universe:
        universe = [s.strip() for s in args.universe.split(',')]
    else:
        universe = LOCAL_CONFIG.get('stock_universe', [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA',
            'BABA', 'BRK-B', 'BAC', 'V', 'KO',
        ])
    
    # ---- 步骤1: 获取行情数据 ----
    logger.info("📥 步骤1/4: 获取行情数据...")
    stock_data = fetch_stock_data_yfinance(universe)
    
    if not stock_data:
        logger.error("无法获取任何股票数据，请检查网络连接")
        sys.exit(1)
    
    # ---- 步骤2: 因子评分 ----
    logger.info("\n📊 步骤2/4: BDE五因子评分...")
    ranked = run_factor_scoring(stock_data)
    
    if not ranked:
        logger.error("因子评分无结果")
        sys.exit(1)
    
    # ---- 步骤3: 生成交易信号 ----
    logger.info(f"\n🎯 步骤3/4: 生成交易信号 (Top {args.top})...")
    signals = generate_trade_signals(ranked, top_n=args.top)
    
    # ---- 步骤4: 执行交易 ----
    mode_text = "干跑" if args.dry_run else "实盘"
    logger.info(f"\n💰 步骤4/4: 通过富途模拟盘执行交易 [{mode_text}]...")
    results = execute_trades(signals, dry_run=args.dry_run)
    
    # ---- 推送结果 ----
    if not args.no_feishu:
        push_to_feishu(signals, results)
    
    # ---- 汇总报告 ----
    print()
    print("=" * 60)
    print("  📋 执行汇总")
    print("=" * 60)
    print(f"  股票池:  {len(universe)} 只")
    print(f"  有效数据: {len(stock_data)} 只")
    print(f"  交易信号: {len(signals)} 只")
    print(f"  执行结果: {len(results)} 单")
    
    if results:
        total_value = sum(r.get('value', 0) for r in results)
        success_count = sum(1 for r in results if r['status'] in ['Filled', 'Submitted', 'DRY_RUN'])
        print(f"  成功订单: {success_count}/{len(results)}")
        print(f"  交易金额: ${total_value:,.2f}")
    
    print()
    print("  🛡️  段永平框架: 只做多 | 不做空 | 不加杠杆")
    print("  ✅ 运行完成!")
    print()


if __name__ == '__main__':
    main()
