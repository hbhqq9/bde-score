# Devpost Submission

## Project Title
BDE Score™ — AI Stock Analysis for Everyone

## Tagline
Open-source, AI-powered stock analysis covering US, HK, and China A-shares — no account, no black boxes.

## Project Category
Software / FinTech / Open Source

## Built With
- Python (backend)
- Multi-factor scoring algorithms
- Cloudflare Tunnels (deployment)
- GitHub Pages (frontend)
- USDC (payments)

## Project Description

### Inspiration
Institutional stock analysis tools (Bloomberg Terminal, FactSet) cost $20,000+/year and exclude most retail investors. Meanwhile, free tools offer fragmented data with zero transparency on methodology. We asked: what if a single open-source platform could deliver transparent, multi-market AI analysis — for free, or at a fraction of the cost?

### What It Does
BDE Score™ provides AI-driven stock analysis across three major markets:
- **US Markets**: NYSE & NASDAQ
- **Hong Kong**: HKEX
- **China Mainland**: SSE & SZSE

Covering 73 pre-analyzed stocks, the platform evaluates each ticker using a transparent, multi-factor BDE scoring methodology that combines fundamental analysis, technical indicators, and market sentiment into a single, auditable score.

### How We Built It
- Multi-factor BDE scoring engine combining fundamental, technical, and sentiment dimensions
- Real-time market data integration across US, HK, and CN exchanges
- RESTful API with tiered access (free: 3 queries/day; Premium: unlimited)
- Embeddable widgets for third-party websites
- Dynamic share cards for social media
- USDC payment integration for borderless subscriptions ($29/month Premium)
- Full EU AI Act Article 50 compliance with transparent AI disclosure

### Challenges We Ran Into
- Integrating real-time data across markets with different trading hours, regulatory frameworks, and data formats
- Designing a scoring methodology that is both transparent and multi-dimensional
- Ensuring EU AI Act compliance while maintaining a frictionless user experience

### Accomplishments That We're Proud Of
- Fully open-source under MIT license — auditable by anyone
- Zero account required to start analyzing stocks
- EU AI Act Art.50 compliant AI system with full transparency
- Multi-market coverage that most competitors only offer at enterprise tiers
- USDC payment support enabling global accessibility

### What We Learned
Building transparent AI tools requires balancing sophistication with explainability. Our BDE scoring methodology had to be both rigorous enough for informed decisions and transparent enough for users to understand and verify.

### What's Next
- Expanding coverage to European markets (LSE, Euronext)
- Enhanced sentiment analysis with multi-language NLP
- Community-contributed scoring factor plugins
- Mobile-native applications

## Links

- **Source Code**: https://github.com/hbhqq9/bde-score
- **Live Demo (GitHub Pages)**: https://hbhqq9.github.io/bde-score/
- **API Endpoint**: https://atlantic-remains-atomic-floor.trycloudflare.com
- **Downloads / Releases**: https://github.com/hbhqq9/bde-score/releases

## Key Features
- Multi-market stock coverage (US, HK, A-shares)
- Transparent BDE scoring methodology
- Free API access (3 queries/day, no account needed)
- Premium tier: $29/month via USDC, unlimited queries
- Embeddable widgets for websites
- Dynamic share cards for social sharing
- EU AI Act Art.50 compliant
- Open source (MIT License)

## License
MIT License

## Try It Out
Visit https://hbhqq9.github.io/bde-score/ — no account, no credit card, no friction.
