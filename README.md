# 📊 BDE Score™ — MCP Server

**AI-Powered Multi-Market Stock Analysis via Model Context Protocol**

[![MCP Server](https://img.shields.io/badge/MCP-Server-blue?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNiIgaGlnaHQ9IjE2IiB2aWV3Qm94PSIwIDAgMTYgMTYiPjxwYXRoIGZpbGw9IiNmZmYiIGQ9Ik04IDBMNCBoOEwxMiAwSDR6TTQgNnY0aDhWNkw0IDZ6TTQgMTJ2NGg4di00SDR6Ii8+PC9zdmc+)](https://modelcontextprotocol.io)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-io.github.hbhqq9%2Fbde--score-blue?style=for-the-badge)](https://registry.modelcontextprotocol.io)
[![EU AI Act](https://img.shields.io/badge/EU%20AI%20Act-Art.50%20Compliant-orange?style=for-the-badge)](#compliance)
[![License](https://img.shields.io/badge/License-AGPL--3.0-blue?style=for-the-badge)](LICENSE)

---

## 🤖 What is BDE Score™?

BDE Score™ is an **MCP (Model Context Protocol) Server** that gives AI agents direct access to transparent, multi-factor quantitative stock scoring across **US, HK, and A-share markets**.

It is **not** a REST API wrapper — it is a **native MCP server** built with the [MCP SDK](https://github.com/modelcontextprotocol/typescript-sdk) that exposes structured tools, each returning explainable 7-factor scores.

**73 stocks · 3 markets · 6 MCP tools · One comparable score per stock.**

---

## 🔧 MCP Tools

BDE Score exposes **6 MCP tools** that AI agents can call directly:

| Tool | Description |
|------|-------------|
| `get_bde_score` | Get BDE composite scores (0-100) for all stocks in a market (US/HK/CN/ALL). Returns 7-factor breakdown: VIX, Volume Profile, Momentum, Mean Reversion, Volume, Volatility, Trend. |
| `get_stock_analysis` | Detailed single-stock analysis with factor-by-factor breakdown, signal classification (Bullish/Neutral/Bearish), and price context. |
| `get_multi_market_comparison` | Compare the same company's scores across US, HK, and CN markets (e.g., compare BYD on NASDAQ vs HK vs Shenzhen). |
| `get_stock_screener` | Screen stocks by minimum BDE score threshold. Returns ranked list of stocks meeting criteria. |
| `get_sector_analysis` | Sector-level aggregation: average scores per sector, sector rankings, and relative strength. |
| `get_esg_analysis` | ESG (Environmental, Social, Governance) analysis per stock with compliance metadata. |

### Tool Input/Output Example

**Tool:** `get_bde_score`
**Input:** `{ "market": "US" }`
**Output:**
```json
{
  "AAPL": { "bde_score": 72, "signal": "BULLISH", "factors": { "momentum": 85, "volatility": 68, ... } },
  "NVDA": { "bde_score": 81, "signal": "BULLISH", "factors": { ... } }
}
```

---

## 🚀 Quick Setup

### Claude Desktop

Add to `claude_desktop_config.json`:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "bde-score": {
      "url": "https://consolidated-survey-gamma-arrival.trycloudflare.com/mcp",
      "headers": {
        "X-API-Key": "your-api-key-here"
      }
    }
  }
}
```

Restart Claude Desktop. BDE Score tools will appear in the tool list.

### Cursor IDE

Add to `.cursor/mcp.json` in your project:

```json
{
  "mcpServers": {
    "bde-score": {
      "url": "https://consolidated-survey-gamma-arrival.trycloudflare.com/mcp",
      "headers": {
        "X-API-Key": "your-api-key-here"
      }
    }
  }
}
```

### Any MCP Client (Streamable HTTP)

BDE Score uses the **Streamable HTTP** transport (MCP protocol). Connect from any MCP-compatible client:

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async with streamablehttp_client("https://consolidated-survey-gamma-arrival.trycloudflare.com/mcp") as (read, write, _):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        result = await session.call_tool("get_bde_score", {"market": "US"})
        print(result)
```

### Local (stdio transport)

For local development without network:

```bash
pip install mcp httpx
cd mcp/
python mcp_http_server.py
```

Then configure your MCP client to use stdio:
```json
{
  "mcpServers": {
    "bde-score": {
      "command": "python",
      "args": ["mcp/mcp_http_server.py"]
    }
  }
}
```

---

## 💰 Pricing

| Tier | Price | Access |
|------|-------|--------|
| **Free** | $0 | 3 MCP tool calls/day |
| **Premium** | $29/mo | Unlimited MCP calls + 365-day history |
| **Institutional** | $199/mo | Custom universe + compliance reports + SLA |

**Payment:** USDC on Base chain (x402 payment protocol supported)

---

## 🌏 Coverage

### US Market (25 stocks)
AAPL, MSFT, GOOG, AMZN, META, NVDA, AMD, AVGO, ARM, INTC, V, MA, JNJ, UNH, LLY, PFE, PG, KO, WMT, MCD, TSLA, NFLX, BABA, SPY, QQQ

### HK Market (26 stocks)
00700 (Tencent), 09988 (Alibaba), 09888 (Baidu), 03690 (Meituan), 01024 (Kuaishou), 01810 (Xiaomi), 09618 (JD), 09999 (NetEase), 02015 (Li Auto), 09868 (XPeng), 01211 (BYD), 09863 (Leapmotor), 02318 (Ping An), 01398 (ICBC), 00939 (CCB), 03988 (BOC), 02628 (China Life), 02899 (Zijin Mining), 00883 (CNOOC), 00857 (PetroChina), 01088 (China Shenhua), 00941 (China Mobile), 00728 (China Telecom), 00762 (China Unicom), 01833 (Ping An Good Doctor), 02269 (WuXi Biologics)

### A-Share Market (23 stocks, CN prefix)
SH600519 (Moutai), SZ000858 (Wuliangye), SZ000568 (Luzhou Laojiao), SH600887 (Yili), SZ002714 (Muyuan), SH601318 (Ping An), SH600036 (CMB), SH601398 (ICBC), SH601288 (ABC), SZ300750 (CATL), SH601012 (LONGi), SZ002594 (BYD-A), SH600900 (Yangtze Power), SH688981 (SMIC), SZ002475 (Luxshare), SZ002230 (iFlytek), SH603501 (Will Semi), SH601899 (Zijin-A), SH601088 (China Shenhua), SH600585 (Conch Cement), SZ000333 (Midea), SH600690 (Haier), SZ000651 (Gree)

---

## 🔒 EU AI Act Art.50 Compliance

BDE Score™ is **compliance-first by design**. When Art.50 takes effect on **August 2, 2026**, our MCP server is already ready:

- ✅ **AGL Receipt Schema v2.0** — every MCP tool call generates an immutable, drift-aware receipt
- ✅ **Full audit trails** — every score decision logged with factor weights and timestamps
- ✅ **Explainable methodology** — transparent 7-factor breakdown per stock, embedded in every tool response
- ✅ **Machine-readable metadata** — JSON compliance data in `.well-known/ai-trust.txt` and receipt responses
- ✅ **Identity disclosure** — AGL identity markers in all MCP response headers

> 78% of AI system operators have NOT taken Art.50 compliance measures yet (April 2026 data). BDE Score™ closes this gap — the only open-source MCP server with built-in regulatory compliance.

---

## 📡 Discovery Endpoints

BDE Score implements standard agent discovery protocols:

| Endpoint | URL |
|----------|-----|
| MCP Server | `https://consolidated-survey-gamma-arrival.trycloudflare.com/mcp` |
| `.well-known/mcp.json` | `https://hbhqq9.github.io/bde-score/.well-known/mcp.json` |
| `.well-known/agent.json` | `https://hbhqq9.github.io/bde-score/.well-known/agent.json` |
| `.well-known/agent-card.json` | `https://hbhqq9.github.io/bde-score/.well-known/agent-card.json` |
| `.well-known/security.txt` | `https://hbhqq9.github.io/bde-score/.well-known/security.txt` |
| `.well-known/ai-trust.txt` | `https://hbhqq9.github.io/bde-score/.well-known/ai-trust.txt` |
| Dashboard | `https://hbhqq9.github.io/bde-score/` |

---

## 🛠 Tech Stack

- **MCP Protocol:** Streamable HTTP transport via Cloudflare Tunnel
- **MCP SDK:** Python `mcp` package (FastMCP) + `@modelcontextprotocol/sdk` (TypeScript)
- **Scoring Engine:** 7-factor model (VIX, Volume Profile, RSI, MACD, Bollinger, OBV, ATR)
- **Data:** FutuOpenD (primary) + Sina Finance (fallback) + Yahoo Finance (JS plugin)
- **Security:** API Key auth, rate limiting, x402 payment protocol, AGL Receipt Schema v2.0
- **Governance:** EU AI Act Art.50 compliant, AGL identity markers

---

## 📦 Claude Code Plugin (Local)

For Claude Code users who prefer a local, self-contained MCP plugin:

```bash
cd claude-code-plugin/plugins/mcp/bde-score
npm install
npm start
```

This runs the BDE scoring engine locally via stdio transport — no network required, no API keys needed for the local plugin.

**Local tools:**
| Tool | Description |
|------|-------------|
| `score_stock` | Score a single stock using 7-factor composite model |
| `batch_score` | Score multiple stocks in one call with ranked results |
| `top_performers` | Get top N performing stocks from a watchlist |
| `worst_performers` | Get worst N performing stocks from a watchlist |
| `market_overview` | Get overall market sentiment including VIX level |

---

## ⚠️ Disclaimer

**BDE Score™ is a technical analysis tool, NOT financial advice.** All investment decisions should be made independently. Past performance does not guarantee future results. This service does not provide investment suitability assessments.

---

## 📄 License

**Dual License — AGPL-3.0 / Commercial**

- **Open Source**: Licensed under [AGPL-3.0](LICENSE). Network use requires source disclosure.
- **Commercial License**: For proprietary deployment (SaaS, enterprise, embedded), contact **nnhbh@foxmail.com**.
- **EU AI Act Compliance**: BDE Score™ includes native Article 50 transparency markers — the only open-source MCP server with built-in regulatory compliance.

---

<p align="center">
  <strong>BDE Score™</strong> — MCP-Native. Multi-Market. Compliance-Ready.<br>
  <a href="https://hbhqq9.github.io/bde-score/">Dashboard</a> · 
  <a href="https://github.com/hbhqq9/bde-score">GitHub</a> ·
  <a href="https://registry.modelcontextprotocol.io">MCP Registry</a>
</p>
