# BDE Score™ MCP Directory Submission Tracker

**Last updated: 2026-07-12 09:50 UTC**

## Registry Status

| Platform | Status | Details |
|----------|--------|---------|
| **Official MCP Registry** | ✅ ACTIVE v1.0.1 | `io.github.hbhqq9/bde-score`, isLatest=true |
| **Remote MCP Server** | ✅ LIVE | 6 tools via Streamable HTTP, Cloudflare Tunnel |

## Directory Platforms

### Confirmed Active

| # | Platform | Status | URL / Reference |
|---|----------|--------|----------------|
| 1 | Official MCP Registry | ✅ ACTIVE v1.0.1 | https://registry.modelcontextprotocol.io |
| 2 | punkpeye/awesome-mcp-servers (90K★) | ✅ PR #9829 OPEN | Pending review |
| 3 | yzfly/Awesome-MCP-ZH (7.4K★) | ✅ PR #384 OPEN | Pending review |
| 4 | Cline MCP Marketplace | ✅ Issue #1997 | Pending review |
| 5 | Glama (53K+ servers) | ⏳ glama.json submitted | Awaiting 24h index |
| 6 | mcp.so (~19K) | ✅ Issue #3121 SUBMITTED | chatmcp/mcpso |
| 19 | mcp.directory | ✅ SUBMITTED (07-12) | 24h review, "Server Submitted!" |
| 20 | mcpservers.org | ✅ Issue #1 (07-12) | tmrseoteam-commits/mcpservers-org |

### Auto-Sync (from Official Registry)

| # | Platform | Status | Notes |
|---|----------|--------|-------|
| 7 | PulseMCP (~15K) | 🔍 Auto-syncing | Pulls from Official Registry |
| 8 | Smithery (~7K) | 🔍 Auto-syncing | Pulls from Official Registry |
| 9 | Artifacta.io (9.8K ranked) | 🔍 Next regen ~Jul 13 | v1.0.1 repo fix should enable listing |
| 10 | Skillful.sh (469K/55dirs) | 🔍 Aggregating | Pulls from multiple directories |
| 11 | MCPFind (15.8K+ servers) | ⏳ Browser submission pending | Open-source directory |

### Queued / Needs Browser

| # | Platform | Status | Notes |
|---|----------|--------|-------|
| 12 | Claude Connector Directory | 📋 Data prepared | Google Form, needs browser to fill |
| 13 | cursor.directory (250K MAU) | ⏳ Browser submission pending | Form-based |
| 14 | SourceForge | 🔍 Needs verification | |

### Blocked / Dropped

| # | Platform | Status | Reason |
|---|----------|--------|--------|
| 15 | wong2/awesome-mcp-servers (4.2K★) | ❌ DROPPED | Repo owner disabled PRs |
| 16 | appcypher/awesome-mcp-servers (5.7K★) | ❌ DROPPED | Repo owner disabled PRs |
| 17 | Smithery CLI | ❌ Needs API Key | Registration required |
| 18 | Microsoft Partner Center | ❌ Needs partner account | Enterprise certification |

## Technical Readiness

### MCP Server Annotations ✅
All 6 tools now include standard MCP ToolAnnotations:
- `title`: Human-readable names
- `readOnlyHint: true` — all tools are read-only
- `idempotentHint: true` — safe to retry
- `destructiveHint: false` — no side effects
- `openWorldHint: false` — closed data scope

### Claude Connector Readiness
- ✅ Streamable HTTP transport
- ✅ Tool annotations (title + readOnlyHint)
- ✅ Privacy Policy (https://hbhqq9.github.io/bde-score/privacy/)
- ✅ Terms of Service (https://hbhqq9.github.io/bde-score/terms/)
- ✅ Support channel (GitHub Issues)
- ✅ No auth required (authless)
- 📋 Google Form submission pending
- Form URL: https://docs.google.com/forms/d/e/1FAIpQLSeafJF2NDI7oYx1r8o0ycivCSVLNq92Mpc1FPxMKSw1CzDkqA/viewform

## Token Refresh Method

Registry JWT expires. Refresh using:
```bash
GH_TOKEN=$(cat /app/data/所有对话/主对话/.gh/hosts.yml | grep oauth_token | awk '{print $2}')
REGISTRY_TOKEN=$(curl -s -X POST "https://registry.modelcontextprotocol.io/v0/auth/github-at" \
  -H "Content-Type: application/json" \
  -d "{\"github_token\": \"$GH_TOKEN\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['registry_token'])")
cat > ~/.mcp_publisher_token << EOF
{"method":"github","registry":"https://registry.modelcontextprotocol.io","token":"$REGISTRY_TOKEN"}
EOF
```

## Key Infrastructure

- **MCP HTTP Server**: port 8891, FastMCP + streamable-http
- **Cloudflare Tunnel (MCP)**: `https://retrieve-jobs-congress-made.trycloudflare.com/mcp` → port 8891
- **Cloudflare Tunnel (API)**: `https://atlantic-remains-atomic-floor.trycloudflare.com` → port 8890
- **Keepalive**: crontab every 5min, monitors both servers + tunnels
- **⚠️ Tunnel URLs are temporary** — restart changes URL, requires server.json update + re-publish

## Awesome Lists PR Status

25 PRs submitted (1 MERGED, 2 CLOSED, 22 OPEN).
See full list in mcp-submission-guide.md.

## Monitoring

Calendar task UID: `96785531-7e44-4846-9906-c994562395e1`
Runs every 4 hours, checks all PR statuses and API health.
