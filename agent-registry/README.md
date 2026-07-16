# BDE Score™ Agent Registry

**版本**: v0.1.0 (MVP)
**状态**: 建设中
**创建日期**: 2026-07-13

## 愿景

从"被收录"到"建设网络"——BDE Score Agent Registry是一个**Agent原生的、去中心化的发现与注册服务**。

## 核心设计原则

1. **Agent-Native**: API-first，所有操作通过标准HTTP接口完成
2. **零Gatekeeper**: 无需人工审核，Agent自注册自管理
3. **协议兼容**: 支持A2A、MCP、OpenAI Plugin三大发现协议
4. **去中心化**: 每个注册的Agent是网络节点，不是从属
5. **安全内建**: 注册需验证端点可达性，防滥用

## 架构

```
┌─────────────────────────────────────────┐
│         BDE Score Agent Registry        │
├─────────────────────────────────────────┤
│  POST /api/v1/agents/register           │  ← Agent自注册
│  GET  /api/v1/agents                    │  ← 发现所有Agent
│  GET  /api/v1/agents/{id}               │  ← 查询单个Agent
│  GET  /api/v1/agents/{id}/health        │  ← 健康检查
│  DELETE /api/v1/agents/{id}             │  ← 注销
│  GET  /api/v1/search?q=finance          │  ← 语义搜索
└─────────────────────────────────────────┘
         │
         ▼ 自动发现
┌─────────────────────────────────────────┐
│  .well-known/agent.json  (A2A)          │
│  .well-known/mcp.json    (MCP)          │
│  .well-known/ai-plugin.json (OpenAI)    │
└─────────────────────────────────────────┘
```

## 数据模型

```json
{
  "id": "bde-score-primary",
  "name": "BDE Score™ Financial Analysis Engine",
  "description": "Comprehensive stock analysis with EU AI Act Art.50 compliance",
  "category": ["finance", "stock-analysis", "compliance"],
  "protocols": {
    "a2a": "https://italic-telecharger-degrees-appendix.trycloudflare.com/.well-known/agent.json",
    "mcp": "https://freight-disabilities-agrees-rebates.trycloudflare.com/.well-known/mcp.json",
    "openai_plugin": "https://italic-telecharger-degrees-appendix.trycloudflare.com/.well-known/ai-plugin.json"
  },
  "capabilities": ["stock-analysis", "compliance-check", "risk-assessment"],
  "registration_time": "2026-07-13T21:00:00Z",
  "health_status": "healthy",
  "last_seen": "2026-07-13T21:00:00Z"
}
```

## 颠覆性创新点

| 传统Gatekeeper模式 | BDE Agent Registry模式 |
|-------------------|------------------------|
| 人工审核，天→月周期 | 自动验证，秒级注册 |
| 单一入口，中心化 | 去中心化，多协议 |
| 平台控制准入 | Agent自主管理 |
| 依赖平台流量 | 自建发现网络 |
| 被收录=被动 | 建网络=主动 |

## 下一步

- [ ] 实现registry API端点
- [ ] 自注册BDE Score为首个节点
- [ ] 添加自动健康检查（定时验证端点可达性）
- [ ] 发布Agent Discovery文档，引导其他Agent注册
