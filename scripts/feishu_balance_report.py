#!/usr/bin/env python3
"""
BDE Score™ 账户余额与变动报告 - 飞书推送脚本
定期采集账户数据并推送到飞书群
"""

import sqlite3
import json
import subprocess
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
BDE_STOCK_DIR = Path(__file__).parent.parent
DB_PATH = BDE_STOCK_DIR / "bde_history.db"
PAYMENTS_DB = BDE_STOCK_DIR / "x402_payments.db"
FEISHU_CHAT_ID = "oc_8c9081046ededba2030a9c65e760c84b"  # BDE Score™ 专项团队
API_BASE = "http://localhost:8890"
LARK_CLI_DIR = Path(os.path.expanduser("~")) / ".." / "app" / "data" / "所有对话" / "主对话"


def get_db_data():
    """从SQLite获取账户数据"""
    data = {
        "analysis_history_count": 0,
        "user_credits_count": 0,
        "credit_ledger_recent": [],
        "payments_count": 0,
        "free_usage_count": 0,
        "total_revenue_usdc": 0.0,
    }

    # bde_history.db
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")

        cursor = conn.execute("SELECT COUNT(*) FROM analysis_history")
        data["analysis_history_count"] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM user_credits")
        data["user_credits_count"] = cursor.fetchone()[0]

        # 最近24h的credit变动
        since = (datetime.now() - timedelta(hours=24)).isoformat()
        cursor = conn.execute(
            "SELECT key_hash, amount, reason, created_at FROM credit_ledger "
            "WHERE created_at > ? ORDER BY created_at DESC LIMIT 10",
            (since,)
        )
        data["credit_ledger_recent"] = [
            {"key": r[0][:8] + "...", "amount": r[1], "reason": r[2], "time": r[3]}
            for r in cursor.fetchall()
        ]

        conn.close()
    except Exception as e:
        data["db_error"] = str(e)

    # x402_payments.db
    try:
        conn = sqlite3.connect(str(PAYMENTS_DB), timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")

        cursor = conn.execute("SELECT COUNT(*) FROM x402_payments")
        data["payments_count"] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM x402_free_usage")
        data["free_usage_count"] = cursor.fetchone()[0]

        # 总收入
        cursor = conn.execute("SELECT COALESCE(SUM(amount_usdc), 0) FROM x402_payments")
        data["total_revenue_usdc"] = cursor.fetchone()[0]

        conn.close()
    except Exception as e:
        data["payments_db_error"] = str(e)

    return data


def get_onchain_data():
    """获取链上数据"""
    try:
        result = subprocess.run(
            ["curl", "-s", f"{API_BASE}/api/payment/chain-status"],
            capture_output=True, text=True, timeout=10
        )
        return json.loads(result.stdout)
    except Exception as e:
        return {"error": str(e)}


def get_api_status():
    """检查API健康状态"""
    try:
        result = subprocess.run(
            ["curl", "-s", f"{API_BASE}/api/health"],
            capture_output=True, text=True, timeout=10
        )
        return json.loads(result.stdout)
    except Exception as e:
        return {"error": str(e)}


def format_report(data, onchain, health):
    """生成报告文本"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    lines = [
        f"📊 **BDE Score™ 账户报告** | {now}",
        "",
        "**━━━ 系统状态 ━━━**",
        f"API: {'✅ 正常' if health.get('status') == 'healthy' else '❌ 异常'}",
        f"链连接: {'✅ Base链' if onchain.get('connected') else '❌ 未连接'}",
        f"钱包: `{onchain.get('wallet', 'N/A')[:12]}...`",
        "",
        "**━━━ 业务数据 ━━━**",
        f"📈 分析总次数: **{data['analysis_history_count']}**",
        f"🔑 已注册API Key: **{data['user_credits_count']}**",
        f"💰 USDC支付笔数: **{data['payments_count']}**",
        f"🎁 免费使用次数: **{data['free_usage_count']}**",
        f"💵 累计收入: **${data['total_revenue_usdc']:.4f} USDC**",
        "",
    ]

    if data["credit_ledger_recent"]:
        lines.append("**━━━ 近24h变动 ━━━**")
        for entry in data["credit_ledger_recent"]:
            lines.append(f"• {entry['key']} | {entry['amount']:+} | {entry['reason']} | {entry['time'][:16]}")
        lines.append("")

    lines.extend([
        "**━━━ 服务链接 ━━━**",
        "🌐 [主页](https://bathroom-ebooks-isa-accommodation.trycloudflare.com/)",
        "🤖 [MCP](https://tex-adequate-date-facing.trycloudflare.com/mcp)",
        "✅ [合规](https://bathroom-ebooks-isa-accommodation.trycloudflare.com/compliance)",
    ])

    return "\n".join(lines)


def send_to_feishu(message):
    """发送到飞书群"""
    lark_cli_path = "/usr/bin/lark-cli"
    feishu_cli_dir = "/app/data/所有对话/主对话"
    
    # Use markdown format for rich text
    content = json.dumps({"text": message})
    
    cmd = [
        lark_cli_path, "im", "+messages-send",
        "--chat-id", FEISHU_CHAT_ID,
        "--text", message,
        "--as", "bot"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=feishu_cli_dir)
    
    if result.returncode != 0:
        # Try user mode
        cmd[-1] = "user"
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=feishu_cli_dir)
    
    return result.returncode == 0, result.stdout + result.stderr


def main():
    print("📊 采集数据...")
    data = get_db_data()
    onchain = get_onchain_data()
    health = get_api_status()
    
    print("📝 生成报告...")
    report = format_report(data, onchain, health)
    
    print("📤 推送到飞书...")
    success, output = send_to_feishu(report)
    
    if success:
        print("✅ 推送成功")
    else:
        print(f"❌ 推送失败: {output}")
    
    # Save report to file for reference
    report_file = BDE_STOCK_DIR / "reports" / f"balance_report_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    report_file.parent.mkdir(exist_ok=True)
    report_file.write_text(report)
    print(f"📄 报告已保存: {report_file}")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
