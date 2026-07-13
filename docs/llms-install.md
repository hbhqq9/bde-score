# BDE Score Installation Guide

## For AI Agents (MCP)

### Remote Server (Recommended)
Add to your MCP configuration:
```json
{
  "mcpServers": {
    "bde-score": {
      "url": "https://tex-adequate-date-facing.trycloudflare.com/mcp",
      "headers": {
        "X-API-Key": "YOUR_API_KEY"
      }
    }
  }
}
```

### Claude Desktop Setup
1. Open Claude Desktop → Settings → Developer → Edit Config
2. Add the JSON above to `claude_desktop_config.json`
3. Restart Claude Desktop

### Cursor Setup
1. Go to Cursor Settings → MCP
2. Click "Add new MCP server"
3. Name: `bde-score`
4. URL: `https://tex-adequate-date-facing.trycloudflare.com/mcp`
5. Add header: `X-API-Key: YOUR_API_KEY`

### Auto-Discovery
BDE Score supports MCP auto-discovery. Agents can find the server at:
- GitHub Pages: `https://hbhqq9.github.io/bde-score/.well-known/mcp.json`
- Glama registry: `https://hbhqq9.github.io/bde-score/.well-known/glama.json`

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
curl "https://bathroom-ebooks-isa-accommodation.trycloudflare.com/api/stock/AAPL"
```

## For LLMs
See [llms.txt](https://hbhqq9.github.io/bde-score/llms.txt) for machine-readable documentation.
Full docs: [llms-full.txt](https://hbhqq9.github.io/bde-score/llms-full.txt)

## Authentication
All endpoints require an API Key via `X-API-Key` header.
- Free tier: 3 queries/day, 10 requests/minute
- x402 micropayment: $0.01/query USDC on Base (no key needed)

## Coverage
74 stocks across US (25), HK (26), and CN A-share (23) markets.
