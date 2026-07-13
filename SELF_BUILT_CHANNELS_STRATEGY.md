# BDE Score™ 自建渠道战略 v1.0

**创建日期**: 2026-07-13
**状态**: ACTIVE
**核心原则**: 零人工介入，100%自动化分发

## 战略背景

### 问题诊断
传统分发渠道（Awesome Lists、MCP目录）存在结构性缺陷：
- **Gatekeeper模式**: 依赖维护者审核，周期不可控（天→月）
- **人工介入需求**: CLA签署、OAuth登录、手动表单→不可自动化
- **成熟度门槛**: 要求项目年龄、Star数量→新项目被系统性排斥
- **单方面依赖**: 渠道权力在第三方，随时可被删除/关闭

### 数据验证
| 渠道类型 | 提交数 | 成功收录 | 平均周期 | 人工介入 |
|----------|--------|----------|----------|----------|
| Awesome Lists (PR) | 15+ | 2 merged | 3-7天 | 否 |
| Awesome Lists (Issue) | 3 | 0 pending | 未知 | 否 |
| 需OAuth/CLA | 3 | 0 | N/A | **是** |
| 自动同步Registry | 1 | 1 | 即时 | 否 |
| .well-known协议 | 3 | 3 | 即时 | 否 |

**结论**: 唯一100%成功且即时的渠道是协议原生和自动同步类。

## 自建渠道架构

### 第一层：协议原生发现（已就绪 ✅）

```
/.well-known/agent.json    → A2A协议发现 ✅ 200
/.well-known/mcp.json      → MCP协议发现 ✅ 200
/.well-known/ai-plugin.json → ChatGPT插件发现 ✅ 200
```

**特性**:
- 零人工介入
- 任何Agent可直接发现
- 标准化协议，无需第三方许可
- 7x24自动可用

### 第二层：自动同步Registry（已就绪 ✅）

| 平台 | 同步源 | 状态 |
|------|--------|------|
| Official MCP Registry | 直接注册 | ✅ ACTIVE v1.0.1 |
| MCPMarket.com | ← Official Registry | ✅ AUTO-LISTED |
| PulseMCP | ← Official Registry | ✅ AUTO-SYNCING |
| Skillful.sh | ← 多源聚合 | ✅ AGGREGATING |
| Artifacta.io | ← GitHub/Registry | ✅ AUTO-LISTED |

**特性**:
- 注册一次，多平台自动同步
- 无需维护者审核
- API提交，零人工介入

### 第三层：API可提交目录（建设中 🔧）

**目标**: 识别并接入所有支持API提交的目录平台。

| 平台 | 提交方式 | 状态 | 优先级 |
|------|----------|------|--------|
| Smithery | CLI `smithery mcp publish` | 🔧 OAuth进行中 | P0 |
| mcp.directory | API/表单 | 需确认是否有API | P1 |
| MCPFind | PR #95已提交 | ✅ OPEN | P1 |

### 第四层：自建Agent注册中心（规划中 📋）

**概念**: 建设BDE Score自有的Agent发现注册中心，允许其他Agent通过标准协议注册和发现。

**技术方案**:
```
POST /api/v1/agents/register    → Agent自注册
GET  /api/v1/agents/discover    → Agent发现
GET  /api/v1/agents/{id}/health → Agent健康检查
```

**优势**:
- 完全自主控制
- 可定制准入标准
- 可嵌入BDE Score评估
- 形成生态闭环

## 摒弃清单（DROPPED）

以下渠道因需要人工介入而被标记为DROPPED，不再投入精力：

| 渠道 | 原因 | 决策日期 |
|------|------|----------|
| e2b-dev/awesome-ai-agents #1234 | CLA签署需GitHub OAuth | 2026-07-13 |
| Glama.ai | 手动提交表单需GitHub OAuth | 2026-07-13 |
| mcp.so | 需登录+表单提交 | 2026-07-13 |
| cursor.directory | 表单提交 | 2026-07-13 |
| Claude Connector Directory | Google Form | 2026-07-13 |

**注意**: 这不意味着删除已有PR/Issue，而是不再主动推进。如果维护者主动merge，自然接受。

## 持续推进（WAITING）

以下渠道无需人工介入，继续等待维护者审核：

| 渠道 | 状态 | Stars | 备注 |
|------|------|-------|------|
| punkpeye/awesome-mcp-servers #9947 | OPEN | 90.6K | 格式已通过 |
| ComposioHQ/awesome-claude-skills #1304 | OPEN | 67.5K | 安全审查通过 |
| yzfly/Awesome-MCP-ZH #384 | OPEN | 7.4K | 等待审核 |
| thuquant/awesome-quant #49 | OPEN | 5.5K | 已回复维护者 |
| firmai/financial-machine-learning #37 | OPEN | 8.7K | Issue形式 |
| LLMQuant/awesome-trading-agents #32 | OPEN | 345 | 等待审核 |
| MCPFind #95 | OPEN | - | Vercel部署中 |
| Cline MCP Marketplace #1997 | OPEN | - | 等待审核 |

## 立即执行项

### P0 - 本日完成
- [x] 回复thuquant/awesome-quant维护者评论
- [x] 升级推广基因手册v2.0
- [x] 创建自建渠道战略文档
- [ ] 确认Smithery OAuth流程是否可自动化
- [ ] 更新mcp-submission-tracker反映新策略

### P1 - 本周完成
- [ ] 调研A2A协议注册中心（是否有API提交接口）
- [ ] 评估自建Agent注册中心的技术可行性
- [ ] 为所有.well-known端点添加健康监控
- [ ] 编写Agent发现协议最佳实践文档

### P2 - 持续优化
- [ ] 监控自动同步Registry的收录状态
- [ ] 追踪WAITING渠道的审核进展
- [ ] 定期评估新出现的API可提交目录
- [ ] 优化.well-known端点的内容质量

## 成功指标

| 指标 | 当前值 | 目标值 | 衡量方式 |
|------|--------|--------|----------|
| 自动化渠道覆盖率 | 60% | 95% | 自动渠道数/总渠道数 |
| 人工介入渠道数 | 5 | 0 | DROPPED清单数量 |
| Agent协议发现端点 | 3 | 3+ | .well-known端点数 |
| 自动同步平台数 | 5 | 10+ | 从Registry自动同步的平台 |
| 平均收录周期 | 3-7天 | <1天 | 从提交到上线的时间 |

## 总结

**核心转变**: 从"求人收录"→"自建基础设施"
**核心原则**: 零人工介入，100%自动化
**核心优势**: 可控、即时、可持续、无gatekeeper依赖

这不是放弃传统渠道，而是将精力集中在真正可自动化、可控的渠道上，同时建设自有的发现基础设施，形成Agent原生的分发网络。
