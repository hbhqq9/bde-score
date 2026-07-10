# BDE Score™ Agent团队架构

## 项目定位
BDE Score™ 是面向全球投资者的多市场量化分析SaaS工具，同时承载EU AI Act Art.50合规咨询业务。

## Agent团队编制

### 🎯 主Agent（指挥官）
- **职责**：全局决策、资源调度、用户沟通、战略方向
- **当前状态**：✅ 在线

### 📊 Agent-Alpha（数据分析官）
- **职责**：BDE因子引擎维护、标的池管理、数据质量监控
- **触发方式**：每日08:00定时任务（Calendar UID: 1ef053b4-88c6-413c-b4e0-44b6e4c5f6cf）
- **工作流**：
  1. 检查FutuOpenD/Sina数据源状态
  2. 执行73只标的BDE五因子分析
  3. 存储结果到SQLite
  4. 异常告警（数据源中断/标的异常波动）

### 🔧 Agent-Ops（运维官）
- **职责**：进程保活、隧道维护、部署管理
- **触发方式**：Cron每5分钟keepalive.sh
- **监控项**：
  - FutuOpenD进程 + 端口11111
  - BDE API进程 + 端口8890
  - Bore隧道进程 + 公网连通性

### 📝 Agent-Content（内容官）
- **职责**：LinkedIn内容、白皮书更新、合规材料
- **待执行任务**：
  - [ ] LinkedIn Post 1 (英文) — 待发布
  - [ ] LinkedIn Post 2 (中文) — 待发布
  - [ ] LinkedIn Post 3 (技术) — 2天后发布
  - [ ] 白皮书PDF排版

### 💰 Agent-Finance（财务官）
- **职责**：收款追踪、发票管理、链上账务
- **钱包信息**：
  - 链: Base Mainnet (8453)
  - 地址: 0x87d6C8F71d89d7E1f17EcAB138EDfaAc19d9D2fE
  - 用途: USDC收款（SaaS订阅 + 合规咨询）
  - 独立于NeuroBridge AGL项目

---

## 飞书团队协作
- **群名**: BDE Score™ 专项团队
- **Chat ID**: oc_8c9081046ededba2030a9c65e760c84b
- **加入链接**: https://applink.feishu.cn/client/chat/chatter/add_by_link?link_token=0b7kc10f-ec2f-4a35-8fe6-e6e6941c819e

## 商业模型

### A线：SaaS数据工具
- 目标客户：个人投资者、量化爱好者
- 定价：¥199/月（基础版）/ ¥599/月（专业版）
- 交付：Web Dashboard + API
- 收款：Stripe（国际）/ 微信支付（中国）/ USDC（链上）

### B线：EU AI Act合规服务
- 目标客户：出海AI企业、SaaS平台
- 定价：€10K+/单（评估+实施）
- 交付：合规报告 + 技术实施方案
- 收款：USDC on Base / 银行电汇
- 关键日期：2026-08-02 Art.50强制生效

---

## 技术架构

```
┌─────────────────────────────────────────────┐
│                  用户层                       │
│  Dashboard (bore.pub:18502) + API           │
├─────────────────────────────────────────────┤
│                应用层                         │
│  FastAPI (bde_api.py:8890)                  │
│  ├── /api/analyze   → 运行BDE分析            │
│  ├── /api/snapshot  → 获取缓存结果           │
│  ├── /api/history   → 历史数据               │
│  └── /api/health    → 健康检查               │
├─────────────────────────────────────────────┤
│                分析层                         │
│  FactorEngine (factor_engine.py)            │
│  ├── 动量因子 (Momentum)                     │
│  ├── 均值回归 (Mean Reversion)               │
│  ├── 成交量因子 (Volume)                     │
│  ├── 波动率因子 (Volatility)                 │
│  └── 趋势因子 (Trend)                       │
├─────────────────────────────────────────────┤
│                数据层                         │
│  FutuOpenD (主) ←→ Sina Finance (备)         │
│  SQLite (bde_history.db)                    │
│  15分钟缓存 + Cron保活                       │
└─────────────────────────────────────────────┘
```

## 标的池（73只）
- 🇺🇸 美股 25只：Mega-Cap Tech / AI-Semi / Payments / Healthcare / Consumer / Growth / ETF
- 🇭🇰 港股 26只：互联网 / 新能源车 / 金融 / 能源资源 / 电信 / 医疗
- 🇨🇳 A股 23只：消费 / 金融 / 新能源 / 科技 / 资源 / 制造
