# 📊 BDE Score™

**AI-Powered Multi-Market Stock Analysis — One Score, Every Market**

[![Live](https://img.shields.io/badge/Live-Try%20Now-blue?style=for-the-badge)](https://animal-munich-topics-tasks.trycloudflare.com)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-io.github.hbhqq9%2Fbde--score-blue?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNiIgaGVpZ2h0PSIxNiIgdmlld0JveD0iMCAwIDE2IDE2Ij48cGF0aCBmaWxsPSIjZmZmIiBkPSJNOCAwTDQgNGg4TDEyIDBoLTR6TTQgNnY0aDhWNkw0IDZ6TTQgMTJ2NGg4di00SDR6Ii8+PC9zdmc+)](https://registry.modelcontextprotocol.io)
[![API](https://img.shields.io/badge/API-RESTful-green?style=for-the-badge)](#api)
[![EU AI Act](https://img.shields.io/badge/EU%20AI%20Act-Art.50%20Compliant-orange?style=for-the-badge)](#compliance)
[![License](https://img.shields.io/badge/License-AGPL--3.0-blue?style=for-the-badge)](LICENSE) [![Commercial](https://img.shields.io/badge/Commercial-License-green?style=for-the-badge)](#license)

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
👉 **[Open Dashboard](https://animal-munich-topics-tasks.trycloudflare.com/dashboard)**

### API Usage

```bash
# Get latest scores (US market)
curl https://animal-munich-topics-tasks.trycloudflare.com/api/snapshot?market=US

# Get all markets
curl https://animal-munich-topics-tasks.trycloudflare.com/api/snapshot?market=ALL

# With Premium API Key (unlimited access)
curl -H "X-API-Key: bde_your_key_here" \
  https://animal-munich-topics-tasks.trycloudflare.com/api/snapshot?market=ALL

# Historical data
curl https://animal-munich-topics-tasks.trycloudflare.com/api/history?symbol=AAPL&days=30
```

### Pricing

| Tier | Price | Access |
|------|-------|--------|
| **Free** | $0 | Dashboard + 3 API queries/day |
| **Premium** | $29/mo | Unlimited API + 365-day history |
| **Institutional** | $199/mo | Custom universe + compliance reports + SLA |

**Payment:** USDC on Base chain → `0x87d6C8F71d89d7E1f17EcAB138EDfaAc19d9D2fE`

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

## ⚠️ Disclaimer

**BDE Score™ is a technical analysis tool, NOT financial advice.** All investment decisions should be made independently. Past performance does not guarantee future results. This service does not provide investment suitability assessments.

## 📄 License

**Dual License — AGPL-3.0 / Commercial**

- **Open Source**: This project is licensed under the [GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0). If you use this software on a network server, you **must** make your complete source code available to users.
- **Commercial License**: If your use case requires proprietary deployment without source code disclosure (SaaS, enterprise, embedded products), contact **nnhbh@foxmail.com** for a commercial license.
- **EU AI Act Compliance**: BDE Score™ includes native Article 50 transparency markers — the only open-source MCP server with built-in regulatory compliance.

---

<p align="center">
  <strong>BDE Score™</strong> — Transparent. Multi-Market. Compliance-Ready.<br>
  <a href="https://animal-munich-topics-tasks.trycloudflare.com">Try Live →</a> · 
  <a href="https://github.com/hbhqq9/bde-score">GitHub</a>
</p>
