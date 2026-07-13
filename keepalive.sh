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

# 4. MCP HTTP Server (Remote MCP endpoint - port 8891)
check_and_restart "MCP-HTTP-Server" "mcp_http_server.py" \
    "cd $BDE_DIR && nohup python3 mcp/mcp_http_server.py > /tmp/mcp_http.log 2>&1 &"

# 5. MCP Cloudflare Tunnel (separate tunnel for MCP server on port 8891)
MCP_TUNNEL_COUNT=$(pgrep -f "cloudflared.*8891" | wc -l)
if [ "$MCP_TUNNEL_COUNT" -eq 0 ]; then
    echo "[$(date)] MCP-Tunnel stopped, restarting..." >> "$LOG"
    nohup cloudflared tunnel --url http://localhost:8891 > /tmp/mcp_tunnel.log 2>&1 &
    sleep 3
    if pgrep -f "cloudflared.*8891" > /dev/null 2>&1; then
        NEW_URL=$(grep -o "https://[^ ]*trycloudflare.com" /tmp/mcp_tunnel.log | tail -1)
        echo "[$(date)] MCP-Tunnel restarted: $NEW_URL" >> "$LOG"
    else
        echo "[$(date)] MCP-Tunnel restart FAILED" >> "$LOG"
    fi
fi

# 6. Agent Registry v0.2.0 (port 8892 - agent-native discovery)
check_and_restart "Agent-Registry" "registry_server.py" \
    "cd $BDE_DIR && nohup python3 agent-registry/registry_server.py > /tmp/registry_server.log 2>&1 &"

echo "[$(date)] 守护检查完成 (FutuOpenD: $(pgrep -c -f FutuOpenD)进程, BDE-API: $(pgrep -c -f bde_api.py)进程, CF-Tunnel: $(pgrep -c -f cloudflared)进程)" >> "$LOG"
