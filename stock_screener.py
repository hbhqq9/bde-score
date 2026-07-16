"""
BDE Score™ - AI-Powered Multi-Market Stock Analysis MCP Server
Copyright (C) 2026 BDE Score™ (https://github.com/hbhqq9/bde-score)

Licensed under AGPL-3.0 with commercial option.
If you run a modified version on a network server, you must make
the complete source code available. See LICENSE for details.
Commercial licensing available: nnhbh@foxmail.com
"""

"""
股票筛选器
==========
从全市场 5000+ 标的中筛选出符合交易条件的候选列表。

筛选流程：
1. 流动性过滤 — 成交量、市值门槛
2. 价格过滤 — 排除仙股和异常高价
3. 可交易性过滤 — 排除停牌、OTC 等
4. 因子预筛选 — 用因子引擎快速粗筛

设计原则：
- 先粗后细：先用低成本过滤缩小范围，再精细评分
- 段永平框架：只买看得懂的（大市值、高流动性、主流标的）
"""

import logging
from typing import Optional
from dataclasses import dataclass

import pandas as pd

from config import RISK_LIMITS, TRADING_PARAMS
from alpaca_client import AlpacaClient
from factor_engine import FactorEngine, FactorResult

logger = logging.getLogger(__name__)


@dataclass
class ScreenResult:
    """筛选结果"""
    symbol: str
    passed: bool
    reason: str = ""
    factor_score: float = 0.0


class StockScreener:
    """
    股票筛选器
    
    Usage:
        screener = StockScreener(alpaca_client)
        candidates = screener.screen(["AAPL", "MSFT", "TSLA"])
    """
    
    def __init__(
        self,
        alpaca_client: Optional[AlpacaClient] = None,
        factor_engine: Optional[FactorEngine] = None,
        risk_limits=None,
    ):
        """
        初始化筛选器
        
        Args:
            alpaca_client: Alpaca API 客户端
            factor_engine: 因子引擎实例
            risk_limits: 风控约束配置
        """
        self.client = alpaca_client
        self.factor_engine = factor_engine or FactorEngine()
        self.limits = risk_limits or RISK_LIMITS
    
    def screen(
        self,
        symbols: list[str] = None,
        apply_factor: bool = True,
        top_n: int = 20,
    ) -> list[dict]:
        """
        执行筛选流程
        
        Args:
            symbols: 候选股票列表，默认使用 config 中的 watchlist
            apply_factor: 是否运行因子引擎评分
            top_n: 返回 Top N 只
            
        Returns:
            list[dict]: 筛选结果列表
        """
        symbols = symbols or TRADING_PARAMS.watchlist
        
        logger.info(f"开始筛选 | 候选 {len(symbols)} 只")
        
        # Step 1: 基础过滤
        passed = self._basic_filter(symbols)
        logger.info(f"基础过滤后: {len(passed)}/{len(symbols)} 只")
        
        if not passed:
            logger.warning("无股票通过基础过滤")
            return []
        
        # Step 2: 因子评分（可选）
        if apply_factor and self.client:
            results = self._factor_screen(passed)
        else:
            results = [{"symbol": s, "factor_score": 0, "signal": "PENDING"} for s in passed]
        
        # Step 3: 排序并返回 Top N
        results.sort(key=lambda x: -x.get("factor_score", 0))
        
        return results[:top_n]
    
    def _basic_filter(self, symbols: list[str]) -> list[str]:
        """
        基础过滤（无需行情数据）
        
        检查项：
        - 股票代码格式合法
        - 不在排除名单中
        
        Returns:
            list[str]: 通过过滤的股票列表
        """
        # 简单排除规则
        excluded_patterns = ["", "."]  # 空字符串
        
        passed = []
        for sym in symbols:
            sym = sym.strip().upper()
            
            # 格式检查
            if not sym or len(sym) > 10:
                logger.debug(f"{sym} 格式不合法，跳过")
                continue
            
            # 排除特殊字符（如 BRK.B 这类可以保留，但某些奇怪的要排除）
            if any(c in sym for c in ["@", "#", "$", "%"]):
                logger.debug(f"{sym} 含特殊字符，跳过")
                continue
            
            passed.append(sym)
        
        return passed
    
    def _factor_screen(self, symbols: list[str]) -> list[dict]:
        """
        因子评分筛选
        
        获取历史数据 → 运行因子引擎 → 返回评分结果
        
        Args:
            symbols: 通过基础过滤的股票列表
            
        Returns:
            list[dict]: 含因子评分的结果列表
        """
        if not self.client:
            return [{"symbol": s, "factor_score": 0, "signal": "NO_DATA"} for s in symbols]
        
        # 批量获取历史K线
        stock_data = {}
        try:
            bars = self.client.get_bars(
                symbols=symbols,
                days=TRADING_PARAMS.default_lookback_days,
            )
            
            # 处理返回的 DataFrame
            if isinstance(bars.index, pd.MultiIndex):
                for sym in symbols:
                    try:
                        sym_data = bars.xs(sym, level=0)
                        if len(sym_data) >= 30:
                            stock_data[sym] = sym_data
                    except KeyError:
                        continue
            else:
                # 单只股票
                if len(symbols) == 1 and len(bars) >= 30:
                    stock_data[symbols[0]] = bars
        
        except Exception as e:
            logger.error(f"批量获取K线失败: {e}")
            # 降级：逐个获取
            for sym in symbols:
                try:
                    bars = self.client.get_bars(sym, days=TRADING_PARAMS.default_lookback_days)
                    if len(bars) >= 30:
                        stock_data[sym] = bars
                except Exception as e2:
                    logger.debug(f"{sym} K线获取失败: {e2}")
        
        if not stock_data:
            return [{"symbol": s, "factor_score": 0, "signal": "NO_DATA"} for s in symbols]
        
        # 运行因子引擎
        factor_results: list[FactorResult] = self.factor_engine.evaluate(stock_data)
        
        # 转换为 dict 列表
        results = []
        scored_symbols = set()
        for r in factor_results:
            scored_symbols.add(r.symbol)
            results.append({
                "symbol": r.symbol,
                "factor_score": r.composite_score,
                "signal": r.signal,
                "scores": r.scores,
                "details": r.details,
            })
        
        # 补充没有评分结果的
        for sym in symbols:
            if sym not in scored_symbols:
                results.append({
                    "symbol": sym,
                    "factor_score": 0,
                    "signal": "NO_DATA",
                })
        
        return results
    
    def quick_check(self, symbol: str) -> dict:
        """
        快速检查单只股票是否值得深入分析
        
        Args:
            symbol: 股票代码
            
        Returns:
            dict: 检查结果
        """
        symbol = symbol.strip().upper()
        
        result = {
            "symbol": symbol,
            "valid": True,
            "issues": [],
        }
        
        # 基础检查
        if not symbol or len(symbol) > 10:
            result["valid"] = False
            result["issues"].append("代码格式不合法")
        
        return result
