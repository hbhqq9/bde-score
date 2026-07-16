#!/bin/bash
# BDE Score 自愈型发现栈 URL 修复脚本 v3.0
# v3.0: 全自动从日志发现3个Tunnel URL + 动态替换所有过时URL
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

echo "  Discovering API URL from /tmp/tunnel_api.log..."
API_URL=$(discover_url "/tmp/tunnel_api.log" "/" "200") || API_URL=""
if [ -n "$API_URL" ]; then
    API_HOST="${API_URL#https://}"
    echo "  ✅ API: $API_URL"
else
    echo "  ❌ API tunnel not found in logs"
fi

echo "  Discovering MCP URL from /tmp/tunnel_mcp.log..."
MCP_URL=$(discover_url "/tmp/tunnel_mcp.log" "/mcp" "401") || MCP_URL=""
if [ -n "$MCP_URL" ]; then
    MCP_HOST="${MCP_URL#https://}"
    echo "  ✅ MCP: $MCP_URL"
else
    echo "  ❌ MCP tunnel not found in logs"
fi

echo "  Discovering Registry URL from /tmp/tunnel_registry.log..."
REG_URL=$(discover_url "/tmp/tunnel_registry.log" "/" "200") || REG_URL=""
if [ -n "$REG_URL" ]; then
    REG_HOST="${REG_URL#https://}"
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

# 检查.well-known/mcp.json
CURRENT_MCP=$(python3 -c "import json; print(json.load(open('docs/.well-known/mcp.json'))['transport']['url'].split('/mcp')[0])" 2>/dev/null)
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
HOSTS
)

# === 4. 更新 .well-known files ===
python3 << PYEOF
import json

api_url = "$API_URL"
mcp_url = "$MCP_URL"
reg_url = "$REG_URL"
timestamp = "$TIMESTAMP"

# Update mcp.json
try:
    mcp = json.load(open('docs/.well-known/mcp.json'))
    mcp['transport']['url'] = f'{mcp_url}/mcp'
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
    
    while IFS= read -r old_host; do
        [ -z "$old_host" ] && continue
        old_host="${old_host// /}"  # trim whitespace
        [ "$old_host" = "$API_HOST" ] && continue
        [ "$old_host" = "$MCP_HOST" ] && continue
        [ "$old_host" = "$REG_HOST" ] && continue
        
        # 检查文件中是否有这个旧host
        if grep -q "$old_host" "$f" 2>/dev/null; then
            # 判断上下文：如果在/mcp路径附近，替换为MCP host
            # 如果在registry相关上下文，替换为Registry host
            # 默认替换为API host
            if grep -q "${old_host}.*mcp\|mcp.*${old_host}" "$f" 2>/dev/null; then
                sed -i "s|${old_host}|${MCP_HOST}|g" "$f"
            else
                sed -i "s|${old_host}|${API_HOST}|g" "$f"
            fi
            changed=true
        fi
    done <<< "$ALL_KNOWN_HOSTS"
    
    # Registry URL replacement (specific to registry context)
    if [ -n "$REG_URL" ]; then
        # 查找frequently-plays-pit-friendship等旧registry host
        for old_reg in "frequently-plays-pit-friendship"; do
            if grep -q "$old_reg" "$f" 2>/dev/null; then
                sed -i "s|${old_reg}|${REG_HOST}|g" "$f"
                changed=true
            fi
        done
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
