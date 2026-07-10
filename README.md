# 📊 BDE Score™

**AI-Powered Multi-Market Stock Analysis — One Score, Every Market**

[![Live](https://img.shields.io/badge/Live-Try%20Now-blue?style=for-the-badge)](https://hbhqq9.github.io/bde-score/)
[![API](https://img.shields.io/badge/API-RESTful-green?style=for-the-badge)](#api)
[![EU AI Act](https://img.shields.io/badge/EU%20AI%20Act-Art.50%20Compliant-orange?style=for-the-badge)](#compliance)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

### 📈 Live BDE Scores (real-time)

[![Market](https://img.shields.io/endpoint?url=https://atlantic-remains-atomic-floor.trycloudflare.com/api/badge)](https://github.com/hbhqq9/bde-score)
[![AAPL](https://img.shields.io/endpoint?url=https://atlantic-remains-atomic-floor.trycloudflare.com/api/badge?symbol=AAPL)]()
[![NVDA](https://img.shields.io/endpoint?url=https://atlantic-remains-atomic-floor.trycloudflare.com/api/badge?symbol=NVDA)]()
[![00700](https://img.shields.io/endpoint?url=https://atlantic-remains-atomic-floor.trycloudflare.com/api/badge?symbol=00700)]()
[![SH600519](https://img.shields.io/endpoint?url=https://atlantic-remains-atomic-floor.trycloudflare.com/api/badge?symbol=SH600519)]()

---

## 🎯 What is BDE Score™?

BDE Score™ is a **transparent, multi-factor quantitative scoring system** that analyzes stocks across **US, HK, and A-share markets** using 5 explainable factors:

| Factor | What it Measures |
|--------|-----------------|
| **Momentum** | Trend strength & directional persistence |
| **Mean Reversion** | Oversold/overbought positioning |
| **Volume** | Smart money flow detection |
| **Volatility** | Risk-adjusted return profile |
| **Trend** | Moving average alignment |

**73 stocks. 3 markets. One comparable score.**

## 🚀 Quick Start

### View Live Dashboard
👉 **[Open Dashboard](https://hbhqq9.github.io/bde-score/)**

### Use as GitHub Action
Add automated stock analysis to your workflow:
```yaml
- uses: hbhqq9/bde-score@main
  with:
    market: ALL
    min_score: '55'
```
Results appear in GitHub Step Summary. [Learn more](#github-action)

### API Usage

```bash
# Get latest scores (US market)
curl https://atlantic-remains-atomic-floor.trycloudflare.com/api/snapshot?market=US

# Get all markets
curl https://atlantic-remains-atomic-floor.trycloudflare.com/api/snapshot?market=ALL

# With Premium API Key (unlimited access)
curl -H "X-API-Key: bde_your_key_here" \
  https://atlantic-remains-atomic-floor.trycloudflare.com/api/snapshot?market=ALL

# Historical data
curl https://atlantic-remains-atomic-floor.trycloudflare.com/api/history?symbol=AAPL&days=30
```

### Pricing

| Tier | Price | Access |
|------|-------|--------|
| **Free** | $0 | Dashboard + 3 API queries/day |
| **Premium** | $29/mo | Unlimited API + 365-day history |
| **Institutional** | $199/mo | Custom universe + compliance reports + SLA |

**Payment:** USDC on Base chain (Base) → `0x349Eea0E2f4d3594797851758325Da3eb49D4343`

## 🌏 Coverage

### US Market (25 stocks)
AAPL, MSFT, GOOG, AMZN, META, NVDA, AMD, AVGO, ARM, INTC, V, MA, JNJ, UNH, LLY, PFE, PG, KO, WMT, MCD, TSLA, NFLX, BABA, SPY, QQQ

### HK Market (26 stocks)
00700 (Tencent), 09988 (Alibaba), 09888 (Baidu), 03690 (Meituan), 01024 (Kuaishou), 01810 (Xiaomi), 09618 (JD), 09999 (NetEase), 02015 (Li Auto), 09868 (XPeng), 01211 (BYD), 09863 (Leapmotor), 02318 (Ping An), 01398 (ICBC), 00939 (CCB), 03988 (BOC), 02628 (China Life), 02899 (Zijin Mining), 00883 (CNOOC), 00857 (PetroChina), 01088 (China Shenhua), 00941 (China Mobile), 00728 (China Telecom), 00762 (China Unicom), 01833 (Ping An Good Doctor), 02269 (WuXi Biologics)

### A-Share Market (23 stocks)
600519 (Moutai), 000858 (Wuliangye), 000568 (Luzhou Laojiao), 600887 (Yili), 002714 (Muyuan), 601318 (Ping An), 600036 (CMB), 601398 (ICBC), 601288 (ABC), 300750 (CATL), 601012 (LONGi), 002594 (BYD-A), 600900 (Yangtze Power), 688981 (SMIC), 002475 (Luxshare), 002230 (iFlytek), 603501 (Will Semi), 601899 (Zijin-A), 601088 (China Shenhua), 600585 (Conch Cement), 000333 (Midea), 600690 (Haier), 000651 (Gree)

## 🔒 EU AI Act Art.50 Compliance

BDE Score™ is **compliance-first by design**. When Art.50 takes effect on **August 2, 2026**, our system is already ready:

- ✅ **Full audit trails** — every score decision logged with factor weights
- ✅ **Explainable methodology** — transparent 5-factor breakdown per stock
- ✅ **Machine-readable metadata** — JSON compliance data for regulatory reporting

> 78% of AI system operators have NOT taken Art.50 compliance measures yet (April 2026 data). BDE Score™ closes this gap.

## 🛠 Tech Stack

- **Data:** FutuOpenD (primary) + Sina Finance (fallback) — dual-channel auto-failover
- **API:** FastAPI + Uvicorn
- **Security:** Rate limiting, concurrent locks, input validation, security headers
- **Infrastructure:** Cloudflare Tunnel (HTTPS + DDoS protection)
- **Payments:** USDC on Base chain (ERC-20)

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Landing page |
| `/dashboard` | GET | Interactive dashboard |
| `/api/snapshot` | GET | Latest scores (free: 3/day) |
| `/api/analyze` | GET | Run fresh analysis |
| `/api/history` | GET | Historical scores |
| `/api/health` | GET | System status |
| `/api/market-status` | GET | Market hours |

## 💬 Community

- **Discussions**: [Join the conversation](https://github.com/hbhqq9/bde-score/discussions)
- **Roadmap**: [v1.1 plans](https://github.com/hbhqq9/bde-score/issues/2)
- **Related Projects**: [NeuroBridge](https://github.com/hbhqq9/neurobridge) · [IPO Compliance](https://github.com/hbhqq9/ipo-compliance)

## ⚠️ Disclaimer

**BDE Score™ is a technical analysis tool, NOT financial advice.** All investment decisions should be made independently. Past performance does not guarantee future results. This service does not provide investment suitability assessments.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>BDE Score™</strong> — Transparent. Multi-Market. Compliance-Ready.<br>
  <a href="https://hbhqq9.github.io/bde-score/">Try Live →</a> · 
  <a href="https://github.com/hbhqq9/bde-score">GitHub</a>
</p>
