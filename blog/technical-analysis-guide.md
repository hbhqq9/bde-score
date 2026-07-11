---
title: "Technical Analysis with BDE Score: A Practical Guide"
tags: [python, finance, technical-analysis, opensource, eu-ai-act]
description: "Learn how to use BDE Score for transparent, explainable technical analysis of stocks"
published_at: "2026-07-11"
---

# Technical Analysis with BDE Score: A Practical Guide

Technical analysis is one of the most widely used methods for evaluating stocks. However, traditional technical analysis tools often lack transparency and explainability.

In this guide, we'll explore how BDE Score combines technical indicators with a multi-factor scoring system to provide transparent, EU AI Act compliant stock analysis.

## What Makes BDE Score Different?

Unlike traditional technical analysis tools that focus solely on price patterns and indicators, BDE Score:

1. **Combines Multiple Factors**: Technical indicators are just one piece of the puzzle. BDE Score also considers fundamentals, sentiment, risk, and compliance metrics.

2. **Provides Explainability**: Every score comes with a detailed breakdown of how each factor contributed to the final result.

3. **Ensures Compliance**: Built from the ground up to meet EU AI Act requirements for high-risk AI systems in finance.

## Getting Started

### Installation

```bash
# Clone the repository
git clone https://github.com/hbhqq9/bde-score.git
cd bde-score

# Install dependencies
pip install -r requirements.txt

# Start the API server
python bde_api.py
```

### Basic Usage

```python
import requests

# Analyze a stock
response = requests.post(
    "http://localhost:8890/api/score",
    json={
        "stock_code": "HK.00700",  # Tencent
        "include_explanation": True
    }
)

result = response.json()
print(f"Score: {result['score']}/100")
print(f"Confidence: {result['confidence']:.2%}")
```

## Understanding the Score

### Factor Breakdown

BDE Score uses five main factors:

1. **Technical (25%)**: RSI, MACD, Moving Averages, Volume indicators
2. **Fundamental (25%)**: P/E ratio, P/B ratio, ROE, Revenue growth
3. **Sentiment (20%)**: News sentiment, social media trends
4. **Risk (15%)**: Volatility, liquidity, drawdown risk
5. **Compliance (15%)**: Regulatory risk, ESG factors

### Interpreting Scores

- **80-100**: Strong bullish signal (human review recommended)
- **60-79**: Moderately bullish
- **40-59**: Neutral
- **20-39**: Moderately bearish
- **0-19**: Strong bearish signal (human review recommended)

## Advanced Features

### Custom Weights

You can customize factor weights based on your investment strategy:

```python
custom_weights = {
    "technical": 0.35,    # Emphasize technical indicators
    "fundamental": 0.15,
    "sentiment": 0.30,
    "risk": 0.10,
    "compliance": 0.10
}
```

### Batch Analysis

Analyze multiple stocks in one request:

```python
stocks = ["HK.00700", "HK.09988", "US.AAPL"]
results = []

for stock in stocks:
    response = requests.post(
        "http://localhost:8890/api/score",
        json={"stock_code": stock}
    )
    results.append(response.json())
```

## EU AI Act Compliance

BDE Score is designed to meet EU AI Act requirements:

- **Transparency**: Every decision includes detailed explanations
- **Traceability**: Full audit trail for all analysis requests
- **Human Oversight**: Automatic flagging for extreme scores
- **Robustness**: Confidence scoring and risk warnings

## Next Steps

- Try our [Interactive Tutorial](https://github.com/hbhqq9/bde-score/blob/master/bde_score_tutorial.ipynb)
- Read the [API Documentation](https://hbhqq9.github.io/bde-score/)
- Join the [Discussion](https://github.com/hbhqq9/bde-score/discussions)

---

**Disclaimer**: This tool is for technical research and educational purposes only. It does not constitute investment advice.
