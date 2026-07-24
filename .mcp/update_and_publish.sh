#!/bin/bash
# Update MCP Registry with ngrok URL and publish
set -euo pipefail

REGISTRY_API="https://registry.modelcontextprotocol.io/v0.1"
ENV_FILE="/app/data/所有对话/主对话/BDE-Stock/.env"
source "$ENV_FILE"

NEW_VERSION="$1"  # e.g., "1.28.0"
NGROK_DOMAIN="$2"  # e.g., "decorated-during-book.ngrok-free.dev"
SERVER_JSON="/app/data/所有对话/主对话/BDE-Stock/.mcp/server.json"

echo "Updating server.json to v${NEW_VERSION} with ngrok domain: ${NGROK_DOMAIN}"

python3 -c "
import json
with open('$SERVER_JSON') as f:
    data = json.load(f)
data['version'] = '${NEW_VERSION}'
for r in data.get('remotes', []):
    if r.get('type') == 'streamable-http' or 'mcp' in r.get('url', ''):
        r['url'] = 'https://${NGROK_DOMAIN}/mcp'
        break
with open('$SERVER_JSON', 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
"

echo "Validating..."
VALIDATE=$(curl -s -X POST "${REGISTRY_API}/validate" \
    -H "Authorization: Bearer ${GITHUB_OAUTH_TOKEN}" \
    -H "Content-Type: application/json" \
    -d @"$SERVER_JSON" 2>/dev/null)
echo "Validate result: $VALIDATE"

echo "Publishing..."
RESULT=$(curl -s -w "\nHTTP %{http_code}" -X POST "${REGISTRY_API}/publish" \
    -H "Authorization: Bearer ${GITHUB_OAUTH_TOKEN}" \
    -H "Content-Type: application/json" \
    -d @"$SERVER_JSON" 2>/dev/null)
echo "Publish result: $RESULT"

# Git commit
cd /app/data/所有对话/主对话/BDE-Stock
git add .mcp/server.json
git commit -m "chore: MCP Registry v${NEW_VERSION} - ngrok permanent URL ${NGROK_DOMAIN}"
git push

echo "✅ Done! v${NEW_VERSION} published with ${NGROK_DOMAIN}"
