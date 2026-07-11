# 我开源了一个多因子选股评分系统，一行命令分析美股/港股/A股

> 花了几周时间写了一个开源的多因子量化评分工具 **BDE Score™**，覆盖三大市场 73 只股票，免费 API 一键调用。今天跟大家聊聊它的设计思路，以及怎么用。

---

## 0x00 背景：散户为什么需要多因子评分？

不知道你有没有遇到过这种场景——

看到一只股票涨得好，追进去，结果高位站岗。看技术指标都说"强势"，但买入后就回调。单一指标（比如 RSI、MACD）经常给你矛盾信号：动量说你买，波动率说你跑，成交量又说观望。

**问题出在哪？** 出在"只看一个维度"。

华尔街的量化机构早就在用多因子模型了，Fama-French 三因子、Carhart 四因子这些经典模型论文里写得清清楚楚。但这些工具要么贵（Bloomberg Terminal 一年几万美金），要么不透明（给你一个黑盒 AI 预测，不告诉你怎么算的），要么门槛高（你需要会写 Python、懂金融工程）。

对于普通的个人投资者和独立开发者来说，**一个免费、透明、开箱即用的多因子工具，几乎是空白。**

所以我就想：能不能做一个开源的多因子评分系统？每个分数都能拆成你能看懂的子因子，覆盖美股、港股、A 股三大市场，一行 API 就能用。

这就是 **BDE Score™** 的由来。

---

## 0x01 BDE Score 是什么？

BDE Score™ 是一个**透明可解释的多因子量化评分系统**。它不是黑盒 AI，不会给你一个莫名其妙的"预测涨跌概率"。它的核心逻辑很直接：

### 综合评分 = 5 个可解释因子的加权组合

| 因子 | 含义 | 直觉理解 |
|------|------|----------|
| 📈 **Momentum（动量）** | 近期价格趋势强度 | 最近涨得猛不猛 |
| 📉 **Mean Reversion（均值回归）** | 偏离均线的程度 | 是不是涨过头了 |
| 📊 **Volume（成交量）** | 量能变化比率 | 资金进场的力度 |
| 📉 **Volatility（波动率）** | 价格波动剧烈程度 | 稳不稳 |
| 📈 **Trend（趋势）** | 中长期趋势方向 | 大方向对不对 |

**为什么比单一指标靠谱？**

举个例子：一只股票动量得分 90，但均值回归得分只有 20——说明它虽然在涨，但可能已经涨过头了。如果你只看动量就冲进去，大概率吃面。但如果综合评分告诉你"58 分，HOLD"，你就知道：趋势还行，但别急。

这就是多因子的价值——**让你看到全貌，而不是管中窥豹。**

---

## 0x02 覆盖范围

目前覆盖 **3 个市场、73 只股票**：

- 🇺🇸 **美股**：25 只（AAPL、NVDA、TSLA、META、MSFT 等）
- 🇭🇰 **港股**：26 只（腾讯、阿里、美团、小米、京东等）
- 🇨🇳 **A 股**：22 只（茅台、宁德时代、伊利、五粮液、招商银行等）

数据源基于富途 OpenD 双通道实时数据，每日更新。

---

## 0x03 实操：一行 curl 拿到三大市场分析

不废话，直接上手。BDE Score 提供了 REST API，一行命令就能调用。

### 案例一：美股苹果（AAPL）

```bash
curl 'https://atlantic-remains-atomic-floor.trycloudflare.com/api/analyze?symbol=AAPL&market=US'
```

返回结果（已精简）：

```json
{
  "symbol": "AAPL",
  "composite_score": 58.6,
  "signal": "HOLD",
  "scores": {
    "momentum": 84.1,
    "mean_reversion": 26.9,
    "volume": 21.3,
    "volatility": 78.4,
    "trend": 80.0
  },
  "details": {
    "close": 315.32,
    "close_5d_ago": 312.66,
    "close_20d_ago": 295.63,
    "ma20": 298.10
  }
}
```

**解读**：苹果动量得分 84.1（近期涨势不错），但均值回归只有 26.9（已经偏离均线较多），成交量得分 21.3 偏低（量能没跟上）。综合 58.6 分，信号 HOLD——趋势向好，但短期追高风险不低。

### 案例二：港股腾讯（00700）

```bash
curl 'https://atlantic-remains-atomic-floor.trycloudflare.com/api/analyze?symbol=00700&market=HK'
```

返回结果（已精简）：

```json
{
  "symbol": "腾讯",
  "composite_score": 56.9,
  "signal": "HOLD",
  "scores": {
    "momentum": 64.1,
    "mean_reversion": 34.3,
    "volume": 60.6,
    "volatility": 64.3,
    "trend": 60.0
  },
  "details": {
    "close": 460.2,
    "close_5d_ago": 452.0,
    "close_20d_ago": 457.2,
    "ma20": 442.82
  }
}
```

**解读**：腾讯 56.9 分，比较"均衡"。动量 64.1 适中，成交量 60.6 还行（量能配合不错），波动率 64.3 也算稳定。各因子没有明显短板，属于"稳步上行但未突破"的状态。

### 案例三：A 股贵州茅台（SH600519）

```bash
curl 'https://atlantic-remains-atomic-floor.trycloudflare.com/api/analyze?symbol=600519&market=A'
```

返回结果（已精简）：

```json
{
  "symbol": "贵州茅台",
  "composite_score": 51.2,
  "signal": "HOLD",
  "scores": {
    "momentum": 41.8,
    "mean_reversion": 48.8,
    "volume": 61.4,
    "volatility": 75.9,
    "trend": 35.0
  },
  "details": {
    "close": 1204.98,
    "close_5d_ago": 1206.91,
    "close_20d_ago": 1263.89,
    "ma20": 1201.34
  }
}
```

**解读**：茅台 51.2 分，接近中性。动量 41.8 偏弱，趋势 35.0 向下（20 天前还在 1263，现在 1205，明显下行通道）。成交量 61.4 尚可（有人在接盘），波动率 75.9 偏高。整体看，短期偏弱震荡，但波动率大意味着如果方向反转，弹性也不小。

### 三市场横向对比

把三只股票放在一起看，BDE Score 的跨市场比较优势就体现出来了：

| 股票 | 市场 | 综合分 | 动量 | 均值回归 | 成交量 | 波动率 | 趋势 | 信号 |
|------|------|--------|------|----------|--------|--------|------|------|
| AAPL | 美股 | 58.6 | 84.1 | 26.9 | 21.3 | 78.4 | 80.0 | HOLD |
| 腾讯 | 港股 | 56.9 | 64.1 | 34.3 | 60.6 | 64.3 | 60.0 | HOLD |
| 茅台 | A股 | 51.2 | 41.8 | 48.8 | 61.4 | 75.9 | 35.0 | HOLD |

几个有意思的观察：

- **苹果"偏科"明显**：动量 84.1 但成交量只有 21.3，典型的"价涨量缩"，趋势好但缺乏资金共识。
- **腾讯最均衡**：5 个因子都在 34-67 之间，没有明显短板，也没有突出亮点，属于"稳健型"选手。
- **茅台趋势反转中**：趋势 35.0 是三家里最低的，但波动率 75.9 很高——这种组合意味着变盘在即，方向选择的关键时刻。

这种多维度对比，就是多因子评分的价值所在。

---

## 0x04 为什么 BDE Score 值得一试？

### ✅ 完全透明，拒绝黑盒

每个综合分数都能拆成 5 个子因子。你可以清楚看到分数是怎么来的，而不是"AI 说的"。

### ✅ 三市场一套 API

美股、港股、A 股统一接口，切换 `market` 参数就行。对于做跨市场研究的兄弟，这个很方便。

### ✅ 开源 + MIT 协议

代码全开源，MIT 协议，你可以 fork 了改、集成到自己的系统里、或者纯粹学习多因子建模的思路。

```bash
git clone https://github.com/hbhqq9/bde-score.git
cd bde-score
```

### ✅ 社区认可

项目已经被 [awesome-quant](https://github.com/wilsonfreitas/awesome-quant)（15K+ Stars）等 21 个 Awesome List 收录/PR 提交中。

### ✅ 合规设计

符合 EU AI Act Art.50 透明性要求，所有评分带有可审计的方法论文档和机器可读的合规元数据。

---

## 0x05 快速上手

### 方式一：直接调 API（最快）

```bash
# 美股
curl 'https://atlantic-remains-atomic-floor.trycloudflare.com/api/analyze?symbol=AAPL&market=US'

# 港股
curl 'https://atlantic-remains-atomic-floor.trycloudflare.com/api/analyze?symbol=00700&market=HK'

# A 股
curl 'https://atlantic-remains-atomic-floor.trycloudflare.com/api/analyze?symbol=600519&market=A'
```

### 方式二：本地部署

```bash
git clone https://github.com/hbhqq9/bde-score.git
cd bde-score
# 按照 README 配置数据源和环境变量
# 支持 FutuOpenD 数据通道
```

### 方式三：在线 Dashboard

直接访问 [Live Demo](https://hbhqq9.github.io/bde-score/)，浏览器里就能看可视化评分。

---

## 0x06 技术架构简述

给想深入了解的同学简单说下架构：

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  FutuOpenD   │────▶│  Data Engine  │────▶│  Scoring Model   │
│  (数据源)    │     │  (清洗/对齐)  │     │  (5因子加权)     │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                   │
                                          ┌────────▼────────┐
                                          │   REST API      │
                                          │   (Cloudflare)  │
                                          └────────┬────────┘
                                                   │
                              ┌────────────────────┼────────────────────┐
                              ▼                    ▼                    ▼
                        Dashboard            Embeddable           第三方集成
                                               Widget
```

- **数据层**：富途 OpenD 实时行情，双通道冗余
- **计算层**：Python 多因子引擎，每个因子 0-100 标准化
- **服务层**：REST API 部署在 Cloudflare，全球低延迟
- **展示层**：Web Dashboard + 可嵌入式 Widget + 可分享评分卡片

---

## 0x07 未来规划

这个项目还在快速迭代中，接下来计划做的事情：

### 🔮 MCP / AI Agent 集成

计划支持 MCP（Model Context Protocol），让 AI Agent 可以直接调用 BDE Score 进行自动化分析。想象一下：你对 AI 说"帮我分析下腾讯最近怎么样"，Agent 自动调 API、解读分数、生成报告。

### 🔮 合规审计报告

面向机构用户的合规模块，输出符合监管要求的审计轨迹报告。

### 🔮 更多市场 & 因子

计划扩展更多新兴市场，同时加入基本面因子（PE、PB、ROE 等），让评分体系更全面。

### 🔮 社区驱动

如果你对这个项目感兴趣，欢迎：
- ⭐ 在 GitHub 上 star 支持
- 🐛 提 Issue 报 Bug 或建议
- 🔀 Fork 后贡献代码
- 📝 写 PR 提交到 Awesome List

---

## 0x08 最后

做这个项目的初衷很简单——**量化不应该只是机构的特权。**

开源的意义在于让每个人都有机会用透明的工具去理解市场。BDE Score 不是预测涨跌的水晶球，它是一面多棱镜，让你从更多角度去看清一只股票的当前状态。

如果这个项目对你有帮助，去 GitHub 给个 Star 就是最大的支持 👇

**🔗 GitHub: [github.com/hbhqq9/bde-score](https://github.com/hbhqq9/bde-score)**

**🔗 在线 Demo: [hbhqq9.github.io/bde-score](https://hbhqq9.github.io/bde-score/)**

---

> ⚠️ **声明**：BDE Score™ 仅提供技术分析数据，**不构成任何投资建议**。股市有风险，投资需谨慎。过往表现不代表未来收益。
>
> 📌 *技术服务，非金融投资建议。*
