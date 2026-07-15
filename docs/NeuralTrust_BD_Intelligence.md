# NeuralTrust BD Intelligence Report

**完成日期**: 2026-07-15  
**目标**: 为BDE Score与NeuralTrust的BD合作提案提供全面情报支撑  
**分类**: Confidential — BD Use Only

---

## 1. 公司概览

| 维度 | 详情 |
|------|------|
| **公司名** | NeuralTrust |
| **官网** | https://neuraltrust.ai |
| **文档站** | https://docs.neuraltrust.ai |
| **成立时间** | 2022年7月，西班牙巴塞罗那 [(NeuralTrust News)](https://neuraltrust.ai/news/neuraltrust-raises-20m) |
| **办公地点** | 巴塞罗那（HQ）、伦敦、慕尼黑、纽约 [(GSMA Case Study)](https://www.gsma.com/get-involved/gsma-foundry/wp-content/uploads/2026/07/Securing-the-Agentic-Enterprise-hr.pdf) |
| **员工数** | 约21人（+61.5% YoY） [(Crustdata)](https://profiles.crustdata.com/company/neuraltrust) |
| **定位** | EU领先的AI Agent安全与治理平台 |

### 1.1 融资情况

| 轮次 | 金额 | 时间 | 领投 | 参投 |
|------|------|------|------|------|
| **Seed** | **$20M（€17.2M）** | 2026-06-17 | Alstin Capital | VentureFriends, Seaya, Kibo Ventures, Banc Sabadell, EA Ventures Plug and Play, Finaves (IESE) |
| **Public Funding** | 未披露 | 持续 | European Innovation Council (EIC) | Spain's State Research Agency (AEI) |
| **Total Funding** | **$22.9M** across 4 rounds | — | — | [(Crustdata)](https://profiles.crustdata.com/company/neuraltrust) |

**关键信号**:
- 自称"EU史上最大网络安全Seed轮" [(NeuralTrust News)](https://neuraltrust.ai/news/neuraltrust-raises-20m)
- 公私混合融资（VC + EIC + AEI），体现EU数字主权战略支持 [(GSMA Case Study)](https://www.gsma.com/get-involved/gsma-foundry/wp-content/uploads/2026/07/Securing-the-Agentic-Enterprise-hr.pdf)
- Q1 2026 ARR已翻倍于2025全年 [(NeuralTrust News)](https://neuraltrust.ai/news/neuraltrust-raises-20m)

### 1.2 行业认可

| 认可机构 | 认可内容 | 时间 |
|----------|----------|------|
| Gartner | Representative Vendor — Market Guide for AI Gateways | 2025 |
| Gartner | Representative Vendor — Market Guide for Guardian Agents | 2026 |
| Gartner | Sample Vendor — Hype Cycle for Data Security Technologies (AI Runtime Defense) | 2026-07 |
| Gartner | AI Vendor Race: AI Guardrails — Named a Star | 2026 |
| KuppingerCole | Leader — 2025 Leadership Compass for Generative AI Defense | 2025 |
| MarketsandMarkets | Leader — 2026 Agentic AI Security Quadrant | 2026 |
| OWASP | Research contributions (Echo Chamber Attack, Semantic Chaining) | 持续 |
| 4YFN / MWC | Digital Horizons Award finalist | 2026 |
| South Summit Madrid | 双奖 | 2025 |

[(NeuralTrust News)](https://neuraltrust.ai/news/neuraltrust-raises-20m) [(GSMA Case Study)](https://www.gsma.com/get-involved/gsma-foundry/wp-content/uploads/2026/07/Securing-the-Agentic-Enterprise-hr.pdf) [(NeuralTrust About)](https://neuraltrust.ai/es/about)

---

## 2. 创始团队与核心人员

### 2.1 三位联合创始人

| 角色 | 姓名 | 背景 |
|------|------|------|
| **CEO & Co-Founder** | **Joan Vendrell Farreny** | 前Mango首席数字官(CDO)，负责AI部署与安全；此前任职Amazon、McKinsey [(GSMA Case Study)](https://www.gsma.com/get-involved/gsma-foundry/wp-content/uploads/2026/07/Securing-the-Agentic-Enterprise-hr.pdf) |
| **CTO & Co-Founder** | **Victor Garcia** | 深度ML与安全架构背景；前Mango Head of Big Data；前Bigfinite Chief Architect；Apache Zeppelin贡献者；计算机科学学位 [(RocketReach)](https://rocketreach.co/victor-garcia-email_100808550) |
| **COO & Co-Founder** | **Alejandro Domingo Salvador** | 前McKinsey Associate Partner（AI transformation）；此前曾将一家startup做到exit；运营/合规/GTM经验 [(NeuralTrust News)](https://neuraltrust.ai/news/neuraltrust-raises-20m) |

### 2.2 其他核心人员

| 角色 | 姓名 |
|------|------|
| CMO | Rodrigo F. Baon |
| UK Managing Director | Cameron Brown |
| Head of Compliance | Juan José Jaimes Gaitán |
| Head of Revenue Operations | Sanjna Mallappa |

[(Crustdata)](https://profiles.crustdata.com/company/neuraltrust)

### 2.3 公开联系方式

| 渠道 | 信息 |
|------|------|
| Press Contact | rodrigo.fernandez@neuraltrust.ai [(NeuralTrust News)](https://neuraltrust.ai/news/neuraltrust-raises-20m) |
| LinkedIn (Joan Vendrell) | 公开可查 |
| X/Twitter | 未发现官方活跃账号 |
| 官网联系 | https://neuraltrust.ai (Book a Demo) |

---

## 3. 产品体系深度分析

NeuralTrust平台当前包含**4个产品**（早期3个，最新为4个）：

### 3.1 TrustGate — Agent Gateway（策略执行层）

| 维度 | 详情 |
|------|------|
| **定位** | AI Agent流量网关，拦截、路由、治理所有LLM/MCP/Tool调用 |
| **开源** | ✅ Apache-2.0，Go语言，https://github.com/NeuralTrust/TrustGate [(docs)](https://docs.neuraltrust.ai/trustgate/overview.md) |
| **版本** | v1.8.9（截至2025-10-13，Go module发布） [(pkg.go.dev)](https://pkg.go.dev/github.com/NeuralTrust/TrustGate@v1.8.9) |
| **架构** | 单Go二进制 + Postgres + Redis + Kafka；支持Docker/K8s部署 [(docs)](https://docs.neuraltrust.ai/trustgate/getting-started/install) |
| **三个平面** | Admin(:8080)、Proxy(:8081)、MCP(:8082) [(docs)](https://docs.neuraltrust.ai/trustgate/getting-started/install) |
| **性能** | <100ms延迟，20K+ RPS/节点 [(NeuralTrust Homepage)](https://neuraltrust.ai) |
| **支持的LLM** | OpenAI, Anthropic, Azure OpenAI, AWS Bedrock, Google Gemini/Vertex AI, Groq, Mistral, Cohere, Together, Self-hosted [(docs)](https://docs.neuraltrust.ai/trustgate/platform/integration-guides/openai-sdk) |

**TrustGate核心对象模型**:

| 对象 | 作用 |
|------|------|
| Gateway | 顶层容器，持有所有配置 |
| Consumer | 流量来源（inline或role_based） |
| Route | 路由规则，将流量映射到LLM provider |
| Policy | 检测/动作策略（Where + When + Then） |
| Auth | 认证凭据（API Key, OAuth2, JWT, mTLS） |
| Registry | 上游服务注册（LLM provider或MCP server） |
| Role | 角色定义，用于role_based consumer的权限继承 |

**TrustGate四大执行表面(Surfaces)**:

| Surface | 覆盖流量 | 运行位置 |
|---------|----------|----------|
| Gateway | LLM代理流量 | Gateway engine (Serverless/Dedicated) |
| Browser | Web端LLM交互 | 浏览器扩展 |
| API | 后端直接调用 | API engine |
| Endpoint | 桌面应用/IDE/CLI | MITM代理（MDM推送PAC文件） |

[(docs)](https://docs.neuraltrust.ai/trustgate/platform/enforcement-surfaces)

**插件架构（关键集成切入点）**:

TrustGate提供**两种扩展方式**：
1. **External API Plugin** — 声明式配置，通过HTTP调用外部服务，在请求/响应生命周期特定阶段执行
2. **Custom Plugin** — Go原生插件，在gateway内部执行，可访问完整请求/响应上下文

External API Plugin配置示例：
```json
{
  "name": "external_api",
  "enabled": true,
  "stage": "pre_request",
  "settings": {
    "endpoint": "https://api.example.com/validate",
    "method": "POST",
    "timeout": "5s",
    "headers": {"Authorization": "Bearer token"},
    "field_maps": [{"source": "input", "destination": "text"}],
    "conditions": [{
      "field": "result.is_valid",
      "operator": "eq",
      "value": false,
      "stop_flow": true,
      "message": "Validation failed"
    }]
  }
}
```

[(docs: External API Plugin)](https://docs.neuraltrust.ai/trustgate/plugins/external-api) [(docs: How to Extend)](https://docs.neuraltrust.ai/trustgate/extending/how-to)

**MCP平面**:

TrustGate运行独立的MCP平面(:8082)，聚合多个MCP Server为统一端点：
- 支持tools/list, tools/call, resources/*, prompts/*
- Toolkit机制限制每个consumer可用的工具集合
- 内置OAuth2 Server用于agent认证
- 支持streamable-http传输

[(docs: MCP Plane)](https://docs.neuraltrust.ai/trustgate/mcp/overview)

### 3.2 TrustGuard — Agent Runtime Security（运行时安全）

| 维度 | 详情 |
|------|------|
| **定位** | 自主Agent运行时安全引擎，跨平台/端点检测和阻止威胁 |
| **核心能力** | 有状态行为安全、持久攻击者追踪、Guardian Agent控制 |
| **Guardian Agent** | 监控并控制自主Agent行为和工具执行 [(NeuralTrust Blog)](https://neuraltrust.ai/blog/best-ai-governance-tools) |
| **与TrustGate关系** | TrustGuard检测器作为TrustGate策略的检测组件嵌入运行 |

### 3.3 TrustLens — Agent Posture Management（持续态势管理）

| 维度 | 详情 |
|------|------|
| **定位** | 发现、记录、评分企业内所有AI Agent/模型/工具集成 |
| **核心能力** | Agent资产发现、风险评分、权限漂移检测、remediation工作流 |
| **Shadow AI检测** | 自动发现未授权AI工具使用 [(NeuralTrust Blog)](https://neuraltrust.ai/blog/best-ai-governance-tools) |
| **合规映射** | 支持OWASP, MITRE, ISO框架映射与实时覆盖率追踪 |

### 3.4 TrustTest — Automated Red Teaming（自动化红队）

| 维度 | 详情 |
|------|------|
| **定位** | 自适应红队测试引擎，模拟对抗攻击 |
| **核心能力** | 150+攻击目录、自适应攻击生成、持续评估 [(NeuralTrust Homepage)](https://neuraltrust.ai) |
| **研究贡献** | Echo Chamber Attack（多轮越狱）、Semantic Chaining（多模态攻击），已进入OWASP AI安全项目分类法 [(NeuralTrust News)](https://neuraltrust.ai/news/neuraltrust-raises-20m) |

### 3.5 TrustScan — CI/CD安全扫描

| 维度 | 详情 |
|------|------|
| **定位** | AI代码库、配置、开源依赖安全扫描，集成CI/CD管道 |

[(NeuralTrust Blog)](https://neuraltrust.ai/fr/blog/offensive-vs-defensive-ai-security)

---

## 4. 技术架构深度分析

### 4.1 Split-Plane架构（数据主权核心设计）

NeuralTrust采用**控制平面(Control Plane) + 数据平面(Data Plane)**分离架构：

- **数据平面**：在客户VPC/On-Prem内运行，执行策略、检测流量、**客户数据不离开客户环境**
- **控制平面**：可在NeuralTrust云或客户自有云运行，不处理客户内容

[(NeuralTrust Homepage)](https://neuraltrust.ai) [(docs)](https://docs.neuraltrust.ai/neuraltrust/deployment/deployment-models.md)

### 4.2 部署模型

| 模型 | 描述 |
|------|------|
| **Hybrid** | Data Plane在客户环境（EKS/AKS/GKE/K8s），Control Plane在NeuralTrust SaaS |
| **Self-Hosted** | 全部组件在客户集群，支持air-gapped环境 |
| **SaaS** | EU/US区域，NeuralTrust托管 |

支持云平台：AWS EKS, Azure AKS, Google GKE, Vanilla Kubernetes, Red Hat OpenShift [(docs: llms.txt)](https://docs.neuraltrust.ai/llms.txt)

### 4.3 技术栈

| 层面 | 技术 |
|------|------|
| 核心语言 | Go (TrustGate), Python (Firewall/ML workers) |
| Web框架 | Fiber (Go) |
| 数据库 | PostgreSQL, Redis, Kafka, ClickHouse |
| 容器 | Docker, Kubernetes (Helm chart) |
| 可观测性 | Prometheus, Kafka telemetry, TrustLens集成 |
| ML推理 | GPU节点支持 (Firewall workers) |
| 认证 | JWT, OAuth2, mTLS, API Key |
| SIEM集成 | Microsoft Sentinel, Datadog, Splunk, Elastic, IBM QRadar, Generic Webhook (OCSF格式) |

### 4.4 安全认证

- **ISO 27001** 认证已获得（2026年6月4日公告） [(NeuralTrust About)](https://neuraltrust.ai/es/about)

---

## 5. EU AI Act合规能力评估

### 5.1 NeuralTrust公开声明的合规框架支持

NeuralTrust明确声明支持以下合规框架：
- **EU AI Act** — 风险分级合规、透明度义务、审计追踪 [(NeuralTrust Blog)](https://neuraltrust.ai/blog/ai-governance-complete-guide)
- **GDPR** — 数据处理合规、隐私保护 [(docs)](https://docs.neuraltrust.ai/neuraltrust/data-privacy/overview.md)
- **ISO/IEC 42001** — AI管理体系 [(NeuralTrust Blog)](https://neuraltrust.ai/blog/best-ai-governance-tools)
- **NIST AI RMF** — 风险管理框架 [(NeuralTrust Blog)](https://neuraltrust.ai/blog/best-ai-governance-tools)
- **OWASP LLM Top 10** — 安全基准 [(NeuralTrust Blog)](https://neuraltrust.ai/blog/best-ai-governance-tools)
- **DORA** — 数字运营韧性法案 [(GSMA Case Study)](https://www.gsma.com/get-involved/gsma-foundry/wp-content/uploads/2026/07/Securing-the-Agentic-Enterprise-hr.pdf)
- **HIPAA/SOX** — 数据隐私文档中提及 [(docs)](https://docs.neuraltrust.ai/neuraltrust/data-privacy/overview.md)

### 5.2 Article 50（透明度义务）具体能力

**未发现**NeuralTrust对EU AI Act Article 50透明度义务（如AI交互披露、合成内容机器可读标记、深度伪造标识）的**专门公开声明或产品功能**。

当前NeuralTrust的合规能力集中在：
- Article 9: 风险管理 → TrustGuard运行时检测 + TrustTest红队
- Article 10: 数据治理 → TrustLens数据流追踪
- Article 12: 日志与可追溯性 → TrustGate全量审计日志
- Article 13: 透明度（面向部署者） → TrustLens可观测性
- Article 14: 人工监督 → Guardian Agent + Break-the-Glass机制
- Article 15: 准确性与稳健性 → TrustTest持续评估

**[INFO_GAP]**: Article 50(2) 合成内容标记和Article 50(4) 深度伪造披露能力，NeuralTrust暂无公开产品声明。2026年8月2日Art.50强制执行期限临近，这可能是合作切入点。

### 5.3 EU AI Act关键截止日期

| 日期 | 义务 |
|------|------|
| 2025-02-02 | 禁止AI实践条款生效 |
| 2025-08-02 | GPAI模型义务开始 |
| **2026-08-02** | **Art.50透明度义务生效**（高关注度） |
| 2026-12-02 | AI Omnibus过渡期（2026年8月前已上市的GenAI系统） |
| 2027-08-02 | 全面适用（所有条款） |

[(artificialintelligenceact.eu)](https://artificialintelligenceact.eu/transparency-rules-article-50/)

---

## 6. 客户与合作伙伴

### 6.1 已公开客户

| 客户 | 行业 | 来源 |
|------|------|------|
| AirEuropa | 航空 | [(NeuralTrust News)](https://neuraltrust.ai/news/neuraltrust-raises-20m) |
| Abanca | 银行 | [(NeuralTrust News)](https://neuraltrust.ai/news/neuraltrust-raises-20m) |
| Iberia | 航空 | [(NeuralTrust News)](https://neuraltrust.ai/news/neuraltrust-raises-20m) |
| Banc Sabadell | 银行 | [(NeuralTrust News)](https://neuraltrust.ai/news/neuraltrust-raises-20m) |
| ISDIN | 医药/护肤 | [(NeuralTrust Homepage)](https://neuraltrust.ai) |
| Capgemini (作为logo展示) | IT咨询 | [(NeuralTrust Homepage)](https://neuraltrust.ai) |
| NTT Data | IT咨询 | [(NeuralTrust Homepage)](https://neuraltrust.ai) |
| Devoteam | IT咨询 | [(NeuralTrust Homepage)](https://neuraltrust.ai) |
| Bentego | IT咨询 | [(NeuralTrust Homepage)](https://neuraltrust.ai) |
| LugaPel | 零售 | [(NeuralTrust Homepage)](https://neuraltrust.ai) |

**客户画像**:
- 92%客户年收入 >$1B [(NeuralTrust News)](https://neuraltrust.ai/news/neuraltrust-raises-20m)
- 80%位于欧洲，20%国际 [(NeuralTrust News)](https://neuraltrust.ai/news/neuraltrust-raises-20m)
- 客户覆盖：银行、航空、能源、医疗、零售、电信、保险、政府 [(GSMA Case Study)](https://www.gsma.com/get-involved/gsma-foundry/wp-content/uploads/2026/07/Securing-the-Agentic-Enterprise-hr.pdf)
- Ibex-35成分企业中已有大量覆盖 [(Revista Corporate)](https://www.revistacorporate.com/244709/cuando-la-ia-pasa-de-hablar-a-actuar-neuraltrust-lidera-en-europa-la-ciberseguridad-de-los-agentes-de-ia)

### 6.2 战略合作伙伴

| 合作伙伴 | 合作性质 |
|----------|----------|
| **KPMG** | 核心战略伙伴，带来大型企业客户。>40%客户管道来自合作伙伴 [(GSMA Case Study)](https://www.gsma.com/get-involved/gsma-foundry/wp-content/uploads/2026/07/Securing-the-Agentic-Enterprise-hr.pdf) |
| Capgemini | 行业协作 |
| Sopra Steria | 行业协作 |
| Bentego | 行业协作 |
| M3Corp | 行业协作 |
| NTT Data | 行业协作 |
| Deloitte, EY | 管道合作伙伴 [(GSMA Case Study)](https://www.gsma.com/get-involved/gsma-foundry/wp-content/uploads/2026/07/Securing-the-Agentic-Enterprise-hr.pdf) |

---

## 7. 运营数据

| 指标 | 数值 | 来源 |
|------|------|------|
| 攻击拦截 | 3M+（官网）/ 15M+（西语报道） | [(NeuralTrust.ai)](https://neuraltrust.ai) [(Revista Corporate)](https://www.revistacorporate.com/244709/cuando-la-ia-pasa-de-hablar-a-actuar-neuraltrust-lidera-en-europa-la-ciberseguridad-de-los-agentes-de-ia) |
| AI应用监控 | 1,000+ / 6,000+ | [(NeuralTrust.ai)](https://neuraltrust.ai) [(Revista Corporate)](https://www.revistacorporate.com/244709/cuando-la-ia-pasa-de-hablar-a-actuar-neuraltrust-lidera-en-europa-la-ciberseguridad-de-los-agentes-de-ia) |
| AI交互分析 | 22M+ | [(NeuralTrust.ai)](https://neuraltrust.ai) |
| 模型扫描 | 1.7M+ | [(NeuralTrust.ai)](https://neuraltrust.ai) |
| 恶意交互比例 | ~1.2% | [(NeuralTrust News)](https://neuraltrust.ai/news/neuraltrust-raises-20m) |
| 防止财务损失 | $43M / $107M | [(NeuralTrust.ai)](https://neuraltrust.ai) [(Revista Corporate)](https://www.revistacorporate.com/244709/cuando-la-ia-pasa-de-hablar-a-actuar-neuraltrust-lidera-en-europa-la-ciberseguridad-de-los-agentes-de-ia) |
| 检测延迟 | <10ms / <100ms | [(Revista Corporate)](https://www.revistacorporate.com/244709/cuando-la-ia-pasa-de-hablar-a-actuar-neuraltrust-lidera-en-europa-la-ciberseguridad-de-los-agentes-de-ia) [(NeuralTrust.ai)](https://neuraltrust.ai) |
| 攻击目录 | 150+ | [(NeuralTrust.ai)](https://neuraltrust.ai) |
| 多语言检测 | 99% | [(NeuralTrust.ai)](https://neuraltrust.ai) |

**注意**: 官网西语报道数据存在差异（官网3M vs 西媒15M拦截数），可能反映不同统计时间窗口。

---

## 8. 竞品格局

| 竞品 | 总部 | 关键差异 |
|------|------|----------|
| Protect AI | 美国 | 全栈AI安全，开源LLM Guard |
| Robust Intelligence (Cisco) | 美国 | 模型评估/测试，被Cisco收购 |
| Lakera | 瑞士 | Prompt注入专注，Guard产品 |
| HiddenLayer | 美国 | ML模型安全，MLOps集成 |

NeuralTrust差异化定位：
1. **EU原生** — 数据主权优先，split-plane架构 [(GSMA Case Study)](https://www.gsma.com/get-involved/gsma-foundry/wp-content/uploads/2026/07/Securing-the-Agentic-Enterprise-hr.pdf)
2. **Agent原生** — 不是从模型安全演进，而是从Agent行为安全出发
3. **MCP原生** — 专门MCP平面，Agent-to-Tool安全网关
4. **开源核心** — TrustGate Apache-2.0，可社区贡献

---

## 9. AGL集成切入点分析

### 9.1 技术集成路径

基于TrustGate的插件架构，BDE Score的AGL（链上治理层）可通过以下路径集成：

#### 路径一：External API Plugin（推荐首选）

```
Agent Request → TrustGate → [External API Plugin: AGL Verify]
                                        ↓
                              AGL链上验证服务
                              (on-chain compliance check)
                                        ↓
                              返回 {is_compliant: true/false, evidence_hash: "0x..."}
                                        ↓
                    TrustGate根据condition决定: 放行 / 阻断
```

**集成配置示例**:
```json
{
  "name": "external_api",
  "enabled": true,
  "stage": "pre_request",
  "settings": {
    "endpoint": "https://agl.bde-score.xyz/v1/verify",
    "method": "POST",
    "timeout": "3s",
    "headers": {"Authorization": "Bearer ${AGL_API_KEY}"},
    "field_maps": [
      {"source": "input", "destination": "agent_action"},
      {"source": "model", "destination": "target_model"},
      {"source": "route.tags", "destination": "compliance_scope"}
    ],
    "conditions": [
      {
        "field": "result.is_compliant",
        "operator": "eq",
        "value": false,
        "stop_flow": true,
        "message": "On-chain compliance verification failed"
      }
    ]
  }
}
```

#### 路径二：Custom Plugin（深度集成）

直接在TrustGate Go代码中实现AGL验证插件：
- 实现`pluginiface.Plugin`接口
- 可访问完整请求/响应上下文（含MCP tool calls）
- 在pre_request阶段执行链上验证
- 适合需要极低延迟（<5ms）或复杂上下文判断的场景

#### 路径三：MCP Tool集成

将AGL暴露为MCP Server的一个工具：
- Agent在调用敏感工具前，先调用`agl_verify`工具
- TrustGate MCP平面统一路由
- 适合"Agent主动合规"场景

### 9.2 合作价值映射

| NeuralTrust痛点 | AGL解决方案 | 价值 |
|----------------|------------|------|
| off-chain合规证据无法链上验证 | AGL提供链上验证层 | 增强审计可信度 |
| EU AI Act Art.50/Art.12需要不可篡改日志 | AGL链上存证 | 合规差异化 |
| 客户（银行/政府）要求更高可信度 | 链上+链下双重证明 | 客户获取优势 |
| 无链上治理能力 | AGL作为TrustGate的"链上验证插件" | 产品完整度 |

### 9.3 核心提案定位

**"TrustGate执行 + AGL验证 = 完整的off-chain + on-chain合规栈"**

```
┌─────────────────────────────────────────────────────────┐
│                   NeuralTrust Platform                    │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────┐    │
│  │ TrustGate │  │  TrustGuard   │  │   TrustLens    │    │
│  │ (execute) │  │  (monitor)    │  │   (observe)    │    │
│  └─────┬─────┘  └──────────────┘  └────────────────┘    │
│        │ off-chain enforcement                             │
│        ▼                                                  │
│  ┌──────────────────────────────────────┐                │
│  │     AGL Plugin (External API)         │                │
│  │     on-chain verification layer       │                │
│  │  • compliance hash on-chain           │                │
│  │  • audit trail immutability           │                │
│  │  • regulatory evidence chain          │                │
│  └──────────────────────────────────────┘                │
│        │                                                  │
│        ▼                                                  │
│  ┌──────────────────────────────────────┐                │
│  │         Blockchain (on-chain)         │                │
│  │  • compliance receipts                │                │
│  │  • tamper-proof audit logs            │                │
│  │  • cross-jurisdiction verification    │                │
│  └──────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────┘
```

---

## 10. 联系策略建议

### 10.1 首选联系人

| 优先级 | 联系人 | 渠道 | 理由 |
|--------|--------|------|------|
| 1 | Joan Vendrell (CEO) | LinkedIn / rodrigo.fernandez@neuraltrust.ai | 决策者，战略合作需CEO级别 |
| 2 | Alejandro Domingo (COO) | LinkedIn | GTM合作，渠道策略 |
| 3 | Victor Garcia (CTO) | LinkedIn | 技术集成深度讨论 |
| 4 | Juan José Jaimes (Head of Compliance) | — | 合规框架对接 |

### 10.2 接触时机

- ✅ Seed融资刚完成（2026-06-17），团队扩张期，开放合作
- ✅ EU AI Act Art.50 2026-08-02生效前，合规需求紧迫
- ✅ 产品深化集成阶段（融资用途之一）
- ✅ ISO 27001刚获认证，安全合规形象强化期

### 10.3 潜在顾虑与应对

| 顾虑 | 应对 |
|------|------|
| "区块链增加延迟" | AGL通过External API Plugin集成，异步验证+本地缓存，<5ms增量延迟 |
| "链上验证是否必要" | 定位为可选增强层，不替代off-chain能力；对高合规客户（银行/政府）提供差异化 |
| "BDE Score规模太小" | 强调开源TrustGate社区贡献路径，降低合作门槛 |
| "与现有合作伙伴冲突" | 定位为技术插件而非竞争服务，与KPMG/Capgemini的GTM合作不冲突 |

---

## 11. 信息缺口标注

| 缺口 | 说明 |
|------|------|
| [INFO_GAP] GitHub Stars/Forks | TrustGate开源仓库的社区活跃度数据未获取到精确值 |
| [INFO_GAP] Art.50具体产品功能 | NeuralTrust是否已开发Art.50透明度工具（AI内容标记/深度伪造标识）未有公开信息 |
| [INFO_GAP] 定价模型 | 企业定价基于protected apps/agents/traffic，需联系获取报价 |
| [INFO_GAP] ARR绝对值 | 仅知Q1 2026翻倍于2025全年，基数未披露 |
| [INFO_GAP] 慕尼黑/纽约办公室 | 最新GSMA案例提及4个办公室，但官网仅列Barcelona/London |
