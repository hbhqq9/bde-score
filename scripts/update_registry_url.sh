#!/bin/bash
# Auto-update MCP Registry when tunnel URL changes
# Triggered by keepalive.sh after MCP tunnel restart
# Requires: MCP_GITHUB_TOKEN env var or ~/.config/mcp-publisher/ token
SERVER_JSON="/app/data/所有对话/主对话/BDE-Stock/server.json"
MCP_PUBLISHER="/tmp/mcp-bin/mcp-publisher"
LOG_FILE="/app/data/所有对话/主对话/BDE-Stock/logs/registry_update.log"
TUNNEL_LOG="/tmp/tunnel_mcp.log"
mkdir -p "$(dirname "$LOG_FILE")"

# Detect current tunnel URL
if [ -f "$TUNNEL_LOG" ]; then
    CURRENT_HOST=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$TUNNEL_LOG" | tail -1 | sed 's|https://||')
fi
if [ -z "$CURRENT_HOST" ]; then
    MCP_PID=$(pgrep -f "cloudflared.*8891" | head -1)
    [ -n "$MCP_PID" ] && CURRENT_HOST=$(strings /proc/$MCP_PID/fd/1 2>/dev/null | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' | tail -1 | sed 's|https://||')
fi
[ -z "$CURRENT_HOST" ] && { echo "$(date -Iseconds) ERROR: Cannot detect tunnel URL" >> "$LOG_FILE"; exit 1; }

MCP_URL="https://${CURRENT_HOST}/mcp"
REGISTERED_URL=$(python3 -c "
import json
with open('$SERVER_JSON') as f:
    data = json.load(f)
remotes = data.get('remotes', [])
print(remotes[0].get('url', '') if remotes else '')
" 2>/dev/null)

[ "$MCP_URL" = "$REGISTERED_URL" ] && { echo "$(date -Iseconds) OK: unchanged" >> "$LOG_FILE"; exit 0; }

echo "$(date -Iseconds) CHANGED: $REGISTERED_URL -> $MCP_URL" >> "$LOG_FILE"
python3 << PYEOF
import json
with open("$SERVER_JSON") as f:
    data = json.load(f)
v = data.get("version", "1.0.0").split(".")
v[-1] = str(int(v[-1]) + 1)
data["version"] = ".".join(v)
if data.get("remotes"):
    data["remotes"][0]["url"] = "$MCP_URL"
with open("$SERVER_JSON", "w") as f:
    json.dump(data, f, indent=2)
PYEOF

$MCP_PUBLISHER login github >> "$LOG_FILE" 2>&1
$MCP_PUBLISHER publish "$SERVER_JSON" >> "$LOG_FILE" 2>&1
echo "$(date -Iseconds) Published" >> "$LOG_FILE"
