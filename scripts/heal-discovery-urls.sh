#!/bin/bash
# BDE Score 自愈型发现栈 URL 修复脚本 v2.1
# v2.1: 只更新live文件，不碰历史文档；不逐一测试旧URL
set -e
REPO_DIR="/app/data/所有对话/主对话/BDE-Stock"
cd "$REPO_DIR"

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[$TIMESTAMP] Checking tunnel health..."

API_URL=""
MCP_URL=""

# === 1. 探测 API Tunnel ===
KNOWN_API_URLS=(
    "https://thinks-discussions-proof-dec.trycloudflare.com"
    "https://bathroom-ebooks-isa-accommodation.trycloudflare.com"
    "https://size-jackson-jesse-celebrity.trycloudflare.com"
    "https://study-comprehensive-jvc-mia.trycloudflare.com"
)

AUTO_API_URL=$(grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' /tmp/tunnel_api.log 2>/dev/null | tail -1)
if [ -n "$AUTO_API_URL" ]; then
    KNOWN_API_URLS=("$AUTO_API_URL" "${KNOWN_API_URLS[@]}")
fi

for url in "${KNOWN_API_URLS[@]}"; do
    STATUS=$(curl -s --max-time 5 -o /dev/null -w "%{http_code}" "$url/api/health" 2>/dev/null)
    if [ "$STATUS" = "200" ]; then
        API_URL="$url"
        API_HOST="${url#https://}"
        echo "  API: $url ✅"
        break
    fi
done

# === 2. 探测 MCP Tunnel ===
KNOWN_MCP_URLS=(
    "https://generators-computation-picked-emily.trycloudflare.com"
    "https://tex-adequate-date-facing.trycloudflare.com"
)

AUTO_MCP_URL=$(grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' /var/log/cloudflared-mcp.log 2>/dev/null | tail -1)
if [ -n "$AUTO_MCP_URL" ]; then
    KNOWN_MCP_URLS=("$AUTO_MCP_URL" "${KNOWN_MCP_URLS[@]}")
fi

for url in "${KNOWN_MCP_URLS[@]}"; do
    STATUS=$(curl -s --max-time 5 -o /dev/null -w "%{http_code}" "$url/mcp" 2>/dev/null)
    if [ "$STATUS" = "401" ]; then
        MCP_URL="$url"
        MCP_HOST="${url#https://}"
        echo "  MCP: $url ✅"
        break
    fi
done

if [ -z "$API_URL" ] || [ -z "$MCP_URL" ]; then
    echo "  ❌ Tunnel URLs not reachable."
    pgrep -x cloudflared > /dev/null && echo "  Process running but URLs stale" || echo "  Process NOT running"
    exit 1
fi

# === 3. 比较当前mcp.json是否需要更新 ===
CURRENT=$(python3 -c "import json; print(json.load(open('docs/.well-known/mcp.json'))['transport']['url'].split('/mcp')[0])" 2>/dev/null)

if [ "$CURRENT" = "$MCP_URL" ]; then
    # Even if mcp.json is current, check if README has the current API URL
    if grep -q "$API_HOST" README.md 2>/dev/null; then
        echo "  All URLs up-to-date ✅"
        exit 0
    fi
    echo "  ⚠️ mcp.json OK but README may have stale API URL"
fi

echo "  🔧 Updating files..."

# === 4. 更新 .well-known files ===
python3 << PYEOF
import json

api_url = "$API_URL"
mcp_url = "$MCP_URL"
timestamp = "$TIMESTAMP"

# Update mcp.json
mcp = json.load(open('docs/.well-known/mcp.json'))
mcp['transport']['url'] = f'{mcp_url}/mcp'
mcp['metadata']['last_verified'] = timestamp
json.dump(mcp, open('docs/.well-known/mcp.json','w'), indent=2, ensure_ascii=False)

# Update agent.json
agent = json.load(open('docs/.well-known/agent.json'))
agent['endpoints']['api'] = api_url
agent['endpoints']['mcp'] = f'{mcp_url}/mcp'
agent['endpoints']['compliance_check'] = f'{api_url}/compliance-check'
agent['endpoints']['x402_pay_info'] = f'{api_url}/pay/info'
agent['last_verified'] = timestamp
json.dump(agent, open('docs/.well-known/agent.json','w'), indent=2, ensure_ascii=False)

print('  ✅ .well-known updated')
PYEOF

# === 5. 更新 live 文件（只替换已知过时的URL pattern） ===
# 过时API URL列表
STALE_API_HOSTS=(
    "bathroom-ebooks-isa-accommodation.trycloudflare.com"
    "size-jackson-jesse-celebrity.trycloudflare.com"
    "study-comprehensive-jvc-mia.trycloudflare.com"
    "refresh-bringing-goat-buildings.trycloudflare.com"
    "producers-zum-brochures-elvis.trycloudflare.com"
    "appropriate-movie-skin-formats.trycloudflare.com"
    "atlantic-remains-atomic-floor.trycloudflare.com"
    "burning-until-bath-breeding.trycloudflare.com"
    "retrieve-jobs-congress-made.trycloudflare.com"
)
STALE_MCP_HOSTS=(
    "tex-adequate-date-facing.trycloudflare.com"
)

# Only update these live files (NOT historical docs/reports/blogs)
LIVE_FILES=(
    "README.md"
    "ACCESS_URLS.md"
    "STATUS.md"
    "agent-registry/README.md"
    "agent-registry/agents.json"
    "agent-registry/registry.html"
)

for f in "${LIVE_FILES[@]}"; do
    [ -f "$f" ] || continue
    for old in "${STALE_API_HOSTS[@]}"; do
        sed -i "s|$old|$API_HOST/g" "$f"
    done
    for old in "${STALE_MCP_HOSTS[@]}"; do
        # In MCP context (e.g. /mcp path), replace with MCP host
        if grep -q "$old" "$f" 2>/dev/null; then
            sed -i "s|$old|$MCP_HOST|g" "$f"
        fi
    done
done

echo "  ✅ Live files updated"

# === 6. Git commit and push ===
cd "$REPO_DIR"
git add docs/.well-known/mcp.json docs/.well-known/agent.json \
    README.md ACCESS_URLS.md STATUS.md \
    agent-registry/README.md agent-registry/agents.json agent-registry/registry.html 2>/dev/null

git diff --cached --quiet && echo "  No changes to commit" && exit 0

git commit -m "🔧 auto-heal v2.1: URLs updated ($TIMESTAMP)" 2>/dev/null && \
git push origin master 2>/dev/null && echo "  ✅ Pushed" || echo "  ⚠️ Push failed"
