"""
飞书推送模块
============
将交易信号、风控预警、每日报告推送到飞书群。

推送类型：
- 交易通知：下单/成交/平仓
- 风控预警：止损触发、仓位超限
- 每日报告：持仓汇总、盈亏统计
- 因子报告：因子评分排行（调试用）

格式规范：
- 使用飞书 Webhook 富文本卡片格式
- 颜色标记：盈利=绿色，亏损=红色，警告=黄色
"""

import json
import logging
from datetime import datetime
from typing import Optional

import requests

from config import FEISHU_CONFIG

logger = logging.getLogger(__name__)


class FeishuPusher:
    """
    飞书消息推送器
    
    Usage:
        pusher = FeishuPusher()
        pusher.send_trade_notify("BUY", "AAPL", 10, 180.5)
        pusher.send_daily_report(account, positions)
    """
    
    def __init__(self, config=None):
        """
        初始化推送器
        
        Args:
            config: FeishuConfig 实例
        """
        self.config = config or FEISHU_CONFIG
    
    def _send(self, payload: dict) -> bool:
        """
        发送消息到飞书 Webhook
        
        Args:
            payload: 飞书消息体
            
        Returns:
            bool: 是否发送成功
        """
        if not self.config.webhook_url:
            logger.warning("飞书 Webhook URL 未配置，跳过推送")
            return False
        
        try:
            response = requests.post(
                self.config.webhook_url,
                json=payload,
                timeout=10,
            )
            result = response.json()
            
            if result.get("code") == 0 or result.get("StatusCode") == 0:
                logger.info("飞书推送成功")
                return True
            else:
                logger.error(f"飞书推送失败: {result}")
                return False
        except Exception as e:
            logger.error(f"飞书推送异常: {e}")
            return False
    
    def _build_card(self, title: str, elements: list[dict], color: str = "blue") -> dict:
        """
        构建飞书卡片消息
        
        Args:
            title: 卡片标题
            elements: 卡片元素列表
            color: 标题颜色 (blue/green/red/yellow)
            
        Returns:
            dict: 飞书消息体
        """
        color_map = {
            "blue": "blue",
            "green": "green",
            "red": "red",
            "yellow": "orange",
        }
        
        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title,
                    },
                    "template": color_map.get(color, "blue"),
                },
                "elements": elements,
            },
        }
    
    def _text_element(self, text: str) -> dict:
        """创建文本元素"""
        return {
            "tag": "markdown",
            "content": text,
        }
    
    def _divider(self) -> dict:
        """创建分割线"""
        return {"tag": "hr"}
    
    # ================================================================
    # 交易通知
    # ================================================================
    
    def send_trade_notify(
        self,
        action: str,
        symbol: str,
        qty: float,
        price: float,
        order_id: str = "",
        status: str = "",
    ):
        """
        推送交易通知
        
        Args:
            action: "BUY" / "SELL"
            symbol: 股票代码
            qty: 数量
            price: 成交价格
            order_id: 订单ID
            status: 订单状态
        """
        if not self.config.enable_trade_notify:
            return
        
        emoji = "🟢" if action.upper() == "BUY" else "🔴"
        color = "green" if action.upper() == "BUY" else "red"
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        elements = [
            self._text_element(
                f"**{emoji} {action.upper()}** {symbol}\n"
                f"数量: {qty} 股\n"
                f"价格: ${price:,.2f}\n"
                f"金额: ${qty * price:,.2f}\n"
                f"订单ID: {order_id}\n"
                f"状态: {status}\n"
                f"时间: {now}"
            ),
        ]
        
        payload = self._build_card(f"BDE-Stock 交易通知", elements, color)
        self._send(payload)
    
    # ================================================================
    # 风控预警
    # ================================================================
    
    def send_risk_alert(self, title: str, message: str, level: str = "warning"):
        """
        推送风控预警
        
        Args:
            title: 预警标题
            message: 预警详情
            level: "warning" / "critical"
        """
        if not self.config.enable_alert_notify:
            return
        
        color = "red" if level == "critical" else "yellow"
        emoji = "🚨" if level == "critical" else "⚠️"
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        elements = [
            self._text_element(f"{emoji} **{title}**\n\n{message}\n\n时间: {now}"),
        ]
        
        payload = self._build_card("BDE-Stock 风控预警", elements, color)
        self._send(payload)
    
    # ================================================================
    # 每日报告
    # ================================================================
    
    def send_daily_report(
        self,
        account: dict,
        positions: list[dict],
        risk_report: str = "",
    ):
        """
        推送每日持仓报告
        
        Args:
            account: 账户信息
            positions: 持仓列表
            risk_report: 风控状态文本
        """
        if not self.config.enable_daily_report:
            return
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 账户概要
        equity = float(account.get("equity", 0))
        cash = float(account.get("cash", 0))
        pnl = equity - 100000  # Paper trading 初始 $100,000
        
        lines = [
            f"**📊 每日报告** | {now}",
            "",
            f"**账户概览**",
            f"净值: ${equity:,.2f}",
            f"现金: ${cash:,.2f}",
            f"持仓: ${equity - cash:,.2f}",
            f"今日盈亏: {'🟢' if pnl >= 0 else '🔴'} ${pnl:,.2f}",
        ]
        
        # 持仓明细
        if positions:
            lines.append("")
            lines.append("**持仓明细**")
            for p in positions:
                sym = p.get("symbol", "?")
                qty = p.get("qty", "0")
                pnl_pct = p.get("unrealized_plpc", "0")
                try:
                    pnl_pct_f = float(pnl_pct)
                    emoji = "🟢" if pnl_pct_f >= 0 else "🔴"
                    lines.append(f"  {emoji} {sym}: {qty}股 ({pnl_pct_f:+.2%})")
                except (ValueError, TypeError):
                    lines.append(f"  {sym}: {qty}股")
        else:
            lines.append("")
            lines.append("当前无持仓")
        
        elements = [self._text_element("\n".join(lines))]
        
        if risk_report:
            elements.append(self._divider())
            elements.append(self._text_element(f"```\n{risk_report}\n```"))
        
        payload = self._build_card("BDE-Stock 每日报告", elements, "blue")
        self._send(payload)
    
    # ================================================================
    # 因子报告
    # ================================================================
    
    def send_factor_report(self, table_text: str):
        """
        推送因子评分报告
        
        Args:
            table_text: 格式化的评分表格文本
        """
        if not self.config.enable_factor_report:
            return
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        elements = [
            self._text_element(
                f"**📈 因子评分报告** | {now}\n\n```\n{table_text}\n```"
            ),
        ]
        
        payload = self._build_card("BDE-Stock 因子报告", elements, "blue")
        self._send(payload)
    
    def send_text(self, text: str, title: str = "BDE-Stock"):
        """
        发送纯文本消息
        
        Args:
            text: 消息文本
            title: 标题
        """
        elements = [self._text_element(text)]
        payload = self._build_card(title, elements, "blue")
        self._send(payload)
