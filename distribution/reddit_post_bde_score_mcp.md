# Reddit Post Draft — BDE Score™ MCP Server
> Target: r/mcp, r/MCPservers, r/ClaudeAI, r/Cursor
> Created: 2026-07-13

---

## Post for r/mcp & r/MCPservers

### Title
I built an MCP server for multi-market stock scoring (US/HK/A-shares, 73 stocks) — here's what I learned about the MCP ecosystem

### Body

Hey r/mcp 👋

I've been building **BDE Score™** — an MCP server that provides quantitative stock scoring across 3 markets (US, HK, A-shares) with 73 stocks total.

**What it does:**
- Multi-factor scoring: momentum, mean reversion, volume, volatility, trend
- Cross-market normalization (compare AAPL vs Tencent vs Moutai on the same scale)
- x402 micropayments built-in (pay per query with USDC on Base, $0.000752/event)
- Full audit trail for EU AI Act Art.50 compliance (transparency obligations kick in Aug 2, 2026)

**Why I built it as MCP:**
The MCP protocol made it trivially easy to connect to Claude, Cursor, and any MCP-compatible client. One protocol, every AI assistant. The discoverability via `.well-known/mcp.json` + A2A is a game-changer.

**Tech stack:**
- Python/FastAPI backend
- FutuOpenD + Sina Finance for market data
- Cloudflare Tunnel for HTTPS
- Base chain for payments
- Triple discovery: `.well-known/mcp.json` + `.well-known/agent.json` + `openapi.json`

**Interesting things I learned:**
1. The MCP ecosystem has 54K+ servers on Glama alone — discoverability is the real challenge
2. Self-healing discovery URLs are essential (Cloudflare Tunnel URLs change on restart)
3. The x402 protocol integration was surprisingly smooth — micropayments at $0.000752/event
4. EU AI Act compliance isn't optional anymore — building it in from day 1 is cheaper than retrofitting

**Links:**
- GitHub: https://github.com/hbhqq9/bde-score
- Live demo: https://hbhqq9.github.io/bde-score
- MCP config: https://hbhqq9.github.io/bde-score/.well-known/mcp.json

Happy to answer questions about the build process, MCP integration, or the x402 micropayment setup.

⚠️ Technical analysis tool only. Not financial advice.

---

## Post for r/ClaudeAI

### Title
I built an MCP-powered stock scoring tool with built-in EU AI Act compliance — transparent multi-market analysis for Claude

### Body

I wanted a stock analysis tool that:
1. Works directly in Claude via MCP
2. Covers US + HK + A-share markets (I work across all three)
3. Is transparent about HOW it scores stocks (no black boxes)
4. Is compliant with upcoming AI regulations

So I built **BDE Score™**.

**How it works in Claude:**
Just connect via MCP and ask things like:
- "Score all US tech stocks"
- "Compare AAPL vs MSFT vs GOOGL on momentum"
- "What's the best mean reversion opportunity in HK?"

**The scoring is fully transparent:**
Each stock gets 5 factor scores:
- Momentum (trend strength)
- Mean Reversion (oversold/overbought)
- Volume (smart money flow)
- Volatility (risk-adjusted)
- Trend (MA alignment)

You can see exactly why a stock got its score. No "trust the AI" — full explainability.

**Compliance angle:**
EU AI Act Art.50 requires AI systems to disclose they're AI-generated and provide explainability. BDE Score has this built-in: audit trails, machine-readable metadata, and explainable methodology.

**Micropayments:**
Uses x402 protocol — pay per query with USDC on Base chain. $0.000752 per event. No subscriptions, no gatekeepers.

**Try it:**
- MCP config: `https://hbhqq9.github.io/bde-score/.well-known/mcp.json`
- GitHub: https://github.com/hbhqq9/bde-score
- Dashboard: https://hbhqq9.github.io/bde-score

⚠️ Technical analysis tool. Not financial advice.

---

## Post for r/Cursor

### Title
Built an MCP server for stock analysis that works great with Cursor — multi-market scoring across 73 stocks

### Body

For anyone building finance-related AI workflows in Cursor:

I built **BDE Score™** as an MCP server that provides real-time stock scoring across US (25), HK (26), and A-share (23) markets.

**Setup in Cursor:**
Add to your MCP config:
```json
{
  "mcpServers": {
    "bde-score": {
      "url": "https://hbhqq9.github.io/bde-score/.well-known/mcp.json"
    }
  }
}
```

Then you can ask Cursor's AI to:
- Score specific stocks or entire sectors
- Compare stocks across markets
- Track momentum and mean reversion signals
- Generate portfolio-level analysis

**What makes it useful for Cursor workflows:**
- Structured JSON responses (easy to chain with other tools)
- x402 micropayments ($0.000752/query) — no API key signup
- Full audit trail for compliance
- Auto-discovery via `.well-known/mcp.json`

GitHub: https://github.com/hbhqq9/bde-score

⚠️ Technical analysis tool. Not financial advice.

---

## Hashtags & Flair Suggestions

- r/mcp flair: "Show & Tell" or "Server"
- r/ClaudeAI flair: "Tools & Integrations"
- r/Cursor flair: "MCP" or "Showcase"

## Posting Strategy
1. Post to r/mcp first (most relevant community)
2. Wait 24h, then post adapted version to r/ClaudeAI
3. Wait another day, then r/Cursor
4. Don't cross-post same day (Reddit anti-spam)
5. Engage with every comment within first 2 hours
6. Pin GitHub link in first comment
