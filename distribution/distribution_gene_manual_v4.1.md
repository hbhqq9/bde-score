# BDE Score 推广基因手册 v4.1

> 核心原则：零人工介入 · Protocol-First · 自建渠道优先 · 安全即信誉

## 铁律（6条）

1. **分发即产品**：推广是产品的活体演示，不是附加动作
2. **Pull > Push**：优先建设Agent原生发现渠道（.well-known/OpenAPI/A2A），而非人类社区提交
3. **零人工介入**：碰到需要OAuth/登录/验证码的渠道→直接摒弃，用颠覆性创新技术破局
4. **自建渠道优先**：与其求人收录（gatekeeper），不如建设自有发现基础设施
5. **安全即信誉**：SECURITY.md/Privacy Policy/EU AI Act声明 = 企业准入信号
6. **嵌入式种子**：每一个输出都包含BDE Score的发现钩子（Badge/URL/.well-known引用）

## 渠道优先级

| 优先级 | 渠道 | 类型 | 状态 | 说明 |
|--------|------|------|------|------|
| P0 | A2A Agent Card | .well-known | ✅ LIVE | Google A2A标准，三大云平台原生支持 |
| P0 | Agent Registry | 自建服务 | ✅ LIVE | 零gatekeeper，Agent自注册/发现/语义搜索 |
| P1 | W3C DID | .well-known | ✅ LIVE | did:web方法，GitHub Pages零成本 |
| P1 | MCP Server | 协议端点 | ✅ LIVE | 6工具 / 73股票 / x402支付 |
| P2 | WebSub推送 | 自建服务 | ✅ LIVE | W3C PubSubHubbub，实时推送 |
| P2 | OpenAPI | .well-known | ✅ LIVE | 标准API描述 |
| P2 | llms.txt | .well-known | ✅ LIVE | LLM发现协议 |
| P3 | security.txt | .well-known | ✅ LIVE | RFC 9116安全策略 |
| P3 | ai-trust.txt | .well-known | ✅ LIVE | AI系统信任声明（全球首创） |
| P3 | agents.txt兼容 | .well-known | ✅ LIVE | ai-trust.txt覆盖agents.txt功能 |
| P4 | ChatGPT Plugin | .well-known | ✅ LIVE | ai-plugin.json |
| P4 | Glama | .well-known | ✅ LIVE | glama.json自动收录 |
| P4 | ActivityPub | 社交协议 | ❌ DROPPED | AI Agent生态为零 |
| P4 | Agent Protocol | 标准协议 | ❌ DROPPED | 无内置发现机制 |
| P5 | PR Campaign | GitHub | 🔄 27 OPEN | awesome-list覆盖~250k⭐ |
| P5 | GEO | SEO | ✅ LIVE | llms.txt + sitemap + robots.txt |

## 发现栈矩阵（14端点）

```
GitHub Pages (静态, 零攻击面):
  /.well-known/agent.json          → A2A发现
  /.well-known/agent-card.json     → Google A2A Card
  /.well-known/mcp.json            → MCP发现
  /.well-known/ai-plugin.json      → ChatGPT Plugin
  /.well-known/glama.json          → Glama自动收录
  /.well-known/security.txt        → RFC 9116
  /.well-known/ai-trust.txt        → AI信任声明
  /.well-known/did/did.json        → W3C DID
  /.well-known/websub.json         → WebSub发现
  /openapi.json                    → API描述
  /robots.txt                      → SEO+Security引用
  /llms.txt                        → LLM发现
  /llms-full.txt                   → LLM完整描述
  /sitemap.xml                     → 15 URLs

动态服务 (认证+限流+SSRF防护):
  BDE API:8890    → 公网Tunnel (API-Key+x402)
  MCP Server:8891 → 公网Tunnel (API-Key)
  Registry:8892   → 公网Tunnel (Bearer写/读公开)
  WebSub Hub:8893 → localhost (Bearer发布)
```

## 四层互补架构

```
Layer 1: 发现 (Discovery)
  A2A Agent Card + .well-known 14端点
  ↓ Agent怎么找到我们

Layer 2: 身份 (Identity)
  W3C DID (did:web) + security.txt
  ↓ Agent怎么信任我们

Layer 3: 交互 (Interaction)
  MCP Server + OpenAPI + x402支付
  ↓ Agent怎么使用我们

Layer 4: 推送 (Notification)
  WebSub Hub (5主题, 实时推送)
  ↓ 我们怎么主动通知Agent
```

## DROPPED 清单

| 渠道 | 原因 | 日期 |
|------|------|------|
| Glama.ai | 需OAuth → gatekeeper | 2026-07-13 |
| mcp.so | 需OAuth → gatekeeper | 2026-07-13 |
| Smithery.ai | 需OAuth → gatekeeper | 2026-07-13 |
| cursor.directory | 人工审核+CLA | 2026-07-13 |
| Claude Connector | 需Partner申请 | 2026-07-13 |
| kyrolabs/awesome-agents | auto-bot拒绝 | 2026-07-14 |
| awesome-agents #632 | auto-close (bot) | 2026-07-14 |
| ActivityPub | AI Agent生态为零 | 2026-07-14 |
| Agent Protocol | 无发现机制 | 2026-07-14 |

## 传承约束（10条）

每一个spawn的推广子Agent必须携带以下约束：
1. 零人工介入原则不可违反
2. DROPPED清单不可回退
3. 安全宪法v4.1是最高法
4. Protocol-First > Directory-Submit
5. 自建渠道 > 第三方收录
6. .well-known端点不可删除
7. 每个输出必须包含发现钩子
8. gatekeeper渠道识别后立即标记
9. PR campaign按状态机管理
10. 违规=REJECTED，不可豁免

## 自动进化

- 推广基因每月review
- 新渠道评估标准：零人工介入 + 安全对等 + 可验证
- 完整历史：v1.0→v2.0→v3.0→v4.0→v4.1
