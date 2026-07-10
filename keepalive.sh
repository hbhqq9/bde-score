#!/bin/bash
# BDE Score™ 进程守护脚本
# 每5分钟检查一次，确保API服务+bore隧道+FutuOpenD持续运行

LOG="/app/data/所有对话/主对话/BDE-Stock/keepalive.log"
BDE_DIR="/app/data/所有对话/主对话/BDE-Stock"

check_and_restart() {
    local name=$1
    local pattern=$2
    local restart_cmd=$3
    
    if ! pgrep -f "$pattern" > /dev/null 2>&1; then
        echo "[$(date)] $name 已停止，正在重启..." >> "$LOG"
        eval "$restart_cmd"
        sleep 2
        if pgrep -f "$pattern" > /dev/null 2>&1; then
            echo "[$(date)] $name 重启成功" >> "$LOG"
        else
            echo "[$(date)] $name 重启失败！" >> "$LOG"
        fi
    fi
}

# 检查FutuOpenD
check_and_restart "FutuOpenD" "FutuOpenD" "cd ~/futu/opend && nohup ./FutuOpenD > /dev/null 2>&1 &"

# 检查BDE API
check_and_restart "BDE-API" "bde_api.py" "cd $BDE_DIR && nohup python3 bde_api.py > /tmp/bde_api.log 2>&1 &"

# 检查bore隧道
check_and_restart "Bore-Tunnel" "bore local" "nohup bore local 8890 --to bore.pub > /tmp/bore.log 2>&1 &"

echo "[$(date)] 守护检查完成" >> "$LOG"
