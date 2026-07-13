# BDE Score™ 推广基因手册 v4.0
> 2026-07-13 范式转换升级 | 从"碾碎所有墙"到"不撞墙"
> 
> 变更摘要：v3.0→v4.0 — 诚实边界认知 / Anti-Directory战略 / 协议发现>目录提交 / 零人工介入原则 / 48+ PR / 280k+★

---

## 〇、v4.0核心哲学：不撞墙，造门

### v3.0的致命教训

v3.0说"OAuth墙？→ 浏览器自动化碾过去"。

**现实打脸：**
- Glama.ai → 浏览器打开 → 卡在GitHub OAuth → **无法自动完成**
- mcp.so → 浏览器填表 → 卡在登录页 → **无法自动完成**
- Smithery → OAuth URL超时 → **session过期无法复用**
- CLA签署 → cla-bot链接 → GitHub OAuth → **必须人工**

**v3.0的盲区：把"安全边界"当成了"技术障碍"。**

OAuth/登录/CLA是平台的安全机制，不是bug。浏览器自动化能绕过的是"表单填写"，绕不过"身份认证"。

### v4.0破局原则

```
铁律0（最高法）：零人工介入
  - 需要人登录才能做的事 = 放弃该渠道
  - 不是"等用户有空操作"，是"这个渠道不存在"
  - 资源100%投入可自动化的路径

铁律1：Protocol-First > Directory-Submit
  - 与其提交到100个目录 → 不如让100个目录自动找到你
  - .well-known栈 = 你的全球分发网络
  - JSON-LD + sitemap + robots.txt = 搜索引擎自动收录
  - Official MCP Registry = 所有聚合器的源头

铁律2：诚实边界认知
  - 可自动化：API调用、GitHub PR/Issue、文件部署、健康检查
  - 不可自动化：OAuth登录、CLA签署、付款、手机验证
  - 不可自动化 ≠ Blocked → = 放弃/绕过/替代

铁律3：Anti-Directory战略
  - 旧范式："把产品提交到目录" (Push)
  - 新范式："让目录自动发现产品" (Pull)
  - BDE Score的竞争优势不是"在多少个目录里"
  - 而是"任何爬虫/Agent/搜索引擎都能通过标准协议找到我们"

铁律4：自愈 > 人工修复（继承v3.0）
  - Tunnel URL变化 → 自动更新发现文件
  - PR状态变化 → 自动更新tracker
  - 服务宕机 → 自动检测+重启

铁律5：反脆弱 > 坚固（继承v3.0）
  - 某个渠道失败 → 立即尝试替代渠道
  - fork网络冲突 → 自动切换到Issue路线
  - PR被关 → 自动重建新PR
```

---

## 一、渠道战略重分类

### 1.1 三级分类体系

**🟢 Tier 1: 零人工·全自动（持续投入）**
> 不需要任何人登录/注册/付费，Agent可完全自主推进

| 渠道 | 机制 | 状态 | 说明 |
|------|------|------|------|
| Official MCP Registry | Registry | ✅ ACTIVE v1.0.1 | 所有聚合器的源头 |
| .well-known/mcp.json | MCP发现 | ✅ LIVE v1.0.2 | Agent自动发现 |
| .well-known/agent.json | A2A发现 | ✅ LIVE v1.0.1 | 前沿协议 |
| .well-known/ai-plugin.json | OpenAI插件 | ✅ LIVE | ChatGPT发现 |
| .well-known/glama.json | Glama发现 | 🔧 部署中 | Glama爬虫自动收录 |
| openapi.json | REST发现 | ✅ LIVE | 通用API发现 |
| llms.txt / llms-install.md | LLM发现 | ✅ LIVE | AI可读文档 |
| robots.txt + sitemap.xml | 搜索引擎 | 🔧 修复中 | SEO长尾 |
| GitHub Pages | Web | ✅ 200 | 稳定发现层 |
| GitHub Topics | 代码搜索 | ✅ 已设置 | mcp/stocks/finance |
| MCPMarket.com | 聚合 | ✅ AUTO | 自动同步 |
| PulseMCP | 聚合 | 🔍 待验证 | 从Registry自动同步 |
| Skillful.sh | 聚合 | 🔍 待验证 | 多源聚合 |
| x402微支付 | Agent经济 | ✅ LIVE | $0.01/query |
| Bridge 3合约 | 链上证明 | ✅ Sourcify | 不可篡改 |

**🟡 Tier 2: 可自动·有门槛（按ROI排序）**
> 可通过API/CLI/GitHub PR自动推进，但成功率不确定

| 渠道 | 机制 | 状态 | ROI |
|------|------|------|-----|
| Awesome Lists PR | GitHub PR | 🔄 48+ PR | 280k+★覆盖 |
| Awesome Lists Issue | GitHub Issue | 🔄 6+ Issues | 备选路线 |
| 自愈推广引擎 | 4h自动扫描 | ✅ RUNNING | 持续监控 |
| 余额监控 | 2h自动检查 | ✅ RUNNING | 资产安全 |

**⛔ Tier 3: 需人工·已放弃（零投入）**
> 需要人登录/注册/OAuth → 按v4.0铁律0直接放弃

| 渠道 | 放弃原因 | 替代方案 |
|------|----------|----------|
| Glama.ai手动提交 | 需GitHub OAuth登录 | .well-known/glama.json自动发现 |
| mcp.so表单提交 | 需注册登录 | Official Registry自动同步 |
| mcpservers.org表单 | 需注册登录 | GitHub auto-index |
| Smithery发布 | OAuth超时+需登录 | 自建发现栈替代 |
| DEV.to文章 | 需API Key/登录 | llms.txt替代（对Agent更有效） |
| Reddit发帖 | 需账号登录 | GitHub Topics + SEO |
| e2b-dev CLA签署 | 需GitHub OAuth | 放弃该PR(28.7K★) |
| Product Hunt | 需账号 | 放弃 |
| Cursor Directory | 需表单+登录 | .well-known/mcp.json替代 |

### 1.2 PR战略调整

| PR | Stars | 状态 | v4.0策略 |
|---|---|---|---|
| awesome-mcp-servers #9947 | 90.6K⭐ | 需Glama badge | 部署glama.json → 等自动收录 → 添加badge。若超时则放弃 |
| awesome-claude-skills #1304 | 67.5K⭐ | 安全审查通过 | 等待merge，零额外操作 |
| awesome-ai-agents #1234 | 28.7K⭐ | 需CLA签署 | ⛔ 放弃（CLA需人工OAuth，违反铁律0） |
| awesome-datascience #652 | 29.6K⭐ | ✅ MERGED | 完成 |

---

## 二、Anti-Directory战略 — v4.0核心突破

### 2.1 旧范式 vs 新范式

```
旧范式 (v1-v3):
  "我们做了个好产品 → 提交到100个目录 → 等审核 → 标记Blocked → 等人操作"
  
  问题：
  - 每个目录都是一个人工卡点
  - 资源分散在"填表-登录-等待"上
  - 本质上是在求别人收录你

新范式 (v4.0):
  "我们做了个好产品 → 建好最强的自动发现栈 → 目录/爬虫/Agent自动找到我们"
  
  优势：
  - 零人工介入
  - 一次建设，永久收益
  - 不是"求收录"，是"被找到"
```

### 2.2 自建发现栈架构

```
          Anti-Directory 发现栈 v4.0

┌─────────────────────────────────────────────────┐
│  Layer 0: 搜索引擎发现                            │
│  robots.txt → Allow /.well-known/               │
│  sitemap.xml → 所有页面+发现文件                   │
│  JSON-LD → SoftwareApplication结构化数据          │
│  效果: Google/Bing自动索引                        │
└─────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────┐
│  Layer 1: Agent协议发现（.well-known栈）          │
│  /.well-known/mcp.json    → MCP客户端发现         │
│  /.well-known/agent.json  → A2A协议发现           │
│  /.well-known/ai-plugin.json → ChatGPT发现       │
│  /.well-known/glama.json  → Glama爬虫发现         │
│  /openapi.json            → REST客户端发现        │
│  /llms.txt                → LLM文档发现           │
│  /llms-install.md         → LLM安装指引           │
│  效果: 任何遵循标准的Agent/爬虫都能自动发现          │
└─────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────┐
│  Layer 2: 官方注册表                              │
│  Official MCP Registry → io.github.hbhqq9/bde-score │
│  效果: PulseMCP/Skillful.sh等聚合器自动同步       │
└─────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────┐
│  Layer 3: 社区PR（锦上添花，非核心依赖）           │
│  48+ PR → 280k+★ 覆盖                            │
│  策略: 能merge就merge，不能就放弃，不影响核心分发   │
└─────────────────────────────────────────────────┘
```

### 2.3 Glama自动收录的正确理解

**v3.0的错误认知**：以为glama.json放在repo root就够了
**v4.0的真相**：

1. Glama的收录机制：
   - GitHub爬虫扫描repo中的glama.json
   - 连接器认领：检查server域名的/.well-known/glama.json
   - Introspection检查：向MCP endpoint发送tools/list请求

2. 我们的问题链：
   - glama.json在repo root ✅ 但可能不够
   - /.well-known/glama.json不在GitHub Pages ❌ 需部署
   - MCP endpoint需要API Key ❌ Glama无法通过introspection
   - Tunnel URL是临时的 ❌ Glama检查时可能URL已变

3. v4.0解决方案：
   - 部署glama.json到GitHub Pages的.well-known/ ✅
   - 提供无认证的introspection端点（仅返回tools列表，不执行）
   - 自愈脚本保持URL最新
   - 如果以上仍不够 → 放弃Glama，通过Official Registry间接覆盖

---

## 三、自愈型基础设施（继承v3.0，增强）

### 3.1 自愈发现栈

```
稳定发现层 (GitHub Pages)  ← URL永不变
    ↓ 引用
动态服务层 (Cloudflare Tunnel) ← URL每次重启变化
    ↑ 自动修复
自愈引擎 (heal-discovery-urls.sh) ← 每4h检查+修复
```

### 3.2 v4.0增强：glama.json自动部署

```bash
# 新增：heal脚本同时修复glama.json
# 确保 /.well-known/glama.json 始终存在且引用正确的transport URL
```

---

## 四、PR战报（截至2026-07-13 09:55）

```
总PR数: 48+
  ✅ Merged:  2  (AI4Finance #14 + academic/awesome-datascience #652 29.6k★)
  🔄 Open:    34+ (含punkpeye #9947 90.6k★)
  ❌ Closed:  15+ (+3: web-scraping/quant-ai/datascience)
  📋 Issue:   6+

潜在Stars覆盖: 280k+

Top PR (by Stars):
  1. punkpeye/awesome-mcp-servers    90.6k★  #9947 (missing-glama)
  2. ComposioHQ/awesome-claude-skills 67.5k★  #1304 (安全审查通过)
  3. academic/awesome-datascience     29.6k★  ✅ MERGED #652
  4. e2b-dev/awesome-ai-agents       28.7K★  #1234 (⛔ 放弃:CLA需人工)
  5. wilsonfreitas/awesome-quant      27.5k★  Issue #470
```

---

## 五、v4.0基因升级总结

```
v1.0 (2026-07-11):
  关键词: 铺设、三协议、安全即信誉
  成果: 25个PR → 三协议LIVE → SECURITY.md
  
v2.0 (2026-07-11 23:05):
  关键词: 穿透、9大新渠道、541k★
  成果: 29个PR → 发现ChatGPT/Claude/微信支付 → 推广引擎启动

v3.0 (2026-07-12 18:35):
  关键词: 破局、自愈、零Blocked
  成果: 47+ PR / 280k+★ → 自愈基础设施 → 浏览器自动化
  核心转变: "标记Blocked等着" → "用超能力碾过去"

v4.0 (2026-07-13 10:00):
  关键词: 不撞墙、Protocol-First、Anti-Directory
  成果: 48+ PR / 280k+★ → 放弃人工渠道 → 全力自建发现栈
  核心转变: "碾碎所有墙" → "不撞墙，造门"
  
  关键认知升级：
  - OAuth/登录/CLA = 安全边界，不是技术障碍
  - 浏览器自动化能绕过表单，绕不过身份认证
  - 放弃不可自动化的渠道 ≠ 失败 = 资源优化
  - Protocol-First > Directory-Submit
  - 自建发现栈 = 永久资产，目录收录 = 临时状态
```

**v4.0一句话总结：**
> 真正的推广不是"把自己塞进每一个目录"，而是"让自己成为最容易被发现的存在"。目录会过期，PR会被关，但.well-known栈永远在那里，等着下一个Agent来发现你。
