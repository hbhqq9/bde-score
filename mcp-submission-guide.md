# BDE Score MCP 目录分发跟踪指南

> 最后更新: 2026-07-11 13:25 UTC+8

## 🏆 Official MCP Registry — ACTIVE v1.0.1

```
Name: io.github.hbhqq9/bde-score
Version: 1.0.1 (latest)
Status: ✅ active
Published: 2026-07-11T05:25:28Z
Repository: https://github.com/hbhqq9/bde-score
Remote: https://retrieve-jobs-congress-made.trycloudflare.com/mcp (streamable-http)
```

### v1.0.1 关键修复
- ✅ repository 字段填充 (url + source + id)
- ✅ website_url 添加
- ✅ remotes 数组格式 (streamable-http)
- ✅ description ≤100字符
- ✅ 6个工具声明

---

## 📊 平台分发状态（18个平台）

### 自动同步平台（无需手动提交）
| 平台 | 状态 | 说明 |
|------|------|------|
| **Official MCP Registry** | ✅ ACTIVE v1.0.1 | 权威源，其他平台从这里同步 |
| **Artifacta.io** (9,868 ranked) | 🔍 等待下次regen | 每2天从Registry重建，需repository字段(v1.0.1已修复) |
| **Skillful.sh** (469K tools) | 🔍 等待索引 | 从55个目录聚合 |
| **SourceForge** | 🔍 等待索引 | MCP目录 |
| **PulseMCP** (~14.9K) | 🔍 自动同步中 | 从Registry拉取 |
| **Smithery** (~7K) | 🔍 自动同步中 | 页面已存在 |

### 已提交PR/Issue的平台
| 平台 | Stars | 状态 | 详情 |
|------|-------|------|------|
| **punkpeye/awesome-mcp-servers** | 90,589★ | ✅ PR #9829 OPEN | 最大MCP列表 |
| **Awesome-MCP-ZH** | 7,417★ | ✅ PR #384 OPEN | 中文MCP列表 |
| **Cline MCP Marketplace** | - | ✅ Issue #1997 OPEN | AI IDE市场 |
| **wong2/awesome-mcp-servers** | 4,202★ | ⏳ PR提交中 | 浏览器任务进行中 |
| **appcypher/awesome-mcp-servers** | 5,677★ | ⏳ branch ready | 等待提交 |

### Glama（需glama.json）
| 平台 | Stars | 状态 |
|------|-------|------|
| **Glama** | 53,941 | ✅ glama.json已提交，等待24h索引 |

### 需要浏览器提交的平台
| 平台 | MAU | 状态 | 说明 |
|------|-----|------|------|
| **mcp.so** | ~19K | ❌ 待重试 | 表单提交 |
| **cursor.directory** | 250K | ❌ 待重试 | 表单提交 |

### 待准备的平台
| 平台 | 状态 | 说明 |
|------|------|------|
| **mcp-directory** | 📝 待提交 | MCP目录 |
| **MCPize Marketplace** | 📝 需mcpize.json | 需要配置文件 |
| **Higress MCP市场（阿里）** | 📝 即将上线 | 中国市场入口 |
| **Microsoft Partner Center** | 📝 需Partner账户 | 企业认证 |

---

## 🔧 技术认证进度

### 完成
- [x] Official MCP Registry v1.0.1 — ACTIVE
- [x] Remote MCP Server — 6工具全可用 (streamable-http)
- [x] MCP HTTP Server — FastMCP + Cloudflare Tunnel
- [x] LangChain Tools — 4个集成工具
- [x] glama.json — 已提交
- [x] llms.txt — AI文档标准
- [x] llms-install.md — Agent安装指南
- [x] GitHub Topics — 20个(满)
- [x] Logo — 400×400 PNG

### 运行中
- [x] BDE API — 端口8890
- [x] MCP HTTP Server — 端口8891
- [x] Cloudflare Tunnel (API) — 公网入口
- [x] Cloudflare Tunnel (MCP) — MCP公网入口
- [x] Keepalive — 每5分钟守护

---

## 🔑 Registry Token管理

Registry JWT token有过期时间，需要定期刷新。

**快速刷新方法（无需浏览器）：**
```bash
# 从gh CLI获取GitHub token并交换Registry JWT
GH_TOKEN=$(cat /app/data/所有对话/主对话/.gh/hosts.yml | grep oauth_token | awk '{print $2}')
REGISTRY_TOKEN=$(curl -s -X POST "https://registry.modelcontextprotocol.io/v0/auth/github-at" \
  -H "Content-Type: application/json" \
  -d "{\"github_token\": \"$GH_TOKEN\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['registry_token'])")
cat > ~/.mcp_publisher_token << EOF
{"method":"github","registry":"https://registry.modelcontextprotocol.io","token":"$REGISTRY_TOKEN"}
EOF
```

---

## 📋 Remote MCP Server

当前远程MCP端点：
```
URL: https://retrieve-jobs-congress-made.trycloudflare.com/mcp
Transport: streamable-http
Tools: 6个 (get_bde_score, get_stock_analysis, get_multi_market_comparison, get_stock_screener, get_sector_analysis, get_esg_analysis)
```

⚠️ Cloudflare Tunnel URL是临时的，服务重启后会变化。需要更新server.json并重新发布到Registry。
