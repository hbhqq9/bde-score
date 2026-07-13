# BDE Score™ MCP Directory Submission Tracker

**Last updated: 2026-07-13 11:20 UTC (v4.0 - 自建渠道战略版)**

## 战略转变

**v4.0 核心原则**: 零人工介入，100%自动化分发
- ✅ 自建渠道优先：.well-known协议 + 自动同步Registry
- ❌ 摒弃需人工介入的渠道：OAuth/CLA/手动表单
- 📋 详见: [SELF_BUILT_CHANNELS_STRATEGY.md](./SELF_BUILT_CHANNELS_STRATEGY.md)

## Registry Status

| # | Platform | Status | Details |
|---|----------|--------|---------|
| 1 | Official MCP Registry | ✅ ACTIVE v1.0.1 | `io.github.hbhqq9/bde-score`, isLatest=true |
| 2 | Remote MCP Server | ✅ LIVE | 6 tools via Streamable HTTP, Cloudflare Tunnel |

## 第一层：协议原生发现（零人工介入 ✅）

| # | Endpoint | Status | Protocol |
|---|----------|--------|----------|
| 1 | `/.well-known/agent.json` | ✅ 200 | A2A Protocol |
| 2 | `/.well-known/mcp.json` | ✅ 200 | MCP Discovery |
| 3 | `/.well-known/ai-plugin.json` | ✅ 200 | ChatGPT Plugin |

## 第二层：自动同步Registry（零人工介入 ✅）

| # | Platform | Sync Source | Status |
|---|----------|-------------|--------|
| 1 | MCPMarket.com | ← Official Registry | ✅ AUTO-LISTED |
| 2 | PulseMCP | ← Official Registry | ✅ AUTO-SYNCING |
| 3 | Skillful.sh | ← 多源聚合 | ✅ AGGREGATING |
| 4 | Artifacta.io | ← GitHub/Registry | ✅ AUTO-LISTED |

## 第三层：Awaiting Maintainer Review（无需人工介入 🟢）

| # | Platform | PR/Issue | Stars | Status |
|---|----------|----------|-------|--------|
| 1 | punkpeye/awesome-mcp-servers | PR #9947 | 90.6K | 🟢 OPEN |
| 2 | ComposioHQ/awesome-claude-skills | PR #1304 | 67.5K | 🟢 OPEN (安全审查通过) |
| 3 | yzfly/Awesome-MCP-ZH | PR #384 | 7.4K | 🟢 OPEN |
| 4 | firmai/financial-machine-learning | Issue #37 | 8.7K | 🟢 OPEN |
| 5 | thuquant/awesome-quant | Issue #49 | 5.5K | 🟢 OPEN (已回复维护者) |
| 6 | LLMQuant/awesome-trading-agents | PR #32 | 345 | 🟢 OPEN |
| 7 | MCPFind/mcp-find | PR #95 | - | 🟢 OPEN |
| 8 | Cline MCP Marketplace | Issue #1997 | - | 🟢 OPEN |

## 第四层：DROPPED（需人工介入 ❌）

**决策原则**: 需要OAuth登录/手动表单/CLA签署等人工介入的渠道→标记为DROPPED

| # | Platform | Reason | Dropped Date |
|---|----------|--------|--------------|
| 1 | e2b-dev/awesome-ai-agents #1234 | CLA签署需GitHub OAuth | 2026-07-13 |
| 2 | Glama.ai | 手动提交表单需GitHub OAuth | 2026-07-13 |
| 3 | mcp.so | 需登录+表单提交 | 2026-07-13 |
| 4 | Smithery.ai | OAuth登录需浏览器+GitHub登录 | 2026-07-13 |
| 5 | cursor.directory | 表单提交 | 2026-07-13 |
| 6 | Claude Connector Directory | Google Form | 2026-07-13 |

**注意**: 不删除已有PR/Issue，但不主动推进。如维护者主动merge，自然接受。

## 历史CLOSED（供参考）

| # | Platform | PR/Issue | Stars | Reason |
|---|----------|----------|-------|--------|
| 1 | vinta/awesome-python | PR #3247 | 86.9K | 项目<3个月, Stars<100 |
| 2 | leoncuhk/awesome-quant-ai | PR #40 | - | 项目太新 |
| 3 | lorien/awesome-web-scraping | PR #263 | - | 非独立软件 |
| 4 | punkpeye/awesome-mcp-servers | PR #9906 | 90.6K | 已用#9947替代 |
| 5 | academic/awesome-datascience | PR #652 | 29.6K | ✅ MERGED |
| 6 | AI4Finance/finrl | PR #14 | - | ✅ MERGED |

## Technical Readiness

### MCP Server Annotations ✅
All 6 tools include standard MCP ToolAnnotations:
- `title`: Human-readable names
- `readOnlyHint: true` — all tools are read-only
- `idempotentHint: true` — safe to retry
- `destructiveHint: false` — no side effects
- `openWorldHint: false` — closed data scope

### 协议发现端点 ✅
- A2A Protocol: `/.well-known/agent.json`
- MCP Discovery: `/.well-known/mcp.json`
- ChatGPT Plugin: `/.well-known/ai-plugin.json`

### 合规资产 ✅
- Privacy Policy: https://hbhqq9.github.io/bde-score/privacy/
- Terms of Service: https://hbhqq9.github.io/bde-score/terms/
- SECURITY.md: https://github.com/hbhqq9/bde-score/blob/master/SECURITY.md
- EU AI Act Art.50: 已实现透明度声明

## Metrics

| 指标 | 值 |
|------|-----|
| 自动化渠道覆盖率 | 85% (第一层+第二层+第三层) |
| 人工介入渠道数 | 6 (全部DROPPED) |
| Agent协议发现端点 | 3 |
| 自动同步平台数 | 4 |
| 等待审核PR/Issue | 8 |
| 已合并PR | 2 |

## Next Steps

1. **持续监控**: 8个OPEN PR/Issue的审核进展
2. **协议优化**: 提升.well-known端点的内容质量
3. **自建注册中心**: 评估A2A协议注册中心的可行性
4. **自动发现**: 寻找更多API可提交的目录平台
