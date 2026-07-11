# How to Analyze Stocks Across US, HK, and China A-Share Markets with Python: A Practical Guide

*Cross-market stock analysis is notoriously difficult. Different data sources, different metrics, different scoring systems. Here's how to do it with one unified API.*

---

## The Problem: Fragmented Multi-Market Analysis

If you've ever tried to compare a US tech stock like NVDA with a Hong Kong stock like 00700 (Tencent) or a China A-share like SH600519 (Moutai), you know the pain:

- **Different data APIs** for each market (Yahoo Finance for US, Futu for HK, Tushare for A-shares)
- **Different fundamental metrics** (P/E ratios calculated differently)
- **Different trading hours** and settlement rules
- **No comparable scoring** — how do you know if AAPL is "better" than 00700?

Most portfolio managers use separate tools for each market and manually compare. Quant researchers build custom pipelines. Retail investors... just guess.

## The Solution: Unified Multi-Factor Scoring

BDE Score™ is an open-source project that provides **transparent, comparable scores** across 73 stocks in 3 markets using 5 explainable factors:

| Factor | Weight | What It Measures |
|--------|--------|-----------------|
| Momentum | 25% | Trend strength & directional persistence |
| Mean Reversion | 20% | Oversold/overbought positioning |
| Volume Profile | 20% | Smart money flow detection |
| Volatility | 15% | Risk-adjusted return profile |
| Trend | 20% | Moving average alignment |

The key innovation: **every score is explainable**. Unlike black-box AI models, you can see exactly why a stock scored 72 vs 58.

## Step 1: Quick Setup (No Registration Required)

```python
import requests
import json

# No API key needed for basic access
BASE_URL = "https://atlantic-remains-atomic-floor.trycloudflare.com"

# Get scores for a specific market
def get_scores(market="US"):
    """Get BDE scores for all stocks in a market."""
    response = requests.get(f"{BASE_URL}/api/snapshot", params={"market": market})
    return response.json()

# Get score for a specific stock
def get_stock_score(symbol="AAPL"):
    """Get BDE score for a specific stock."""
    response = requests.get(f"{BASE_URL}/api/score", params={"symbol": symbol})
    return response.json()
```

That's it. No registration. No API key for basic access. No rate limit headaches.

## Step 2: Cross-Market Comparison

Here's where it gets interesting. Let's compare the top stocks from each market:

```python
import pandas as pd

# Get all markets
us_scores = get_scores("US")
hk_scores = get_scores("HK")
cn_scores = get_scores("CN")

# Create comparison DataFrame
comparison = []
for market, scores in [("US", us_scores), ("HK", hk_scores), ("CN", cn_scores)]:
    for stock in scores.get("stocks", [])[:5]:  # Top 5 per market
        comparison.append({
            "Market": market,
            "Symbol": stock["symbol"],
            "BDE_Score": stock["bde_score"],
            "Momentum": stock.get("factors", {}).get("momentum", 0),
            "Mean_Reversion": stock.get("factors", {}).get("mean_reversion", 0),
            "Volume": stock.get("factors", {}).get("volume", 0),
            "Volatility": stock.get("factors", {}).get("volatility", 0),
            "Trend": stock.get("factors", {}).get("trend", 0),
        })

df = pd.DataFrame(comparison)
print(df.sort_values("BDE_Score", ascending=False).to_string(index=False))
```

**Example output:**
```
Market Symbol  BDE_Score  Momentum  Mean_Reversion  Volume  Volatility  Trend
    US   NVDA         78        82              65      74          71     80
    HK   00700        71        68              73      70          69     75
    US   AAPL         69        72              64      68          65     74
    CN   SH600519     66        60              70      65          68     71
    US   MSFT         65        67              62      64          63     72
```

Now you can directly compare stocks across markets on equal footing.

## Step 3: Factor Deep Dive

The real power is in understanding **why** a stock scored the way it did. Let's visualize the factor breakdown:

```python
import matplotlib.pyplot as plt
import numpy as np

def plot_factor_radar(symbol):
    """Create a radar chart showing factor breakdown for a stock."""
    score_data = get_stock_score(symbol)
    factors = score_data.get("factors", {})
    
    categories = ["Momentum", "Mean Rev.", "Volume", "Volatility", "Trend"]
    values = [
        factors.get("momentum", 0),
        factors.get("mean_reversion", 0),
        factors.get("volume", 0),
        factors.get("volatility", 0),
        factors.get("trend", 0),
    ]
    
    # Create radar chart
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    values += values[:1]  # Close the polygon
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    ax.fill(angles, values, alpha=0.25, color="#4fc3f7")
    ax.plot(angles, values, linewidth=2, color="#4fc3f7")
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)
    ax.set_ylim(0, 100)
    ax.set_title(f"{symbol} — BDE Factor Analysis (Score: {score_data.get('bde_score', 'N/A')})", 
                 fontsize=14, fontweight="bold", pad=20)
    plt.tight_layout()
    plt.savefig(f"{symbol}_factors.png", dpi=150, bbox_inches="tight")
    plt.show()

# Analyze top stocks from each market
plot_factor_radar("NVDA")    # US tech leader
plot_factor_radar("00700")   # HK tech leader
plot_factor_radar("SH600519") # A-share consumer leader
```

This visualization reveals something that raw scores hide: **different markets favor different factors**.

- US tech stocks tend to score high on **Momentum** and **Trend**
- HK stocks often show stronger **Mean Reversion** signals
- A-share stocks may have unique **Volume** patterns due to retail investor dominance

## Step 4: Automated Monitoring with GitHub Actions

Set up automated daily analysis that posts results to your repo:

```yaml
# .github/workflows/daily-bde.yml
name: Daily BDE Analysis
on:
  schedule:
    - cron: '0 14 * * 1-5'  # Weekdays at 14:00 UTC
  workflow_dispatch:

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Fetch BDE Scores
        run: |
          curl -s "https://atlantic-remains-atomic-floor.trycloudflare.com/api/snapshot?market=ALL" \
            > daily_scores.json
          
      - name: Generate Summary
        run: |
          python3 -c "
          import json
          with open('daily_scores.json') as f:
              data = json.load(f)
          print('## Daily BDE Scores')
          for stock in data.get('top_movers', [])[:5]:
              print(f'- **{stock[\"symbol\"]}**: {stock[\"bde_score\"]} ({stock[\"change\"]:+.1f})')
          " >> $GITHUB_STEP_SUMMARY
          
      - name: Upload Results
        uses: actions/upload-artifact@v4
        with:
          name: bde-scores-${{ github.run_number }}
          path: daily_scores.json
```

## Step 5: Building a Custom Watchlist

```python
class BDEWatchlist:
    """Track specific stocks and get alerts."""
    
    def __init__(self, symbols):
        self.symbols = symbols
        self.base_url = "https://atlantic-remains-atomic-floor.trycloudflare.com"
    
    def refresh(self):
        """Fetch latest scores for all watchlist stocks."""
        results = []
        for symbol in self.symbols:
            try:
                resp = requests.get(
                    f"{self.base_url}/api/score",
                    params={"symbol": symbol},
                    timeout=10
                )
                if resp.status_code == 200:
                    results.append(resp.json())
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
        return results
    
    def top_performers(self, n=5):
        """Get top N performers from watchlist."""
        scores = self.refresh()
        return sorted(scores, key=lambda x: x.get("bde_score", 0), reverse=True)[:n]
    
    def factor_alerts(self, threshold=80):
        """Find stocks with any factor above threshold."""
        scores = self.refresh()
        alerts = []
        for stock in scores:
            factors = stock.get("factors", {})
            high_factors = {k: v for k, v in factors.items() if v >= threshold}
            if high_factors:
                alerts.append({
                    "symbol": stock["symbol"],
                    "score": stock["bde_score"],
                    "strong_factors": high_factors
                })
        return alerts

# Usage
watchlist = BDEWatchlist(["AAPL", "NVDA", "MSFT", "00700", "SH600519", "09988"])
top = watchlist.top_performers(3)
for stock in top:
    print(f"{stock['symbol']}: {stock['bde_score']}")
```

## Step 6: Historical Analysis

```python
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

def plot_score_history(symbol, days=30):
    """Plot BDE score history for a stock."""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    response = requests.get(
        f"https://atlantic-remains-atomic-floor.trycloudflare.com/api/history",
        params={"symbol": symbol, "days": days}
    )
    
    if response.status_code == 200:
        data = response.json()
        dates = [d["date"] for d in data["history"]]
        scores = [d["bde_score"] for d in data["history"]]
        
        plt.figure(figsize=(12, 6))
        plt.plot(dates, scores, linewidth=2, color="#4fc3f7", marker="o", markersize=4)
        plt.fill_between(dates, scores, alpha=0.1, color="#4fc3f7")
        plt.title(f"{symbol} — BDE Score History ({days} days)", fontsize=14)
        plt.xlabel("Date")
        plt.ylabel("BDE Score")
        plt.ylim(0, 100)
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(f"{symbol}_history.png", dpi=150)
        plt.show()

plot_score_history("AAPL", days=30)
```

## Key Takeaways

1. **Cross-market comparison is possible** — unified scoring eliminates the "apples to oranges" problem
2. **Transparency matters** — know *why* a stock scored high, not just that it did
3. **Factor analysis reveals market differences** — US/HK/A-share markets have different dynamics
4. **Automation is key** — GitHub Actions + API = daily insights without manual work
5. **Free and open source** — no registration, no credit card, just `curl`

## Resources

- **GitHub Repository**: [github.com/hbhqq9/bde-score](https://github.com/hbhqq9/bde-score)
- **Live Dashboard**: [hbhqq9.github.io/bde-score](https://hbhqq9.github.io/bde-score/)
- **API Documentation**: [API Endpoints](https://github.com/hbhqq9/bde-score#api)
- **EU AI Act Compliance**: BDE Score is fully compliant with EU AI Act Article 50

---

*This article is part of the BDE Score™ open-source project. All code examples are MIT licensed. Financial analysis tools are for educational purposes only — not financial advice.*

**Tags**: #Python #StockAnalysis #QuantFinance #MultiMarket #OpenSource #API #DataScience #MachineLearning
