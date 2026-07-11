# BDE Score MCP Server 分发指南

> 最后更新: 2026-07-11 13:10 UTC+8

## 📊 分发全景状态

### ✅ 已确认上线 (7个平台)

| # | 平台 | Stars/规模 | 状态 | 链接 |
|---|------|-----------|------|------|
| 1 | **Official MCP Registry** | 权威源 | ✅ ACTIVE v1.0.0 | `io.github.hbhqq9/bde-score` |
| 2 | **punkpeye/awesome-mcp-servers** | 90,589★ | ✅ PR #9829 | [链接](https://github.com/punkpeye/awesome-mcp-servers/pull/9829) |
| 3 | **yzfly/Awesome-MCP-ZH** | 7,417★ | ✅ PR #384 | [链接](https://github.com/yzfly/Awesome-MCP-ZH/pull/384) |
| 4 | **Cline MCP Marketplace** | — | ✅ Issue #1997 | [链接](https://github.com/cline/mcp-marketplace/issues/1997) |
| 5 | **Glama** | 53,941 servers | ✅ glama.json已提交 | 等待24h自动索引 |
| 6 | **Smithery** | ~7K curated | ✅ Registry页面存在 | 从Registry自动同步 |
| 7 | **PulseMCP** | ~14.9K indexed | 🔍 从Registry自动同步 | 待验证 |

### 🔄 自动同步中 (3个平台 — 从Official Registry级联)

| # | 平台 | Stars/规模 | 机制 | 预计时间 |
|---|------|-----------|------|---------|
| 8 | **Artifacta.io Leaderboard** | 9,868 ranked | 每2天从Registry重建 | 下次regen: ~Jul 13 |
| 9 | **Skillful.sh** | 469K tools/55 dirs | 从55个目录聚合 | 自动 |
| 10 | **SourceForge MCP Directory** | — | MCP server listing | 待验证 |

### ⏳ 待手动提交 (需浏览器操作)

| # | 平台 | Stars/规模 | 操作 | 优先级 |
|---|------|-----------|------|--------|
| 11 | **mcp.so** | ~19K indexed | 浏览器表单 mcp.so/submit | 🔴 高 |
| 12 | **cursor.directory** | 250K MAU | 浏览器表单 | 🔴 高 |
| 13 | **wong2/awesome-mcp-servers** | 4,202★ | 手动PR (分支已就绪) | 🟡 中 |
| 14 | **appcypher/awesome-mcp-servers** | 5,677★ | 手动PR (分支已就绪) | 🟡 中 |
| 15 | **mcp-directory** | — | Submit按钮提交 | 🟢 低 |

### 📝 待创建基础设施

| # | 平台 | 说明 | 难度 |
|---|------|------|------|
| 16 | **MCPize Marketplace** | 需创建 mcpize.json | 简单 |

## 🏗️ v1.0.1 更新计划

修复 Official Registry 中 `repository` 字段为空的bug：

```json
"repository": {
  "url": "https://github.com/hbhqq9/bde-score",
  "source": "github",
  "id": "1295975285"
}
```

**影响**：修复后 Artifacta.io Leaderboard 将通过 ownership integrity check，自动出现在排行榜。

## 📈 覆盖规模统计

### 通过 Official Registry 一次发布覆盖的平台
- Official MCP Registry (权威源)
- PulseMCP (~14.9K)
- Smithery (~7K)
- Artifacta.io (9,868 ranked)
- Skillful.sh (469K tools from 55 dirs)

### 手动PR/表单覆盖的平台
- awesome-mcp-servers 系列 (~108K+ stars)
- mcp.so (~19K)
- cursor.directory (250K MAU)
- Cline Marketplace

### 总覆盖估计
- **自动索引**: ~490K+ 条目 (通过Registry级联)
- **手动分发**: ~140K+ stars (Awesome Lists系列)
- **MCP生态总规模**: 146,815 MCP servers (截至 2026-07-11)

## 🔧 基础设施文件

| 文件 | 用途 | 状态 |
|------|------|------|
| `mcp/server.json` | Official Registry schema | ✅ v1.0.1 (待发布) |
| `glama.json` | Glama 自动索引触发 | ✅ 已提交 |
| `llms.txt` | AI文档标准 | ✅ 已创建 |
| `llms-install.md` | AI Agent安装指南 | ✅ 已创建 |
| `bde-score-logo.png` | 400×400 Logo | ✅ 已创建 |
| `mcp/bde_score_mcp.py` | MCP Server 代码 | ✅ 5个工具 |
| `mcp/bde_score_langchain.py` | LangChain集成 | ✅ 4个工具 |

## 📅 时间线

- 2026-07-11 12:50 — v1.0.0 发布到 Official MCP Registry
- 2026-07-11 12:42 — Cline MCP Marketplace Issue #1997
- 2026-07-11 12:40 — GitHub Topics 更新 + glama.json + llms.txt
- 2026-07-11 12:33 — punkpeye PR #9829 提交
- 2026-07-11 ~ — Awesome-MCP-ZH PR #384 提交
- 2026-07-11 13:05 — server.json v1.0.1 修复 repository 字段
- 2026-07-11 ~ — 重新认证 + 发布 v1.0.1
