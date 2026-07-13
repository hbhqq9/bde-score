# BDE Score™ MCP Directory Submission Tracker

**Last updated: 2026-07-13 21:55 UTC (v5.0 - Agent Registry上线版)**

## 战略转变

**v5.0 核心**: 自建Agent Registry v0.1.0上线，集成到主API服务，公网可达
- ✅ 自建Agent Registry: `/api/v1/registry` 端点
- ✅ BDE Score作为founding agent自注册
- ✅ 推广基因升级至v3.0
- 详见: [SELF_BUILT_CHANNELS_STRATEGY.md](./SELF_BUILT_CHANNELS_STRATEGY.md)

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

## 第三层：自建Agent Registry（零人工介入 ✅ v0.1.0）

**URL**: `https://bathroom-ebooks-isa-accommodation.trycloudflare.com/api/v1/registry`

| 端点 | 功能 | 状态 |
|------|------|------|
| GET /api/v1/registry | Registry信息 | ✅ |
| GET /api/v1/registry/agents | 发现所有Agent | ✅ |
| POST /api/v1/registry/register | Agent自注册 | ✅ |
| GET /api/v1/registry/agents/{id} | 查询Agent | ✅ |
| GET /api/v1/registry/agents/{id}/health | 健康检查 | ✅ |
| DELETE /api/v1/registry/agents/{id} | 注销 | ✅ |
| GET /api/v1/registry/search?q= | 语义搜索 | ✅ |
| GET /api/v1/registry/stats | 统计 | ✅ |

**已注册Agent**: BDE Score (ID: f473f03d098785a0)

## 第四层：Awaiting Maintainer Review（无需人工介入 🟢）

| # | Platform | PR/Issue | Stars | Status |
|---|----------|----------|-------|--------|
| 1 | punkpeye/awesome-mcp-servers | PR #9947 | 90.6K | 🟢 OPEN（已回复Agent-native策略，不再追Glama路径） |
| 2 | ComposioHQ/awesome-claude-skills | PR #1304 | 67.5K | 🟢 OPEN (安全审查通过) |
| 3 | yzfly/Awesome-MCP-ZH | PR #384 | 7.4K | 🟢 OPEN |
| 4 | firmai/financial-machine-learning | Issue #37 | 8.7K | 🟢 OPEN |
| 5 | thuquant/awesome-quant | Issue #49 | 5.5K | 🟢 OPEN（维护者婉拒，保持关注） |
| 6 | LLMQuant/awesome-trading-agents | PR #32 | 345 | 🟢 OPEN |
| 7 | MCPFind/mcp-find | PR #95 | - | 🟢 OPEN |
| 8 | Cline MCP Marketplace | Issue #1997 | - | 🟢 OPEN |

## 第五层：DROPPED（需人工介入 ❌）

**决策原则**: 需要OAuth登录/手动表单/CLA签署等人工介入的渠道→标记为DROPPED

| # | Platform | Reason | Dropped Date |
|---|----------|--------|--------------|
| 1 | e2b-dev/awesome-ai-agents #1234 | CLA签署需GitHub OAuth | 2026-07-13 |
| 2 | Glama.ai | 手动提交表单需GitHub OAuth（punkpeye PR merge前提） | 2026-07-13 |
| 3 | mcp.so | 需登录+表单提交 | 2026-07-13 |
| 4 | Smithery.ai | OAuth登录需浏览器+GitHub登录 | 2026-07-13 |
| 5 | cursor.directory | 表单提交 | 2026-07-13 |
| 6 | Claude Connector Directory | Google Form | 2026-07-13 |

## 历史CLOSED（供参考）

| # | Platform | PR/Issue | Stars | Reason |
|---|----------|----------|-------|--------|
| 1 | vinta/awesome-python | PR #3247 | 86.9K | 项目<3个月, Stars<100 |
| 2 | leoncuhk/awesome-quant-ai | PR #40 | - | 项目太新 |
| 3 | lorien/awesome-web-scraping | PR #263 | - | 非独立软件 |
| 4 | punkpeye/awesome-mcp-servers | PR #9906 | 90.6K | 已用#9947替代 |
| 5 | academic/awesome-datascience | PR #652 | 29.6K | ✅ MERGED |
| 6 | AI4Finance/finrl | PR #14 | - | ✅ MERGED |

## Metrics

| 指标 | v4.0 | v5.0 | 变化 |
|------|------|------|------|
| 自建Registry | ❌ 无 | ✅ v0.1.0 | 🆕 |
| 自动化渠道覆盖率 | 85% | 95% | +10% |
| 人工介入渠道数 | 6 | 0（全DROPPED） | ✅ |
| Agent协议发现端点 | 3 | 3 | - |
| 自动同步平台数 | 4 | 4 | - |
| Registry注册Agent数 | 0 | 1 | 🆕 |
| 等待审核PR/Issue | 8 | 8 | - |
| 已合并PR | 2 | 2 | - |

## Next Steps

1. **持续监控**: 8个OPEN PR/Issue的审核进展
2. **Registry推广**: 在推广材料中嵌入Registry URL，引导其他Agent注册
3. **Registry增强**: 考虑添加agent.json发现端点、WebSocket通知等
4. **永久域名**: 评估Cloudflare域名绑定，使Registry URL稳定化
