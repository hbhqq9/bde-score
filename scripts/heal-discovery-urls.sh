#!/bin/bash
# BDE Score 自愈型发现栈 URL 修复脚本 v1.0
set -e
REPO_DIR="/app/data/所有对话/主对话/BDE-Stock"
cd "$REPO_DIR"

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[$TIMESTAMP] Checking tunnel health..."

API_URL=""
MCP_URL=""

# 探测已知URL（含历史URL + 自动从cloudflared日志发现新URL）
KNOWN_API_URLS=(
    "https://refresh-bringing-goat-buildings.trycloudflare.com"
    "https://producers-zum-brochures-elvis.trycloudflare.com"
    "https://bathroom-ebooks-isa-accommodation.trycloudflare.com"
)

# 先从cloudflared日志自动发现新URL
AUTO_API_URL=$(grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' /tmp/tunnel_api.log 2>/dev/null | tail -1)
if [ -n "$AUTO_API_URL" ]; then
    KNOWN_API_URLS=("$AUTO_API_URL" "${KNOWN_API_URLS[@]}")
fi

for url in "${KNOWN_API_URLS[@]}"; do
    STATUS=$(curl -s --max-time 5 -o /dev/null -w "%{http_code}" "$url/api/health" 2>/dev/null)
    if [ "$STATUS" = "200" ]; then
        API_URL="$url"
        echo "  API: $url ✅"
        break
    fi
done

KNOWN_MCP_URLS=(
    "https://tex-adequate-date-facing.trycloudflare.com"
)

# 从MCP cloudflared日志自动发现
AUTO_MCP_URL=$(grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' /var/log/cloudflared-mcp.log 2>/dev/null | tail -1)
if [ -n "$AUTO_MCP_URL" ]; then
    KNOWN_MCP_URLS=("$AUTO_MCP_URL" "${KNOWN_MCP_URLS[@]}")
fi

for url in "${KNOWN_MCP_URLS[@]}"; do
    STATUS=$(curl -s --max-time 5 -o /dev/null -w "%{http_code}" "$url/mcp" 2>/dev/null)
    if [ "$STATUS" = "401" ]; then
        MCP_URL="$url"
        echo "  MCP: $url ✅"
        break
    fi
done

if [ -z "$API_URL" ] || [ -z "$MCP_URL" ]; then
    echo "  ❌ Tunnel URLs not reachable. Checking cloudflared..."
    pgrep -x cloudflared > /dev/null && echo "  Process running but URLs stale — tunnel may have restarted" || echo "  Process NOT running"
    exit 1
fi

# 比较当前mcp.json
CURRENT=$(python3 -c "import json; print(json.load(open('docs/.well-known/mcp.json'))['transport']['url'].split('/mcp')[0])" 2>/dev/null)

if [ "$CURRENT" = "$MCP_URL" ]; then
    echo "  Discovery files up-to-date ✅"
    exit 0
fi

echo "  🔧 URL changed: $CURRENT → $MCP_URL"

python3 -c "
import json
mcp = json.load(open('docs/.well-known/mcp.json'))
mcp['transport']['url'] = '${MCP_URL}/mcp'
mcp['metadata']['last_verified'] = '${TIMESTAMP}'
json.dump(mcp, open('docs/.well-known/mcp.json','w'), indent=2, ensure_ascii=False)

agent = json.load(open('docs/.well-known/agent.json'))
agent['endpoints']['api'] = '${API_URL}'
agent['endpoints']['mcp'] = '${MCP_URL}/mcp'
agent['endpoints']['compliance_check'] = '${API_URL}/compliance-check'
agent['endpoints']['x402_pay_info'] = '${API_URL}/pay/info'
agent['last_verified'] = '${TIMESTAMP}'
json.dump(agent, open('docs/.well-known/agent.json','w'), indent=2, ensure_ascii=False)
print('  ✅ Files healed')
"

cd "$REPO_DIR"
git add docs/.well-known/mcp.json docs/.well-known/agent.json
git commit -m "🔧 auto-heal: discovery URLs updated ($TIMESTAMP)" 2>/dev/null && \
git push origin master 2>/dev/null && echo "  ✅ Pushed" || echo "  ⚠️ Push failed"
