#!/bin/bash
# BDE Score 自愈型发现栈 URL 修复脚本 v3.2
# v3.2: 修复日志路径匹配，添加cf_*日志+新URL到已知列表（keepalive重建tunnel后日志文件名变化），支持多路径fallback
# 不再依赖硬编码的已知URL列表，而是从日志文件自动发现
set -e
REPO_DIR="/app/data/所有对话/主对话/BDE-Stock"
cd "$REPO_DIR"

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[$TIMESTAMP] 🔧 auto-heal v3.0: discovering tunnel URLs from logs..."

# === 1. 从日志自动发现当前URL ===
discover_url() {
    local log_file="$1"
    local health_path="$2"
    local expected_status="$3"
    
    # 从日志提取所有trycloudflare URL（去重）
    local urls=$(grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' "$log_file" 2>/dev/null | sort -u | tac)
    
    for url in $urls; do
        local status=$(curl -s --max-time 5 -o /dev/null -w "%{http_code}" "$url${health_path}" 2>/dev/null)
        if [ "$status" = "$expected_status" ]; then
            echo "$url"
            return 0
        fi
    done
    return 1
}

# v3.2 fix: try multiple log file paths (keepalive recreates tunnels with different log names)
echo "  Discovering API URL from tunnel logs..."
API_URL=""
for logfile in /tmp/cf_api_tunnel.log /tmp/api_tunnel4.log /tmp/api_tunnel3.log /tmp/api_tunnel2.log /tmp/api_tunnel.log /var/log/cloudflared-bde.log /tmp/tunnel_api.log; do
    [ -f "$logfile" ] || continue
    API_URL=$(discover_url "$logfile" "/api/health" "200") && break || true
    # fallback: try root path
    API_URL=$(discover_url "$logfile" "/" "200") && break || true
    API_URL=""
done
if [ -n "$API_URL" ]; then
    API_HOST="${API_URL#https://}"
    echo "  ✅ API: $API_URL (from $logfile)"
else
    echo "  ❌ API tunnel not found in logs"
fi

# v3.2 fix: mcp_tunnel.log (not tunnel_mcp.log which is stale)
echo "  Discovering MCP URL from tunnel logs..."
MCP_URL=""
for logfile in /tmp/cf_mcp_tunnel.log /tmp/mcp_tunnel.log /tmp/tunnel_mcp.log; do
    [ -f "$logfile" ] || continue
    MCP_URL=$(discover_url "$logfile" "/mcp" "401") && break || true
    MCP_URL=""
done
if [ -n "$MCP_URL" ]; then
    MCP_HOST="${MCP_URL#https://}"
    echo "  ✅ MCP: $MCP_URL (from $logfile)"
else
    echo "  ❌ MCP tunnel not found in logs"
fi

echo "  Discovering Registry URL from tunnel logs (cloudflared + bore fallback)..."
REG_URL=""
# Try cloudflared logs first
for logfile in /tmp/tunnel_registry.log /tmp/registry_tunnel.log /tmp/registry_server.log; do
    [ -f "$logfile" ] || continue
    REG_URL=$(discover_url "$logfile" "/" "200") && break || true
    REG_URL=""
done
# Fallback: bore.pub (static format, extract port from bore log)
if [ -z "$REG_URL" ] && [ -f /tmp/bore_registry.log ]; then
    BORE_PORT=$(grep -oP 'remote_port=\K\d+' /tmp/bore_registry.log 2>/dev/null | tail -1)
    if [ -n "$BORE_PORT" ]; then
        REG_URL="http://bore.pub:${BORE_PORT}"
        echo "  ✅ Registry: $REG_URL (from bore log, port=$BORE_PORT)"
    fi
fi
if [ -z "$REG_URL" ]; then
    # Last resort: use known bore.pub port
    if curl -s --max-time 5 -o /dev/null -w "%{http_code}" "http://bore.pub:53406/" 2>/dev/null | grep -q "200"; then
        REG_URL="http://bore.pub:53406"
        echo "  ✅ Registry: $REG_URL (fallback known port)"
    fi
fi
if [ -n "$REG_URL" ] && [ "$REG_URL" != "http://bore.pub:53406" ]; then
    REG_HOST="${REG_URL#https://}"
    REG_HOST="${REG_HOST#http://}"
    echo "  ✅ Registry: $REG_URL"
elif [ "$REG_URL" = "http://bore.pub:53406" ]; then
    REG_HOST="bore.pub:53406"
    echo "  ✅ Registry: $REG_URL"
else
    echo "  ❌ Registry tunnel not found in logs"
fi

# 至少需要API和MCP
if [ -z "$API_URL" ] || [ -z "$MCP_URL" ]; then
    echo "  ❌ Critical tunnels (API+MCP) not reachable. Abort."
    pgrep -x cloudflared > /dev/null && echo "  Process running but URLs stale" || echo "  Process NOT running"
    exit 1
fi

# === 2. 检查是否需要更新 ===
NEEDS_UPDATE=false

# 检查.well-known/mcp.json — handle both formats: url as direct field or nested under transport
CURRENT_MCP=$(python3 -c "
import json
m = json.load(open('docs/.well-known/mcp.json'))
u = m.get('url') or m.get('transport',{}).get('url','')
print(u.split('/mcp')[0] if isinstance(u, str) else '')
" 2>/dev/null)
[ "$CURRENT_MCP" != "$MCP_URL" ] && NEEDS_UPDATE=true

# 检查README是否有当前API URL
grep -q "$API_HOST" README.md 2>/dev/null || NEEDS_UPDATE=true

# 检查是否有Registry URL
if [ -n "$REG_URL" ]; then
    grep -q "$REG_HOST" ACCESS_URLS.md 2>/dev/null || NEEDS_UPDATE=true
fi

if [ "$NEEDS_UPDATE" = false ]; then
    echo "  ✅ All URLs up-to-date"
    exit 0
fi

echo "  🔄 Updating files..."

# === 3. 构建完整过时URL列表（从git历史+已知列表） ===
# 所有历史trycloudflare host（动态收集+硬编码fallback）
ALL_KNOWN_HOSTS=$(cat << 'HOSTS'
italic-telecharger-degrees-appendix
thinks-discussions-proof-dec
bathroom-ebooks-isa-accommodation
size-jackson-jesse-celebrity
study-comprehensive-jvc-mia
refresh-bringing-goat-buildings
producers-zum-brochures-elvis
appropriate-movie-skin-formats
atlantic-remains-atomic-floor
burning-until-bath-breeding
retrieve-jobs-congress-made
tex-adequate-date-facing
generators-computation-picked-emily
frequently-plays-pit-friendship
lauderdale-pads-fossil-shot
deputy-athletics-ranks-hopes
purchase-frequencies-trim-slip
neighborhood-frequency-recorder-monetary
charges-cemetery-medium-slight
pathology-attendance-talks-productive
HOSTS
)

# === 4. 更新 .well-known files ===
python3 << PYEOF
import json

api_url = "$API_URL"
mcp_url = "$MCP_URL"
reg_url = "$REG_URL"
timestamp = "$TIMESTAMP"

# Update mcp.json — handle both url formats (direct or nested under transport)
try:
    mcp = json.load(open('docs/.well-known/mcp.json'))
    if 'url' in mcp:
        mcp['url'] = f'{mcp_url}/mcp'
    elif isinstance(mcp.get('transport'), dict):
        mcp['transport']['url'] = f'{mcp_url}/mcp'
    mcp['version'] = '1.0.3'
    mcp['metadata']['last_verified'] = timestamp
    json.dump(mcp, open('docs/.well-known/mcp.json','w'), indent=2, ensure_ascii=False)
    print('  ✅ mcp.json updated')
except Exception as e:
    print(f'  ⚠️ mcp.json: {e}')

# Update agent.json
try:
    agent = json.load(open('docs/.well-known/agent.json'))
    agent['endpoints']['api'] = api_url
    agent['endpoints']['mcp'] = f'{mcp_url}/mcp'
    agent['endpoints']['compliance_check'] = f'{api_url}/compliance-check'
    agent['endpoints']['x402_pay_info'] = f'{api_url}/pay/info'
    agent['last_verified'] = timestamp
    json.dump(agent, open('docs/.well-known/agent.json','w'), indent=2, ensure_ascii=False)
    print('  ✅ agent.json updated')
except Exception as e:
    print(f'  ⚠️ agent.json: {e}')

# Update agent-card.json if exists
try:
    card = json.load(open('docs/.well-known/agent-card.json'))
    if 'url' in card:
        card['url'] = api_url
    if 'endpoints' in card:
        card['endpoints']['api'] = api_url
        card['endpoints']['mcp'] = f'{mcp_url}/mcp'
    json.dump(card, open('docs/.well-known/agent-card.json','w'), indent=2, ensure_ascii=False)
    print('  ✅ agent-card.json updated')
except:
    pass
PYEOF

# === 5. 更新 live 文件 ===
# 替换策略：
# - MCP上下文的旧URL → 替换为当前MCP host
# - Registry上下文的旧URL → 替换为当前Registry host  
# - 其他旧URL → 替换为当前API host

LIVE_FILES=(
    "README.md"
    "ACCESS_URLS.md"
    "STATUS.md"
    "agent-registry/README.md"
    "agent-registry/agents.json"
    "agent-registry/registry.html"
    "docs/.well-known/agent-card.json"
    "docs/.well-known/ai-plugin.json"
    "docs/.well-known/glama.json"
    "docs/.well-known/websub.json"
)

API_HOST_ESC="${API_HOST//./\\.}"
MCP_HOST_ESC="${MCP_HOST//./\\.}"
REG_HOST_ESC="${REG_HOST//./\\.}"

for f in "${LIVE_FILES[@]}"; do
    [ -f "$f" ] || continue
    changed=false
    
    # Step 0: 去重 .trycloudflare.com 后缀（防止历史bug累积）
    python3 -c "
import re
with open('$f','r') as fh: c=fh.read()
c2=re.sub(r'trycloudflare\.com(?:\.trycloudflare\.com)+','trycloudflare.com',c)
if c2!=c:
    with open('$f','w') as fh: fh.write(c2)
    print('  🔧 Fixed duplicate .trycloudflare.com in $f')
" 2>/dev/null

    # Step 1: 先替换所有已知旧host为API host
    while IFS= read -r old_host; do
        [ -z "$old_host" ] && continue
        old_host="${old_host// /}"
        [ "$old_host" = "$API_HOST" ] && continue
        [ "$old_host" = "$MCP_HOST" ] && continue
        [ "$old_host" = "$REG_HOST" ] && continue
        if grep -q "${old_host}.trycloudflare.com" "$f" 2>/dev/null; then
            sed -i "s|${old_host}.trycloudflare.com|${API_HOST}.trycloudflare.com|g" "$f"
            changed=true
        fi
    done <<< "$ALL_KNOWN_HOSTS"
    
    # Step 2: 将 /mcp 上下文中的API host替换为MCP host
    sed -i "s|${API_HOST}/mcp|${MCP_HOST}/mcp|g" "$f"
    
    # Step 3: Registry URL (仅在ACCESS_URLS.md和STATUS.md中添加)
    if [ -n "$REG_URL" ] && [[ "$f" == *"ACCESS_URLS"* || "$f" == *"STATUS"* ]]; then
        grep -q "$REG_HOST" "$f" 2>/dev/null || {
            # Registry URL not yet in file, skip auto-insert (manual management)
            :
        }
    fi
    
    $changed && echo "  📝 Updated: $f"
done

echo "  ✅ Live files updated"

# === 6. Git commit and push ===
cd "$REPO_DIR"
git add docs/.well-known/ README.md ACCESS_URLS.md STATUS.md \
    agent-registry/ scripts/heal-discovery-urls.sh 2>/dev/null

git diff --cached --quiet && echo "  No changes to commit" && exit 0

git commit -m "🔧 auto-heal v3.0: auto-discovered URLs from logs ($TIMESTAMP)

API: $API_HOST
MCP: $MCP_HOST
Registry: ${REG_HOST:-N/A}" 2>/dev/null && \
git push origin master 2>/dev/null && echo "  ✅ Pushed" || echo "  ⚠️ Push failed"

echo "[$TIMESTAMP] ✅ auto-heal complete"
