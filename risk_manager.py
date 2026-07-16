"""
BDE Score™ - AI-Powered Multi-Market Stock Analysis MCP Server
Copyright (C) 2026 BDE Score™ (https://github.com/hbhqq9/bde-score)

Licensed under AGPL-3.0 with commercial option.
If you run a modified version on a network server, you must make
the complete source code available. See LICENSE for details.
Commercial licensing available: nnhbh@foxmail.com
"""

"""
风控管理模块
============
硬编码段永平投资框架的核心约束，作为所有交易操作的最后一道防线。

铁律：
1. 不做空 — short_allowed = False
2. 不加杠杆 — leverage_max = 1.0
3. 买看得懂的 — 通过因子引擎 + 标的质量门槛过滤

职责：
- 订单前置检查（下单前调用）
- 仓位监控（实时监控持仓占比）
- 止损触发（日亏损超限 → 全部平仓）
- 涨跌停保护（不追单）
"""

import logging
from datetime import datetime, date
from dataclasses import dataclass, field
from typing import Optional

from config import RISK_LIMITS, ALPACA_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class RiskCheckResult:
    """风控检查结果"""
    passed: bool              # 是否通过
    reason: str = ""          # 未通过原因
    adjusted_qty: Optional[float] = None  # 调整后的数量（通过但需调仓）
    warnings: list[str] = field(default_factory=list)  # 警告信息


class RiskManager:
    """
    风控管理器
    
    Usage:
        rm = RiskManager(account_info)
        result = rm.check_order("AAPL", qty=10, side="buy", price=180.0)
        if result.passed:
            # 可以下单
            submit_order(...)
        else:
            print(f"被拦截: {result.reason}")
    """
    
    def __init__(self, account_info: dict = None, config=None):
        """
        初始化风控管理器
        
        Args:
            account_info: 账户信息 dict（来自 AlpacaClient.get_account()）
            config: RiskLimits 实例，默认使用全局配置
        """
        self.config = config or RISK_LIMITS
        self.account = account_info or {}
        
        # 日内交易计数
        self._daily_trade_count: int = 0
        self._daily_trade_date: Optional[date] = None
        
        # 日内已实现盈亏
        self._daily_realized_pnl: float = 0.0
        
        # 是否触发了日止损
        self._daily_stop_triggered: bool = False
    
    def update_account(self, account_info: dict):
        """更新账户信息"""
        self.account = account_info
    
    # ================================================================
    # 核心：订单前置检查
    # ================================================================
    
    def check_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        price: float,
        current_positions: list[dict] = None,
    ) -> RiskCheckResult:
        """
        订单前置风控检查（下单前必须调用）
        
        Args:
            symbol: 股票代码
            qty: 下单数量
            side: "buy" 或 "sell"
            price: 预计成交价格
            current_positions: 当前持仓列表
            
        Returns:
            RiskCheckResult: 检查结果
        """
        warnings = []
        
        # 0. 日止损已触发 → 全部拒绝
        if self._daily_stop_triggered:
            return RiskCheckResult(
                passed=False,
                reason="日内止损已触发，今日禁止新开仓"
            )
        
        # 1. 铁律检查：禁止做空
        if side == "sell" and not self.config.short_allowed:
            # 检查是否为平仓（持有该股票的情况下卖出是允许的）
            if not self._has_position(symbol, current_positions):
                return RiskCheckResult(
                    passed=False,
                    reason="段永平铁律：禁止做空。无法卖出未持有的标的。"
                )
        
        # 2. 铁律检查：禁止杠杆
        order_value = qty * price
        equity = self._get_equity()
        if equity > 0 and (order_value / equity) > self.config.leverage_max * self.config.max_position_pct:
            # 单笔超限检查
            pass  # 后面会详细检查
        
        # 3. 涨跌停检查
        if self.config.no_chase_limit:
            change_today = self._get_change_today(symbol, current_positions)
            if change_today is not None and abs(change_today) >= self.config.max_price_change_pct:
                return RiskCheckResult(
                    passed=False,
                    reason=f"涨跌停保护：{symbol} 日内涨跌幅 {change_today:.1%} 超过 {self.config.max_price_change_pct:.0%}，不追单"
                )
        
        # 4. 买入方向的仓位检查
        if side == "buy":
            # 4a. 单笔仓位检查
            if equity > 0:
                max_single_value = equity * self.config.max_position_pct
                if order_value > max_single_value:
                    # 自动调整数量
                    adjusted_qty = max_single_value / price
                    adjusted_qty = int(adjusted_qty)  # 取整
                    warnings.append(
                        f"单笔仓位限制：原 {qty} 股 → 调整为 {adjusted_qty} 股 "
                        f"(上限 {self.config.max_position_pct:.0%} × ${equity:,.0f})"
                    )
                    qty = adjusted_qty
                    order_value = qty * price
                
                # 4b. 总仓位检查
                total_position_value = self._get_total_position_value(current_positions)
                max_total_value = equity * self.config.max_total_position_pct
                remaining_capacity = max_total_value - total_position_value
                
                if remaining_capacity <= 0:
                    return RiskCheckResult(
                        passed=False,
                        reason=f"总仓位已满：当前 ${total_position_value:,.0f} ≥ 上限 ${max_total_value:,.0f} "
                               f"({self.config.max_total_position_pct:.0%} × ${equity:,.0f})"
                    )
                
                if order_value > remaining_capacity:
                    adjusted_qty = int(remaining_capacity / price)
                    warnings.append(
                        f"总仓位限制：原 {qty} 股 → 调整为 {adjusted_qty} 股 "
                        f"(剩余可用 ${remaining_capacity:,.0f})"
                    )
                    qty = adjusted_qty
                
                # 4c. 现金保留检查
                cash = self._get_cash()
                min_cash_reserve = equity * self.config.min_cash_reserve_pct
                available_for_trade = cash - min_cash_reserve
                
                if available_for_trade <= 0:
                    return RiskCheckResult(
                        passed=False,
                        reason=f"现金保留限制：当前现金 ${cash:,.0f} < 保留线 ${min_cash_reserve:,.0f}"
                    )
                
                if order_value > available_for_trade:
                    adjusted_qty = int(available_for_trade / price)
                    if adjusted_qty <= 0:
                        return RiskCheckResult(
                            passed=False,
                            reason="可用资金不足以买入1股（扣除现金保留后）"
                        )
                    warnings.append(
                        f"现金保留限制：原 {qty} 股 → 调整为 {adjusted_qty} 股"
                    )
                    qty = adjusted_qty
        
        # 5. 日交易次数检查
        self._reset_daily_counter()
        if self._daily_trade_count >= self.config.max_daily_trades:
            return RiskCheckResult(
                passed=False,
                reason=f"日交易次数已达上限 {self.config.max_daily_trades} 笔"
            )
        
        # 6. 价格合理性检查
        if price < self.config.min_price or price > self.config.max_price:
            return RiskCheckResult(
                passed=False,
                reason=f"价格异常：${price:.2f} 不在 [${self.config.min_price}, ${self.config.max_price}] 范围内"
            )
        
        # 全部通过
        return RiskCheckResult(
            passed=True,
            adjusted_qty=qty if qty != qty else None,
            warnings=warnings,
        )
    
    # ================================================================
    # 日止损检查
    # ================================================================
    
    def check_daily_loss(self, current_equity: float) -> RiskCheckResult:
        """
        检查日内亏损是否触发止损线
        
        Args:
            current_equity: 当前净值
            
        Returns:
            RiskCheckResult
        """
        if not self.account:
            return RiskCheckResult(passed=True)
        
        start_equity = float(self.account.get("equity", current_equity))
        if start_equity <= 0:
            return RiskCheckResult(passed=True)
        
        daily_return = (current_equity - start_equity) / start_equity
        
        if daily_return <= -self.config.max_daily_loss_pct:
            self._daily_stop_triggered = True
            return RiskCheckResult(
                passed=False,
                reason=(
                    f"⚠️ 日内止损触发！日亏损 {daily_return:.2%} 超过限制 "
                    f"{self.config.max_daily_loss_pct:.0%}，需要全部平仓"
                )
            )
        
        if daily_return <= -(self.config.max_daily_loss_pct * 0.7):
            return RiskCheckResult(
                passed=True,
                warnings=[
                    f"⚠️ 日亏损已达 {daily_return:.2%}，接近止损线 {self.config.max_daily_loss_pct:.0%}，请注意风险"
                ]
            )
        
        return RiskCheckResult(passed=True)
    
    # ================================================================
    # 单笔止损检查
    # ================================================================
    
    def check_single_stop_loss(self, position: dict) -> Optional[str]:
        """
        检查单笔持仓是否触发止损
        
        Args:
            position: 持仓信息 dict
            
        Returns:
            str: 止损原因，None 表示不需要止损
        """
        try:
            unrealized_plpc = float(position.get("unrealized_plpc", 0))
            if unrealized_plpc <= -self.config.max_single_loss_pct:
                return (
                    f"单笔止损：{position['symbol']} 浮亏 {unrealized_plpc:.2%} "
                    f"超过限制 {self.config.max_single_loss_pct:.0%}"
                )
        except (ValueError, TypeError):
            pass
        
        return None
    
    # ================================================================
    # 辅助方法
    # ================================================================
    
    def _get_equity(self) -> float:
        """获取账户净值"""
        return float(self.account.get("equity", 0))
    
    def _get_cash(self) -> float:
        """获取账户现金"""
        return float(self.account.get("cash", 0))
    
    def _get_total_position_value(self, positions: list[dict] = None) -> float:
        """计算当前总持仓市值"""
        if not positions:
            return float(self.account.get("long_market_value", 0))
        
        total = 0.0
        for p in positions:
            try:
                total += float(p.get("market_value", 0))
            except (ValueError, TypeError):
                pass
        return total
    
    def _has_position(self, symbol: str, positions: list[dict] = None) -> bool:
        """检查是否持有指定标的"""
        if not positions:
            return False
        return any(p.get("symbol") == symbol for p in positions)
    
    def _get_change_today(self, symbol: str, positions: list[dict] = None) -> Optional[float]:
        """获取标的日内涨跌幅"""
        if not positions:
            return None
        for p in positions:
            if p.get("symbol") == symbol:
                try:
                    return float(p.get("change_today", 0))
                except (ValueError, TypeError):
                    return None
        return None
    
    def _reset_daily_counter(self):
        """日切重置计数器"""
        today = date.today()
        if self._daily_trade_date != today:
            self._daily_trade_date = today
            self._daily_trade_count = 0
            self._daily_realized_pnl = 0.0
            self._daily_stop_triggered = False
    
    def record_trade(self):
        """记录一笔交易（增加日内计数）"""
        self._reset_daily_counter()
        self._daily_trade_count += 1
    
    # ================================================================
    # 报告
    # ================================================================
    
    def risk_report(self, positions: list[dict] = None) -> str:
        """
        生成风控状态报告
        
        Returns:
            str: 风控状态文本
        """
        equity = self._get_equity()
        cash = self._get_cash()
        total_pos = self._get_total_position_value(positions)
        
        lines = [
            "═══ BDE-Stock 风控状态报告 ═══",
            f"账户净值: ${equity:,.2f}",
            f"可用现金: ${cash:,.2f} ({cash/equity:.1%})" if equity > 0 else f"可用现金: ${cash:,.2f}",
            f"总持仓值: ${total_pos:,.2f} ({total_pos/equity:.1%})" if equity > 0 else f"总持仓值: ${total_pos:,.2f}",
            "",
            f"约束限制:",
            f"  单笔上限: {self.config.max_position_pct:.0%} × ${equity:,.0f} = ${equity * self.config.max_position_pct:,.0f}" if equity > 0 else "",
            f"  总仓位上限: {self.config.max_total_position_pct:.0%} × ${equity:,.0f} = ${equity * self.config.max_total_position_pct:,.0f}" if equity > 0 else "",
            f"  现金保留线: {self.config.min_cash_reserve_pct:.0%} × ${equity:,.0f} = ${equity * self.config.min_cash_reserve_pct:,.0f}" if equity > 0 else "",
            f"  日亏损限制: {self.config.max_daily_loss_pct:.0%}",
            f"  做空: {'允许' if self.config.short_allowed else '禁止（段永平铁律）'}",
            f"  杠杆: {self.config.leverage_max}x {'(无杠杆)' if self.config.leverage_max == 1.0 else ''}",
            f"",
            f"今日交易: {self._daily_trade_count}/{self.config.max_daily_trades} 笔",
            f"日止损状态: {'⚠️ 已触发' if self._daily_stop_triggered else '✅ 正常'}",
            "═══════════════════════════════",
        ]
        
        return "\n".join(line for line in lines if line is not None)
