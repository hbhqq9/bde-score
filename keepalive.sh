#!/bin/bash
# BDE Score Keepalive Script
# Monitors all 8 service processes and restarts if needed

SERVICES=(
    "bde_api:python3 -m uvicorn bde_api:app --host 127.0.0.1 --port 8890"
    "mcp_http_server:python3 mcp/mcp_http_server.py"
    "registry_server:python3 agent-registry/registry_server.py"
    "websub_hub:python3 websub_hub.py"
    "tunnel_api:cloudflared tunnel --url http://localhost:8890"
    "tunnel_mcp:cloudflared tunnel --url http://localhost:8891"
    "tunnel_registry:cloudflared tunnel --url http://localhost:8892"
)

LOG="/tmp/keepalive_bde.log"

while true; do
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    for svc in "${SERVICES[@]}"; do
        NAME="${svc%%:*}"
        CMD="${svc#*:}"
        
        # Check if process is running
        if ! pgrep -f "$CMD" > /dev/null 2>&1; then
            echo "$TIMESTAMP [RESTART] $NAME" >> "$LOG"
            
            case "$NAME" in
                bde_api)
                    cd /app/data/所有对话/主对话/BDE-Stock
                    nohup python3 -m uvicorn bde_api:app --host 127.0.0.1 --port 8890 > /tmp/bde_api.log 2>&1 &
                    ;;
                mcp_http_server)
                    cd /app/data/所有对话/主对话/BDE-Stock
                    nohup python3 mcp/mcp_http_server.py > /tmp/mcp_server.log 2>&1 &
                    ;;
                registry_server)
                    cd /app/data/所有对话/主对话/BDE-Stock
                    nohup python3 agent-registry/registry_server.py > /tmp/registry_server.log 2>&1 &
                    ;;
                websub_hub)
                    cd /app/data/所有对话/主对话/BDE-Stock
                    nohup python3 websub_hub.py > /tmp/websub_hub.log 2>&1 &
                    ;;
                tunnel_api)
                    nohup cloudflared tunnel --url http://localhost:8890 > /tmp/tunnel_api.log 2>&1 &
                    ;;
                tunnel_mcp)
                    nohup cloudflared tunnel --url http://localhost:8891 > /tmp/tunnel_mcp.log 2>&1 &
                    ;;
                tunnel_registry)
                    nohup cloudflared tunnel --url http://localhost:8892 > /tmp/tunnel_registry.log 2>&1 &
                    ;;
            esac
        fi
    done
    
    sleep 60
done
