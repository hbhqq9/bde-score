#!/bin/bash
# BDE Score™ 进程守护脚本 v2.0
# 每5分钟检查一次，确保所有关键服务持续运行

LOG="/app/data/所有对话/主对话/BDE-Stock/keepalive.log"
BDE_DIR="/app/data/所有对话/主对话/BDE-Stock"
FUTU_DIR="/root/futu/opend/Futu_OpenD_10.8.6818_Ubuntu18.04/Futu_OpenD_10.8.6818_Ubuntu18.04"

check_and_restart() {
    local name=$1
    local pattern=$2
    local restart_cmd=$3
    
    if ! pgrep -f "$pattern" > /dev/null 2>&1; then
        echo "[$(date)] ⚠️ $name 已停止，正在重启..." >> "$LOG"
        eval "$restart_cmd"
        sleep 3
        if pgrep -f "$pattern" > /dev/null 2>&1; then
            echo "[$(date)] ✅ $name 重启成功" >> "$LOG"
        else
            echo "[$(date)] ❌ $name 重启失败！" >> "$LOG"
        fi
    fi
}

# 1. FutuOpenD (港股数据源 - 关键!)
check_and_restart "FutuOpenD" "FutuOpenD" \
    "cd $FUTU_DIR && export LD_LIBRARY_PATH=\$LD_LIBRARY_PATH:$FUTU_DIR && nohup ./FutuOpenD > /tmp/futuopd.log 2>&1 &"

# 2. BDE API
check_and_restart "BDE-API" "bde_api.py" \
    "cd $BDE_DIR && nohup python3 bde_api.py > /tmp/bde_api.log 2>&1 &"

# 3. Cloudflare Tunnel (公网入口 - 关键!)
check_and_restart "Cloudflare-Tunnel" "cloudflared" \
    "nohup cloudflared tunnel --url http://127.0.0.1:8890 > /tmp/cloudflared.log 2>&1 &"

echo "[$(date)] 守护检查完成 (FutuOpenD: $(pgrep -c -f FutuOpenD)进程, BDE-API: $(pgrep -c -f bde_api.py)进程, CF-Tunnel: $(pgrep -c -f cloudflared)进程)" >> "$LOG"
