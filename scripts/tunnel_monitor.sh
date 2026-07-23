#!/usr/bin/env bash
# BDE Score - MCP Registry Auto-Update Script
# Monitors Cloudflare Tunnel URL changes and auto-publishes to MCP Registry
# Uses GitHub OAuth token directly (no mcp-publisher Device Flow needed)

set -euo pipefail

# === Configuration ===
REGISTRY_API="https://registry.modelcontextprotocol.io/v0.1"
# Load token from .env (never commit secrets)
ENV_FILE="${BDE_STOCK_DIR:-/app/data/所有对话/主对话/BDE-Stock}/.env"
if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
fi
GITHUB_TOKEN="${GITHUB_OAUTH_TOKEN:?Missing GITHUB_OAUTH_TOKEN in .env}"
SERVER_JSON="/app/data/所有对话/主对话/BDE-Stock/.mcp/server.json"
STATE_FILE="/app/data/所有对话/主对话/BDE-Stock/.mcp/.tunnel_state.json"
LOG_FILE="/app/data/所有对话/主对话/BDE-Stock/logs/tunnel_monitor.log"
CHECK_INTERVAL=300  # 5 minutes
MCP_PORT=8891
BDE_STOCK_DIR="/app/data/所有对话/主对话/BDE-Stock"

# === Functions ===
log() {
    mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null
    local msg="[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] $1"
    echo "$msg" | tee -a "$LOG_FILE"
}

get_current_url_from_server_json() {
    python3 -c "
import json
from urllib.parse import urlparse
with open('$SERVER_JSON') as f:
    data = json.load(f)
for r in data.get('remotes', []):
    if 'mcp' in r.get('url', ''):
        parsed = urlparse(r['url'])
        print(parsed.netloc)
        break
" 2>/dev/null
}

get_current_version() {
    python3 -c "
import json
with open('$SERVER_JSON') as f:
    data = json.load(f)
print(data.get('version', '0.0.0'))
" 2>/dev/null
}

bump_version() {
    local current="$1"
    python3 -c "
v = '$current'.split('.')
v[-1] = str(int(v[-1]) + 1)
print('.'.join(v))
"
}

# Find all cloudflared tunnel URLs by scanning process stderr
find_tunnel_urls() {
    local urls=()
    for pid in $(pgrep -f 'cloudflared tunnel' 2>/dev/null); do
        local url=$(cat /proc/$pid/fd/2 2>/dev/null | grep -o 'https://[a-z-]*\.trycloudflare\.com' | tail -1)
        if [ -n "$url" ]; then
            urls+=("$url")
        fi
    done
    echo "${urls[@]}"
}

# Test if a URL responds to MCP requests
test_mcp_url() {
    local url="$1"
    local status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
        -X POST "${url}/mcp" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"health-check","version":"1.0"}}}' 2>/dev/null || echo "000")
    echo "$status"
}

# Find the active MCP tunnel URL
find_active_mcp_url() {
    local urls=$(find_tunnel_urls)
    for url in $urls; do
        local status=$(test_mcp_url "$url")
        if [ "$status" = "200" ] || [ "$status" = "402" ]; then
            echo "$url"
            return 0
        fi
    done
    return 1
}

# Publish to MCP Registry using GitHub token directly
publish_to_registry() {
    local response=$(curl -s -w "\n%{http_code}" -X POST "${REGISTRY_API}/publish" \
        -H "Authorization: Bearer ${GITHUB_TOKEN}" \
        -H "Content-Type: application/json" \
        -d @"$SERVER_JSON" 2>/dev/null)
    
    local http_code=$(echo "$response" | tail -1)
    local body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        log "✅ Published to MCP Registry successfully (HTTP $http_code)"
        echo "$body" >> "$LOG_FILE"
        return 0
    else
        log "❌ Publish failed (HTTP $http_code): $body"
        return 1
    fi
}

# Update server.json with new URL and version
update_server_json() {
    local new_url="$1"
    local new_version="$2"
    
    python3 -c "
import json
with open('$SERVER_JSON') as f:
    data = json.load(f)
data['version'] = '$new_version'
for r in data.get('remotes', []):
    if 'mcp' in r.get('url', '') or r.get('type') == 'streamable-http':
        r['url'] = 'https://${new_url}/mcp'
        break
with open('$SERVER_JSON', 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
"
    log "📝 Updated server.json: version=$new_version, url=https://${new_url}/mcp"
}

# Save state
save_state() {
    local url="$1"
    local version="$2"
    python3 -c "
import json, time
state = {
    'mcp_url': '$url',
    'version': '$version',
    'last_check': int(time.time()),
    'last_change': int(time.time())
}
with open('$STATE_FILE', 'w') as f:
    json.dump(state, f, indent=2)
"
}

# Main check function
check_and_update() {
    log "--- Check started ---"
    
    # Get current URL from server.json
    local registered_url=$(get_current_url_from_server_json)
    local current_version=$(get_current_version)
    log "Registered MCP URL: $registered_url (version $current_version)"
    
    # Test if current URL is still alive
    if [ -n "$registered_url" ]; then
        local status=$(test_mcp_url "https://${registered_url}")
        if [ "$status" = "200" ] || [ "$status" = "402" ]; then
            log "✅ Current URL alive (HTTP $status), no update needed"
            save_state "$registered_url" "$current_version"
            return 0
        else
            log "⚠️ Current URL dead (HTTP $status), searching for new tunnel..."
        fi
    fi
    
    # Find active MCP tunnel
    local new_url=$(find_active_mcp_url)
    if [ -z "$new_url" ]; then
        log "❌ No active MCP tunnel found! All tunnels may be down."
        return 1
    fi
    
    # Extract hostname
    local new_host=$(echo "$new_url" | sed 's|https://||' | sed 's|/$||')
    log "🔍 Found active MCP tunnel: $new_host"
    
    # Skip if same URL
    if [ "$new_host" = "$registered_url" ]; then
        log "Same URL, no update needed"
        save_state "$new_host" "$current_version"
        return 0
    fi
    
    # URL changed! Update and publish
    local new_version=$(bump_version "$current_version")
    log "🔄 URL changed: $registered_url → $new_host"
    log "📦 Version bump: $current_version → $new_version"
    
    # Update server.json
    update_server_json "$new_host" "$new_version"
    
    # Validate first
    local validate_result=$(curl -s -X POST "${REGISTRY_API}/validate" \
        -H "Authorization: Bearer ${GITHUB_TOKEN}" \
        -H "Content-Type: application/json" \
        -d @"$SERVER_JSON" 2>/dev/null)
    
    if echo "$validate_result" | grep -q '"valid":true'; then
        log "✅ Validation passed"
    else
        log "❌ Validation failed: $validate_result"
        return 1
    fi
    
    # Publish
    if publish_to_registry; then
        save_state "$new_host" "$new_version"
        
        # Git commit
        cd "$BDE_STOCK_DIR"
        git add .mcp/server.json 2>/dev/null
        git commit -m "chore: auto-update MCP Registry v${new_version} (tunnel URL drift)" 2>/dev/null || true
        git push 2>/dev/null || log "⚠️ Git push failed (non-critical)"
        
        log "✅ Full update complete! v${new_version} published with ${new_host}"
    else
        log "❌ Publish failed, keeping old state"
        return 1
    fi
}

# === Main Loop ===
log "🚀 Tunnel Monitor started (interval: ${CHECK_INTERVAL}s)"
log "Server JSON: $SERVER_JSON"
log "Registry API: $REGISTRY_API"

# Create log directory
mkdir -p "$(dirname "$LOG_FILE")"

# Initial check
check_and_update || true

# Loop
while true; do
    sleep "$CHECK_INTERVAL"
    check_and_update || true
done
