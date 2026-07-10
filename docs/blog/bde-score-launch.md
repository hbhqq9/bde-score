---
layout: post
title: "Introducing BDE Score™: Open-Source Multi-Factor Stock Analysis"
date: 2026-07-10
tags: [launch, open-source, finance, api]
---

# Introducing BDE Score™

Today we're launching **BDE Score™** — an open-source multi-factor stock analysis tool that provides real-time composite scores (0-100) for 74 stocks across US, Hong Kong, and China A-share markets.

## What Is BDE Score?

BDE Score combines five analytical dimensions into a single, easy-to-understand number:

| Dimension | Weight | Measures |
|-----------|--------|----------|
| Momentum | 30% | Price trend strength |
| Volatility | 25% | Risk-adjusted returns |
| Volume | 20% | Trading activity signals |
| Trend | 15% | Moving average alignment |
| Risk | 10% | Drawdown protection |

## Why Open Source?

We believe stock analysis should be transparent and accessible. Bloomberg charges $24K/year. Refinitiv charges $22K/year. BDE Score is free and the methodology is fully auditable on GitHub.

## Try It Now

```bash
# All markets at once
curl "https://atlantic-remains-atomic-floor.trycloudflare.com/api/snapshot?market=ALL"

# Specific stock
curl "https://atlantic-remains-atomic-floor.trycloudflare.com/api/analyze?market=US&symbol=AAPL"
```

## Embed in Your Project

```markdown
![BDE Score](https://img.shields.io/endpoint?url=https://atlantic-remains-atomic-floor.trycloudflare.com/api/badge?symbol=AAPL)
```

## GitHub Action

```yaml
- uses: hbhqq9/bde-score@main
  with:
    market: US
    symbol: AAPL
```

## The Compliance Triangle

BDE Score is part of a larger ecosystem:
- **BDE Score™** — Stock analysis API
- **NeuroBridge** — Physical AI cognitive OS
- **IPO Compliance** — EU AI Act transparency toolkit

Together they form the Compliance Triangle for AI-native enterprises.

## Links

- GitHub: https://github.com/hbhqq9/bde-score
- Live API: https://atlantic-remains-atomic-floor.trycloudflare.com/api/health

*Not financial advice. Technical service for educational and research purposes.*
