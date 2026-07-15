# BDE Score 经济模型收益加速行动计划

> **日期**: 2026-07-15  
> **版本**: v1.0  
> **基于**: 竞品与市场变化半月扫描（2026-07-15）  
> **收款地址**: `0x349Eea0E2f4d3594797851758325Da3eb49D4343`（Base L2, USDC）  
> **单位成本**: $0.000752/event（PoC实测值，x402协议）  

---

## 一、形势总览：三个关键时间窗口正在叠加

| 事件 | 时间 | 影响 |
|------|------|------|
| 中国《智能体规范应用与创新发展实施意见》生效 | **今日 (7/15)** | 全球首个AI Agent专项监管框架，三级决策授权结构 |
| EU AI Act Art.50透明度义务执行 | **8/2 (18天)** 或 **12/2 (Omnibus延期)** | 78%企业未准备好，罚款€15M或3%全球营业额 |
| IETF 126维也纳会议 (3个Agent BoF) | **7/18-24 (3天后)** | agentproto / DAWN / DMSC — 协议标准化的决定性时刻 |
| MCP 2026-07-28规范发布 | **7/28** | 最大规模MCP修订，无状态核心+扩展框架 |

**核心判断**: 监管压力（中国+EU）正在制造全球性的Agent合规需求，而所有竞品（NeuralTrust $20M / ChatSee $6.5M / NewCore $66M / Arcade $60M）全部聚焦off-chain，链上合规治理空白正在急剧扩大。AGL是当前唯一将治理锚定在链上的开源方案。

---

## 二、分层行动计划

### 🔴 立即执行（今日7/15 — 7/17，72小时冲刺）

#### 行动1：推进3个可合并PR → 扩大GitHub可见度

| PR | 目标仓库 | Stars | 状态 | 预计流量 | 优先级 |
|----|---------|-------|------|---------|--------|
| **#1234** | e2b (AI Agent沙箱) | 9k+ | CLA-signed, clean | ⭐⭐⭐ 高（Agent开发者直接受众） | P0 |
| **#10049** | punkpeye/awesome-chatgpt | 90.6k | Clean, 1 addition | ⭐⭐⭐ 最高（全平台最大流量入口） | P0 |
| **#309** | best-of-python | 高流量 | Clean | ⭐⭐ 中（Python生态曝光） | P0 |

**执行步骤**:
1. 确认3个PR无reviewer请求变更
2. 在相关仓库Issues/Discussions发布简短技术说明，提及AGL合规能力
3. 准备合并后Twitter/LinkedIn公告文案

#### 行动2：准备IETF 126 BoF材料（7/18开始）

3个直接相关的BoF session：

| BoF | 日期时间(CEST) | 与AGL的关系 | 行动 |
|-----|--------------|------------|------|
| **DAWN** (Agent发现) | 7/21 14:00-16:00 | AGL Receipt可作Agent发现的可信凭证 | 提交远程参会，展示Receipt Schema |
| **DMSC** (多Agent安全协作) | 7/22 09:00-11:00 | AGL治理管道=Agent Gateway策略层的链上验证 | 重点参与，展示$0.000752/event的治理可行性 |
| **agentproto** (Agent通信协议) | 7/23 09:00-11:00 | 核心战场：MCP/A2A/ACP/ANP vs AGL治理层 | 必须参与，提交Internet-Draft草案意向 |

**执行步骤**:
1. 注册IETF 126远程参会（免费）
2. 准备3页AGL技术摘要（已有`AGL_IETF126_BoF_Brief.md`，更新监管数据）
3. 加入agentproto和DMSC邮件列表，提前发言
4. 准备live demo：实时展示一笔$0.000752的治理锚定交易

#### 行动3：发布"中国+EU双监管生效"BD邮件

**目标**: 向所有已建立联系的中国+EU AI合规负责人发送紧急通知

**邮件主题**: `[URGENT] 中国智能体治理今日生效 + EU Art.50倒计时18天 — 链上合规方案`

### 🟡 本周执行（7/16 — 7/24）

#### 行动4：推进awesome-quant #474合并

- 当前状态：等待10 stars
- 策略：在quant/finance相关社区推广，获取必要stars
- 价值：量化社区是BDE Score的直接受众

#### 行动5：推进mcp-find #95和time_series #50

- mcp-find：MCP生态搜索工具，合并后增加Agent开发者可见度
- time_series：时间序列数据工具，与BDE多因子分析直接相关

#### 行动6：IETF 126会议周BD攻势

**目标1：与NeuralTrust团队建立联系**

NeuralTrust（$20M融资，EU初创）核心产品：
- **TrustGate**：Agent Gateway — 运行时策略执行
- **TrustGuard**：Agent Runtime Security — 行为监控
- **TrustLens**：Agent Posture Management — 持续可观测性

**合作切入点**: NeuralTrust的全部产品是off-chain的。AGL可以为他们提供链上验证层，形成"off-chain执行 + on-chain验证"的完整合规栈。

**BD话术**:
> "NeuralTrust的TrustGate解决策略执行，TrustGuard解决行为监控。但当客户需要向EU监管证明'你7月22日的那次Agent操作确实遵守了Art.50披露义务'时，off-chain日志可以被篡改、可以被质疑。AGL在Base L2上提供$0.000752/event的不可篡改合规证明。我们不是竞品，我们是你的链上验证插件。"

**目标2：在agentproto BoF推动"治理层"纳入协议讨论**

核心论点：
- MCP/A2A/ACP解决了Agent"能做什么"和"怎么通信"
- 但没有任何协议解决"Agent做了一件事后，怎么证明它遵守了规则"
- AGL的Receipt Schema可以作为协议层的治理扩展，不需要新建传输层
- 成本论证：$0.000752/event在Base L2，相当于每次Agent操作增加不到0.1美分的合规成本

#### 行动7：针对中国监管新规的BD材料

**中国《智能体规范应用与创新发展实施意见》核心要求（7/15生效）**:

1. **三级决策授权结构**:
   - 仅限用户本人决策（高敏感操作）
   - 用户授权决策（中风险操作）
   - 智能体自主决策（低风险操作）

2. **高风险领域强制备案**: 金融、医疗、教育等领域必须向网信办备案

3. **行为管控**: 规则内嵌、行为围栏等技术要求

4. **审计追溯**: 操作留痕、可追溯

5. **19个典型应用场景**: 覆盖政务、金融、医疗、教育、制造等

**AGL与中国监管的对接点**:
- Receipt = 三级决策授权的链上证据
- SHA-256锚定 = 不可篡改的行为审计记录
- $0.000752/event = 大规模部署的经济可行性

**BD话术（中国市场）**:
> "《实施意见》今天生效，要求在智能体治理中实现'决策权限明确、行为可管控、风险可追溯'。AGL提供开源的链上治理层，每个Agent决策生成不可篡改的合规Receipt，成本不到1美分/次。无论是金融场景的备案，还是医疗场景的审计追溯，AGL都能提供监管方认可的技术证据。"

### 🟢 本月执行（7/25 — 8/15）

#### 行动8：利用MCP 2026-07-28新规范发布窗口

MCP新版核心变化与AGL的关系：
- **无状态核心**: 移除session handshake → 每笔请求独立 → 完美适配AGL Receipt模式
- **显式句柄模式**: 状态对模型可见 → Receipt hash可作为句柄传递
- **扩展框架正式化**: reverse-DNS标识符 + 能力协商 → AGL可注册为官方扩展
- **W3C Trace Context传播**: 与AGL的链上追溯天然对齐

**执行步骤**:
1. 在MCP 2026-07-28发布当天，提交AGL作为官方Extension的提案
2. 更新llms.txt / openapi.json以适配新规范
3. 发布技术博客："AGL Receipt作为MCP治理扩展的设计"

#### 行动9：启动收入流

**收入模型A：合规评估服务（最快变现）**

| 服务 | 定价 | 目标客户 |
|------|------|---------|
| AI系统Art.50合规评估报告 | €5,000-50,000/份 | EU面向的AI产品公司 |
| AGL部署咨询 | $2,000-10,000/项目 | 需要链上审计的企业 |
| 合规Dashboard SaaS | $500/月 | 持续合规监控需求 |

**收入模型B：API调用费（被动收入）**

- x402 USDC支付，$0.000752/event
- 目标：首月达到10,000 events/天 = $7.52/天
- 达到100,000 events/天时 = $75.2/天 = $2,256/月

**收入模型C：内容变现**

- 发布"EU AI Act + 中国智能体治理"双视角白皮书
- 通过付费内容（深度分析、合规模板）获取收入

#### 行动10：31个OPEN PR的系统性推进

**按价值排序的PR推进策略**:

| 优先级 | 仓库 | Stars | 预计影响 | 策略 |
|--------|------|-------|---------|------|
| P0 | awesome-chatgpt (punkpeye) #10049 | 90.6k | 最大曝光 | 已clean，跟进reviewer |
| P0 | e2b #1234 | 9k+ | Agent开发者 | CLA-signed，等待合并 |
| P1 | best-of-python #309 | 高 | Python生态 | 已clean，跟进 |
| P1 | awesome-quant #474 | 高 | 量化社区 | 需10 stars，社区推广 |
| P2 | mcp-find #95 | 中 | MCP生态 | 跟进review |
| P2 | time_series #50 | 中 | 数据科学 | 跟进review |
| P3 | 其余25个PR | 各不同 | 长尾曝光 | 每2天跟进一次 |

---

## 三、最快收益路径分析

### 路径1：PR合并 → GitHub可见度 → 开发者试用 → API付费

**时间线**: 1-4周  
**转化漏斗**:
- awesome-chatgpt PR合并 → 90.6k⭐仓库的README曝光
- 假设日访问1000人，0.5%点击AGL链接 = 5次/天
- 其中10%注册试用 = 0.5次/天
- 其中50%转为付费API调用 = 0.25次/天

**预期首月**: ~$5-15（验证阶段）

### 路径2：合规咨询 → 直接收入（最快变现）

**时间线**: 即时  
**目标**: 找到1个需要EU AI Act合规评估的客户

**渠道**:
- LinkedIn（面向EU AI合规负责人）
- 中国AI社区（面向《实施意见》合规需求）
- IETF 126参会者中的企业代表

**预期首月**: $2,000-10,000（单笔咨询）

### 路径3：IETF标准化 → 协议层集成 → 规模化收入

**时间线**: 3-12个月  
**价值**: 一旦AGL Receipt被纳入MCP/A2A等协议的治理层，每次Agent操作都需要AGL

**预期年收入**: $50,000-500,000（取决于协议采纳规模）

### 推荐优先级

```
路径2（咨询收入）→ 路径1（PR曝光）→ 路径3（标准化）
  即时变现           1-4周见效          长线布局
```

---

## 四、中国《智能体治理实施指导意见》深度分析

### 4.1 法规核心内容

**正式名称**: 《智能体规范应用与创新发展实施意见》  
**发布机关**: 国家网信办、国家发改委、工信部（三部门联合）  
**发布日期**: 2026年5月8日  
**生效日期**: 2026年7月15日（今日）  
**法律依据**: 国务院《关于深入实施"人工智能+"行动的意见》

**四大核心举措**:
1. **夯实发展基础**: 基础技术研发、工具链完善、标准体系建设
2. **守牢安全底线**: 权限管理、行为管控、数据安全
3. **场景牵引**: 19个典型应用场景
4. **创新生态**: 行业自律、平台规则、信用评价

### 4.2 对AGL的直接影响与BD机会

| 法规要求 | AGL能力对接 | BD机会 |
|---------|-----------|--------|
| 三级决策授权（人/授权/自主） | Receipt记录每笔决策的授权级别 | 提供合规技术栈 |
| 高风险领域强制备案 | 链上Receipt作为备案证据 | 帮助金融机构完成备案 |
| 行为管控（规则内嵌、行为围栏） | 治理管道=行为围栏的链上实现 | 作为围栏层出售 |
| 操作留痕、可追溯 | SHA-256锚定=不可篡改的操作记录 | 审计追溯方案 |
| 19个典型场景 | 每个场景都需要合规 | 场景化合规模板 |

### 4.3 中国市场BD策略

**目标客户（按优先级）**:
1. **银行/金融机构**: 需要向银保监会备案Agent部署 → 最紧迫
2. **医疗AI公司**: 需要审计追溯 → 高价值
3. **政务智能体**: 需要行为管控证据 → 政策驱动
4. **教育AI平台**: 需要决策透明度 → 社会关注度高

**关键话术**:
> "今天生效的《实施意见》要求'明确决策权限、加强行为管控、提升内生安全'。AGL是开源的链上治理层，已经部署在Base L2上，成本$0.000752/次操作。我们可以帮您在72小时内完成Agent行为审计系统的部署。"

### 4.4 TC260配套标准

TC260同步发布了《AI Agent部署和使用安全指南》（TC260-PG-20266A），6大核心要求：
1. 软件/模型来源完整性验证
2. 最小权限原则
3. 最小网络暴露
4. 详细审计日志
5. 高风险操作控制
6. 敏感数据和长期记忆保护

**AGL优势**: 第4项（审计日志）和第5项（高风险操作控制）是AGL的核心能力。Receipt天然提供审计日志，治理管道天然实现高风险操作控制。

---

## 五、更新版BD话术

### 5.1 面向EU客户（Art.50倒计时版本）

**标题**: "18 Days to Art.50: 78% of Enterprises Are Not Ready. Here's How to Be in the 22%."

**正文**:
> The EU AI Act Article 50 transparency obligations become enforceable on August 2, 2026. Penalties: up to €15M or 3% of global turnover.
>
> According to the Vision Compliance 2026 Readiness Report, 78% of enterprises have not taken meaningful steps toward compliance.
>
> Meanwhile, every new entrant in the Agent infrastructure space — NewCore ($66M), Arcade ($60M), NeuralTrust ($20M), ChatSee ($6.5M) — is building off-chain only. None of them offer tamper-evident governance logging.
>
> AGL (Agent Governance Layer) fills this gap: $0.000752/event on Base L2, generating immutable compliance Receipts that answer the question every regulator will ask: "Can you prove what your Agent disclosed, decided, and did?"
>
> We're open-source, deployed today, and ready for your compliance stack.

### 5.2 面向中国客户（《实施意见》今日生效版本）

**标题**: "智能体治理新规今日生效 — 您的Agent合规了吗？"

**正文**:
> 国家网信办、发改委、工信部联合印发的《智能体规范应用与创新发展实施意见》今天正式生效。这是全球首个针对AI Agent的专项监管框架。
>
> 核心要求：三级决策授权结构 + 高风险领域强制备案 + 行为管控 + 操作可追溯。
>
> 同时，TC260发布了配套的《AI Agent部署安全指南》，明确6大安全要求。
>
> AGL（Agent Governance Layer）是开源的链上治理层，在Base L2上以$0.000752/次的成本，为每个Agent决策生成不可篡改的合规Receipt。
>
> 无论是金融备案、医疗审计，还是政务追溯，AGL都能提供监管方认可的技术证据。

### 5.3 面向IETF 126参会者

**标题**: "Governance Layer for Agent Protocols — $0.000752/event on Base L2"

**正文**:
> At IETF 126, three BoFs are discussing how agents communicate: agentproto (A2A protocols), DAWN (agent discovery), and DMSC (multi-agent collaboration).
>
> But there's a missing piece: how do agents PROVE they followed the rules?
>
> China's Agent Governance Rules took effect today (July 15). EU AI Act Art.50 enforces in 18 days. Both require verifiable governance records — not self-reported logs.
>
> AGL provides a deployed, open-source solution: immutable Receipts anchored on Base L2 at $0.000752/event. It works with MCP, A2A, and any agent protocol.
>
> Let's talk at the agentproto BoF (July 23, 09:00 CEST) or DMSC BoF (July 22, 09:00 CEST).

### 5.4 面向NeuralTrust（合作提案）

**标题**: "TrustGate + AGL: Off-chain Execution + On-chain Verification"

**正文**:
> NeuralTrust's product suite — TrustGate, TrustGuard, TrustLens — covers the full off-chain governance stack for AI agents.
>
> But when an EU regulator asks "prove your agent complied with Art.50 on July 22nd", off-chain logs can be challenged. AGL anchors governance Receipts on Base L2 at $0.000752/event — tamper-evident, verifiable, and regulator-ready.
>
> We're not a competitor. We're your chain verification plugin.
>
> Proposal: integrate AGL Receipt generation into TrustGate's policy pipeline. When TrustGate blocks or approves an action, AGL records the decision on-chain. Zero additional infrastructure cost for your customers.

---

## 六、竞品融资空白分析：为什么链上合规是蓝海

### 6.1 6月赛道融资全景

| 公司 | 融资额 | 聚焦方向 | 链上治理 |
|------|--------|---------|---------|
| NewCore | $66M | Agent基础设施 | ❌ Off-chain |
| Arcade | $60M | Agent执行框架 | ❌ Off-chain |
| NeuralTrust | $20M | Agent治理（EU） | ❌ Off-chain |
| ChatSee | $6.5M | 多模态Agent | ❌ Off-chain |
| **合计** | **$152.5M+** | | **全部Off-chain** |

### 6.2 空白与机会

**关键洞察**: $152.5M+的新资金全部涌入off-chain Agent能力层（执行、编排、安全），没有任何一笔投入链上治理。

**原因分析**:
1. 中国监管7/15才生效，多数投资方尚未消化
2. EU Art.50还有18天，紧迫感尚未传导到投资决策
3. 链上合规是新概念，VC尚未建立认知框架

**AGL的先发优势**:
- 唯一已部署的开源Agent链上治理方案
- $0.000752/event的成本使大规模合规成为可能
- 同时覆盖中国（《实施意见》）和EU（Art.50）两大监管体系

### 6.3 商业化路径

1. **短期（1-3月）**: 合规咨询服务 + 企业部署支持
2. **中期（3-6月）**: 与NeuralTrust等off-chain玩家形成"off-chain + on-chain"合作
3. **长期（6-12月）**: 推动AGL Receipt成为IETF标准的一部分

---

## 七、IETF 126深度BD价值

### 7.1 三个Agent相关BoF的战略意义

| BoF | 日期 | AGL参与价值 |
|-----|------|-----------|
| **agentproto** | 7/23 | 🔴 最高：讨论MCP/A2A/ACP/ANP统一 → AGL可作为治理层纳入 |
| **DMSC** | 7/22 | 🟡 高：Agent Gateway模型 → AGL Receipt=Gateway决策的链上证据 |
| **DAWN** | 7/21 | 🟡 中：Agent发现机制 → AGL Receipt可作为可信Agent的凭证 |

### 7.2 具体行动计划

1. **7/16-17**: 在agentproto邮件列表发言，介绍AGL作为"治理层而非通信层"的定位
2. **7/21 DAWN BoF**: 远程参会，提出Receipt作为Agent可信发现的凭证
3. **7/22 DMSC BoF**: 重点参与，展示TrustGate+AGL的集成概念
4. **7/23 agentproto BoF**: 核心战场，提出AGL Receipt Schema作为协议治理扩展

### 7.3 MCP 2026-07-28新规范的对接

MCP新规范的关键变化与AGL的天然契合：

| 新规范变化 | AGL对接方式 |
|-----------|-----------|
| 无状态核心（移除session） | 每笔请求独立 → Receipt可独立锚定 |
| 显式句柄模式 | Receipt hash作为操作句柄传递 |
| 扩展框架正式化 | AGL注册为官方扩展（reverse-DNS标识符） |
| W3C Trace Context | Receipt链上hash与分布式追踪对齐 |
| 可缓存性（ttlMs/cacheScope） | Receipt的合规有效期管理 |

---

## 八、关键指标与里程碑

### 30天目标（7/15 — 8/15）

| 指标 | 目标 | 衡量方式 |
|------|------|---------|
| PR合并数 | 5+个 | GitHub合并记录 |
| 首笔API收入 | >$0.01 | 链上交易记录 |
| IETF BoF参与 | 3个BoF全覆盖 | 参会记录 |
| BD邮件发出 | 50+封 | 邮件记录 |
| 合规咨询线索 | 3+个 | 回复数 |
| NeuralTrust接触 | 至少1次对话 | 会议记录 |

### 90天目标（7/15 — 10/15）

| 指标 | 目标 |
|------|------|
| 月收入 | $1,000+ |
| MCP扩展提案 | 已提交 |
| 中国备案合作 | 1+个金融机构 |
| 开源贡献者 | 10+个 |

---

## 九、风险与缓解

| 风险 | 概率 | 缓解策略 |
|------|------|---------|
| PR被拒绝/关闭 | 中 | 多仓库分散风险，31个PR总量保底 |
| EU Art.50延期到12月 | 高 | 延期≠取消，延期=更多准备时间=更多客户 |
| 中国监管执行延迟 | 中 | 先发优势不变，备案需求会逐步释放 |
| Base L2网络问题 | 低 | 可迁移到其他L2（Arbitrum, Optimism） |
| NeuralTrust不愿合作 | 中 | 独立推进，不依赖单一合作方 |

---

## 十、下一步行动清单

### 今日必做（7/15）
- [ ] 确认e2b #1234、punkpeye #10049、best-of-python #309的PR状态
- [ ] 注册IETF 126远程参会
- [ ] 发送中国监管BD邮件（至少5封）
- [ ] 加入agentproto和DMSC邮件列表

### 本周必做（7/16-7/24）
- [ ] 推进awesome-quant #474的star获取
- [ ] 准备IETF BoF发言材料
- [ ] 向NeuralTrust发送合作提案
- [ ] 发布"双监管"LinkedIn文章
- [ ] 参加IETF 126 DAWN/DMSC/agentproto BoF

### 月底前必做（7/25-7/31）
- [ ] MCP 2026-07-28发布后提交AGL扩展提案
- [ ] 完成至少1次合规咨询交付
- [ ] 实现首笔API调用收入
- [ ] 更新llms.txt和openapi.json适配新MCP规范

---

*本计划基于2026-07-15市场数据制定，建议每周review并更新。*  
*安全宪法v4.1为本计划的最高约束框架。*
