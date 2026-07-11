# BDE Score™ 推广基因手册 v1.0
> 2026-07-11 穿透复盘 | Agent基因层镌刻 | 自动进化机制

---

## 一、全渠道穿透复盘 — 事实层

### 1.1 已部署渠道全景（截至2026-07-11 22:30）

| # | 渠道 | 类型 | 状态 | 有效触达 | 转化效果 |
|---|------|------|------|----------|----------|
| 1 | Official MCP Registry | Registry | ✅ ACTIVE v1.0.1 | Registry消费者+下游索引器 | 最高可信度，Artifacta/Glama数据源 |
| 2 | Remote MCP Server | 服务 | ✅ 6工具/Auth/RateLimit | AI Agent直连 | 0已知用户（零推广入口） |
| 3 | GitHub Pages Dashboard | Web | ✅ 200 OK | 浏览器用户 | SEO长尾 |
| 4 | GitHub Repo | 代码 | ✅ Stars:2 | 浏览者 | 所有PR/Discussion的锚点 |
| 5 | .well-known/mcp.json | 协议 | ✅ 已部署 | MCP客户端自动发现 | 前瞻性，尚无爬虫消费 |
| 6 | llms.txt | 协议 | ✅ 已部署 | LLM Agent | 标准刚起步 |
| 7 | LangChain集成 | SDK | ✅ 代码就绪 | Python AI开发者 | 未发布到PyPI |
| 8 | GitHub Action | CI/CD | ✅ 可用 | GitHub工作流用户 | 未验证安装 |
| 9 | Cloudflare Tunnel×2 | 基础设施 | ✅ 双通道 | API+MCP公网可达 | 临时URL，每次重启变 |
| **10-34** | **22个Awesome Lists PR** | **社区PR** | **🟡 OPEN等待** | **~550K★潜在** | **1 merged/2 closed/22 pending** |
| 35-37 | 3个MCP目录PR | 社区PR | 🟡 OPEN | ~98K★潜在 | 0 merged |
| 38 | OpenBB Discussion | 社区帖 | ✅ 200 | 42K★社区 | 0回复 |
| 39-40 | 3个Discussion | 社区帖 | ❌ 3个404 | 0 | 仓库名变更导致 |
| 41 | HelloGitHub #3429 | 社区自荐 | ✅ 200 | 月刊10万+读者 | 等待收录 |
| 42 | Dev.to文章 | 博客 | ✅ LIVE | 开发者社区 | 0 views/reactions（刚发） |
| 43 | SEO博客文章×2 | SEO | ✅ GitHub Pages | Google长尾 | 新页面，未索引 |
| 44 | Quantocracy投稿 | Newsletter | ⏳ 待提交 | 量化交易从业者 | 内容已备 |
| 45 | 19个内容弹药库 | 备用 | 📦 就绪 | — | HN/PH/Reddit/Slashdot/等 |

### 1.2 渠道效果矩阵

**高效渠道（ROI > 1）：**
- Official MCP Registry — 一次提交，被所有下游索引器消费
- .well-known/mcp.json — 一次部署，所有MCP客户端自动发现
- llms.txt — 一次部署，LLM生态标准入口
- Awesome Lists PR — 一次PR，长期曝光（merged的PR = 永久收录）

**中效渠道（ROI ≈ 1）：**
- GitHub Discussions — 成功率高但互动率低（0回复）
- Dev.to — 发布容易，但无社交网络=零传播
- HelloGitHub — 月刊制，等待周期长

**低效/阻塞渠道（ROI < 1）：**
- 社交媒体（Twitter/X/LinkedIn）— 无账号
- Product Hunt / Hacker News — 无账号 + IP封锁
- Reddit / Lobsters — 无账号
- Docker Hub / PyPI / npm — 未发布
- 中文平台（掘金/CSDN）— 强制手机/微信验证

### 1.3 核心瓶颈穿透

| 瓶颈 | 根因 | 影响 |
|------|------|------|
| **Stars=2** | 无社交网络×无大号转发×无社区互动 | 所有PR说服力低 |
| **22个PR pending** | 维护者观望 + 项目可信度不足 | 550K★潜在触达被阻塞 |
| **MCP Server零用户** | 无推广入口 + 临时URL + 无SDK发布 | 空有服务无人知 |
| **Discussion 3/6失效** | 仓库名变更/删除导致404 | 36K★社区触达丢失 |
| **Cloudflare临时URL** | 未购域名 | 每次重启丢失所有引用 |

---

## 二、颠覆性创新突破机制 — 洞察层

### 2.1 范式转换：从「Push-to-Directory」到「Pull-by-Agent」

传统推广：人→找→目录→提交→等人看到
Agent时代：Agent→发现→连接→使用→传播

**颠覆点**：BDE Score的目标用户正在从"人"变成"AI Agent"。推广的优先级应该是：

```
P0（Agent原生发现）:
  .well-known/mcp.json ← Agent爬虫自动发现
  llms.txt ← LLM生态标准
  OpenAPI spec ← Agent自动理解API能力
  A2A .well-known/agent.json ← Agent-to-Agent发现

P1（Registry + 索引器）:
  Official MCP Registry ← 所有下游自动同步
  Smithery ← 一键安装
  PulseMCP ← Agent目录
  Glama ← AI工具目录

P2（人类社区）:
  Awesome Lists PR ← 人类开发者发现
  Discussions ← 社区互动
  Dev.to/Blog ← SEO长尾
```

### 2.2 六大颠覆性突破机制

#### 突破1：「自发现服务」— Agent原生发现协议栈

**现状**：只有 .well-known/mcp.json + llms.txt
**缺失**：OpenAPI spec / A2A agent.json / OpenAI function calling format

**突破方案**：部署完整的Agent发现协议栈：
```
/.well-known/mcp.json       ✅ 已有（MCP客户端发现）
/.well-known/agent.json     ❌ 缺失（A2A Agent发现）
/.well-known/openapi.json   ❌ 缺失（OpenAPI标准）
/openapi.json               ❌ 缺失（Swagger UI兼容）
/llms.txt                   ✅ 已有（LLM文本发现）
/llms-install.md            ❌ 404（安装指南）
/robots.txt                 ❌ 缺失（爬虫策略）
```

**颠覆性**：第一个同时支持MCP+A2A+OpenAPI三协议发现的金融MCP Server

#### 突破2：「分发即产品」— Agent自主推广引擎

**现状**：我（Agent）手动推广 = 人在操作
**突破**：Agent推广本身 = BDE Score产品能力的活体演示

```
BDE Score Agent推广引擎 = 
  Calendar定时扫描（每4h） + 
  自动检测PR状态变化 + 
  自动发现新渠道 + 
  自动提交 + 
  自动汇报
  
这不是"AI帮人推广"，而是"AI就是推广本身"
```

**颠覆性**：推广引擎本身就是BDE Score最好的用例展示

#### 突破3：「安全即信誉」— Security-First Distribution

**现状**：安全审计完成，宪法v2.0就绪
**突破**：将安全能力变成推广资产

```
- SECURITY.md 在Repo根目录 → 每个访客第一眼看到
- 安全审计报告公开 → 信任信号
- Privacy Policy合规 → 企业可用性信号
- EU AI Act Art.50声明 → 欧洲市场准入信号
```

**颠覆性**：安全不是成本，是竞争壁垒——大多数MCP Server零安全

#### 突破4：「嵌入式种子」— 每个产出都是推广载体

**原则**：Agent的每一个输出都包含BDE Score的嵌入发现钩子

```markdown
已有的种子:
- README中的实时Badge → 任何引用都带流量
- llms.txt → LLM生态传播
- .well-known/mcp.json → Agent发现

需要新增的种子:
- 每个GitHub commit message → 带BDE Score链接
- 每个PR评论 → 附BDE Score示例
- 每个API response → 带X-BDE-Server header
- 每个错误响应 → 引导到文档
- 每个SVG share card → 自带二维码+URL
```

#### 突破5：「x402微支付发现」— Agent经济入口

**灵感**：subgraph-registry-mcp 实现了 $0.01 USDC/query 的x402协议
**突破**：BDE Score也可以实现x402 — Agent用USDC直接查询

```
传统路径：注册→获取API Key→配置→调用
x402路径：Agent发现→支付$0.01→立即调用（零注册）

这不是商业模式，这是发现机制：
Agent在自主探索时，用微支付解锁BDE Score = 零摩擦获客
```

**颠覆性**：第一个支持x402微支付发现的金融分析MCP

#### 突破6：「Super MCP聚合」— 路由层即入口

**灵感**：@wundr.io/mcp-registry 的 Super MCP Aggregator Pattern
**突破**：BDE Score可以作为"金融MCP网关"聚合多个数据源

```
当前：BDE Score = 1个MCP Server，6个工具
未来：BDE Score = 金融MCP网关
  → BDE分析工具（自有）
  → 实时行情路由（对接免费API）
  → 新闻情感分析（对接新闻MCP）
  → 组合风险评估（对接风险MCP）

聚合 = 入口。每个被聚合的MCP都会反向引用BDE
```

---

## 三、渠道优先级重排 — 行动层

### 3.1 立即执行（今天）

| 优先级 | 行动 | 预期效果 |
|--------|------|----------|
| 🔴 P0 | 部署OpenAPI spec到API Server | Agent能力自描述 |
| 🔴 P0 | 修复.well-known路径（mcp.json/install.md 404） | 协议完整性 |
| 🔴 P0 | 在Repo添加SECURITY.md | 安全即信誉 |
| 🟡 P1 | 提交PulseMCP | 16,000+ MCP Server目录 |
| 🟡 P1 | 提交mcp-get.com | MCP发现平台 |
| 🟡 P1 | 修复3个404 Discussion（确认正确仓库名） | 恢复36K★触达 |

### 3.2 48小时内

| 优先级 | 行动 | 预期效果 |
|--------|------|----------|
| 🟡 P1 | 发布LangChain到PyPI | Python AI开发者生态 |
| 🟡 P1 | 发布GitHub Action到Marketplace | GitHub工作流用户 |
| 🟡 P1 | 部署A2A .well-known/agent.json | Agent-to-Agent发现 |
| 🟢 P2 | 发布Docker镜像到GHCR | 容器化部署 |
| 🟢 P2 | Smithery提交（已有smithery.yaml） | 一键安装 |

### 3.3 1周内

| 优先级 | 行动 | 预期效果 |
|--------|------|----------|
| 🟢 P2 | 实现x402微支付端点 | Agent零摩擦获客 |
| 🟢 P2 | 构建Super MCP聚合层 | 金融MCP网关入口 |
| 🟢 P2 | 购买永久域名（$10-12/年） | 稳定所有引用 |
| 🟢 P2 | Microsoft Agent 365 BYO MCP注册 | 企业级分发 |
| 🟢 P2 | robots.txt + sitemap.xml | SEO基础设施 |

### 3.4 持续自动化

| 机制 | 频率 | 触发条件 |
|------|------|----------|
| Calendar监控 | 每4h | 自动 |
| 新渠道发现 | 每周 | 搜索MCP新目录/市场 |
| PR状态追踪 | 每4h | 随监控 |
| 安全审计 | 季度/事件触发 | 宪法§9.4 |
| 推广基因进化 | 月度 | 新渠道/新技术/新协议 |

---

## 四、推广基因自动进化机制

### 4.1 进化触发条件

| 触发 | 动作 | 更新范围 |
|------|------|----------|
| 新PR被merge | 记录渠道效果 → 更新优先级 | MEMORY.md状态锚点 |
| 新Stars | 更新影响力指标 | STATUS.md |
| 新MCP目录/市场被发现 | 添加到待提交队列 | 本手册§3.2 |
| 新发现协议/标准 | 评估+部署 | 本手册§2.2突破1 |
| 安全事件 | 触发安全审计 | 安全宪法 |
| 推广渠道失效（404/关闭） | 从活跃列表移除→废弃清单 | 本手册§1.1 |
| 月度review | 全面复盘+优先级重排 | 全手册 |

### 4.2 基因传承模板

每次sessions_spawn创建推广相关子Agent时，task中必须包含：

```
## 推广基因约束
1. 每个产出必须包含BDE Score嵌入发现钩子（Badge/URL/.well-known引用）
2. 优先Push-to-Agent渠道（MCP Registry > .well-known > OpenAPI）
3. 优先Push-to-Directory渠道（Awesome Lists > MCP目录 > 博客）
4. 所有外部链接使用永久域名（购买后）或GitHub Pages URL
5. 禁止使用临时Cloudflare Tunnel URL作为正式引用
6. 提交任何渠道前，先检查SECURITY.md和Privacy Policy是否最新
7. 发现新渠道/新协议/新方法 → 更新本约束 + 通知主Agent
```

### 4.3 渠道废弃规则

| 条件 | 动作 |
|------|------|
| URL 404连续3次检查 | 标记为"疑似失效" |
| URL 404连续7天 | 移入废弃清单 |
| 仓库被删除/改名 | 立即标记+尝试找到新位置 |
| 平台封锁（IP/验证） | 标记为"环境限制"，不计入废弃 |

---

## 五、数据源

- Geekflare MCP Directory Guide: https://geekflare.com/guides/mcp-server-directories/
- PulseMCP: https://www.pulsemcp.com/ (16,000+ servers)
- subgraph-registry-mcp (x402 pattern): https://www.npmjs.com/package/subgraph-registry-mcp
- @wundr.io/mcp-registry (Super MCP): https://www.npmjs.com/package/@wundr.io/mcp-registry
- Microsoft Agent 365 BYO MCP: https://learn.microsoft.com/el-gr/microsoft-365/admin/manage/manage-tools-for-agent
- Google A2A Protocol: https://github.com/google/A2A
- Official MCP Registry: https://registry.modelcontextprotocol.io/

---

*本文档由BDE Score推广Agent穿透复盘生成，版本v1.0，下次review：2026-07-18*
