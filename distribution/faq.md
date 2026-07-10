# BDE Score™ FAQ

Frequently Asked Questions for community submissions, support, and SEO.

---

## General

### What is BDE Score™?
BDE Score™ is an AI-powered stock analysis platform that evaluates stocks using a transparent 5-factor scoring system. It covers 73 stocks across US, HK, and A-share markets with a single comparable score (0-100).

### What does BDE stand for?
BDE represents the core methodology pillars: Breadth (market coverage), Depth (multi-factor analysis), and Edge (actionable signals).

### Is BDE Score™ free?
The dashboard and 3 API queries per day are completely free — no account required. Premium ($29/mo) unlocks unlimited API access and 365-day history.

### What markets are covered?
- **US** (25 stocks): AAPL, MSFT, GOOG, AMZN, NVDA, TSLA, SPY, QQQ, and more
- **Hong Kong** (26 stocks): Tencent, Alibaba, BYD, Meituan, Xiaomi, and more
- **A-shares / China** (23 stocks): Kweichow Moutai, CATL, BYD, Ping An, and more

---

## Technical

### How is the BDE Score calculated?
Each stock is evaluated on 5 independent factors:
1. **Momentum** (20%) — Price momentum and rate of change
2. **Mean Reversion** (20%) — Distance from statistical mean
3. **Volume** (20%) — Trading volume patterns and money flow
4. **Volatility** (20%) — Risk-adjusted returns
5. **Trend** (20%) — Moving average alignment

Each factor contributes equally (20% weight) to a composite score of 0-100.

### What do the score ranges mean?
- **>70**: Bullish signal
- **40-70**: Neutral
- **<40**: Bearish signal

### How often is data updated?
Data is refreshed at each market open. US market data updates during NYSE/NASDAQ hours, HK data during HKEX hours, and A-share data during SSE/SZSE hours.

### Is there an API?
Yes. RESTful API with endpoints for:
- Market snapshots (`/api/snapshot`)
- Individual stock analysis (`/api/stock/{symbol}`)
- Historical data (`/api/history`)
- Shareable score cards (`/share/{symbols}`)

### Can I embed BDE scores on my website?
Yes! The widget system (`/widget`) provides embeddable iframe cards. Use `/embed/snippet` to get the embed code for your site.

---

## Payment

### How do I pay for Premium?
Premium is $29/month, paid in USDC on Base chain. Visit `/payment` to see the QR code and wallet address.

### Why USDC?
USDC enables instant, global, permissionless payment — no credit card, no bank, no geographic restrictions. It aligns with our zero-friction philosophy.

### Can I try before paying?
Absolutely. The free tier gives you 3 API queries per day — enough to evaluate the tool before committing.

---

## Compliance

### Is BDE Score™ EU AI Act compliant?
Yes. BDE Score™ is designed for EU AI Act Art.50 compliance (effective August 2, 2026). We provide:
- Full transparency about AI usage in analysis
- Explainable scoring methodology
- Machine-readable compliance metadata

### Is this financial advice?
**No.** BDE Score™ is a technical analysis tool. It provides quantitative signals based on historical data patterns. It is not investment advice. Always consult a qualified financial advisor before making investment decisions.

### Where is my data stored?
User data (email, payment records) is stored locally and never shared with third parties. We comply with GDPR data protection regulations.

---

## Open Source

### What license?
MIT License — free for personal and commercial use.

### Can I contribute?
Yes! We welcome contributions. Check out the GitHub repo for open issues and contribution guidelines.

### How is it different from Bloomberg Terminal?
| | BDE Score™ | Bloomberg Terminal |
|---|---|---|
| Price | Free / $29/mo | $24,000/yr |
| Source | Open source | Proprietary |
| AI Transparency | Full (EU AI Act compliant) | Black box |
| Account needed | No | Yes |
| Payment | USDC / Free | Credit card / Invoice |
| Multi-market API | Single endpoint | Multiple products |

---

## Contact

- **Email**: nnhbh@foxmail.com
- **GitHub**: https://github.com/hbhqq9/bde-score
- **Issues**: https://github.com/hbhqq9/bde-score/issues
