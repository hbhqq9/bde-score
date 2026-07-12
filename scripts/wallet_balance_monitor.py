#!/usr/bin/env python3
"""
BDE Score 账户余额监控 + 飞书群推送
监控 Base 链上 ETH 余额变动，有变化时推送到飞书群
"""

import json
import subprocess
import os
import sys
from datetime import datetime, timezone, timedelta

# === 配置 ===
ADDRESSES = {
    "Deployer(正式)": "0x6c667Fc5c770bf7899b1843472f43C51b5c4Fecd",
    "x402收款": "0x349Eea0E2f4d3594797851758325Da3eb49D4343",
}

STATE_FILE = "/app/data/所有对话/主对话/BDE-Stock/scripts/.balance_state.json"
FEISHU_CHAT_ID = "oc_e76aeb49eb5d48bc840d3a558c83bed4"  # BDE Score Agent 群
RPC_URL = "https://mainnet.base.org"
BJT = timezone(timedelta(hours=8))


def get_balance(address: str) -> float:
    """通过 Base RPC 查询 ETH 余额"""
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "10", "-X", "POST", RPC_URL,
             "-H", "Content-Type: application/json",
             "-d", json.dumps({
                 "jsonrpc": "2.0",
                 "method": "eth_getBalance",
                 "params": [address, "latest"],
                 "id": 1
             })],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(result.stdout)
        wei = int(data["result"], 16)
        return wei / 1e18
    except Exception as e:
        print(f"  [ERROR] 查询失败 {address}: {e}", file=sys.stderr)
        return -1.0


def get_tx_count(address: str) -> int:
    """查询交易次数（nonce）"""
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "10", "-X", "POST", RPC_URL,
             "-H", "Content-Type: application/json",
             "-d", json.dumps({
                 "jsonrpc": "2.0",
                 "method": "eth_getTransactionCount",
                 "params": [address, "latest"],
                 "id": 1
             })],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(result.stdout)
        return int(data["result"], 16)
    except:
        return -1


def load_state() -> dict:
    """加载上次余额状态"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    """保存当前余额状态"""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def send_feishu(message: str):
    """通过 lark-cli 发送消息到飞书群"""
    try:
        result = subprocess.run(
            ["lark-cli", "im", "+messages-send",
             "--chat-id", FEISHU_CHAT_ID,
             "--text", message,
             "--as", "bot"],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout + result.stderr
        # Check for success
        if '"ok":true' in output.replace(' ', '').replace('"ok": true', '"ok":true') or '"ok": true' in output:
            print("  [OK] 飞书消息发送成功")
            return True
        else:
            print(f"  [WARN] 飞书发送结果: {output[:200]}", file=sys.stderr)
            return True  # Don't fail on feishu errors, just warn
    except Exception as e:
        print(f"  [ERROR] 飞书发送失败: {e}", file=sys.stderr)
        return False


def main():
    now = datetime.now(BJT)
    print(f"=== BDE Score 账户余额监控 ({now.strftime('%Y-%m-%d %H:%M BJT')}) ===")

    # 加载历史状态
    old_state = load_state()
    new_state = {}
    changes = []

    # 查询每个账户
    for name, addr in ADDRESSES.items():
        print(f"\n查询 {name} ({addr[:8]}...{addr[-4:]})...")
        balance = get_balance(addr)
        tx_count = get_tx_count(addr)

        if balance < 0:
            print(f"  [SKIP] 查询失败，跳过")
            continue

        old_balance = old_state.get(addr, {}).get("balance", None)
        old_tx = old_state.get(addr, {}).get("tx_count", None)

        new_state[addr] = {
            "name": name,
            "balance": balance,
            "tx_count": tx_count,
            "last_check": now.isoformat()
        }

        print(f"  余额: {balance:.6f} ETH")
        print(f"  交易数: {tx_count}")

        # 检测变动
        if old_balance is not None:
            delta = balance - old_balance
            if abs(delta) > 0.000001:  # 忽略极小精度误差
                direction = "📈 增加" if delta > 0 else "📉 减少"
                changes.append({
                    "name": name,
                    "addr_short": f"{addr[:6]}...{addr[-4:]}",
                    "old": old_balance,
                    "new": balance,
                    "delta": delta,
                    "direction": direction,
                    "old_tx": old_tx,
                    "new_tx": tx_count
                })
                print(f"  ⚡ 变动: {direction} {abs(delta):.6f} ETH")
            else:
                print(f"  [OK] 无变动")
        else:
            print(f"  [INIT] 首次记录基线")

    # 保存新状态
    save_state(new_state)

    # 构建飞书消息
    if changes:
        lines = [f"🔔 BDE Score 账户变动报告", f"⏰ {now.strftime('%Y-%m-%d %H:%M')} BJT", ""]
        for c in changes:
            lines.append(f"{c['direction']} {c['name']}")
            lines.append(f"  {c['old']:.6f} → {c['new']:.6f} ETH")
            lines.append(f"  变动: {'+' if c['delta']>0 else ''}{c['delta']:.6f} ETH")
            if c['old_tx'] is not None and c['new_tx'] != c['old_tx']:
                lines.append(f"  交易数: {c['old_tx']} → {c['new_tx']}")
            lines.append("")
        lines.append("💰 当前总余额: {:.6f} ETH".format(sum(s["balance"] for s in new_state.values())))
        message = "\n".join(lines)
    else:
        # 无变动时，每6小时发一次全量报告
        last_report = old_state.get("_last_full_report", "")
        hours_since = 999
        if last_report:
            try:
                last_dt = datetime.fromisoformat(last_report)
                hours_since = (now - last_dt).total_seconds() / 3600
            except:
                pass

        if hours_since >= 6 or not last_report:
            lines = [f"💰 BDE Score 账户余额报告", f"⏰ {now.strftime('%Y-%m-%d %H:%M')} BJT", ""]
            total = 0
            for addr, s in new_state.items():
                if addr.startswith("_"):
                    continue
                lines.append(f"{'🟢' if s['balance'] > 0 else '⚪'} {s['name']}: {s['balance']:.6f} ETH (TX:{s['tx_count']})")
                total += s['balance']
            lines.append(f"\n💎 总余额: {total:.6f} ETH")
            lines.append("✅ 无变动" if not changes else "")
            message = "\n".join(lines)
            new_state["_last_full_report"] = now.isoformat()
            save_state(new_state)
        else:
            print(f"\n[INFO] 无变动，距上次全量报告{hours_since:.1f}h（<6h），不推送")
            return

    # 发送到飞书
    print(f"\n发送到飞书群...")
    print(f"消息内容:\n{message}")
    send_feishu(message)
    print("\n完成！")


if __name__ == "__main__":
    main()
