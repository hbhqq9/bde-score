---
title: "How to Discover and Use Financial MCP Servers: A Developer's Guide to AI-Powered Stock Analysis"
published: false
tags: mcp, ai, finance, stock-analysis, python, langchain, claude, cursor
series: "BDE Score™ AI Integration"
cover_image: https://hbhqq9.github.io/bde-score/assets/og-image.png
---

The Model Context Protocol (MCP) ecosystem is exploding — [punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) now lists over **90,000 stars** with thousands of servers across every category. For developers building in the finance and quantitative analysis space, this means you can now connect AI agents directly to market data, scoring systems, and analysis tools through standardized interfaces.

In this guide, I'll show you how to discover financial MCP servers, with BDE Score™ as a concrete example of a multi-market stock analysis server that works with Claude Desktop, Cursor, LangChain, and any MCP-compatible client.

## Why MCP Changes Everything for Financial Analysis

Traditional financial APIs require you to:
1. Read documentation
2. Install SDKs
3. Handle authentication
4. Parse response formats
5. Write integration code

With MCP, the flow is:
1. Add the server to your MCP client config
2. Ask your AI assistant to analyze stocks

That's it. The AI agent handles the rest.

## Discovering Financial MCP Servers

### 1. Official MCP Registry
The [official registry](https://registry.modelcontextprotocol.io) is the canonical source. Search for finance, stock, trading, or market data to find servers.

### 2. Curated Awesome Lists
- [awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) — The largest directory (90K+ ★)
- Finance & Fintech section has stock analysis, crypto, payment, and trading servers

### 3. MCP.so and Smithery
- [mcp.so](https://mcp.so) — Community-driven discovery platform
- [Smithery](https://smithery.ai) — Marketplace with one-click install

## BDE Score™: Multi-Market Stock Analysis via MCP

[BDE Score](https://github.com/hbhqq9/bde-score) is an open-source MCP server that provides composite stock scoring across US, Hong Kong, and China A-share markets.

### What It Does

The BDE Score™ is a 0-100 composite metric that synthesizes:
- **Fundamental Analysis**: P/E ratio, P/B ratio, ROE, revenue growth, profit margins, dividend yield
- **Technical Indicators**: RSI, MACD, Bollinger Bands, moving averages, volume analysis
- **Risk Assessment**: Volatility, beta, drawdown, VaR, risk-adjusted returns

### MCP Tools Available

| Tool | Description |
|------|-------------|
| `get_bde_score` | Composite 0-100 score with dimension breakdown |
| `get_stock_fundamentals` | Fundamental metrics (P/E, ROE, margins, etc.) |
| `get_technical_indicators` | RSI, MACD, Bollinger Bands, MAs |
| `get_risk_assessment` | Volatility, beta, VaR, drawdown analysis |
| `compare_stocks` | Side-by-side comparison across markets |

### Setup in 2 Minutes

**Claude Desktop:**

```json
{
  "mcpServers": {
    "bde-score": {
      "command": "python",
      "args": ["-c", "from bde_score_mcp import main; import asyncio; asyncio.run(main())"],
      "env": {
        "BDE_API_URL": "https://your-tunnel.trycloudflare.com"
      }
    }
  }
}
```

**Cursor / VS Code:**

Add to `.cursor/mcp.json` or `.vscode/mcp.json`:
```json
{
  "servers": {
    "bde-score": {
      "url": "https://your-tunnel.trycloudflare.com/mcp"
    }
  }
}
```

### LangChain Integration

```python
from bde_score_langchain import BDEScoreTool, CompareStocksTool

# Single stock analysis
scorer = BDEScoreTool()
result = scorer.invoke({"symbol": "AAPL", "market": "US"})
print(f"BDE Score: {result['composite_score']}/100")

# Compare across markets
comparator = CompareStocksTool()
comparison = comparator.invoke({
    "symbols": ["AAPL", "00700.HK", "600519.SH"]
})
```

## Real-World Use Cases

### 1. AI-Powered Stock Screener
Ask Claude: "Find stocks with BDE Score above 80 in the tech sector across US and HK markets"

### 2. Risk-Adjusted Portfolio Review
Ask Claude: "Analyze my portfolio's risk profile using BDE Score risk assessments"

### 3. Cross-Market Arbitrage Discovery
Ask Claude: "Compare similar companies across US, HK, and A-share markets"

### 4. EU AI Act Compliance
BDE Score includes built-in compliance metadata, making it suitable for European financial applications that must meet AI Act requirements.

## The Architecture

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│ Claude/     │────>│ MCP Protocol │────>│ BDE Score     │
│ Cursor/     │<────│ JSON-RPC 2.0 │<────│ MCP Server    │
│ LangChain   │     └──────────────┘     └───────┬───────┘
└─────────────┘                                   │
                                                   │ REST API
                                           ┌───────▼───────┐
                                           │ BDE Score     │
                                           │ FastAPI       │
                                           │ (US/HK/CN)    │
                                           └───────────────┘
```

## What Makes This Different from Traditional APIs

| Feature | Traditional API | BDE Score MCP |
|---------|----------------|---------------|
| Discovery | Read docs, find endpoints | AI agent auto-discovers tools |
| Integration | Install SDK, write code | Add config, done |
| Multi-market | Separate APIs per market | Unified interface |
| Scoring | Calculate yourself | Built-in composite scores |
| Compliance | Your responsibility | EU AI Act metadata included |

## Getting Started

1. **Try the API**: Visit [hbhqq9.github.io/bde-score](https://hbhqq9.github.io/bde-score)
2. **GitHub**: [github.com/hbhqq9/bde-score](https://github.com/hbhqq9/bde-score)
3. **MCP setup**: See [mcp/README.md](https://github.com/hbhqq9/bde-score/tree/main/mcp)
4. **LangChain**: Import from `mcp/bde_score_langchain.py`

## Conclusion

The MCP ecosystem is making financial analysis accessible to every AI developer. Instead of spending days integrating financial APIs, you can now connect AI agents to sophisticated multi-market analysis tools in minutes.

BDE Score™ is just one example. As the MCP ecosystem grows, expect to see more specialized financial servers covering options pricing, alternative data, regulatory filings, and more.

The future of financial analysis isn't just data — it's data that AI agents can directly consume, analyze, and act upon through standardized protocols.

---

*Disclaimer: BDE Score™ is a technical tool for educational and research purposes. It does not constitute financial advice. All investment decisions should be made with professional guidance.*
