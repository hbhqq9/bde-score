# 📊 BDE Score™

**AI-Powered Multi-Market Stock Analysis — One Score, Every Market**

[![Live](https://img.shields.io/badge/Live-Try%20Now-blue?style=for-the-badge)](https://hbhqq9.github.io/bde-score/)
[![API](https://img.shields.io/badge/API-RESTful-green?style=for-the-badge)](#api)
[![EU AI Act](https://img.shields.io/badge/EU%20AI%20Act-Art.50%20Compliant-orange?style=for-the-badge)](#compliance)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

### 📈 Live BDE Scores (real-time)

[![Market](https://img.shields.io/endpoint?url=https://freight-disabilities-agrees-rebates.trycloudflare.com.trycloudflare.com/api/badge)](https://github.com/hbhqq9/bde-score)
[![AAPL](https://img.shields.io/endpoint?url=https://freight-disabilities-agrees-rebates.trycloudflare.com.trycloudflare.com/api/badge?symbol=AAPL)]()
[![NVDA](https://img.shields.io/endpoint?url=https://freight-disabilities-agrees-rebates.trycloudflare.com.trycloudflare.com/api/badge?symbol=NVDA)]()
[![00700](https://img.shields.io/endpoint?url=https://freight-disabilities-agrees-rebates.trycloudflare.com.trycloudflare.com/api/badge?symbol=00700)]()
[![SH600519](https://img.shields.io/endpoint?url=https://freight-disabilities-agrees-rebates.trycloudflare.com.trycloudflare.com/api/badge?symbol=SH600519)]()

---

## 🎯 What is BDE Score™?

BDE Score™ is a **transparent, multi-factor quantitative scoring system** that analyzes stocks across **US, HK, and A-share markets** using 5 explainable factors:

| Factor | What it Measures |
|--------|-----------------|
| **Momentum** | Trend strength & directional persistence |
| **Mean Reversion** | Oversold/overbought positioning |
| **Volume** | Smart money flow detection |
| **Volatility** | Risk-adjusted return profile |
| **Trend** | Moving average alignment |

**73 stocks. 3 markets. One comparable score.**



---

## 🔍 Agent Compliance Quick Check (NEW!)

**Free tool to assess EU AI Act readiness for your MCP endpoint:**

```bash
# Get compliance score (JSON)
curl "https://freight-disabilities-agrees-rebates.trycloudflare.com.trycloudflare.com/compliance-check?url=https://your-mcp-endpoint.com"

# Get visual report (HTML)
# Open in browser: https://freight-disabilities-agrees-rebates.trycloudflare.com.trycloudflare.com/compliance-check?url=https://your-mcp-endpoint.com
```

**10 automated checks** covering HTTPS, security headers, API documentation, privacy policy, rate limiting, and EU AI Act Art.50 transparency.

**Rate limit**: 3 checks per IP per minute

---

## 🤖 MCP Server Integration

BDE Score is available as an MCP server for AI agent integration:

```json
{
  "mcpServers": {
    "bde-score": {
      "transport": {
        "type": "streamable-http",
        "url": "https://freight-disabilities-agrees-rebates.trycloudflare.com/mcp"
      }
    }
  }
}
```

### Available MCP Tools
- `analyze_stock` - Get BDE Score for any stock (US/HK/A-share)
- `check_compliance` - Run EU AI Act compliance assessment
- `get_trust_score` - Evaluate MCP server reliability


## 🚀 Quick Start

### View Live Dashboard
👉 **[Open Dashboard](https://hbhqq9.github.io/bde-score/)**

### Use as GitHub Action
Add automated stock analysis to your workflow:
```yaml
- uses: hbhqq9/bde-score@main
  with:
    market: ALL
    min_score: '55'
```
Results appear in GitHub Step Summary. [Learn more](#github-action)

### API Usage

```bash
# Get latest scores (US market)
curl https://freight-disabilities-agrees-rebates.trycloudflare.com.trycloudflare.com/api/snapshot?market=US

# Get all markets
curl https://freight-disabilities-agrees-rebates.trycloudflare.com.trycloudflare.com/api/snapshot?market=ALL

# With Premium API Key (unlimited access)
curl -H "X-API-Key: bde_your_key_here" \
  https://freight-disabilities-agrees-rebates.trycloudflare.com.trycloudflare.com/api/snapshot?market=ALL

# Historical data
curl https://freight-disabilities-agrees-rebates.trycloudflare.com.trycloudflare.com/api/history?symbol=AAPL&days=30
```

### Pricing

| Tier | Price | Access |
|------|-------|--------|
| **Free** | $0 | Dashboard + 3 API queries/day |
| **Premium** | $29/mo | Unlimited API + 365-day history |
| **Institutional** | $199/mo | Custom universe + compliance reports + SLA |

**Payment:** USDC on Base chain (Base) → `0x349Eea0E2f4d3594797851758325Da3eb49D4343`

### 💸 x402 Micro-Payments (Agent-Native, Zero Registration)

BDE Score™ supports the [x402 protocol](https://x402.org) — HTTP 402 Payment Required as an open standard. AI Agents can pay per query in USDC with **no registration, no API keys, no subscriptions**.

| Method | Price | How |
|--------|-------|-----|
| **Free** | $0 | 3 queries/day per IP (auto) |
| **x402 Pay-per-query** | $0.01/query | `X-Payment` header with USDC on Base |
| **API Key (Premium)** | $29/mo | `X-API-Key` header, unlimited |

#### Quick Start (x402)

```bash
# 1. Discover pricing & config
curl https://freight-disabilities-agrees-rebates.trycloudflare.com.trycloudflare.com/pay/info

# 2. Check your free quota
curl https://freight-disabilities-agrees-rebates.trycloudflare.com.trycloudflare.com/pay/free

# 3. First 3 queries are FREE! No payment needed.
curl https://freight-disabilities-agrees-rebates.trycloudflare.com.trycloudflare.com/pay/query?symbol=AAPL

# 4. After free quota, pay $0.01 with x402 (USDC on Base)
# The server returns HTTP 402 with payment requirements:
curl -i https://freight-disabilities-agrees-rebates.trycloudflare.com.trycloudflare.com/pay/query?symbol=NVDA

# Response: 402 Payment Required
# {
#   "accepts": [{
#     "scheme": "exact",
#     "network": "eip155:8453",
#     "maxAmountRequired": "10000",  // 10000 = $0.01 USDC (6 decimals)
#     "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
#     "payTo": "0x349Eea0E2f4d3594797851758325Da3eb49D4343"
#   }]
# }

# 5. Sign payment & retry with X-Payment header
# (use x402 SDK: pip install x402[fastapi,httpx,evm])
```

#### x402 Python Client Example

```python
from x402 import x402Client
from x402.mechanisms.evm.exact import ExactEvmScheme

client = x402Client()
client.register("eip155:*", ExactEvmScheme(signer=your_signer))

# Auto-pays $0.01 USDC on Base, returns BDE Score
response = await client.get(
    "https://freight-disabilities-agrees-rebates.trycloudflare.com.trycloudflare.com/pay/query?symbol=AAPL"
)
```

**Economics:** $0.01/query revenue, $0.000752/event cost → **>92% profit margin**

## 🌏 Coverage

### US Market (25 stocks)
AAPL, MSFT, GOOG, AMZN, META, NVDA, AMD, AVGO, ARM, INTC, V, MA, JNJ, UNH, LLY, PFE, PG, KO, WMT, MCD, TSLA, NFLX, BABA, SPY, QQQ

### HK Market (26 stocks)
00700 (Tencent), 09988 (Alibaba), 09888 (Baidu), 03690 (Meituan), 01024 (Kuaishou), 01810 (Xiaomi), 09618 (JD), 09999 (NetEase), 02015 (Li Auto), 09868 (XPeng), 01211 (BYD), 09863 (Leapmotor), 02318 (Ping An), 01398 (ICBC), 00939 (CCB), 03988 (BOC), 02628 (China Life), 02899 (Zijin Mining), 00883 (CNOOC), 00857 (PetroChina), 01088 (China Shenhua), 00941 (China Mobile), 00728 (China Telecom), 00762 (China Unicom), 01833 (Ping An Good Doctor), 02269 (WuXi Biologics)

### A-Share Market (23 stocks)
600519 (Moutai), 000858 (Wuliangye), 000568 (Luzhou Laojiao), 600887 (Yili), 002714 (Muyuan), 601318 (Ping An), 600036 (CMB), 601398 (ICBC), 601288 (ABC), 300750 (CATL), 601012 (LONGi), 002594 (BYD-A), 600900 (Yangtze Power), 688981 (SMIC), 002475 (Luxshare), 002230 (iFlytek), 603501 (Will Semi), 601899 (Zijin-A), 601088 (China Shenhua), 600585 (Conch Cement), 000333 (Midea), 600690 (Haier), 000651 (Gree)

## 🔒 EU AI Act Art.50 Compliance

BDE Score™ is **compliance-first by design**. When Art.50 takes effect on **August 2, 2026**, our system is already ready:

- ✅ **Full audit trails** — every score decision logged with factor weights
- ✅ **Explainable methodology** — transparent 5-factor breakdown per stock
- ✅ **Machine-readable metadata** — JSON compliance data for regulatory reporting

> 78% of AI system operators have NOT taken Art.50 compliance measures yet (April 2026 data). BDE Score™ closes this gap.

## 🔌 AI Agent Integration (MCP + LangChain)

BDE Score is directly callable by AI agents — no registration, no API keys.

| Protocol | Platform | Status |
|----------|----------|--------|
| **MCP** | Claude Desktop, Cursor, Windsurf, Cline | ✅ Ready |
| **MCP Registry** | [Official MCP Registry](https://registry.modelcontextprotocol.io) | ✅ `io.github.hbhqq9/bde-score` |
| **LangChain** | Any LangChain agent | ✅ Ready |
| **OpenAI Functions** | ChatGPT plugins, GPTs | ✅ Schema ready |

### MCP Quick Install

**Remote Server (zero-setup):**
```bash
# Claude Code — one command
claude mcp add bde-score --transport http --url https://freight-disabilities-agrees-rebates.trycloudflare.com.trycloudflare.com/mcp
```

**Local Server:**
```bash
# Or add to claude_desktop_config.json
{
  "mcpServers": {
    "bde-score": {
      "command": "python",
      "args": ["/path/to/bde-score/mcp/bde_score_mcp.py"]
    }
  }
}
```

**Find BDE Score on:** [Glama](https://glama.ai/mcp/servers) · [Smithery](https://smithery.ai/server/bde-score) · [Cline Marketplace](https://github.com/cline/mcp-marketplace/issues/1997)

### Tools

| Tool | Description |
|------|-------------|
| `get_bde_score` | Comprehensive BDE scoring (fundamental + technical + ESG) |
| `get_multi_market_comparison` | Cross-market comparison (US/HK/CN) |
| `get_stock_screener` | Screen stocks by BDE criteria |
| `get_esg_analysis` | ESG analysis for a stock |
| `get_sector_analysis` | Sector-level analysis |

### LangChain

```python
from bde_score_langchain import get_bde_tools
tools = get_bde_tools()
```

Full guide: [mcp/README.md](mcp/README.md) · AI Agent install: [llms-install.md](llms-install.md)

## 🛠 Tech Stack

- **Data:** FutuOpenD (primary) + Sina Finance (fallback) — dual-channel auto-failover
- **API:** FastAPI + Uvicorn
- **Security:** Rate limiting, concurrent locks, input validation, security headers
- **Infrastructure:** Cloudflare Tunnel (HTTPS + DDoS protection)
- **Payments:** USDC on Base chain (ERC-20)

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Landing page |
| `/dashboard` | GET | Interactive dashboard |
| `/api/snapshot` | GET | Latest scores (free: 3/day) |
| `/api/analyze` | GET | Run fresh analysis |
| `/api/history` | GET | Historical scores |
| `/api/health` | GET | System status |
| `/api/market-status` | GET | Market hours |

## 💬 Community

- **Discussions**: [Join the conversation](https://github.com/hbhqq9/bde-score/discussions)
- **Roadmap**: [v1.1 plans](https://github.com/hbhqq9/bde-score/issues/2)
- **Related Projects**: [NeuroBridge](https://github.com/hbhqq9/neurobridge) · [IPO Compliance](https://github.com/hbhqq9/ipo-compliance)

## ⚠️ Disclaimer

**BDE Score™ is a technical analysis tool, NOT financial advice.** All investment decisions should be made independently. Past performance does not guarantee future results. This service does not provide investment suitability assessments.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>BDE Score™</strong> — Transparent. Multi-Market. Compliance-Ready.<br>
  <a href="https://hbhqq9.github.io/bde-score/">Try Live →</a> · 
  <a href="https://github.com/hbhqq9/bde-score">GitHub</a>
</p>
