"""
股票因子引擎
============
实现多因子量化选股模型，为每只股票计算综合得分。

当前实现 5 个核心因子：
1. 动量因子 (Momentum)    - N日收益率排名
2. 均值回归因子 (Mean Reversion) - 偏离MA20程度
3. 成交量因子 (Volume)    - 量比异常检测
4. 波动率因子 (Volatility) - ATR/波动率排名
5. 趋势因子 (Trend)       - EMA交叉信号

设计原则：
- 每个因子输出 0~100 的归一化分数
- 因子间加权合成，权重可在 config.py 中配置
- 支持增量扩展新因子
"""

import logging
from typing import Optional
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from config import FACTOR_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class FactorResult:
    """
    单只股票的因子评估结果
    
    Attributes:
        symbol: 股票代码
        scores: 各因子得分 {factor_name: score(0~100)}
        composite_score: 加权综合得分
        signal: 交易信号 (BUY/HOLD/SELL)
        details: 各因子详细数据
    """
    symbol: str
    scores: dict[str, float] = field(default_factory=dict)
    composite_score: float = 0.0
    signal: str = "HOLD"
    details: dict = field(default_factory=dict)
    
    def __repr__(self) -> str:
        return (
            f"FactorResult({self.symbol} | "
            f"综合={self.composite_score:.1f} | "
            f"信号={self.signal})"
        )


class FactorEngine:
    """
    多因子评估引擎
    
    Usage:
        engine = FactorEngine()
        results = engine.evaluate(stock_data)  # stock_data: dict[str, pd.DataFrame]
        for r in sorted(results, key=lambda x: -x.composite_score):
            print(r)
    """
    
    def __init__(self, config=None):
        """
        初始化因子引擎
        
        Args:
            config: FactorConfig 实例，默认使用全局配置
        """
        self.config = config or FACTOR_CONFIG
        self._validate_weights()
    
    def _validate_weights(self):
        """验证因子权重之和为 1.0"""
        total = sum(self.config.weights.values())
        if abs(total - 1.0) > 0.01:
            logger.warning(
                f"因子权重之和={total:.2f}，不等于1.0，将自动归一化"
            )
            # 自动归一化
            for k in self.config.weights:
                self.config.weights[k] /= total
    
    # ================================================================
    # 主入口
    # ================================================================
    
    def evaluate(self, stock_data: dict[str, pd.DataFrame]) -> list[FactorResult]:
        """
        对一组股票进行多因子评估
        
        Args:
            stock_data: {symbol: DataFrame(open, high, low, close, volume)}
            
        Returns:
            list[FactorResult]: 各股票的因子评估结果
        """
        results = []
        
        for symbol, df in stock_data.items():
            if len(df) < 30:
                logger.warning(f"{symbol} 数据不足30条，跳过评估")
                continue
            
            try:
                result = self._evaluate_single(symbol, df)
                results.append(result)
            except Exception as e:
                logger.error(f"{symbol} 因子计算失败: {e}")
                continue
        
        # 按综合得分排序
        results.sort(key=lambda x: -x.composite_score)
        
        logger.info(f"因子评估完成 | {len(results)}/{len(stock_data)} 只股票")
        return results
    
    def _evaluate_single(self, symbol: str, df: pd.DataFrame) -> FactorResult:
        """
        评估单只股票
        
        Args:
            symbol: 股票代码
            df: K线 DataFrame（要求有 open, high, low, close, volume 列）
            
        Returns:
            FactorResult
        """
        result = FactorResult(symbol=symbol)
        
        # 计算各因子得分
        result.scores["momentum"] = self._calc_momentum(df)
        result.scores["mean_reversion"] = self._calc_mean_reversion(df)
        result.scores["volume"] = self._calc_volume(df)
        result.scores["volatility"] = self._calc_volatility(df)
        result.scores["trend"] = self._calc_trend(df)
        
        # 加权合成
        result.composite_score = sum(
            result.scores.get(factor, 50.0) * weight
            for factor, weight in self.config.weights.items()
        )
        
        # 生成交易信号
        result.signal = self._generate_signal(result.composite_score, result.scores)
        
        # 记录详细数据
        result.details = {
            "close": float(df["close"].iloc[-1]),
            "close_5d_ago": float(df["close"].iloc[-5]) if len(df) >= 5 else None,
            "close_20d_ago": float(df["close"].iloc[-20]) if len(df) >= 20 else None,
            "ma20": float(df["close"].rolling(20).mean().iloc[-1]),
            "volume_ratio": float(df["volume"].iloc[-1] / df["volume"].rolling(20).mean().iloc[-1])
                if df["volume"].rolling(20).mean().iloc[-1] > 0 else None,
        }
        
        return result
    
    # ================================================================
    # 因子计算
    # ================================================================
    
    def _calc_momentum(self, df: pd.DataFrame) -> float:
        """
        动量因子
        ----------
        逻辑：计算多个周期的收益率，综合评估动量强度。
        
        评分规则：
        - 5日收益率 > 0 且递增 → 高分
        - 多个周期同时正向 → 动量确认 → 加分
        - 所有周期为负 → 低分
        
        Returns:
            float: 0~100 分
        """
        close = df["close"].values
        scores = []
        
        for period in self.config.momentum_periods:
            if len(close) < period + 1:
                scores.append(50.0)  # 数据不足，中性分
                continue
            
            # 计算该周期收益率
            ret = (close[-1] / close[-period - 1] - 1) * 100
            
            # 映射到 0~100 分
            # -10% → 10分, 0% → 50分, +10% → 90分
            score = np.clip(50 + ret * 4, 0, 100)
            scores.append(score)
        
        # 多周期加权（近期权重更高）
        weights = [0.3, 0.3, 0.2, 0.2][:len(scores)]
        total_weight = sum(weights)
        momentum_score = sum(s * w for s, w in zip(scores, weights)) / total_weight
        
        return float(np.clip(momentum_score, 0, 100))
    
    def _calc_mean_reversion(self, df: pd.DataFrame) -> float:
        """
        均值回归因子
        --------------
        逻辑：计算当前价格偏离 MA20 的程度。
              过度偏离均线 → 可能均值回归。
        
        评分规则（段永平视角：跌多了是好事）：
        - 价格低于 MA20 超过阈值 → 高分（买入机会）
        - 价格接近 MA20 → 中性分
        - 价格远高于 MA20 → 低分（过热）
        
        Returns:
            float: 0~100 分
        """
        window = self.config.mean_reversion_window
        threshold = self.config.mean_reversion_threshold
        
        close = df["close"].values
        ma = pd.Series(close).rolling(window).mean().iloc[-1]
        current = close[-1]
        
        if ma == 0 or np.isnan(ma):
            return 50.0
        
        # 偏离度 = (当前价 - MA) / MA
        deviation = (current - ma) / ma
        
        # 评分：偏离度负向越大（跌多了）→ 分越高
        # 偏离 -10% → 90分, 0% → 50分, +10% → 10分
        score = 50 - deviation * 400
        
        return float(np.clip(score, 0, 100))
    
    def _calc_volume(self, df: pd.DataFrame) -> float:
        """
        成交量因子
        ------------
        逻辑：检测成交量异常放大（机构进场信号）。
        
        评分规则：
        - 量比 > spike_threshold → 高分（有资金关注）
        - 量比接近 1.0 → 中性
        - 量比 < 0.5 → 低分（无人关注）
        
        注意：需结合趋势判断，放量下跌 ≠ 好信号
              这里仅衡量"关注度"，配合其他因子使用
        
        Returns:
            float: 0~100 分
        """
        lookback = self.config.volume_lookback
        spike_threshold = self.config.volume_spike_threshold
        
        volume = df["volume"].values
        
        if len(volume) < lookback + 1:
            return 50.0
        
        avg_volume = np.mean(volume[-lookback - 1:-1])
        if avg_volume == 0:
            return 50.0
        
        current_volume = volume[-1]
        volume_ratio = current_volume / avg_volume
        
        # 量比映射到分数
        # ratio < 0.5 → 20分（缩量）
        # ratio = 1.0 → 50分（正常）
        # ratio = spike_threshold → 80分（放量关注）
        # ratio > spike_threshold * 2 → 95分（极度活跃）
        if volume_ratio < 0.5:
            score = 20 + volume_ratio * 60
        elif volume_ratio <= spike_threshold:
            score = 50 + (volume_ratio - 1) / (spike_threshold - 1) * 30
        else:
            score = 80 + min((volume_ratio - spike_threshold) / spike_threshold, 1) * 15
        
        return float(np.clip(score, 0, 100))
    
    def _calc_volatility(self, df: pd.DataFrame) -> float:
        """
        波动率因子
        ------------
        逻辑：计算 ATR (Average True Range) 和收益率波动率。
              适度波动 = 交易机会，极端波动 = 风险。
        
        评分规则（段永平视角：稳健优先）：
        - 波动率极低 → 60分（稳定但机会少）
        - 波动率适中 → 80分（有交易机会，风险可控）
        - 波动率极高 → 30分（风险过大，不符合"看得懂"原则）
        
        Returns:
            float: 0~100 分
        """
        atr_period = self.config.atr_period
        vol_window = self.config.volatility_window
        
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values
        
        if len(close) < max(atr_period, vol_window) + 1:
            return 50.0
        
        # 计算 ATR
        tr_list = []
        for i in range(1, len(close)):
            tr = max(
                high[i] - low[i],
                abs(high[i] - close[i - 1]),
                abs(low[i] - close[i - 1])
            )
            tr_list.append(tr)
        
        atr = np.mean(tr_list[-atr_period:]) if len(tr_list) >= atr_period else np.mean(tr_list)
        
        # 计算收益率波动率（年化）
        returns = np.diff(np.log(close[-vol_window:]))
        volatility = np.std(returns) * np.sqrt(252) if len(returns) > 0 else 0
        
        # ATR 占价格的比例
        atr_pct = atr / close[-1] if close[-1] > 0 else 0
        
        # 综合波动率评分
        # atr_pct < 0.01 → 非常稳定 → 60分
        # atr_pct 0.01~0.03 → 适度波动 → 80分
        # atr_pct 0.03~0.05 → 偏高 → 50分
        # atr_pct > 0.05 → 极端 → 20分
        if atr_pct < 0.01:
            score = 60
        elif atr_pct < 0.03:
            score = 60 + (atr_pct - 0.01) / 0.02 * 20
        elif atr_pct < 0.05:
            score = 80 - (atr_pct - 0.03) / 0.02 * 30
        else:
            score = max(20, 50 - (atr_pct - 0.05) * 300)
        
        return float(np.clip(score, 0, 100))
    
    def _calc_trend(self, df: pd.DataFrame) -> float:
        """
        趋势因子（权重最高）
        --------------------
        逻辑：使用 EMA 交叉系统判断趋势方向和强度。
        
        评分规则：
        - 强上升趋势（价格 > EMA短 > EMA长）→ 高分
        - 金叉刚形成 → 额外加分
        - 下降趋势 → 低分
        - 震荡无趋势 → 中性分
        
        Returns:
            float: 0~100 分
        """
        close = pd.Series(df["close"].values)
        ema_short = self.config.ema_short
        ema_long = self.config.ema_long
        
        if len(close) < ema_long + 5:
            return 50.0
        
        ema_s = close.ewm(span=ema_short, adjust=False).mean()
        ema_l = close.ewm(span=ema_long, adjust=False).mean()
        
        current = close.iloc[-1]
        es = ema_s.iloc[-1]
        el = ema_l.iloc[-1]
        es_prev = ema_s.iloc[-3]  # 3天前
        el_prev = ema_l.iloc[-3]
        
        # 趋势判断
        # 强上升: price > ema_short > ema_long
        if current > es > el:
            score = 80
            # 金叉加分（短期EMA刚穿越长期EMA）
            if es_prev <= el_prev:
                score = 95  # 刚形成金叉
        # 温和上升: price > ema_long 但 ema_short < ema_long（回调中）
        elif current > el and es < el:
            score = 60  # 回调但未破位
        # 下降趋势: price < ema_short < ema_long
        elif current < es < el:
            score = 20
            # 死叉加分（负面）
            if es_prev >= el_prev:
                score = 10  # 刚形成死叉
        # 温和下降: price < ema_long
        elif current < el:
            score = 35
        # 震荡: ema_short 和 ema_long 交叉缠绕
        else:
            score = 50
        
        # 趋势强度修正：EMA 间距越大，趋势越强
        ema_spread = abs(es - el) / el if el > 0 else 0
        if ema_spread > 0.05:  # 5% 以上差距
            if es > el:
                score = min(100, score + 5)  # 强上升加分
            else:
                score = max(0, score - 5)  # 强下降减分
        
        return float(np.clip(score, 0, 100))
    
    # ================================================================
    # 信号生成
    # ================================================================
    
    def _generate_signal(self, composite: float, scores: dict) -> str:
        """
        根据综合得分生成交易信号
        
        Args:
            composite: 综合得分 (0~100)
            scores: 各因子得分
            
        Returns:
            str: "BUY", "HOLD", "SELL"
        """
        # 买入条件：综合分高 + 趋势因子不为最低
        if composite >= 70 and scores.get("trend", 0) >= 50:
            return "BUY"
        # 卖出条件：综合分低 或 趋势因子极弱
        elif composite <= 30 or scores.get("trend", 0) <= 15:
            return "SELL"
        else:
            return "HOLD"
    
    def summary_table(self, results: list[FactorResult]) -> pd.DataFrame:
        """
        生成因子评分汇总表
        
        Args:
            results: 因子评估结果列表
            
        Returns:
            pd.DataFrame: 汇总表
        """
        rows = []
        for r in results:
            row = {
                "symbol": r.symbol,
                "composite": round(r.composite_score, 1),
                "signal": r.signal,
            }
            row.update({f"f_{k}": round(v, 1) for k, v in r.scores.items()})
            row["price"] = round(r.details.get("close", 0), 2)
            row["ma20"] = round(r.details.get("ma20", 0), 2)
            row["vol_ratio"] = round(r.details.get("volume_ratio", 0) or 0, 2)
            rows.append(row)
        
        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values("composite", ascending=False)
        
        return df
