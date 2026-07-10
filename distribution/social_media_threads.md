# Social Media Threads (Ready to Post)

## Twitter/X Thread
1/ Just launched BDE Score™ — an open-source stock analysis tool that gives you a 0-100 score for 74 stocks across US, HK & A-Share markets.

No signup. No Bloomberg subscription. Just curl.

🧵 Thread ↓

2/ The scoring model combines 5 factors:
• Momentum (30%) — trend strength
• Volatility (25%) — risk-adjusted returns
• Volume (20%) — participation signals
• Trend (15%) — MA alignment
• Risk (10%) — drawdown protection

3/ Why multi-market matters:

Most tools only cover US stocks. BDE Score covers:
🇺🇸 25 US stocks (AAPL, NVDA, MSFT...)
🇭🇰 26 HK stocks (Tencent, Alibaba, Meituan...)
🇨🇳 23 A-Share stocks (Moutai, CATL, BYD...)

4/ You can embed live scores in your README:

![BDE Score](https://img.shields.io/endpoint?url=https://atlantic-remains-atomic-floor.trycloudflare.com/api/badge?symbol=AAPL)

5/ We also built a GitHub Action:

- uses: hbhqq9/bde-score@main
  with:
    market: US
    symbol: AAPL

Run stock analysis in your CI/CD pipeline.

6/ EU AI Act compliant from day one.

Article 50 requires transparency for AI systems influencing financial decisions. Every BDE Score comes with explainable factor breakdowns.

7/ Part of the Compliance Triangle:
📊 BDE Score — Market intelligence
🧠 NeuroBridge — Physical AI cognitive OS
📋 IPO Compliance — EU AI Act toolkit

8/ Open source. Free. No signup.

⭐ https://github.com/hbhqq9/bde-score

#OpenSource #FinTech #StockAnalysis #EUAIAct

---

## LinkedIn Post

🚀 Excited to announce BDE Score™ — an open-source multi-factor stock analysis API.

Key differentiators:
✅ Covers US, HK & A-Share markets (74 stocks)
✅ Zero signup required
✅ EU AI Act Art.50 compliant
✅ Embeddable badges & GitHub Action
✅ Transparent scoring methodology

In a world where Bloomberg charges $24K/yr and Refinitiv $22K/yr, we believe basic stock analysis should be free and open.

Built with Python/FastAPI, FutuOpenD, and Cloudflare Tunnel.

⭐ https://github.com/hbhqq9/bde-score

#FinTech #OpenSource #EUAIAct #StockAnalysis #Compliance

---

## Reddit Post (r/algotrading, r/quantfinance, r/Python)

Title: [Project] BDE Score™ — Open-source multi-factor stock scoring API (US/HK/A-Share, 74 stocks, zero signup)

Body:
Hey everyone,

I've been working on an open-source stock analysis tool and just launched v1.0.0. It provides composite scores (0-100) based on 5 factors: momentum, volatility, volume, trend, and risk.

What makes it different from what's out there:
- Multi-market: 25 US + 26 HK + 23 A-Share stocks
- Zero signup: `curl "https://atlantic-remains-atomic-floor.trycloudflare.com/api/analyze?market=ALL"` just works
- Embeddable: shields.io badges + GitHub Action
- EU AI Act compliant: every score has explainable factor breakdowns

Tech stack: Python/FastAPI + FutuOpenD + SQLite + Cloudflare Tunnel

GitHub: https://github.com/hbhqq9/bde-score

Would love feedback from the community. What features would you like to see?

*Not financial advice — technical tool for educational/research use.*
