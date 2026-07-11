---
title: "How I Built an EU AI Act Compliant Stock Analysis API from Scratch"
published: true
description: "A deep dive into building transparent, explainable financial AI that meets EU AI Act requirements"
tags: [python, finance, machinelearning, euaiact, opensource]
canonical_url: "https://github.com/hbhqq9/bde-score"
---

# How I Built an EU AI Act Compliant Stock Analysis API from Scratch

The EU AI Act classifies financial AI systems as "high-risk," requiring transparency, traceability, and human oversight. But how do you actually build such a system?

In this article, I'll walk you through the architecture and design decisions behind **BDE Score**, an open-source stock analysis API that's compliant from day one.

## The Core Problem: Black Box Finance AI

Most stock analysis tools suffer from the same issue: **they're black boxes**.

You input a stock ticker, and the system outputs "Buy" or "Sell." But:
- What data did it use?
- How did it weigh different factors?
- What happens if market conditions change?
- Is this AI system legally compliant?

For retail investors, this lack of transparency is frustrating. For regulators, it's a red flag.

## The Solution: Multi-Factor Scoring with Full Explainability

BDE Score takes a different approach. Instead of a single neural network predicting prices, it uses a **transparent multi-factor scoring system**:

```python
factors = {
    "technical": 0.25,      # RSI, MACD, Moving Averages
    "fundamental": 0.25,    # P/E, P/B, ROE
    "sentiment": 0.20,      # News, social media
    "risk": 0.15,           # Volatility, liquidity
    "compliance": 0.15      # Regulatory, ESG
}
```

Every score comes with:
- **Factor breakdown**: How much each factor contributed
- **Confidence level**: How reliable the analysis is
- **Risk warnings**: What could go wrong
- **Human review flag**: When to consult a human

## Architecture Deep Dive

### 1. FastAPI + Async Data Fetching

```python
@app.post("/api/score")
async def get_score(request: ScoreRequest):
    stock_code = request.stock_code
    
    # Fetch data asynchronously
    quote_data = await futu_client.get_realtime_quote(stock_code)
    kline_data = await futu_client.get_kline(stock_code)
    
    # Calculate factors
    factors = factor_engine.calculate(quote_data, kline_data)
    
    # Generate explanation
    explanation = compliance_layer.explain(stock_code, factors)
    
    return {
        "stock_code": stock_code,
        "score": factors.total_score,
        "confidence": factors.confidence,
        "explanation": explanation,
        "timestamp": datetime.utcnow().isoformat()
    }
```

### 2. Futu OpenD Integration

Real-time market data is critical. We use **Futu OpenD** as our data source:

```python
class FutuDataProvider:
    def __init__(self):
        self.ctx = futu.OpenQuoteContext(host='127.0.0.1', port=11111)
    
    def get_realtime_quote(self, stock_code: str):
        ret, data = self.ctx.get_market_snapshot([stock_code])
        return data
    
    def get_kline(self, stock_code: str, ktype=futu.KLType.K_DAY, num=100):
        ret, data, _ = self.ctx.request_history_kline(
            stock_code, ktype=ktype, max_count=num
        )
        return data
```

### 3. Cloudflare Tunnel for Secure Access

Instead of exposing our server IP, we use **Cloudflare Tunnel**:

```bash
cloudflared tunnel --url http://localhost:8890
```

Benefits:
- Hidden server IP (DDoS protection)
- Automatic HTTPS
- No need to open ports

## EU AI Act Compliance: Not an Afterthought

The EU AI Act requires four key features for high-risk AI systems:

### 1. Transparency
Every API response includes a detailed explanation:

```json
{
  "score": 72.5,
  "confidence": 0.83,
  "explanation": {
    "factor_breakdown": {
      "technical": 18.5,
      "fundamental": 15.2,
      "sentiment": 14.8,
      "risk": 12.0,
      "compliance": 12.0
    },
    "risk_warnings": ["RSI approaching overbought (68)"],
    "human_review_required": false
  }
}
```

### 2. Traceability
Every analysis request is logged with:
- Request ID
- Timestamp
- Data snapshot
- Factor calculation details

### 3. Human Oversight
When scores are extreme (>80 or <20), the system automatically flags for human review.

### 4. Robustness
Confidence scoring and risk warnings help users understand when to trust the analysis.

## Why Not Deep Learning?

You might wonder: why not use a neural network for better accuracy?

The answer: **signal-to-noise ratio in financial time series is ~0.05**. Deep learning models tend to overfit historical patterns and fail in production.

Multi-factor systems offer:
- **Interpretability**: You can see why a score was calculated
- **Debuggability**: When a factor fails, you can quickly identify and adjust it
- **Compliance**: Meets EU AI Act transparency requirements

## Real-World Usage

### Single Stock Analysis

```bash
curl -X POST "https://your-domain/api/score" \
  -H "Content-Type: application/json" \
  -d '{"stock_code": "HK.00700", "include_explanation": true}'
```

### Batch Analysis

```python
import requests

stocks = ["HK.00700", "HK.09988", "US.AAPL"]
results = []

for stock in stocks:
    resp = requests.post("https://your-domain/api/score", json={
        "stock_code": stock
    })
    results.append(resp.json())

# Filter high-confidence results
high_confidence = [r for r in results if r["confidence"] > 0.7]
```

## Open Source and Community

BDE Score is fully open source (MIT License):

- **GitHub**: https://github.com/hbhqq9/bde-score
- **Documentation**: https://hbhqq9.github.io/bde-score/
- **Interactive Tutorial**: [Jupyter Notebook](https://github.com/hbhqq9/bde-score/blob/master/bde_score_tutorial.ipynb)

We welcome contributions in:
- New data source integrations (A-shares, US options, crypto)
- Additional technical indicators
- EU AI Act compliance enhancements
- Multi-language support

## Lessons Learned

### 1. Data Quality is Everything
Free data sources (Yahoo Finance) often have gaps or delays. We invested in Futu OpenD for real-time data.

### 2. Compliance is a Feature, Not a Burden
Building for EU AI Act compliance forced us to make the system better for everyone, not just EU users.

### 3. Start with Transparency
It's much harder to add explainability later. Design for transparency from day one.

### 4. Cloudflare Tunnel is a Game Changer
No need to worry about SSL certificates, DDoS protection, or port forwarding.

## What's Next?

1. **Multi-market expansion**: A-shares, US options, crypto
2. **ML enhancement**: Add ML models with SHAP explainability
3. **Community scoring**: Allow users to share and discuss scores
4. **Mobile SDK**: Native iOS/Android clients
5. **Enterprise edition**: Private deployment, custom compliance reports

## Conclusion

BDE Score is not a "predict stock prices" tool. It's a **system for understanding markets**.

In financial AI, transparency isn't optional—it's essential. The EU AI Act is just the beginning. More regulations will follow, demanding explainability and accountability from AI systems.

We chose to make compliance a core design principle from day one, not an afterthought. This isn't just responsible—it's good business.

---

**Project**: https://github.com/hbhqq9/bde-score  
**Demo**: https://hbhqq9.github.io/bde-score/  
**License**: MIT

*Disclaimer: This tool is for technical research and educational purposes only. It does not constitute investment advice. Investment involves risks. Please make informed decisions.*
