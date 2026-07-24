#!/usr/bin/env python3
"""
BDE Score 账户余额 & 业务报告 → 飞书群「BDE Score™ 专项团队」
每6小时定时推送：链上余额、API健康、业务指标、服务链接
"""

import json
import os
import subprocess
import sys
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ============================================================
# 配置
# ============================================================
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
STATE_FILE = SCRIPT_DIR / ".balance_state.json"
BJT = timezone(timedelta(hours=8))

BASE_RPC = "https://mainnet.base.org"

WALLETS = {
    "Deployer(正式)": {
        "address": "0x6c667Fc5c770bf7899b1843472f43C51b5c4Fecd",
        "short": "0x6c66...Fecd",
    },
    "x402收款": {
        "address": "0x349Eea0E2f4d3594797851758325Da3eb49D4343",
        "short": "0x349E...4343",
    },
}

# 目标飞书群：BDE Score™ 专项团队
FEISHU_CHAT_ID = "oc_8c9081046ededba2030a9c65e760c84b"


def query_chain_balances():
    """查询Base链上钱包余额"""
    from web3 import Web3
    w3 = Web3(Web3.HTTPProvider(BASE_RPC, request_kwargs={"timeout": 15}))
    chain_ok = w3.is_connected()
    block_num = None
    if chain_ok:
        block_num = w3.eth.block_number

    results = {}
    for name, info in WALLETS.items():
        try:
            addr = info["address"]
            bal_wei = w3.eth.get_balance(addr)
            tx = w3.eth.get_transaction_count(addr)
            results[name] = {
                "balance_eth": float(w3.from_wei(bal_wei, "ether")),
                "tx_count": tx,
                "short": info["short"],
            }
        except Exception as e:
            results[name] = {"error": str(e), "short": info["short"]}
    return chain_ok, block_num, results


def check_api_health():
    """检查API服务状态"""
    import urllib.request
    status = {}

    # ngrok MCP
    ngrok_url = "https://decorated-during-book.ngrok-free.dev/mcp"
    try:
        req = urllib.request.Request(ngrok_url, method="GET")
        resp = urllib.request.urlopen(req, timeout=10)
        status["ngrok_mcp"] = {"ok": True, "url": ngrok_url, "code": resp.status}
    except urllib.error.HTTPError as e:
        # 4xx means server is alive but no GET handler — still OK for MCP
        status["ngrok_mcp"] = {"ok": e.code < 500, "url": ngrok_url, "code": e.code}
    except Exception as e:
        status["ngrok_mcp"] = {"ok": False, "url": ngrok_url, "error": str(e)}

    return status


def get_business_metrics():
    """从本地数据库采集业务指标"""
    metrics = {}

    # 分析总次数 & 最新分析时间
    try:
        conn = sqlite3.connect(str(PROJECT_DIR / "bde_history.db"))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM analysis_history")
        metrics["total_analyses"] = cur.fetchone()[0]
        cur.execute("SELECT MAX(run_time) FROM analysis_history")
        metrics["latest_analysis"] = cur.fetchone()[0] or "N/A"
        cur.execute("SELECT COUNT(DISTINCT symbol) FROM analysis_history")
        metrics["unique_symbols"] = cur.fetchone()[0]
        conn.close()
    except Exception:
        metrics["total_analyses"] = 0
        metrics["latest_analysis"] = "N/A"
        metrics["unique_symbols"] = 0

    # API Key 数量
    try:
        with open(PROJECT_DIR / "api_keys.json") as f:
            keys = json.load(f)
        metrics["total_api_keys"] = len(keys)
        metrics["active_api_keys"] = sum(1 for k in keys if k.get("active"))
    except Exception:
        metrics["total_api_keys"] = 0
        metrics["active_api_keys"] = 0

    # USDC 支付
    try:
        conn = sqlite3.connect(str(PROJECT_DIR / "x402_payments.db"))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM x402_payments")
        metrics["usdc_payments"] = cur.fetchone()[0]
        # 累计收入 (amount字段如有)
        try:
            cur.execute("SELECT COALESCE(SUM(amount), 0) FROM x402_payments")
            metrics["cumulative_revenue_usdc"] = cur.fetchone()[0]
        except Exception:
            metrics["cumulative_revenue_usdc"] = 0
        conn.close()
    except Exception:
        metrics["usdc_payments"] = 0
        metrics["cumulative_revenue_usdc"] = 0

    # 用户 & 会话
    try:
        conn = sqlite3.connect(str(PROJECT_DIR / "users.db"))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        metrics["total_users"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM sessions_audit")
        metrics["total_sessions"] = cur.fetchone()[0]
        conn.close()
    except Exception:
        metrics["total_users"] = 0
        metrics["total_sessions"] = 0

    return metrics


def load_prev_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def detect_24h_changes(prev_state, current_balances):
    """对比上次状态，报告变动"""
    changes = []
    prev_bals = prev_state.get("balances", {})
    for name, curr in current_balances.items():
        if "error" in curr:
            continue
        prev = prev_bals.get(name, {})
        if "error" in prev or not prev:
            continue
        diff = curr["balance_eth"] - prev.get("balance_eth", 0)
        if abs(diff) > 1e-8:
            direction = "📈" if diff > 0 else "📉"
            changes.append({
                "name": name,
                "short": curr["short"],
                "prev": prev.get("balance_eth", 0),
                "curr": curr["balance_eth"],
                "diff": diff,
                "direction": direction,
            })
    return changes


def build_report(chain_ok, block_num, api_status, balances, metrics, changes):
    """构建飞书 Markdown 报告"""
    now_str = datetime.now(BJT).strftime("%Y-%m-%d %H:%M BJT")
    lines = [f"**📊 BDE Score™ 定时报告** | {now_str}\n"]

    # 1. 系统健康
    lines.append("**━━ 系统健康 ━━**")
    chain_emoji = "✅" if chain_ok else "❌"
    block_info = f" Block#{block_num}" if block_num else ""
    lines.append(f"Base链 {chain_emoji}{block_info}")

    for svc, info in api_status.items():
        emoji = "✅" if info.get("ok") else "❌"
        code = info.get("code", info.get("error", ""))
        lines.append(f"{svc} {emoji} (HTTP {code})")
    lines.append("")

    # 2. 业务指标
    lines.append("**━━ 业务指标 ━━**")
    lines.append(f"分析总次数: {metrics['total_analyses']} | 覆盖 {metrics['unique_symbols']} 只标的")
    lines.append(f"最新分析: {metrics['latest_analysis']}")
    lines.append(f"API Key: {metrics['active_api_keys']}/{metrics['total_api_keys']} 活跃")
    lines.append(f"USDC支付: {metrics['usdc_payments']} 笔 | 累计收入: ${metrics['cumulative_revenue_usdc']}")
    lines.append(f"注册用户: {metrics['total_users']} | 会话: {metrics['total_sessions']}")
    lines.append("")

    # 3. 链上余额
    lines.append("**━━ 链上余额 (Base) ━━**")
    total_eth = 0
    for name, info in balances.items():
        if "error" in info:
            lines.append(f"{name} `{info['short']}` ❌ 查询失败")
            continue
        bal = info["balance_eth"]
        tx = info["tx_count"]
        total_eth += bal
        lines.append(f"{name} `{info['short']}`")
        lines.append(f"  {bal:.8f} ETH | TX:{tx}")
    lines.append(f"**合计**: {total_eth:.8f} ETH")
    lines.append("")

    # 4. 近24h变动
    lines.append("**━━ 近24h变动 ━━**")
    if changes:
        for c in changes:
            lines.append(f"{c['direction']} {c['name']} `{c['short']}`: {abs(c['diff']):.8f} ETH")
            lines.append(f"  {c['prev']:.8f} → {c['curr']:.8f}")
    else:
        lines.append("无变动")
    lines.append("")

    # 5. 服务链接
    lines.append("**━━ 服务链接 ━━**")
    lines.append("MCP(ngrok): https://decorated-during-book.ngrok-free.dev/mcp")
    lines.append("Landing: https://hbhqq9.github.io/bde-score/")
    lines.append("GitHub: https://github.com/hbhqq9/bde-score")

    return "\n".join(lines)


def send_feishu(markdown_text, title="BDE Score™ 定时报告"):
    """通过 lark-cli 推送到飞书群
    
    注意：目标群「BDE Score™ 专项团队」bot未加入，需用user身份发送。
    lark-cli 必须在 /app/data/所有对话/主对话 目录下执行（user凭证在此）。
    """
    # lark-cli user 凭证在主对话目录
    work_dir = str(PROJECT_DIR.parent)
    try:
        cmd = [
            "lark-cli", "im", "+messages-send",
            "--chat-id", FEISHU_CHAT_ID,
            "--markdown", markdown_text,
            "--as", "user",
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            cwd=work_dir,
        )
        if result.returncode == 0:
            print(f"[OK] 飞书推送成功: {title}")
            return True
        else:
            # fallback: 尝试 bot 身份（如果以后 bot 加入了群）
            cmd_bot = [
                "lark-cli", "im", "+messages-send",
                "--chat-id", FEISHU_CHAT_ID,
                "--markdown", markdown_text,
                "--as", "bot",
            ]
            result2 = subprocess.run(
                cmd_bot, capture_output=True, text=True, timeout=30,
                cwd=work_dir,
            )
            if result2.returncode == 0:
                print(f"[OK] 飞书推送成功(bot fallback): {title}")
                return True
            print(f"[WARN] 飞书推送失败")
            print(f"  user stderr: {result.stderr[:200]}")
            print(f"  bot stderr: {result2.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print("[WARN] 飞书推送超时")
        return False
    except FileNotFoundError:
        print("[WARN] lark-cli 未安装")
        return False


def save_state(balances):
    """更新状态文件"""
    state = {
        "last_check": datetime.now(BJT).isoformat(),
        "last_full_report": datetime.now(BJT).isoformat(),
        "balances": {
            name: {
                **WALLETS[name],
                "balance_eth": info.get("balance_eth", 0),
                "tx_count": info.get("tx_count", 0),
                "queried_at": datetime.now(BJT).isoformat(),
            }
            for name, info in balances.items()
            if "error" not in info
        },
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def main():
    print(f"[{datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S BJT')}] BDE Score 定时报告开始")

    # 1. 链上余额
    try:
        chain_ok, block_num, balances = query_chain_balances()
        print(f"  链连接: {'OK' if chain_ok else 'FAIL'} Block#{block_num}")
    except Exception as e:
        print(f"  链查询异常: {e}")
        chain_ok, block_num, balances = False, None, {n: {"error": str(e), "short": i["short"]} for n, i in WALLETS.items()}

    # 2. API 健康
    api_status = check_api_health()
    for svc, info in api_status.items():
        print(f"  API {svc}: {'OK' if info.get('ok') else 'FAIL'} (HTTP {info.get('code', '?')})")

    # 3. 业务指标
    metrics = get_business_metrics()
    print(f"  分析次数: {metrics['total_analyses']}, Keys: {metrics['active_api_keys']}/{metrics['total_api_keys']}")

    # 4. 变动检测
    prev_state = load_prev_state()
    changes = detect_24h_changes(prev_state, balances)
    if changes:
        print(f"  检测到 {len(changes)} 个账户余额变动")
    else:
        print("  无余额变动")

    # 5. 构建报告
    report = build_report(chain_ok, block_num, api_status, balances, metrics, changes)

    # 6. 保存本地存档
    reports_dir = PROJECT_DIR / "reports"
    reports_dir.mkdir(exist_ok=True)
    now_tag = datetime.now(BJT).strftime("%Y%m%d_%H%M")
    with open(reports_dir / f"balance_report_{now_tag}.md", "w") as f:
        f.write(f"# BDE Score™ 定时报告\n\n{report}")

    # 7. 推送飞书
    ok = send_feishu(report)

    # 8. 更新状态
    save_state(balances)

    print(f"[{'OK' if ok else 'WARN'}] 报告推送{'成功' if ok else '失败'}")
    return ok


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
