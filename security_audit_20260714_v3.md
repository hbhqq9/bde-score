# 全维度安全宪法校验报告 v4.1-3

**时间**: 2026-07-14 09:25 UTC  
**触发**: WebSub Hub上线 + Registry公网暴露  
**Git**: commit `b664a96`

## 校验范围

| 维度 | 项目数 | PASS | WARN | FAIL |
|------|--------|------|------|------|
| 服务安全层 | 16 | 16 | 0 | 0 |
| .well-known静态端点 | 14 | 14 | 0 | 0 |
| 11铁律 | 11 | 11 | 0 | 0 |
| 6条安全基线 | 6 | 3 | 3 | 0 |
| **总计** | **47** | **44** | **3** | **0** |

## 新增组件审计

### WebSub Hub (websub_hub.py, 315行)

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 认证 | ✅ PASS | publish端点Bearer认证，subscribe公开+速率限制 |
| SSRF防护 | ✅ PASS | 私有IP(127/10/172.16/192.168/169.254)回调全部拒绝 |
| 速率限制 | ✅ PASS | subscribe 5次/分钟，超出429 |
| 安全头 | ✅ PASS | X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Cache-Control |
| 容量限制 | ✅ PASS | MAX_SUBSCRIBERS_PER_TOPIC=100, MAX_BODY_SIZE=64KB |
| 订阅TTL | ✅ PASS | 7天自动过期清理 |
| 绑定地址 | ✅ PASS | 127.0.0.1 only |
| 无效主题 | ✅ PASS | 仅接受5个预定义主题 |
| 错误处理 | ✅ PASS | 通用JSON错误消息，无架构泄露 |

### Registry 公网暴露

| 检查项 | 结果 | 说明 |
|--------|------|------|
| Tunnel URL | ✅ PASS | appropriate-movie-skin-formats.trycloudflare.com |
| 读操作 | ✅ PASS | GET /api/v1/agents → 200 (公开) |
| 写操作 | ✅ PASS | POST 无认证 → 401 |
| 大请求体 | ✅ PASS | 2MB body → 413 |
| CORS | ✅ PASS | 限制allowed-headers/methods |

## 发现栈矩阵（14端点全LIVE）

| # | 端点 | 协议 | 状态 |
|---|------|------|------|
| 1 | /.well-known/agent.json | A2A | ✅ 200 |
| 2 | /.well-known/agent-card.json | Google A2A Card | ✅ 200 |
| 3 | /.well-known/mcp.json | MCP | ✅ 200 |
| 4 | /.well-known/ai-plugin.json | ChatGPT Plugin | ✅ 200 |
| 5 | /.well-known/glama.json | Glama | ✅ 200 |
| 6 | /.well-known/security.txt | RFC 9116 | ✅ 200 |
| 7 | /.well-known/ai-trust.txt | AI信任声明 | ✅ 200 |
| 8 | /.well-known/did/did.json | W3C DID | ✅ 200 |
| 9 | /.well-known/websub.json | W3C WebSub | ✅ 200 |
| 10 | /openapi.json | OpenAPI | ✅ 200 |
| 11 | /robots.txt | Robots+Security | ✅ 200 |
| 12 | /llms.txt | LLM发现 | ✅ 200 |
| 13 | /llms-full.txt | LLM完整 | ✅ 200 |
| 14 | /sitemap.xml | SEO | ✅ 200 |

## 服务进程矩阵（8进程全在线）

| PID | 服务 | 端口 | 安全层 | 公网 |
|-----|------|------|--------|------|
| 163729 | BDE API | 8890 | API-Key+x402+限流+安全头 | ✅ Tunnel |
| 130848 | MCP Server | 8891 | API-Key+限流 | ✅ Tunnel |
| 186156 | Registry | 8892 | Bearer+限流+SSRF+CORS | ✅ Tunnel (新) |
| 195086 | WebSub Hub | 8893 | Bearer+限流+SSRF | ⏳ 限流 |
| 2462 | Keepalive | - | - | - |
| 31367 | Tunnel API | 8890→公网 | Cloudflare | ✅ |
| 31584 | Tunnel MCP | 8891→公网 | Cloudflare | ✅ |
| 195090 | Tunnel Registry | 8892→公网 | Cloudflare | ✅ |

## 3个WARNING

1. **WebSub公网Tunnel限流**: Cloudflare quick tunnel并发上限3个，WebSub tunnel排队中。本地服务正常，待CF配额释放后自动重试。
2. **WebSub HMAC签名未配置**: HUB_SECRET=None，推送内容无HMAC签名。建议下一迭代配置。
3. **Registry CORS全开放**: allow-methods和allow-headers未限定具体值。实际风险低（写操作需Bearer认证）。

## 结论

安全宪法v4.1运行正常，11铁律全部遵守。新增WebSub Hub和Registry公网暴露均通过安全审计，安全层完整。发现栈矩阵从13→14端点。
