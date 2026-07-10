# BDE Score™: How I Built an Open-Source Stock Analysis Tool That Rivals Bloomberg (For Free)

*One number. 74 stocks. 3 markets. Zero cost.*

## The $24,000 Problem

Every morning, traders and analysts fire up their Bloomberg terminals, pay $24,000 a year for the privilege, and look at composite scores that tell them whether a stock is "good" or "bad."

But what if you could get the same multi-factor analysis for free? What if the methodology was completely open, auditable, and didn't require a six-figure salary to access?

That's the problem **BDE Score™** solves.

## How It Works

BDE Score distills thousands of data points into a single number between 0 and 100. The scoring model combines five dimensions:

**Momentum (30%)** — Is the stock trending up or down? How strong is the trend?

**Volatility (25%)** — How much risk are you taking per unit of return?

**Volume (20%)** — Are other market participants confirming or contradicting the price move?

**Trend (15%)** — How do short-term and long-term moving averages align?

**Risk (10%)** — How much has the stock drawn down from recent highs?

The weights aren't arbitrary — they're based on decades of academic research in factor investing and quantitative finance.

## The Tech Stack

- **Python/FastAPI** — The API layer, handling hundreds of requests per second
- **FutuOpenD** — Real-time market data from Futu Securities
- **SQLite** — Lightweight, zero-config historical data storage
- **Cloudflare Tunnel** — Secure, zero-trust public access
- **shields.io** — Real-time embeddable badges

## What Makes It Different

### Multi-Market Coverage

Most open-source tools focus on US stocks. BDE Score covers:
- **25 US stocks** (AAPL, NVDA, MSFT, GOOGL, AMZN, TSLA, META...)
- **26 Hong Kong stocks** (Tencent, Alibaba, Meituan, JD, Baidu...)
- **23 A-Share stocks** (Moutai, CATL, BYD, Wuliangye, Ping An...)

### Zero Signup

```bash
curl "https://atlantic-remains-atomic-floor.trycloudflare.com/api/analyze?market=ALL"
```

That's it. No API key needed for basic queries. No registration. No tracking.

### EU AI Act Compliant

With the EU AI Act's Article 50 requiring transparency for AI systems that influence financial decisions, BDE Score is designed from day one to provide explainable factor breakdowns — every score tells you exactly why it scored that way.

## The Compliance Triangle

BDE Score is one vertex of what we call the **Compliance Triangle**:

1. **BDE Score™** — Market intelligence
2. **NeuroBridge** — Physical AI cognitive OS (translating VLA signals to Spiking Neural Networks)
3. **IPO Compliance** — Regulatory toolkit for EU AI Act, US SEC, and HK SFC

Together, they cover the three axes that matter for AI-native enterprises: market viability, technical architecture, and regulatory compliance.

## What's Next

- **API Key system** — Optional paid tier for high-frequency access (USDC on Base chain)
- **More markets** — Singapore, Japan, Korea
- **Custom indices** — Build your own factor-weighted portfolio
- **GitHub Action** — Run BDE analysis in your CI/CD pipeline

## Try It

```bash
# Get all scores
curl "https://atlantic-remains-atomic-floor.trycloudflare.com/api/snapshot?market=ALL"

# Analyze a specific stock
curl "https://atlantic-remains-atomic-floor.trycloudflare.com/api/analyze?market=US&symbol=AAPL"

# Embed a badge
![BDE Score](https://img.shields.io/endpoint?url=https://atlantic-remains-atomic-floor.trycloudflare.com/api/badge?symbol=AAPL)
```

## Star Us on GitHub

https://github.com/hbhqq9/bde-score

*Not financial advice. BDE Score™ is a technical service for educational and research purposes. Past performance does not guarantee future results.*
