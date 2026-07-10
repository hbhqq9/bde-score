---
layout: post
title: "How to Add Live Stock Analysis Badges to Your GitHub README"
date: 2026-07-10
description: "Step-by-step guide to adding dynamic stock analysis shields.io badges to your GitHub profile and project READMEs"
tags: [github, badges, shields-io, stock-analysis, tutorial]
---

# How to Add Live Stock Analysis Badges to Your GitHub README

Want to show live stock market analysis on your GitHub profile or project README? Here's how to add dynamic shields.io badges using **BDE Score™**.

## Step 1: Choose Your Badge Type

### Market Overview Badge
Shows top scores across all 3 markets (US/HK/A-shares):

```markdown
![BDE Score Market Overview](https://img.shields.io/endpoint?url=https://atlantic-remains-atomic-floor.trycloudflare.com/api/badge)
```

Preview:

![BDE Score](https://img.shields.io/endpoint?url=https://atlantic-remains-atomic-floor.trycloudflare.com/api/badge)

### Individual Stock Badge
Show analysis for a specific stock:

```markdown
![AAPL Score](https://img.shields.io/endpoint?url=https://atlantic-remains-atomic-floor.trycloudflare.com/api/badge?symbol=AAPL)
![Tencent Score](https://img.shields.io/endpoint?url=https://atlantic-remains-atomic-floor.trycloudflare.com/api/badge?symbol=00700)
![Moutai Score](https://img.shields.io/endpoint?url=https://atlantic-remains-atomic-floor.trycloudflare.com/api/badge?symbol=SH600519)
```

## Step 2: Add to Your README

Paste the badge markdown into your `README.md`:

```markdown
# My Trading Project

[![BDE Score](https://img.shields.io/endpoint?url=https://atlantic-remains-atomic-floor.trycloudflare.com/api/badge)](https://github.com/hbhqq9/bde-score)

## Stock Analysis
Powered by BDE Score™ - covers 74 stocks across US, HK, and A-share markets.
```

## Step 3: Add GitHub Action for Automation

```yaml
name: Daily Stock Screen
on:
  schedule:
    - cron: '0 14 * * 1-5'
jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: hbhqq9/bde-score@main
        with:
          market: ALL
          min_score: '65'
```

## Supported Symbols

- **US**: AAPL, GOOGL, MSFT, NVDA, TSLA, META, AMZN...
- **HK**: 00700 (Tencent), 09988 (Alibaba)...
- **A-shares**: SH600519 (Moutai), SH601318 (Ping An)...

Full list: https://github.com/hbhqq9/bde-score#supported-stocks

## Links

- GitHub: https://github.com/hbhqq9/bde-score
- API Docs: https://atlantic-remains-atomic-floor.trycloudflare.com/docs
- shields.io: https://shields.io/

Not investment advice.
