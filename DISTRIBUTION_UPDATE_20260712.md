# BDE Score 分发渠道更新 — 2026-07-12

## 本轮更新内容

### 1. Agent Discovery Protocols（新增）
- `.well-known/ai-plugin.json` — ChatGPT Plugin 发现协议
- `.well-known/agent.json` — A2A（Agent-to-Agent）协议
- `.well-known/mcp.json` — MCP 服务器发现协议

**效果**：任何 AI Agent 都可以通过标准协议自动发现 BDE Score 服务

### 2. Agent Compliance Quick Check（已上线）
- 端点：`/compliance-check?url=<MCP_ENDPOINT>`
- 10项自动检测，100分制评分
- JSON + HTML 双版本输出
- 速率限制：3次/分钟/IP
- **引流逻辑**：免费快检 → 发现问题 → 推荐付费深度评估

### 3. Privacy/Terms 页面（铁律VII合规）
- `/privacy` — GDPR/CCPA 合规隐私政策
- `/terms` — 服务条款
- 修正了"No IP collected"错误措辞

### 4. Tunnel URL 更新
- API: `bathroom-ebooks-isa-accommodation.trycloudflare.com`
- MCP: `tex-adequate-date-facing.trycloudflare.com/mcp`
- 代码中所有旧 URL 已替换

## PR 状态
| 仓库 | Stars | 状态 |
|------|-------|------|
| AI4Finance/Awesome_AI4Finance | — | ✅ MERGED |
| punkpeye/awesome-mcp-servers | 90k+ | 🟡 待 Glama.ai badge |
| 其他7个金融/量化类 | — | 🟡 Open |
| wong2/appcypher | — | 🔴 需手动提交 |

## 待办
1. 🔴 Glama.ai 提交（computer_use 进行中）
2. 🟡 wong2/appcypher 手动 PR
3. 🟡 EU AI Act Art.50 倒计时 ~20天
4. 🟡 支付后端 USDC → API Key 实际测试

## Git Commits
```
afacdd6 feat: Agent discovery protocols + compliance check tool promotion
2db08f8 fix: update all tunnel URLs to current active tunnels
d60d2ea docs: add comprehensive system status document
75cf7b7 feat: Agent Compliance Quick Check + Privacy/Terms pages
7c62fde perf: replace all sqlite3.connect with _get_db() for WAL mode
```
