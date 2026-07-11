# BDE Score™ MCP Server — 市场提交状态检查报告

**报告日期:** 2026-07-11  
**检查范围:** Smithery.ai, MCP.run, Glama.ai, Composio.dev, Toolhouse.ai + 新增高价值市场  

---

## 一、核心发现摘要

| 维度 | 状态 |
|------|------|
| 当前活跃分发渠道 | 4 个 (Official Registry + 3 个 Awesome List PR + Glama pending) |
| 可直接提交的高价值新市场 | 5 个 (Smithery, mcp-marketplace.io, mcpmeter.com, mcpmarket.com, MCPFind) |
| 最大阻塞问题 | ⚠️ **Tunnel URL 不稳定** — 每次重启改变，多数市场需要持久 URL |
| API Key 认证影响 | 新增认证后，部分无认证提交路径需调整配置说明 |

---

## 二、指定平台逐一检查

### 1. Smithery.ai

**当前状态:** 🔍 追踪器标记为"Auto-syncing from Official Registry"  
**实际调查结果:**

- Smithery 并非纯自动同步——它需要**主动提交**，不是从 Registry 自动拉取
- 支持 **Streamable HTTP** 远程服务器发布，BDE Score 的部署模式完全匹配
- 提交方式: Web Dashboard (smithery.ai/new) 或 CLI (`smithery mcp publish`)
- 平台规模: **~7,000 servers**，策展式审核
- **Smithery Quality Score** 系统: 10 维度评分，最高 100 分
  - BDE Score 已具备的加分项: Tool Annotations ✅, Read-only ✅, Streamable HTTP ✅
  - 需要补充: `smithery.yaml` 或 `manifest.json` 元数据文件
  - 需要: 创建 Smithery 账号

**提交就绪度:** 🟡 需要准备
- [ ] 注册 Smithery 账号
- [ ] 准备持久化 URL (当前 Cloudflare Tunnel 不满足)
- [ ] 创建 manifest.json 描述服务器元数据
- [ ] 配置 API Key 为 session configuration (Smithery 支持 configSchema)

**付费用户潜力:** ⭐⭐⭐⭐ — Smithery 用户以 Agent 框架开发者和 Claude/Cursor 重度用户为主

---

### 2. MCP.run

**当前状态:** ❌ 该平台不存在  
**实际调查结果:**

- "MCP.run" 作为独立 MCP 市场**未发现任何活跃平台**
- 搜索结果显示相关的是 **mcp-marketplace.io** (独立策展市场) 和 **mcp.so** (社区目录)
- 建议将 MCP.run 从追踪器中移除，替换为实际存在的平台

---

### 3. Glama.ai

**当前状态:** ⏳ glama.json 已提交，等待 24h 索引  
**实际调查结果:**

- Glama 现在是最大的 MCP 目录之一: **23,250 servers, 3,209 connectors, 154,716 tools**
- 两种提交路径:
  1. **开源服务器** (从 GitHub 自动索引): 需要 repo 有 `mcp` topic + `glama.json`
  2. **Connector** (远程端点): 需要 HTTPS URL + streamable-http 传输
- BDE Score 走 Connector 路径更合适 (远程 MCP 服务器)
- **自动质量检查**: license 检测、安全扫描、健康测试
- 如果 glama.json 已提交且 repo 有正确 topics，应已被索引

**提交就绪度:** 🟢 大概率已生效
- [ ] 验证: 访问 `glama.ai/mcp` 搜索 "bde-score" 确认是否出现
- [ ] 确认 GitHub repo topics 包含 `mcp`, `model-context-protocol`
- [ ] 如未出现，可通过 Glama 的 "Add MCP Server → Connector" 手动提交

**付费用户潜力:** ⭐⭐⭐ — Glama 有 50,000+ 开发者用户，提供浏览器内 MCP Inspector 测试

---

### 4. Composio.dev

**当前状态:** 🆕 新发现平台，未在此前追踪器中  
**实际调查结果:**

- Composio 是**托管式 MCP 平台**，不是开放市场
- 500+ 自建 MCP 服务器，全部由 Composio 团队维护
- 定位: 企业级 AI Agent 集成中间件，处理 OAuth、安全、凭证管理
- **不接受第三方直接提交** — 所有服务器由 Composio 团队构建和维护
- 面向用户: 开发者通过 Composio 统一管理多个 SaaS 工具的 MCP 接入
- 定价: Free / $29/mo / $229/mo / Enterprise

**结论:** ❌ 不适合提交  
Composio 是一个**托管平台**而非**开放市场**。BDE Score 无法作为第三方提交到 Composio。除非 Composio 团队主动集成，否则此路不通。

**替代思路:** 如果 BDE Score 用户量增长，可以联系 Composio BD (bd@composio.dev) 提议集成。

---

### 5. Toolhouse.ai

**当前状态:** 🆕 新发现平台，未在此前追踪器中  
**实际调查结果:**

- Toolhouse 是 AI Agent 基础设施平台，提供 SDK + Tool Store + Agent Studio
- 支持 MCP 通过 `toolhouse-mcp` bridge 包
- Tool Store 有 ~112 个预构建工具 (web search, code exec, email 等)
- **关键区别**: Toolhouse 不是传统 MCP 目录——它是**执行基础设施**
- 开发者可以通过 SDK 的 `registerLocalTool()` 注册自定义工具
- 支持 OAuth 集成 (Google Calendar, Gmail, Slack 等)

**提交就绪度:** 🟡 有限机会
- Toolhouse 的 Tool Store 主要面向通用工具，BDE Score 的金融数据查询需要评估是否匹配
- 可以通过 Toolhouse 的 MCP bridge 将 BDE Score 作为自定义 MCP 服务器接入
- 但这不是"提交到市场"，而是"接入基础设施"

**付费用户潜力:** ⭐⭐ — Toolhouse 用户主要是 Agent 构建者，不是直接金融数据消费者

---

## 三、新增高价值市场推荐

基于调研，以下 5 个新市场值得提交，按优先级排序:

### 🔥 高优先级 (付费变现潜力)

#### A. MCP Marketplace (mcp-marketplace.io)
- **模式:** 策展市场 + Stripe 支付集成
- **分成:** 创作者保留 85%
- **审核:** 自动安全扫描，24h 内批准
- **特点:** 支持免费/付费/订阅模式，Creator Dashboard 追踪安装和收入
- **提交方式:** 填写 listing form → 安全扫描 → 上线
- **⭐ 推荐理由:** 这是目前最接近 "MCP App Store" 的平台，支持变现
- **付费用户潜力:** ⭐⭐⭐⭐⭐ — 核心定位就是付费 MCP 交易

#### B. MCPPMeter (mcpmeter.com)
- **模式:** 代理网关 + 按调用计费
- **分成:** 创始人费率 10% (前 100 名, 12 个月) / 标准 20%
- **结算:** 每月 1 号通过 Stripe Connect 打款
- **特点:** 不托管服务器，只加 metering 代理层
- **定价建议:** $0.001-$0.005/调用 + 50-500 次/月免费额度
- **⭐ 推荐理由:** 最低摩擦的变现方式，BDE Score 保持自有基础设施
- **付费用户潜力:** ⭐⭐⭐⭐ — 适合 BDE Score 的远程部署模式

#### C. MCPMarket (mcpmarket.com)
- **模式:** 社区目录 + 付费加速审核
- **费用:** 免费排队 (2-4 周) / $29 加急 (24h 内 + Official 徽章)
- **提交方式:** 提交 GitHub URL → 审核
- **付费用户潜力:** ⭐⭐ — 主要是发现渠道

### 📋 中优先级 (发现渠道)

#### D. MCPFind (mcpfind.org)
- **规模:** 6,714 servers, 21 分类
- **模式:** 开源目录，从 Registry + GitHub 自动同步
- **提交方式:** 已在 Official Registry → 应已自动收录
- **状态:** 🟢 大概率已生效 (因 BDE Score 已在 Official Registry)

#### E. MCPize Marketplace (mcpize.com)
- **模式:** 策展市场 + OAuth + Stripe 计费
- **分成:** 创作者保留 85%
- **特点:** 高质量策展，支持 x402 加密支付
- **提交方式:** 通过 MCPize CLI 或 Dashboard 提交
- **付费用户潜力:** ⭐⭐⭐⭐ — 有变现能力

---

## 四、关键阻塞问题

### 🚨 问题 1: Tunnel URL 不稳定

**当前:** `retrieve-jobs-congress-made.trycloudflare.com/mcp`  
**问题:** Cloudflare 免费 Tunnel 每次重启改变 URL  
**影响:** 所有需要固定 URL 的市场 (Smithery, Glama Connector, mcp-marketplace.io, mcpmeter.com) 都无法使用

**解决方案 (按成本排序):**
1. **固定域名 Tunnel** — Cloudflare 付费计划 ($24/月) 支持固定域名
2. **自有域名反向代理** — 用自有域名 (如 `mcp.bde-score.com`) 指向 Tunnel
3. **Vercel/Fly.io 部署** — 将 MCP server 部署到有固定 URL 的平台
4. **Glama Hosting** — Glama 提供一键托管，自动生成固定 URL

**建议:** 方案 2 或 3 优先。方案 2 成本最低（如果已有域名），方案 3 最稳定。

### 🚨 问题 2: API Key 认证对提交的影响

**变更:** MCP Server 已添加 API Key 认证  
**影响:**
- Smithery: 需要在 configSchema 中声明 API Key 为 required session config
- Glama Connector: 提交时需提供 test credentials 供 Glama 验证
- mcp-marketplace.io: 认证信息需要在 listing 中明确说明
- mcpmeter.com: 不影响，代理层转发认证请求

**建议:** 准备一份标准的认证说明模板:
```
Authentication: API Key required
Header: Authorization: Bearer <your-api-key>
Get your key: https://hbhqq9.github.io/bde-score/
```

---

## 五、下一步行动计划

### 立即行动 (本周)

| # | 行动 | 依赖 | 预期结果 |
|---|------|------|---------|
| 1 | 验证 Glama 索引状态 | 无 | 确认是否已出现在 Glama 目录 |
| 2 | 确定固定 URL 方案 | 决定部署策略 | 解锁所有需要固定 URL 的市场 |
| 3 | 注册 Smithery 账号 | 无 | 准备提交 |
| 4 | 更新追踪器: 移除 MCP.run | 无 | 清理数据 |

### 短期行动 (下周)

| # | 行动 | 依赖 | 预期结果 |
|---|------|------|---------|
| 5 | 提交 Smithery | #2, #3 | 新增 ~7K 用户曝光 |
| 6 | 提交 mcp-marketplace.io | #2 | 开启变现渠道 |
| 7 | 提交 mcpmeter.com | #2 | 按调用计费变现 |
| 8 | 验证 MCPFind 自动收录 | 无 | 确认分发覆盖 |

### 中期行动 (2-4 周)

| # | 行动 | 依赖 | 预期结果 |
|---|------|------|---------|
| 9 | 提交 MCPize Marketplace | #2 | 策展市场曝光 + 变现 |
| 10 | 完成 Claude Connector 提交 | 浏览器 | 进入 Claude 官方目录 |
| 11 | 提交 cursor.directory | 浏览器 | 250K MAU 曝光 |
| 12 | 评估 Composio 集成可能性 | 用户量数据 | 长期 BD 机会 |

---

## 六、平台对比矩阵 (付费用户获取效率)

| 平台 | 提交难度 | 审核时间 | 用户量级 | 变现能力 | 优先级 |
|------|---------|---------|---------|---------|--------|
| mcp-marketplace.io | 🟢 低 | <24h | 未知 | ✅ Stripe | 🔥 P0 |
| Smithery | 🟡 中 | 2-5 天 | ~7K | 有限 | 🔥 P0 |
| mcpmeter.com | 🟢 低 | 当天 | 新兴 | ✅ 按调用 | 🔥 P0 |
| Glama | 🟢 低 | 自动 | 50K+ 开发者 | 间接 | P1 |
| MCPize | 🟡 中 | 策展 | 增长中 | ✅ Stripe | P1 |
| MCPFind | 🟢 自动 | 自动 | 6.7K | 无 | P2 |
| Composio | 🔴 不可行 | — | 100K+ 开发者 | N/A | ❌ |
| Toolhouse | 🟡 中 | — | 企业用户 | 间接 | P2 |

---

## 七、总结

BDE Score MCP Server 的分发渠道已从最初的 Official Registry + Awesome Lists 扩展到需要覆盖更多**有变现能力的市场**。当前最大的瓶颈是 **Tunnel URL 不稳定性**——解决这个问题后，可以在一个下午内完成 Smithery、mcp-marketplace.io、mcpmeter.com 三个高价值平台的提交。

**最高 ROI 行动:** 固定 URL → 提交 mcp-marketplace.io（开启付费渠道）→ 提交 Smithery（最大开发者市场）。
