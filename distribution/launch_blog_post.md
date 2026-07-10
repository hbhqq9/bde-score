# I Built an AI Stock Scoring System That's EU AI Act Compliant — Here's Why That Matters

**BDE Score™: Transparent multi-factor scoring for 73 stocks across US, HK, and A-share markets. Open source, compliance-first, live now.**

---

## The Problem

On August 2, 2026, the EU AI Act's Article 50 takes effect. It requires all AI systems that interact with users or make decisions affecting them to provide **transparent, explainable outputs**. 

78% of AI system operators haven't taken compliance measures yet (April 2026 data). Meanwhile, retail investors in Asian markets have zero access to systematic, transparent stock analysis tools. Most "AI stock predictors" are black boxes wrapped in a landing page.

I decided to solve both problems at once.

## What I Built

**BDE Score™** is a quantitative stock scoring system that evaluates stocks across 5 independent factors:

1. **Momentum** — Price trend strength and directional persistence
2. **Mean Reversion** — How far price has deviated from statistical mean
3. **Volume** — Smart money flow detection via volume patterns
4. **Volatility** — Risk-adjusted return profile
5. **Trend** — Moving average alignment across multiple timeframes

Each stock gets a composite score (0-100) with clear signal classification:
- **Bullish** (>70): Strong upward signals across multiple factors
- **Neutral** (40-70): Mixed signals, no clear direction
- **Bearish** (<40): Weak or negative signals

**Coverage**: 73 stocks across 3 markets — US (25), Hong Kong (26), China A-shares (23).

## Why Transparency Matters

Every BDE Score breaks down into its 5 component factors with weights. No hidden neural networks. No "trust our AI" marketing. You see exactly why a stock scored 78 or 35.

This isn't just good UX — it's regulatory compliance by design:
- Full audit trails on every score
- Machine-readable compliance metadata
- Explainable methodology documented in code

## The Tech Stack

- **Data**: FutuOpenD (primary) + Sina Finance (fallback) — dual-channel auto-failover across markets
- **API**: FastAPI with rate limiting and concurrent request handling
- **Security**: bcrypt API key hashing, CORS whitelist, HSTS, input validation
- **Infrastructure**: Cloudflare Tunnel for HTTPS + DDoS protection
- **Payments**: USDC on Base chain (crypto-native, no banking dependency)

## Why 3 Markets?

Most stock tools focus on US markets. But Asia accounts for ~40% of global market cap. Chinese retail investors especially lack access to systematic analysis tools that cover both their domestic market AND US/HK opportunities.

BDE Score gives you one comparable score across all three:
- `AAPL` → Score 72 (Bullish)
- `00700` (Tencent) → Score 65 (Neutral)  
- `600519` (Moutai) → Score 58 (Neutral)

Same methodology. Same transparency. Different markets.

## Compliance as Competitive Advantage

Most startups treat regulation as a burden. I built it into the architecture from day 1. When Art.50 enforcement begins on August 2:

- BDE Score already has machine-readable compliance metadata
- Every API response includes methodology disclosure
- Audit logs are built into the scoring pipeline

This isn't "we'll add compliance later." It's compliance-first design.

## What's Next

1. **Expanded coverage**: 200+ stocks by Q4 2026
2. **Historical backtesting**: Show how BDE Score signals would have performed
3. **Widget system**: Embed live scores on any website
4. **Institutional API**: Custom universes + compliance reports + SLA

## Try It

- **Live API**: https://atlantic-remains-atomic-floor.trycloudflare.com
- **GitHub**: https://github.com/hbhqq9/bde-score (MIT licensed)
- **GitHub Pages**: https://hbhqq9.github.io/bde-score/

```bash
# Try it right now
curl "https://atlantic-remains-atomic-floor.trycloudflare.com/api/quote/AAPL"
```

---

*Disclaimer: BDE Score™ is a technical analysis tool. Not financial advice. All investment decisions should be made independently.*
