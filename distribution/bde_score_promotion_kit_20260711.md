# BDE Score™ — 产品推广素材包

**生成时间**: 2026-07-11 22:14 CST  
**API状态**: ✅ LIVE  
**数据更新**: 实时（FutuOpenD）

---

## 📊 实时数据快照 (2026-07-11 22:13 UTC+8)

### 美股 Top 10 (BDE Score排名)
| 排名 | 股票 | BDE Score | 动量 | 波动率 | 均值回归 | 成交量 | 趋势 | 信号 | 现价 |
|:---:|------|:---------:|:----:|:------:|:--------:|:------:|:----:|:----:|-----:|
| 1 | META | **68.5** | 90.9 | 64.8 | 0.0 | 86.2 | 95.0 | HOLD | $669.21 |
| 2 | V | **61.1** | 68.6 | 74.5 | 37.1 | 49.5 | 80.0 | HOLD | $348.97 |
| 3 | TSLA | **60.9** | 79.9 | 50.8 | 43.1 | 32.4 | 95.0 | HOLD | $407.76 |
| 4 | NVDA | **60.8** | 79.5 | 76.6 | 32.2 | 50.3 | 60.0 | HOLD | $210.96 |
| 5 | AVGO | **59.1** | 80.1 | 66.5 | 31.8 | 48.7 | 60.0 | HOLD | $399.97 |
| 6 | AAPL | **58.6** | 84.1 | 78.4 | 26.9 | 21.3 | 80.0 | HOLD | $315.32 |
| 7 | MA | **58.2** | 65.4 | 75.2 | 33.2 | 43.3 | 80.0 | HOLD | $526.74 |
| 8 | JNJ | **57.6** | 65.5 | 76.0 | 35.4 | 33.4 | 85.0 | HOLD | $256.98 |
| 9 | AMD | **57.0** | 85.0 | 44.5 | 29.7 | 30.5 | 85.0 | HOLD | $557.89 |
| 10 | SPY | **56.3** | 65.7 | 62.5 | 43.7 | 32.5 | 80.0 | HOLD | $754.95 |

**市场总评**: 中性偏多，平均BDE 53.9，23个HOLD/2个SELL/0个BUY

### 关键洞察
- **META领涨** (68.5): 动量90.9+趋势95.0 = 强劲上升趋势
- **GOOG唯一SELL** (51.3): 趋势分仅10.0，下降动能明显
- **NFLX预警** (43.1): 动量29.1+趋势15.0 = 双重下行信号
- **AMD暗马** (57.0): 动量85.0+波动率44.5 = 高动量低波动，稳健上行

---

## 🎯 Product Hunt 发布文案

### Tagline (60 chars)
```
AI-Powered Multi-Market Stock Scoring — US, HK & A-Shares
```

### Description (500 words)
```
## Stop juggling 10 different indicators. Get one transparent score.

BDE Score™ combines momentum, volatility, mean-reversion, volume, and trend analysis into a single 0-100 composite score for 73 stocks across US, HK, and China A-share markets.

**Why BDE Score?**
- **Transparent**: Every factor is visible. No black box ML. You see exactly WHY a stock scores 68.5 vs 52.3
- **Multi-market**: One API call covers NYSE, HKEX, and Shanghai/Shenzhen
- **Real-time**: Live data from institutional-grade sources (FutuOpenD)
- **Open source**: MIT license, self-hostable, auditable
- **EU AI Act compliant**: Art.50 transparency documentation built-in

**How it works:**
```
curl https://bde-score.com/api/analyze?symbol=AAPL&market=US
```
Returns:
- Composite BDE Score (0-100)
- Factor breakdown: Momentum / Volatility / Value / Quality
- Trading signal: BUY / HOLD / SELL
- Price context: Current, 5d ago, 20d ago, MA20

**For AI Agents:**
BDE Score ships with MCP (Model Context Protocol) support. Connect directly from Claude, Cursor, or any MCP-compatible agent:
```
Remote: https://bde-score.com/mcp
Auth: X-API-Key header
Tools: get_bde_score, analyze_stock, compare_markets, screen_stocks
```

**Pricing:**
- Free: 10 requests/min, all markets
- Premium $29/mo: Unlimited + priority + custom screening
- Institutional $199/mo: Dedicated + SLA + custom factors

**Tech stack:** Python/FastAPI + Cloudflare Tunnel + Base chain (USDC payments)

🔗 GitHub: https://github.com/hbhqq9/bde-score
🔗 Try: `curl https://atlantic-remains-atomic-floor.trycloudflare.com/api/analyze?symbol=META&market=US`
```

---

## 🐦 Twitter/X Thread (5 tweets)

### Tweet 1 (Hook)
```
I built a free stock scoring tool that covers US, HK, and A-shares.

One API call → 0-100 score with transparent factor breakdown.

No black box. No paid wall for basics. Open source.

Thread 🧵
```

### Tweet 2 (Demo)
```
Live data right now:

🥇 META: 68.5 (Momentum 90.9 🔥)
🥈 TSLA: 60.9 (Trend 95.0)
🥉 NVDA: 60.8
⚠️ GOOG: 51.3 SELL (Trend only 10.0)
⚠️ NFLX: 43.1 (Momentum 29.1)

Same API covers 港股 + A股. One endpoint, three markets.
```

### Tweet 3 (Technical)
```
5 factors, fully transparent:

• Momentum (5d/20d price change)
• Volatility (ATR-based risk)
• Mean Reversion (RSI z-score)
• Volume (relative volume ratio)
• Trend (MA alignment)

Each factor scored 0-100. You see exactly why a stock gets its score.
```

### Tweet 4 (AI Agent)
```
For the AI agents crowd: BDE Score speaks MCP.

Connect from Claude/Cursor/any MCP client:

curl -H "X-API-Key: YOUR_KEY" \
  https://bde-score.com/mcp

6 tools: score, analyze, compare, screen, sector, ESG.

Your AI agent can now do multi-market quant analysis.
```

### Tweet 5 (CTA)
```
⭐ GitHub: https://github.com/hbhqq9/bde-score

🔌 Try it:
curl https://atlantic-remains-atomic-floor.trycloudflare.com/api/analyze?symbol=AAPL&market=US

MIT licensed. Self-hostable. EU AI Act compliant.

Built for quant-minded investors who want transparency over hype.
```

---

## 📧 Newsletter/Email 推送文案 (中文)

**标题**: 免费开源多因子选股工具BDE Score，覆盖美股港股A股

```
Hi，

推荐一个刚上线的开源项目 —— BDE Score™

它解决一个问题：散户缺乏免费的、透明的多因子量化工具。

市面上的量化平台要么收费（QuantConnect $30/月起），要么是黑箱（不告诉你怎么算的）。

BDE Score 的做法：
✅ 5个因子（动量/波动率/均值回归/成交量/趋势）全部透明
✅ 覆盖美股+港股+A股 73只核心股票
✅ 一个API调用，返回0-100评分+买卖信号
✅ 开源MIT协议，可以自己部署
✅ 支持MCP协议，AI Agent直接调用

实时数据演示：
- META 68.5分（动量90.9，趋势95.0）→ 强势
- GOOG 51.3分 SELL信号（趋势仅10.0）→ 预警
- NFLX 43.1分（动量29.1）→ 双下行

API调用示例：
curl https://atlantic-remains-atomic-floor.trycloudflare.com/api/analyze?symbol=AAPL&market=US

GitHub: https://github.com/hbhqq9/bde-score

⚠️ 技术分析工具，非投资建议。
```

---

## 🔗 快速链接

| 资源 | URL |
|------|-----|
| GitHub | https://github.com/hbhqq9/bde-score |
| Live API | https://atlantic-remains-atomic-floor.trycloudflare.com/api/health |
| Landing Page | https://hbhqq9.github.io/bde-score/ |
| Widget Embed | `https://atlantic-remains-atomic-floor.trycloudflare.com/widget` |
| MCP Server | streamable-http (auth required) |
| PyPI | `pip install agent-passport-agl` (SDK) |
