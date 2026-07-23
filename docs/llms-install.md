# BDE Score Installation Guide

## For AI Agents (MCP)

### Remote Server (Recommended)
```json
{
  "mcpServers": {
    "bde-score": {
      "url": "https://fantasy-bald-shark-stereo.trycloudflare.com/mcp",
      "headers": {
        "X-API-Key": "YOUR_API_KEY"
      }
    }
  }
}
```

Transport: Streamable HTTP

### Auto-Discovery
BDE Score supports MCP auto-discovery via `.well-known/mcp.json`:
- GitHub Pages: `https://hbhqq9.github.io/bde-score/.well-known/mcp.json`

### Claude Desktop
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "bde-score": {
      "url": "https://fantasy-bald-shark-stereo.trycloudflare.com/mcp",
      "headers": { "X-API-Key": "YOUR_API_KEY" }
    }
  }
}
```

### Cursor IDE
Add to `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "bde-score": {
      "url": "https://fantasy-bald-shark-stereo.trycloudflare.com/mcp",
      "headers": { "X-API-Key": "YOUR_API_KEY" }
    }
  }
}
```

## For Developers

### Python MCP Client
```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async with streamablehttp_client("https://fantasy-bald-shark-stereo.trycloudflare.com/mcp") as (read, write, _):
    async with ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool("get_bde_score", {"market": "US"})
        print(result)
```
