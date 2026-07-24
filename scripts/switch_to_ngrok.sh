#!/bin/bash
# Switch MCP from Cloudflare Quick Tunnel to ngrok permanent domain
set -euo pipefail

echo "=== Switching MCP to ngrok permanent domain ==="

# 1. Find and kill Cloudflare tunnel for port 8891 (MCP)
echo "1. Finding Cloudflare tunnel for MCP (port 8891)..."
for pid in $(pgrep -f 'cloudflared tunnel' 2>/dev/null); do
    cmdline=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ')
    if echo "$cmdline" | grep -q '8891'; then
        echo "   Killing Cloudflare MCP tunnel PID $pid: $cmdline"
        kill $pid 2>/dev/null || true
    fi
done

# 2. Start ngrok tunnel for MCP
echo "2. Starting ngrok tunnel for MCP..."
nohup ngrok http 8891 --domain=decorated-during-book.ngrok-free.dev > /tmp/ngrok_mcp.log 2>&1 &
NGROK_PID=$!
echo "   ngrok MCP tunnel started (PID: $NGROK_PID)"

# 3. Wait for ngrok to connect
sleep 5
echo "3. Verifying ngrok tunnel..."
curl -s -o /dev/null -w "HTTP %{http_code}" --max-time 10 \
    -X POST "https://decorated-during-book.ngrok-free.dev/mcp" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"health","version":"1.0"}}}' && echo " ✅ ngrok MCP healthy" || echo " ⚠️ ngrok MCP not ready yet"

echo ""
echo "=== Tunnel switch complete ==="
echo "MCP URL: https://decorated-during-book.ngrok-free.dev/mcp (PERMANENT)"
echo "API URL: https://enjoying-wide-boat-stan.trycloudflare.com (Cloudflare, may drift)"
echo "Landing: https://logged-completely-pumps-consolidation.trycloudflare.com (Cloudflare, may drift)"
