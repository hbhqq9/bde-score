# NeuralTrust × BDE Score Partnership Proposal

**日期**: 2026-07-15  
**版本**: v1.0  
**分类**: Confidential — BD Use Only  
**提案核心**: TrustGate执行 + AGL验证 = 完整的off-chain + on-chain合规栈

---

## 1. Executive Summary

NeuralTrust是EU领先的AI Agent安全平台，2026年6月获得$20M Seed融资，客户覆盖Ibex-35头部企业，产品以off-chain治理为核心。BDE Score的AGL（Agent Governance Layer）是链上治理层，提供不可篡改的合规验证与审计存证。

本提案提出将AGL作为TrustGate的**链上验证插件**集成，使NeuralTrust平台从"off-chain治理"升级为"off-chain + on-chain完整合规栈"，为EU AI Act 2026年8月强制执行期提供差异化合规能力。

**一句话**: NeuralTrust执行off-chain策略，AGL验证on-chain合规——两者结合，让每一次Agent交互都有链上可验证的合规证明。

---

## 2. 合作背景与市场时机

### 2.1 为什么是现在

| 驱动因素 | 紧迫性 |
|----------|--------|
| EU AI Act Art.50透明度义务 **2026-08-02生效** | 🔴 高 — 距今不到1个月 |
| NeuralTrust Seed轮融资刚完成，进入产品深化期 | 🟡 中 — 开放合作窗口 |
| Gartner预测2027年40%企业因治理缺口降级AI Agent | 🔴 高 — 市场教育需求 |
| Fortune 500企业预计2028年运行150,000+ Agent | 🟡 中 — 规模化治理刚需 |

[(NeuralTrust News)](https://neuraltrust.ai/news/neuraltrust-raises-20m) [(artificialintelligenceact.eu)](https://artificialintelligenceact.eu/transparency-rules-article-50/)

### 2.2 痛点定位

NeuralTrust当前合规能力集中在**off-chain层面**：

| EU AI Act条款 | NeuralTrust能力 | 缺口 |
|---------------|----------------|------|
| Art.9 风险管理 | ✅ TrustGuard运行时检测 | — |
| Art.10 数据治理 | ✅ TrustLens数据流追踪 | — |
| Art.12 日志可追溯 | ✅ TrustGate全量日志 | ❌ 日志不可篡改性未保证 |
| Art.13 透明度 | ✅ TrustLens可观测性 | — |
| Art.14 人工监督 | ✅ Guardian Agent | — |
| Art.15 稳健性 | ✅ TrustTest持续评估 | — |
| **Art.50 透明度义务** | ⚠️ 部分覆盖 | ❌ 合成内容标记/深度伪造标识缺位 |
| **合规证据链** | ❌ off-chain存储 | ❌ 链上不可篡改验证缺位 |

**核心缺口**: NeuralTrust的审计日志和合规证据存储在off-chain数据库中，无法提供**密码学可验证的不可篡改性**——这对银行、政府等高合规客户是硬需求。

---

## 3. 技术集成方案

### 3.1 集成架构

```
┌───────────────────────────────────────────────────────────────┐
│                    NeuralTrust Platform                        │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    TrustGate Gateway                      │  │
│  │                                                           │  │
│  │  Request Flow:                                            │  │
│  │  Agent ──► TrustGate Proxy ──► [Policy Engine] ──► LLM   │  │
│  │                                  │                        │  │
│  │                    ┌─────────────┴──────────────┐        │  │
│  │                    │   AGL External API Plugin    │        │  │
│  │                    │   (pre_request stage)        │        │  │
│  │                    │                              │        │  │
│  │                    │  1. Verify compliance hash   │        │  │
│  │                    │  2. Check on-chain state     │        │  │
│  │                    │  3. Return pass/fail+evidence │        │  │
│  │                    └─────────────┬──────────────┘        │  │
│  │                                  │                        │  │
│  │                    ┌─────────────▼──────────────┐        │  │
│  │                    │    AGL On-Chain Layer        │        │  │
│  │                    │                              │        │  │
│  │                    │  • Compliance receipts       │        │  │
│  │                    │  • Tamper-proof audit logs   │        │  │
│  │                    │  • Cross-jurisdiction verify │        │  │
│  │                    └────────────────────────────┘        │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │  TrustGuard   │  │  TrustLens    │  │    TrustTest     │    │
│  │  (monitor)    │  │  (observe)    │  │    (test)        │    │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘    │
│         │                 │                    │               │
│         └─────────┬───────┘                    │               │
│                   ▼                            │               │
│         ┌──────────────────┐                   │               │
│         │  AGL Post-Response│◄─────────────────┘               │
│         │  (compliance hash│                                  │
│         │   on-chain)       │                                  │
│         └──────────────────┘                                   │
└───────────────────────────────────────────────────────────────┘
```

### 3.2 集成实现路径

#### Phase 1: External API Plugin（2-4周 MVP）

利用TrustGate已有的External API Plugin机制，零代码修改集成：

**Step 1**: AGL提供验证端点
```
POST https://agl.bde-score.xyz/v1/verify
Body: {
  "agent_action": "...",        // Agent请求内容
  "target_model": "gpt-4o",    // 目标模型
  "compliance_scope": ["eu-ai-act-art9", "gdpr"],  // 合规范围
  "session_id": "...",          // TrustGate会话ID
  "consumer_id": "..."         // TrustGate消费者ID
}
Response: {
  "is_compliant": true,
  "evidence_hash": "0xabc123...",  // 链上证据哈希
  "receipt_tx": "0xdef456...",      // 链上交易哈希
  "confidence": 0.98,
  "details": { ... }
}
```

**Step 2**: 在TrustGate配置External API Plugin
```json
{
  "name": "external_api",
  "enabled": true,
  "stage": "pre_request",
  "settings": {
    "endpoint": "https://agl.bde-score.xyz/v1/verify",
    "method": "POST",
    "timeout": "3s",
    "headers": {
      "Authorization": "Bearer ${AGL_API_KEY}",
      "X-AGL-Network": "mainnet"
    },
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
        "message": "On-chain compliance verification failed — action blocked"
      }
    ]
  }
}
```

**Step 3**: post-response阶段存证
```json
{
  "name": "external_api",
  "enabled": true,
  "stage": "post_response",
  "settings": {
    "endpoint": "https://agl.bde-score.xyz/v1/notarize",
    "method": "POST",
    "timeout": "5s",
    "field_maps": [
      {"source": "response.output", "destination": "interaction_result"},
      {"source": "session_id", "destination": "session_ref"}
    ]
  }
}
```

#### Phase 2: Custom Plugin（4-8周，深度集成）

- 实现TrustGate Go plugin interface
- 直接在gateway进程内执行AGL验证
- 支持本地缓存减少链上调用
- 增量延迟目标 <5ms

#### Phase 3: MCP Tool集成（8-12周，生态集成）

- AGL作为MCP Server注册到TrustGate MCP平面
- Agent可通过`agl_verify`工具主动查询合规状态
- 适合multi-agent编排中的合规检查点

### 3.3 数据流与合规映射

| EU AI Act条款 | TrustGate执行（off-chain） | AGL验证（on-chain） |
|---------------|---------------------------|---------------------|
| Art.9 风险管理 | 风险检测策略执行 | 风险评估结果链上存证 |
| Art.12 日志可追溯 | 全量交互日志 | 日志哈希链上锚定（不可篡改） |
| Art.13 透明度 | 行为可观测 | 合规状态链上可验证 |
| Art.14 人工监督 | Guardian Agent执行 | 人工干预记录链上存证 |
| Art.50 透明度义务 | AI交互披露执行 | 披露证据链上存证 |

---

## 4. 商业价值分析

### 4.1 对NeuralTrust的价值

| 价值维度 | 具体收益 |
|----------|----------|
| **产品差异化** | 唯一提供"off-chain + on-chain"完整合规栈的EU AI Agent安全平台 |
| **客户获取** | 链上验证是银行/政府客户的硬需求，增强竞标能力 |
| **合规溢价** | 可对"on-chain合规增强包"收取额外费用 |
| **Art.50时效** | 2026-08-02生效，链上透明度存证可作为差异化合规证据 |
| **ISO 42001对齐** | 链上审计日志增强ISO 42001认证的证据力 |

### 4.2 对BDE Score的价值

| 价值维度 | 具体收益 |
|----------|----------|
| **用例验证** | NeuralTrust的1000+ AI应用监控量为AGL提供真实用例 |
| **市场进入** | 通过NeuralTrust的KPMG/Capgemini渠道触达大型企业客户 |
| **品牌背书** | NeuralTrust作为Gartner认可厂商，集成AGL增强可信度 |
| **社区曝光** | TrustGate开源项目贡献，获取AI安全社区关注 |

### 4.3 合作模式建议

| 模式 | 描述 | 阶段 |
|------|------|------|
| **技术集成伙伴** | AGL作为TrustGate认证插件上架 | Phase 1-2 |
| **联合Go-to-Market** | 对银行/政府客户联合方案 | Phase 2 |
| **收入分成** | on-chain合规增强包收入分成 | Phase 3 |
| **开源共建** | AGL plugin贡献到TrustGate开源项目 | 持续 |

---

## 5. 竞争护城河分析

### 5.1 为什么NeuralTrust应该选择BDE Score

| 竞品方案 | 局限性 | BDE Score AGL优势 |
|----------|--------|-------------------|
| 自建链上验证 | NeuralTrust 21人团队，不应分散资源 | 即插即用，零基础设施负担 |
| 传统PKI时间戳 | 无法跨司法管辖区验证 | 区块链天然跨域验证 |
| 其他链上方案 | 无AI Agent领域理解 | AGL专门为Agent治理设计 |
| 纯off-chain方案 | 无法满足高合规客户不可篡改需求 | 链上+链下双重保证 |

### 5.2 切换成本分析

- **集成成本**: External API Plugin配置仅需5分钟（零代码修改）
- **运行成本**: AGL验证API调用，按量付费
- **退出成本**: 停用Plugin即可，无lock-in

---

## 6. 实施路线图

```
2026 Q3                          2026 Q4                          2027 Q1
───────────────────────────────── ───────────────────────────────── ────────────────────────────
Week 1-2:  初步接触与Pitch        Week 1-4:  PoC开发与测试          Week 1-4:  Custom Plugin开发
Week 3-4:  技术对齐会议           Week 5-8:  客户联合PoC            Week 5-8:  MCP Tool集成
Week 5-6:  External API Plugin   Week 9-12: Go-to-Market启动      Week 9-12: 规模化部署
           MVP集成                                              收入分成启动
Week 7-8:  联合Demo准备
```

### 6.1 里程碑

| 里程碑 | 时间 | 成功标准 |
|--------|------|----------|
| M1: 首次技术对齐 | 2026-08前 | CTO/CEO会议完成，技术路线图共识 |
| M2: MVP集成 | 2026-09前 | External API Plugin跑通端到端流程 |
| M3: 首个联合客户PoC | 2026-10前 | 与NeuralTrust某银行客户完成PoC |
| M4: 正式合作公告 | 2026-12前 | 联合新闻稿发布 |
| M5: 规模化 | 2027-Q1 | 3+联合客户，Custom Plugin上线 |

---

## 7. 风险与缓解

| 风险 | 概率 | 影响 | 缓解策略 |
|------|------|------|----------|
| NeuralTrust拒绝合作（自建链上能力） | 低 | 高 | 强调开源贡献路径降低门槛；自建成本高且偏离核心 |
| 链上验证增加延迟 | 中 | 中 | 异步验证+本地缓存；post-response存证为主 |
| EU AI Act执行力度不足 | 低 | 高 | 定位为"最佳实践"而非"强制要求"；ISO 42001补充驱动 |
| KPMG等合作伙伴推荐竞品 | 中 | 中 | 与KPMG沟通定位为技术插件，不与GTM服务冲突 |
| 技术集成复杂度超预期 | 中 | 中 | Phase 1使用External API Plugin（零代码），渐进深化 |

---

## 8. 联系计划

### 8.1 推荐接触路径

1. **LinkedIn冷启动** → Joan Vendrell (CEO)，简短介绍BDE Score + 集成价值
2. **技术会议请求** → 通过rodrigo.fernandez@neuraltrust.ai，提请CTO技术对齐
3. **联合活动** → 参与NeuralTrust参与的EU AI Act合规活动/OWASP会议
4. **开源贡献** → 先向TrustGate开源项目提交AGL Plugin PR，建立技术信任

### 8.2 Pitch要点（30秒版）

> "NeuralTrust的TrustGate是EU最强的off-chain Agent治理网关。BDE Score的AGL是链上Agent治理层。集成后，每一次TrustGate的策略执行都有链上可验证的合规证明——off-chain执行 + on-chain验证 = 完整合规栈。这对你的银行和政府客户是硬需求，集成只需要5分钟配置External API Plugin。"

### 8.3 关键联系人

| 姓名 | 角色 | 邮箱 | LinkedIn |
|------|------|------|----------|
| Joan Vendrell | CEO & Co-Founder | — (通过press contact) | ✅ 公开 |
| Victor Garcia | CTO & Co-Founder | — | ✅ 公开 |
| Alejandro Domingo | COO & Co-Founder | — | ✅ 公开 |
| Rodrigo Fernández | CMO / Press Contact | rodrigo.fernandez@neuraltrust.ai | ✅ 公开 |

---

## 9. 附录

### A. TrustGate Plugin接口参考

TrustGate提供两种扩展机制：
1. **External API Plugin** — 声明式HTTP调用，支持pre_request/post_response阶段 [(docs)](https://docs.neuraltrust.ai/trustgate/plugins/external-api)
2. **Custom Plugin** — Go原生插件接口 [(docs)](https://docs.neuraltrust.ai/trustgate/extending/how-to)

### B. AGL集成配置模板

见Section 3.2中的完整配置示例。

### C. EU AI Act合规映射表

见Section 3.3。

### D. 竞品分析

见Intelligence Report Section 8。

---

*本提案基于公开信息编写，不包含任何非公开数据或API密钥。所有信息来源已标注。*
