# BDE Score Installation Guide

## For AI Agents (MCP)

### Remote Server (Recommended)
```json
{
  "mcpServers": {
    "bde-score": {
      "url": "https://retrieve-jobs-congress-made.trycloudflare.com/mcp",
      "headers": {
        "X-API-Key": "YOUR_API_KEY"
      }
    }
  }
}
```

### Auto-Discovery
BDE Score supports MCP auto-discovery via `.well-known/mcp.json`:
- GitHub Pages: `https://hbhqq9.github.io/bde-score/.well-known/mcp.json`

## For Developers

### Python (LangChain)
```python
from bde_score_langchain import get_bde_tools
tools = get_bde_tools()
```

### GitHub Action
```yaml
- uses: hbhqq9/bde-score@main
  with:
    market: ALL
    min_score: '55'
```

### REST API
```bash
curl "https://atlantic-remains-atomic-floor.trycloudflare.com/api/stock/AAPL"
```

## For LLMs
See [llms.txt](https://atlantic-remains-atomic-floor.trycloudflare.com/llms.txt) for machine-readable documentation.

## Authentication
All endpoints require an API Key via `X-API-Key` header.
Free tier: 10 requests/minute. Contact for higher limits.

## Coverage
73 stocks across US (25), HK (26), and CN A-share (23) markets.
