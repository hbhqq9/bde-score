---
title: "BDE Score™: Open-Source Multi-Factor Stock Analysis Tool Covering US, HK & A-Share Markets"
published: true
description: "Real-time composite scoring (0-100) combining momentum, volatility, volume, trend & risk across 74 stocks in 3 markets. Fully open-source, no signup required."
tags: ["opensource", "python", "finance", "trading", "dataanalysis"]
canonical_url: "https://github.com/hbhqq9/bde-score"
---

# BDE Score™ — Open-Source Multi-Factor Stock Analysis

## The Problem

Most stock analysis tools are either:
- **Too simple**: Single-indicator signals (RSI overbought/oversold) that miss the full picture
- **Too expensive**: Bloomberg Terminal ($24K/yr), Refinitiv ($22K/yr), or closed-source quant platforms
- **Too complex**: Require PhD-level math to understand the models

## What BDE Score™ Does

**One number. 0-100. Every stock.** A composite score combining 5 dimensions:

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| Momentum | 30% | Price trend strength & direction |
| Volatility | 25% | Risk-adjusted returns (Sharpe-like) |
| Volume | 20% | Trading activity vs. historical norms |
| Trend | 15% | Moving average alignment |
| Risk | 10% | Drawdown & downside protection |

**Coverage**: 74 stocks across US (25), Hong Kong (26), and A-Share China (23) markets — all in real-time.

## Why It's Different

1. **Zero signup** — REST API works without authentication for basic queries
2. **Multi-market** — Not just US stocks; full HK and A-Share coverage
3. **Transparent scoring** — Every factor weight is documented, no black box
4. **Open source** — Full methodology on GitHub, auditable by anyone
5. **Real-time badges** — Embed live scores in any README or website

## Quick Start

```bash
# Real-time analysis for any market
curl "https://atlantic-remains-atomic-floor.trycloudflare.com/api/analyze?market=US"
curl "https://atlantic-remains-atomic-floor.trycloudflare.com/api/analyze?market=HK"
curl "https://atlantic-remains-atomic-floor.trycloudflare.com/api/analyze?market=A"

# Specific stock
curl "https://atlantic-remains-atomic-floor.trycloudflare.com/api/analyze?market=US&symbol=AAPL"
```

## Live Badges

Embed real-time BDE Scores in your own projects:

```markdown
![BDE Score](https://img.shields.io/endpoint?url=https://atlantic-remains-atomic-floor.trycloudflare.com/api/badge?symbol=AAPL)
```

## GitHub Action

Use BDE Score™ in your own CI/CD pipelines:

```yaml
- uses: hbhqq9/bde-score@main
  with:
    market: US
    symbol: AAPL
```

## The Stack

- **Python/FastAPI** — API layer
- **FutuOpenD** — Real-time market data
- **SQLite** — Historical analysis storage
- **Cloudflare Tunnel** — Secure public access
- **Base Chain (USDC)** — Optional API key activation

## EU AI Act Compliance

Built with [EU AI Act Article 50](https://github.com/hbhqq9/ipo-compliance) transparency requirements in mind. Every score comes with explainable factor breakdowns.

## Links

- **GitHub**: https://github.com/hbhqq9/bde-score
- **Live Demo**: https://atlantic-remains-atomic-floor.trycloudflare.com/api/snapshot?market=ALL
- **NeuroBridge** (cognitive OS): https://github.com/hbhqq9/neurobridge
- **IPO Compliance** (EU AI Act): https://github.com/hbhqq9/ipo-compliance

*Not financial advice. Technical service for educational and research purposes.*

---

**⭐ Star us on GitHub if you find this useful!**
