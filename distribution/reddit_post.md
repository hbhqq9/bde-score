# Reddit Post: r/algotrading / r/QuantFinance / r/StockMarket

## Title
I built an open-source AI stock scoring system covering 73 stocks across US, HK, and A-share markets (transparent methodology, no black box)

## Body

Hey r/algotrading,

I've been working on **BDE Score™** — an open-source, AI-powered stock analysis tool that covers multiple markets with transparent scoring.

### The Problem
- Bloomberg Terminal: $24k/yr, single user
- Most "AI" stock tools: black box, can't explain why they scored a stock the way they did
- Multi-market analysis: usually requires 3 separate tools for US/HK/A-share

### What BDE Score does
Evaluates 73 stocks across 5 independent quantitative factors:
1. **Momentum** — price momentum and rate of change
2. **Mean Reversion** — distance from statistical mean
3. **Volume** — volume patterns and money flow
4. **Volatility** — risk-adjusted returns
5. **Trend** — MA alignment and trend strength

Each stock gets a composite score (0-100) with signal: Bullish (>70), Neutral (40-70), Bearish (<40).

### Coverage
- US: AAPL, MSFT, GOOG, NVDA, TSLA, SPY, QQQ... (25 stocks)
- HK: Tencent, Alibaba, BYD, Meituan, Xiaomi... (26 stocks)  
- A-share: Kweichow Moutai, CATL, BYD, Ping An... (23 stocks)

### Why it's different
- **Open source** (MIT): Full methodology visible, auditable
- **EU AI Act compliant**: Built for the upcoming AI transparency regulations (Aug 2026)
- **No account needed**: Dashboard works immediately
- **API-first**: Can embed scores in your own apps/websites
- **Crypto payment**: $29/mo via USDC on Base chain (optional)

### Links
- GitHub: https://github.com/hbhqq9/bde-score
- Live Dashboard: https://hbhqq9.github.io/bde-score
- API: https://atlantic-remains-atomic-floor.trycloudflare.com

Happy to answer questions about the methodology, the multi-market data pipeline, or the compliance approach.

⚠️ Technical analysis tool, not investment advice.

---

## Flair: Strategy | Open Source

## Cross-post targets
- r/algotrading (main)
- r/QuantFinance
- r/StockMarket
- r/CryptoCurrency (for USDC payment angle)
- r/sideproject (for indie dev angle)
- r/Europe (for EU AI Act angle)
