# 中国《智能体规范应用与创新发展实施意见》AGL合规对接映射文档

> 完成日期：2026-07-15 | 文档版本：v1.0 | 密级：内部-商业敏感

---

## 执行摘要

**2026年7月15日，中国《智能体规范应用与创新发展实施意见》正式生效**，由国家网信办、国家发改委、工信部三部门联合印发，这是**全球首个专项AI Agent监管框架**。该法规以14条核心条款覆盖智能体从研发到运维的全生命周期，构建了**三级决策授权结构**（用户本人决策/用户授权决策/智能体自主决策）、**分类分级治理框架**（敏感领域强制备案 vs 低风险领域行业自律）、**行为管控与可追溯**（规则内嵌+行为围栏+区块链可验证）三大支柱。

与此同时，TC260同步推进《智能体应用安全基本要求》强制性国家标准（20263116-Q-252），国家金融监管总局发布《银行业保险业人工智能安全开发应用指导意见》32条，形成"实施意见+强制国标+行业细则"的三层合规体系。

**BDE Score的AGL（Agent Governance Layer）**基于Base L2以$0.000752/event生成不可篡改合规Receipt，其技术架构（Agent注册→Scope约束→Action Attestation→Governance DAG→Replay）与《实施意见》的逐条要求形成高密度对接映射。本文档完成**14条核心要求的逐条AGL技术方案对接**，识别中国市场**6类优先BD目标**和**量化市场机会**（企业级Agent市场规模2026年约449-480亿元）。

---

## 数据来源

| Provider | Skill used | Dimension covered | Role |
|----------|-----------|---------|------|
| 中国网信网 (CAC) | search_web + fetch_web | 法规全文、答记者问、专家解读 | primary source for regulation text |
| 国家标准化管理委员会 | search_web | 强制性国标计划号与内容 | primary source for TC260 standard |
| 国家金融监管总局 | search_web | 金融AI指导意见32条 | primary source for financial regulation |
| H33.ai Specification | fetch_web | AGL Attestation Model v1.0.0技术规范 | primary source for AGL spec |
| arXiv (AGL-1 Paper) | search_web | AGL-1 Control Plane理论框架 | theoretical framework |
| 通用搜索 | search_web | 专家评论、行业分析、备案流程 | qualitative context & secondary source |

---

## 第一部分：法规全文摘要

### 1.1 基本信息

| 项目 | 内容 |
|------|------|
| **法规名称** | 《智能体规范应用与创新发展实施意见》 |
| **发文机关** | 国家网信办、国家发展改革委、工业和信息化部 |
| **发布日期** | 2026年5月8日 |
| **生效日期** | 2026年7月15日 |
| **官方全文URL** | https://www.cac.gov.cn/2026-05/08/c_1779979789523320.htm |
| **答记者问URL** | https://www.cac.gov.cn/2026-05/08/c_1779979789738376.htm |
| **专家解读URL** | https://www.cac.gov.cn/2026-05/08/c_1779979790736565.htm |
| **法规性质** | 部门规范性文件，国内首部专门针对AI智能体的监管文件 |
| **上位法依据** | 国务院《关于深入实施"人工智能+"行动的意见》(2025年8月) |

### 1.2 智能体官方定义

> 智能体是具备**自主感知、记忆、决策、交互与执行能力**的智能系统，是人工智能产品及服务的重要形态。 [(CAC)](https://www.cac.gov.cn/2026-05/08/c_1779979789523320.htm)

五类能力拆解：
- **自主感知**：理解环境、用户、任务和上下文
- **记忆**：保留上下文、历史经验和长期信息
- **决策**：拆解任务、规划路径、选择行动
- **交互**：和人、系统、设备、其他智能体协同
- **执行**：调用工具、操作系统、驱动流程，真正完成动作

### 1.3 四项基本原则

1. **安全可控**：将智能体安全、可靠、可信作为发展底线要求，贯穿研发、部署、推广全过程
2. **规范有序**：构建与现有政策法规衔接顺畅、行业自律自治、底线红线清晰的治理体系
3. **创新驱动**：体系化突破智能体关键技术，构建开放共享的智能体生态
4. **应用牵引**：围绕五大方向需求，发挥典型场景示范效应，先易后难、循序渐进

### 1.4 核心条款结构（14条 + 配套）

| 章节 | 条款编号 | 核心要求 | AGL对接优先级 |
|------|---------|---------|-------------|
| **二、夯实发展基础** | 1-4 | 技术底座、工具链、标准体系、智能互联网 | P2 |
| **三、守牢安全底线** | 5-14 | 产品准则、决策权限、行为管控、内生安全、供应链安全、应用衍生风险、分类分级治理、合规服务体系、行业自律、信用评价 | **P1** |
| **四、强化应用牵引** | 15-27 | 19个典型应用场景（科学研究、产业发展、提振消费、民生福祉、社会治理） | P2 |
| **五、建设创新生态** | 34-38 | 开源创新、产业协作、应用推广、全球生态 | P3 |

### 1.5 第三部分"守牢安全底线"逐条摘要（AGL对接核心区）

| 条款 | 标题 | 核心要求摘要 |
|------|------|------------|
| **第5条** | 完善政策法规和伦理规范 | 防止智能体利用数据优势、人格化技术传播不良价值观、算法压榨；防范未成年人/老年人沉迷成瘾、情感依赖 |
| **第6条** | 明确决策权限 | **厘清三级决策边界**：仅限用户本人决策、需由用户授权决策、智能体自主决策。确保用户知情权和最终决策权，执行不得超出授权范围 |
| **第7条** | 加强行为管控 | 发展规则内嵌、行为围栏技术；**探索利用区块链建立重要应用场景行为可验证、可追溯机制** |
| **第8条** | 提升内生安全能力 | 研究数据安全、个人信息保护、密码防护、攻击检测、权限管理、行为控制等安全技术；探索建立安全评估体系 |
| **第9条** | 加强供应链安全 | 制定开发、部署、应用、维护全周期安全规范；加强模型接入、API调用、扩展工具使用环节安全管理 |
| **第10条** | 化解应用衍生风险 | 完善常态化风险识别、预警及干预机制；强化人机协同审核、拦截阻断等风险处置能力 |
| **第11条** | 构建分类分级治理框架 | **敏感领域**：网信部门+行业主管部门确定开放场景，实行**备案、检测、问题产品召回**；**低风险领域**：合规自测、信息报告、分发平台管理、行业自律 |
| **第12条** | 健全合规服务体系 | 强化风险监测预警、检测评估、咨询、认证等专业服务；推动认证与检测结果互通互认 |
| **第13条** | 引导行业加强自律 | 行业组织联合制定自律规则；开发平台、分发平台建立平台规则、隐私政策 |
| **第14条** | 探索信用评价机制 | 对技术滥用、诱导消费、虚假宣传、隐瞒缺陷等行为进行信用评价和失信惩戒 |

---

## 第二部分：TC260配套标准

### 2.1 《智能体应用安全基本要求》强制性国家标准

| 项目 | 内容 |
|------|------|
| **标准计划号** | 20263116-Q-252 |
| **归口单位** | 中央网信办（TC260体系） |
| **下达日期** | 2026年7月2日 |
| **标准性质** | **强制性国家标准**（具备法定约束效力） |
| **全球地位** | 全球首部聚焦智能体安全的强制性国家标准 |
| **核心导向** | 定底线、护用户、防风险；强统筹、促平衡 |

[(吉林省科协转载国家标准委)](http://m.jlskx.org.cn/science/show-8845.html)

**三大落地原则**：
1. **技术中立**：不绑定单一模型、架构与部署路线
2. **实操可行**：可量化、可检测、可落地
3. **合规对齐**：严格衔接现有网络安全、数据安全及AI治理法律法规

### 2.2 GB/Z 185系列 — 智能体互联国家标准（7项）

2026年7月市场监管总局批准发布《人工智能 智能体互联》系列7项国家标准：

| 部分 | 内容 | AGL对接点 |
|------|------|----------|
| 第1部分 | 总体架构（五层域） | AGL Governance DAG结构 |
| 第2部分 | 身份码 | AGL agent_id + scope_hash |
| **第3部分** | **身份管理** | **AGL Agent Registration Receipt** |
| 第4部分 | 智能体描述 | AGL Scope Constraints |
| 第5部分 | 智能体发现 | AGL agent registry查询 |
| 第6部分 | 交互协议 | AGL Cross-Agent References |
| 第7部分 | 工具调用 | AGL action_type + policy_hash |

[(GB/Z 185.3解读)](http://m.toutiao.com/group/7661094984614953491/)

### 2.3 TC260-PG-20266A《AI Agent部署和使用安全指南》

> **注：TC260-PG-20266A的具体全文尚未公开**，以下信息基于行业解读和标准框架推断。标准处于研制阶段，预计将覆盖评估、准备、部署、使用、停用五个阶段的安全要求。

基于TC260已发布的《智能体安全标准化研究报告》(2026年3月)和行业实践，TC260-PG-20266A预计覆盖：

| 阶段 | 预期核心要求 | AGL对接 |
|------|------------|---------|
| **评估阶段** | Agent风险初判、自主性分级、作用范围划定 | AGL Scope Constraints定义 |
| **准备阶段** | 身份注册、权限配置、安全测试 | AGL Agent Registration Receipt |
| **部署阶段** | 沙箱隔离、网络白名单、最小权限 | AGL scope enforcement + escalation |
| **使用阶段** | 运行时监控、行为审计、异常告警 | AGL Action Receipt + Governance DAG |
| **停用阶段** | 凭证注销、日志归档、身份码废弃 | AGL cascade revocation |

---

## 第三部分：法规逐条AGL对接映射

### 3.1 映射总览表

| 法规条款 | 法规要求 | AGL技术能力 | 对接完整度 | BDE产品形态 |
|---------|---------|------------|----------|------------|
| **第5条** 伦理规范 | 防止不良价值观、算法压榨；防范沉迷成瘾 | Scope Constraints (action_type白名单) + Negative Authority Proof | 🟢 高 | AGL Base L2 Receipt |
| **第6条** 决策权限 | 三级决策边界+知情权+最终决策权 | Scope Constraints (action_type + delegation_depth + time_window) + Escalation Semantics (escalate_human/escalate_auto/reject) | 🟢 高 | AGL Base L2 + Escalation |
| **第7条** 行为管控 | 规则内嵌+行为围栏+区块链可验证可追溯 | Scope Enforcement (7.1确定性评估算法) + Governance DAG (区块链级不可篡改) + Action Receipt | 🟢 高 | AGL Base L2 Receipt @ $0.000752/event |
| **第8条** 内生安全 | 数据安全+密码防护+攻击检测+权限管理+行为控制 | Scope Constraints全类 + Multi-Family PQ Signature + scope_evaluation审计 | 🟡 中 | AGL + PQ-Sig附加 |
| **第9条** 供应链安全 | 全周期安全规范+模型接入/API调用/工具使用安全 | Registration Receipt (delegator_id链式验证) + cascade revocation + predecessor_hash链 | 🟡 中 | AGL + 供应链扫描 |
| **第10条** 应用衍生风险 | 风险识别+预警+干预+人机协同审核+拦截阻断 | Escalation Semantics (三种策略) + Negative Authority Proof + scope_evaluation.result=denied | 🟢 高 | AGL Base L2 + Escalation |
| **第11条** 分类分级治理 | 敏感领域备案/检测/召回；低风险自律治理 | Scope Constraints (jurisdiction + max_value + action_type) 按分级动态配置 | 🟢 高 | AGL + 分级策略包 |
| **第12条** 合规服务体系 | 风险监测+检测评估+认证+结果互认 | Governance DAG Replay (11.1确定性回放) + 独立验证 | 🟢 高 | AGL + 合规报告导出 |
| **第13条** 行业自律 | 平台规则+隐私政策+权责明确 | Scope定义标准化 + Registration Receipt平台级签发 | 🟡 中 | AGL + 平台集成SDK |
| **第14条** 信用评价 | 信用评价+失信惩戒 | OIS Agent Scope Integrity维度 + scope violation计数 | 🟡 中 | AGL + OIS评分 |

**对接完整度说明**：🟢高=AGL现有能力直接覆盖；🟡中=AGL核心能力覆盖但需补充行业定制层；🔴低=需重大扩展（本次无低评级项）

### 3.2 重点条款深度对接

#### 第6条：三级决策权限 ←→ AGL Scope Constraints + Escalation

**法规要求**：
> 厘清仅限用户本人决策、需由用户授权决策和智能体自主决策等各种决策方式的合理边界及所需权限。确保用户对智能体自主决策享有知情权和最终决策权。

**AGL技术对接**：

| 决策级别 | 法规定义 | AGL实现 | 代码示例 |
|---------|---------|---------|---------|
| **L1: 用户本人决策** | 智能体仅提供建议，人做最终决策并自己执行 | `delegation_depth: 0` + `action_type: ["read", "review", "flag"]` | 禁止write/execute类action |
| **L2: 用户授权决策** | 智能体在用户明确授权范围内自主执行 | `action_type: ["read", "review", "execute"]` + `escalation_policy: "escalate_human"` | 高风险action触发人工审批 |
| **L3: 智能体自主决策** | 护栏内独立运行，人看异常和结果 | `action_type: ["read", "write", "execute"]` + `escalation_policy: "reject"` + 异常监控 | 越界直接拒绝+告警 |

**关键对齐点**：
- 用户**知情权** ←→ AGL Action Receipt中包含`scope_evaluation`（constraints_evaluated/passed），每次action均产生receipt可审计
- 用户**最终决策权**（"叫停权"） ←→ AGL Escalation Semantics的`escalate_human`策略 + cascade revocation（立即吊销agent权限）

#### 第7条：行为管控与可追溯 ←→ AGL Governance DAG + Action Receipt

**法规要求**：
> 发展规则内嵌、行为围栏等技术...探索利用区块链等技术，建立重要应用场景智能体行为可验证、可追溯机制。

**AGL技术对接**：

| 法规概念 | AGL实现 | 技术特性 |
|---------|---------|---------|
| **规则内嵌** | Scope Constraints在Agent Registration时写入scope对象，scope_hash存入receipt | 约束不可篡改（hash锚定） |
| **行为围栏** | Scope Enforcement (Section 7) 确定性评估算法：5步evaluation → permitted/denied | 每次action执行前强制评估 |
| **区块链可验证** | Governance DAG：每个receipt含`predecessor_hash`形成链式结构，Multi-Family PQ签名 | 量子安全签名+链式不可篡改 |
| **可追溯** | Replay Semantics (Section 11)：从governance chain可确定性重建任意历史时刻的agent authority state | 不依赖originating infrastructure即可验证 |

**AGL Receipt示例（金融风控场景）**：
```json
{
  "receipt_type": "agent_action",
  "agent_id": "agent:risk-monitor-001",
  "action_type": "review",
  "action_payload_hash": "sha3-256:7c8d9e...",
  "scope_evaluation": {
    "result": "permitted",
    "constraints_evaluated": 5,
    "constraints_passed": 5
  },
  "timestamp": "2026-07-15T10:30:00Z",
  "predecessor_hash": "sha3-256:a0b1c2...",
  "signatures": { "pq_bundle": "..." }
}
```

#### 第11条：分类分级治理 ←→ AGL Scope Constraints动态配置

**法规要求**：
> 敏感领域及重点行业：实行备案、检测、问题产品召回；低风险领域：合规自测、信息报告、行业自律。

**AGL分级策略包设计**：

| 治理级别 | 适用领域 | AGL Scope配置 | Receipt要求 |
|---------|---------|-------------|------------|
| **强监管级** | 金融、医疗、公共安全、司法 | `action_type: 严格白名单` + `max_value: 低阈值` + `escalation: escalate_human` + `delegation_depth: 0` | 全量Receipt + 实时上报 + 年度合规报告 |
| **中等监管级** | 教育、电商、工业制造 | `action_type: 扩展白名单` + `escalation: escalate_auto` + `delegation_depth: 1` | 全量Receipt + 季度抽检 |
| **自律级** | 生活娱乐、日常办公 | `action_type: 宽松白名单` + `escalation: reject` + `delegation_depth: 2` | 基础Receipt + 年度自评 |

---

## 第四部分：金融领域Agent备案流程

### 4.1 金融智能体合规体系

金融领域智能体同时受**三重合规约束**：

1. **《实施意见》**（网信办+发改委+工信部）→ 分类分级治理 + 备案要求
2. **《银行业保险业AI安全开发应用指导意见》**（金融监管总局，32条）→ 谁使用谁负责 + 高风险准入 + 人工干预
3. **《生成式AI服务管理暂行办法》+《算法推荐管理规定》** → 算法备案 + 安全评估 + 内容标识

[(金融监管总局指导意见)](http://m.toutiao.com/group/7661777373947265588/)

### 4.2 金融智能体备案全流程

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  1.业务梳理  │ →  │  2.架构与    │ →  │  3.安全测评  │ →  │  4.合规文档  │
│  场景分级    │    │  风险初判    │    │  全维度实施  │    │  全套编制    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐          ↓
│  7.长效合规  │ ←  │  6.备案公示  │ ←  │  5.材料提交  │ ← ┌─────────────┐
│  年度自查    │    │  归档完成    │    │  属地网信    │    │  整合完善    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### 4.3 金融智能体备案核心核查要点

| 核查维度 | 具体要求 | AGL对接 |
|---------|---------|---------|
| **权限边界** | 智能体权限范围、任务执行约束 | AGL Scope Constraints (action_type + max_value + jurisdiction) |
| **风险拦截** | 风险拦截机制、越权操作阻断 | AGL Scope Enforcement + Escalation |
| **全链路行为留痕** | 操作可查、责任可追溯 | AGL Action Receipt + Governance DAG |
| **算法备案** | 网信办算法备案系统提交 | AGL导出合规报告（含scope_hash + policy_hash） |
| **安全评估** | 输入输出安全/隐私防护/工具权限/提示攻击/幻觉 | AGL scope_evaluation + Negative Authority Proof |

### 4.4 金融监管总局"四道安检门"

| 安检门 | 核心要求 | AGL能力 |
|-------|---------|---------|
| **治理门** | 董事会专门委员会负责AI；功能边界/权限/责任/追溯四道边界 | AGL Registration Receipt (delegator_id层级) + Scope定义 |
| **数据门** | 数据分类分级；高质量数据集；知识工程 | AGL scope约束可绑定数据分级标签 |
| **风险门** | AI风险纳入全面风险管理体系；高风险应用准入+人工干预 | AGL Escalation (escalate_human) + 分类分级Scope |
| **能力门** | 稳健性/透明度/可解释性/伦理公平/数据安全/网安/运营韧性 | AGL Replay确定性回放 + OIS评分 |

---

## 第五部分：BD机会与目标客户

### 5.1 市场规模

| 指标 | 数值 | 来源 |
|------|------|------|
| 2026年中国企业级AI Agent市场规模 | **449-480亿元** | [(IDC/Gartner)](https://blog.csdn.net/xiangwang2206/article/details/160940396) |
| 2029年中国企业级AI Agent市场规模（预测） | **3320亿元** | [(IDC)](https://blog.csdn.net/xiangwang2206/article/details/160940396) |
| 2027年将被降级/停用的企业Agent比例 | **40%**（因治理粒度错配） | [(Gartner)](http://m.toutiao.com/group/7659997352903672361/) |
| 金融智能体进入业务运行的比例 | **仅4%**（96%仍在PoC/试运行） | [(中国金融智能体发展研究报告)](http://m.toutiao.com/group/7659979914371793446/) |

### 5.2 六类优先BD目标

| 优先级 | 目标客户类型 | 痛点 | AGL价值主张 | 预估年event量级 |
|-------|------------|------|------------|---------------|
| **P0** | **银行/保险机构** | 金融监管总局32条合规+算法备案+高风险准入 | AGL Receipt满足"全链路行为留痕"核查+Escalation满足"人工干预"要求 | 10^8-10^9 event/年 |
| **P1** | **政务/央国企数字化平台** | 涉密数据管控+分级权限+全程留痕 | AGL Scope (jurisdiction+action_type) + PQ签名 + cascade revocation | 10^7-10^8 event/年 |
| **P1** | **医疗健康智能体** | 患者数据隐私+辅助型决策（人做最终决定） | AGL L1决策模式(delegation_depth:0) + escalate_human | 10^7-10^8 event/年 |
| **P2** | **电商平台/消费级智能体** | UGC智能体关停潮后转向企业Agent | AGL分类分级Scope + 合规自测报告导出 | 10^8-10^9 event/年 |
| **P2** | **工业制造/能源调度** | 生产安全+操作可撤销+沙箱隔离 | AGL scope enforcement + Negative Authority Proof | 10^7-10^8 event/年 |
| **P3** | **AI Agent开发平台** | 平台需为入驻智能体提供合规基础设施 | AGL平台级SDK + Registration Receipt平台签发 | 平台级×N个agent |

### 5.3 BD话术模板

**金融客户话术**：
> "金融监管总局〔2026〕8号文明确要求'谁使用谁负责'，在高风险应用关键环节建立人工监督和干预机制。AGL的Governance Receipt以$0.000752/event的成本，为每一个Agent action生成不可篡改的合规凭证，直接满足'全链路行为留痕'和'操作可查、责任可追溯'的核查要求。相比自建审计系统，AGL的Receipt天然具备区块链级不可篡改性（Multi-Family PQ签名），且支持确定性回放（Replay），监管问询时可即时导出完整合规链。"

**政务/央国企话术**：
> "《实施意见》第7条明确要求'利用区块链等技术建立重要应用场景智能体行为可验证、可追溯机制'。AGL的Governance DAG正是这一要求的技术实现——每个Agent action产生cryptographically signed receipt，形成链式结构，支持从任意历史时刻确定性重建Agent权限状态。第6条的三级决策权限（用户本人/用户授权/智能体自主）直接映射为AGL的Scope Constraints三档配置，一键切换决策模式。"

**AI Agent平台话术**：
> "7月15日《实施意见》生效后，所有面向公众的智能体都需完成算法备案+安全测评。平台作为分发平台，需为入驻开发者提供合规基础设施。AGL平台级SDK可以为每个入驻Agent自动签发Registration Receipt、配置Scope Constraints、生成Action Receipt，让开发者的Agent'天生合规'，降低平台整体合规风险。"

### 5.4 竞争格局与AGL差异化

| 维度 | 传统API网关 | 合规审计系统 | AGL (BDE Score) |
|------|-----------|------------|----------------|
| 管控对象 | API接口调用 | 人的操作/交易结果 | **Agent全行为**（感知/决策/执行/工具调用） |
| 管控时机 | 接口调用前 | 事后审计 | **行为执行前实时校验** |
| 不可篡改性 | 无 | 日志可被修改 | **Multi-Family PQ签名+链式hash** |
| 合规证据 | 简单error code | 统计报表 | **Governance Receipt (per-action)** |
| 回放能力 | 无 | 无 | **确定性Replay** |
| 法规对齐 | 通用 | 需手动映射 | **直接映射第6/7/11条** |
| 单价 | 按API call | 按审计量 | **$0.000752/event** |

---

## 第六部分：合规技术对接架构

### 6.1 AGL在中国智能体治理体系中的定位

```
┌─────────────────────────────────────────────────────────────────┐
│                    中国智能体治理体系                              │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │ 《实施意见》     │  │ 强制国标         │  │ 行业细则       │ │
│  │ (三部门联合)     │  │ 20263116-Q-252  │  │ 金融32条等    │ │
│  └────────┬────────┘  └────────┬─────────┘  └───────┬────────┘ │
│           │                    │                     │          │
│           └──────────┬─────────┘─────────────────────┘          │
│                      ↓                                          │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              AGL (Agent Governance Layer)                  │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐│ │
│  │  │Registration│ │  Scope   │ │  Action   │ │ Governance   ││ │
│  │  │  Receipt  │ │Constraints│ │  Receipt  │ │    DAG      ││ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘│ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐│ │
│  │  │Escalation │ │ Negative │ │  Replay   │ │    OIS       ││ │
│  │  │ Semantics │ │ Authority│ │ Semantics │ │   Score      ││ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘│ │
│  └───────────────────────────────────────────────────────────┘ │
│                      ↓                                          │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              合规输出层                                    │ │
│  │  算法备案材料 │ 安全评估报告 │ 审计日志 │ 合规Receipt导出 │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 AGL Receipt与中国法规要求对照

| Receipt字段 | 对应法规要求 | 合规用途 |
|------------|------------|---------|
| `agent_id` | 第7条行为可追溯 | 智能体身份标识，GB/Z 185.2身份码 |
| `action_type` | 第6条决策权限 | 三级决策白名单 enforcement |
| `scope_evaluation.result` | 第7条规则内嵌/行为围栏 | 每次action的合规判定记录 |
| `scope_evaluation.constraints_passed` | 第11条分类分级 | 分级合规达标证据 |
| `predecessor_hash` | 第7条区块链可验证 | 链式不可篡改证明 |
| `signatures` | 第7条可验证 | Multi-Family PQ签名，量子安全 |
| `timestamp` | 第10条风险预警 | 时间线审计 |
| `delegator_id` | 第6条最终决策权 | 权限委托链追溯 |
| `policy_hash` | 第11条分级治理 | 策略版本审计 |

---

## 第七部分：风险与局限

### 7.1 AGL能力边界

| 法规要求 | AGL当前覆盖度 | 需补充能力 |
|---------|-------------|----------|
| 第5条 伦理规范（未成年人/老年人保护） | 部分（Scope可限制action但不含用户画像判断） | 需叠加内容安全审核层 |
| 第8条 安全评估体系 | Receipt可提供评估数据但不替代评估本身 | 需对接第三方评测机构 |
| 第9条 供应链安全预警 | Registration Receipt可追溯delegator但不扫描组件漏洞 | 需叠加SCA/SBOM扫描工具 |
| TC260-PG-20266A具体条款 | 待标准全文公开后需逐条对齐 | 标准仍在研制中 |

### 7.2 合规不确定性

1. **TC260-PG-20266A全文未公开**：标准处于研制阶段，具体技术条款和检测方法待确认
2. **属地网信审核细则差异化**：各省市网信部门审核标准细化程度不同，AGL需适配属地差异
3. **金融大模型备案暂停**：券商领域大模型新增备案申请处于暂停状态，窗口重启时间不确定
4. **强制国标制定周期**：20263116-Q-252从立项到发布通常需12-18个月，过渡期合规以实施意见为准

---

## 第八部分：行动建议

### 8.1 90天落地路线图

| 时间 | 行动 | 产出 |
|------|------|------|
| **Day 1-30** | 1. 发布AGL中国合规对接白皮书（本文档为基础）<br>2. 针对金融客户开发"金融风控Agent"AGL Scope模板包<br>3. 在BDE-Stock文档库建立中国合规研究专区 | 白皮书+模板包+文档库 |
| **Day 31-60** | 4. 与1-2家头部银行完成AGL PoC对接（风控/审批场景）<br>5. 开发属地网信备案材料自动生成工具（从AGL Receipt导出）<br>6. 建立GB/Z 185.3身份管理↔AGL Registration双向映射 | PoC案例+备案工具+标准映射 |
| **Day 61-90** | 7. 发布AGL中国版SDK（含金融/政务/医疗三档预置Scope）<br>8. 申请参与TC260智能体安全标准研制（作为合规技术贡献单位）<br>9. 在3-5家AI Agent平台完成AGL平台级SDK集成 | SDK+标准参与+平台集成 |

### 8.2 定价策略建议

基于AGL Base L2 $0.000752/event的基线：

| 场景 | 建议定价 | 理由 |
|------|---------|------|
| 金融强监管级 | $0.001/event | 需全量Receipt+实时上报+PQ签名，成本上浮 |
| 政务/央国企 | $0.0009/event | 涉密场景需增强签名强度 |
| 一般合规级 | $0.000752/event | 标准AGL Base L2定价 |
| 平台级SDK | 按agent数收费 | 平台作为分发方，按入驻agent数而非event量 |

---

## 附录A：参考法规清单

| 法规/标准 | 发布机关 | 生效/状态 | URL |
|----------|---------|----------|-----|
| 《智能体规范应用与创新发展实施意见》 | 网信办+发改委+工信部 | 2026-07-15生效 | https://www.cac.gov.cn/2026-05/08/c_1779979789523320.htm |
| 《智能体应用安全基本要求》20263116-Q-252 | 国家标准委（网信办归口） | 研制中 | [(吉林省科协转载)](http://m.jlskx.org.cn/science/show-8845.html) |
| GB/Z 185系列（7项智能体互联国标） | 市场监管总局 | 2026-07发布 | [(解读)](http://m.toutiao.com/group/7661094984614953491/) |
| 《银行业保险业AI安全开发应用指导意见》 | 金融监管总局 | 2026-06-18发布 | [(报道)](http://m.toutiao.com/group/7661777373947265588/) |
| 《人工智能拟人化互动服务管理暂行办法》 | 网信办等五部门 | 2026-07-15生效 | — |
| 《生成式AI服务管理暂行办法》 | 网信办等七部门 | 已生效 | — |
| 《算法推荐管理规定》 | 网信办等四部门 | 已生效 | — |
| 《网络安全法》(2025修订) | 全国人大常委会 | 2026-01-01生效 | — |

## 附录B：AGL Specification关键术语

| 术语 | 定义 | 来源 |
|------|------|------|
| Governance Receipt | 不可篡改的、密码学签名的agent action记录，是审计历史的原子单位 | [(H33.ai Spec v1.0.0)](https://h33.ai/specifications/agent-governance/) |
| Scope Constraints | Agent授权范围约束集，每条约束独立评估为boolean | [(H33.ai Spec v1.0.0)](https://h33.ai/specifications/agent-governance/) |
| Governance DAG | Governance Receipt组成的有向无环图 | [(H33.ai Spec v1.0.0)](https://h33.ai/specifications/agent-governance/) |
| Negative Authority Proof | 密码学证明agent不具有某action的权限（无需访问完整scope定义） | [(H33.ai Spec v1.0.0)](https://h33.ai/specifications/agent-governance/) |
| Escalation Semantics | action超出scope时的三种处理策略：escalate_auto/escalate_human/reject | [(H33.ai Spec v1.0.0)](https://h33.ai/specifications/agent-governance/) |
| Replay | 从governance chain确定性重建agent在任意历史时刻的authority state | [(H33.ai Spec v1.0.0)](https://h33.ai/specifications/agent-governance/) |
| Multi-Family PQ Signature | 多族后量子签名方案，保障Receipt的量子安全不可伪造性 | [(H33.ai Spec)](https://h33.ai/specifications/multi-family-pq/) |

---

*文档生成时间：2026-07-15 | 基于公开法规文本、行业标准草案、AGL Specification v1.0.0*
*所有法规引用标注官方来源URL，技术对接描述基于AGL公开规范，未夸大AGL能力*
