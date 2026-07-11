# BDE Score: Building an EU AI Act Compliant Stock Analysis API from Scratch

*How we built a transparent, multi-factor stock scoring system that covers US, HK, and A-share markets while meeting EU AI Act requirements.*

---

## The Problem: Opaque Stock Analysis Tools

Most stock analysis tools are black boxes. They give you a score or a recommendation, but you can't see how they got there. As a developer building quantitative tools, I wanted something different: a stock analysis API that is **transparent by design**.

That's why we built [BDE Score](https://github.com/hbhqq9/bde-score) — an open-source, multi-factor stock scoring API that covers US, HK, and A-share markets, with built-in EU AI Act compliance.

In this article, I'll walk you through the architecture, the multi-factor scoring system, and how we made it compliant with the EU AI Act.

---

## Architecture Overview

BDE Score is built with a simple but powerful architecture:

```
┌─────────────────┐
│   REST API      │  FastAPI + Cloudflare Tunnel
│   (Port 8890)   │
└────────┬────────┘
         │
    ┌────▼────┐
    │ Scoring │  Multi-factor engine
    │ Engine  │  (Technical + Fundamental + Sentiment)
    └────┬────┘
         │
    ┌────▼────┐
    │  Data   │  Futu OpenAPI / Alpaca / Mock
    │ Sources │  (Multi-market support)
    └─────────┘
```

The API exposes five main endpoints:

- `GET /api/stock/{symbol}` — Real-time stock snapshot with BDE score
- `GET /api/analyze/{symbol}` — Deep analysis with factor breakdown
- `GET /api/history/{symbol}` — Historical score data
- `GET /api/universe` — List of supported stocks
- `GET /api/health` — System health check

Let's dive into each component.

---

## The Multi-Factor Scoring System

The BDE Score (0-100) combines three major factor categories:

### 1. Technical Factors (40% weight)

Technical analysis looks at price patterns and market behavior:

```python
technical_score = (
    rsi_score * 0.25 +           # RSI: Overbought/Oversold
    macd_score * 0.25 +          # MACD: Trend momentum
    ma_score * 0.30 +            # Moving averages: Trend direction
    volatility_score * 0.20      # Volatility: Risk assessment
)
```

For example, a stock with RSI = 45 gets a high RSI score (neutral zone), while RSI = 80 gets a low score (overbought).

### 2. Fundamental Factors (35% weight)

Fundamental analysis evaluates the company's financial health:

```python
fundamental_score = (
    pe_score * 0.25 +            # P/E ratio: Valuation
    pb_score * 0.20 +            # P/B ratio: Asset valuation
    roe_score * 0.30 +           # ROE: Profitability
    debt_ratio_score * 0.25      # Debt ratio: Financial risk
)
```

A stock with P/E = 15 in a sector where average P/E = 25 gets a high valuation score.

### 3. Sentiment Factors (25% weight)

Sentiment analysis captures market psychology:

```python
sentiment_score = (
    volume_trend_score * 0.40 +  # Volume: Market interest
    price_momentum_score * 0.35 + # Momentum: Short-term trend
    market_breadth_score * 0.25   # Market breadth: Sector strength
)
```

### Combining the Factors

The final BDE Score is:

```python
bde_score = (
    technical_score * 0.40 +
    fundamental_score * 0.35 +
    sentiment_score * 0.25
)
```

The weights are configurable, but these defaults work well across different market conditions.

---

## EU AI Act Compliance

The EU AI Act (Art. 50) requires transparency for AI systems that interact with users. BDE Score is designed to be compliant from the ground up.

### Compliance Metadata

Every API response includes compliance metadata:

```json
{
  "symbol": "AAPL",
  "bde_score": 72.5,
  "factors": {
    "technical": 68.3,
    "fundamental": 75.1,
    "sentiment": 74.2
  },
  "_compliance": {
    "ai_system": true,
    "transparency": "full",
    "methodology": "Multi-factor scoring with technical (40%), fundamental (35%), and sentiment (25%) analysis",
    "data_sources": ["Futu OpenAPI", "Alpaca API"],
    "last_updated": "2026-07-11T11:30:00Z",
    "explainability": "Factor-level breakdown provided in /api/analyze endpoint"
  }
}
```

### Key Compliance Features

1. **Explainable Methodology** — The scoring methodology is documented in the API response
2. **Data Source Transparency** — All data sources are explicitly listed
3. **Factor-Level Breakdown** — Users can see exactly how the score was calculated
4. **Timestamp** — Clear indication of when the data was last updated
5. **No Hidden Logic** — All code is open-source and auditable

---

## Multi-Market Support

One of the biggest challenges was supporting multiple markets with different data formats and trading hours.

### Supported Markets

- **US Market** — NYSE, NASDAQ (via Alpaca API)
- **HK Market** — HKEX (via Futu OpenAPI)
- **A-Share Market** — SSE, SZSE (via Futu OpenAPI)

### Market-Specific Adjustments

Different markets have different characteristics:

```python
# A-share market: 10% daily limit, T+1 trading
if market == "CN":
    max_score = min(score, 90)  # Cap at 90 due to daily limit
    sentiment_weight = 0.20     # Lower sentiment weight (T+1 restriction)

# US market: No daily limit, T+0 trading
elif market == "US":
    sentiment_weight = 0.30     # Higher sentiment weight (intraday trading)

# HK market: No daily limit, T+0 trading
elif market == "HK":
    sentiment_weight = 0.25     # Balanced approach
```

---

## GitHub Action Integration

BDE Score includes a GitHub Action that automatically adds a real-time stock badge to your repository:

```yaml
# .github/workflows/bde-score-badge.yml
name: BDE Score Badge
on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:

jobs:
  update-badge:
    runs-on: ubuntu-latest
    steps:
      - uses: hbhqq9/bde-score-action@v1
        with:
          symbol: 'AAPL'
          token: ${{ secrets.GITHUB_TOKEN }}
```

This generates a badge like:

```
[![BDE Score](https://img.shields.io/endpoint?url=...)](https://github.com/hbhqq9/bde-score)
```

The badge updates automatically, showing the latest BDE score in your README.

---

## Real-World Usage

Here's how developers are using BDE Score:

### Use Case 1: Portfolio Screening

```python
import requests

# Get scores for all stocks in your portfolio
portfolio = ["AAPL", "GOOGL", "MSFT", "AMZN"]
scores = {}

for symbol in portfolio:
    resp = requests.get(f"https://your-api.com/api/stock/{symbol}")
    scores[symbol] = resp.json()["bde_score"]

# Sort by score
ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
print(f"Top pick: {ranked[0][0]} (score: {ranked[0][1]})")
```

### Use Case 2: Automated Trading Signals

```python
# Get deep analysis
analysis = requests.get("https://your-api.com/api/analyze/TSLA").json()

# Generate trading signal
if analysis["bde_score"] > 80 and analysis["factors"]["technical"] > 75:
    print("Strong buy signal")
elif analysis["bde_score"] < 30:
    print("Strong sell signal")
else:
    print("Hold")
```

### Use Case 3: Compliance Reporting

```python
# Get compliance metadata
stock = requests.get("https://your-api.com/api/stock/NVDA").json()
compliance = stock["_compliance"]

print(f"Methodology: {compliance['methodology']}")
print(f"Data sources: {', '.join(compliance['data_sources'])}")
print(f"Last updated: {compliance['last_updated']}")
```

---

## Performance and Scalability

BDE Score is designed for low-latency, high-throughput scenarios:

- **Response Time** — < 100ms for cached data, < 2s for real-time data
- **Rate Limiting** — 60 requests/minute (free tier), configurable
- **Caching** — In-memory cache with 5-minute TTL
- **Horizontal Scaling** — Stateless API, can run multiple instances

---

## What's Next

We're working on several exciting features:

1. **More Markets** — Adding support for European markets (LSE, Euronext)
2. **Custom Factors** — Allow users to define their own scoring factors
3. **Historical Backtesting** — Built-in backtesting framework
4. **Webhook Integration** — Real-time notifications for score changes

---

## Get Started

BDE Score is fully open-source and self-hostable:

```bash
# Clone the repository
git clone https://github.com/hbhqq9/bde-score.git

# Install dependencies
pip install -r requirements.txt

# Start the API server
python bde_api.py
```

Or use the hosted API:

```bash
curl https://your-api.com/api/stock/AAPL
```

---

## Conclusion

Building a transparent, compliant stock analysis API is challenging but rewarding. BDE Score proves that you can have a powerful multi-factor scoring system that is also explainable and compliant with regulations like the EU AI Act.

We'd love to hear your feedback and contributions. Check out the [GitHub repository](https://github.com/hbhqq9/bde-score) and let us know what you think!

---

*Disclaimer: BDE Score is a technical tool for educational and research purposes. It does not constitute financial advice. Always do your own research before making investment decisions.*
