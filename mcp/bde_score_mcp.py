"""
BDE Score™ MCP (Model Context Protocol) Server
================================================
Makes BDE Score directly callable by AI agents (Claude, Cursor, Windsurf, etc.)

MCP is the emerging standard for AI tool integration. By providing an MCP server,
BDE Score becomes instantly usable in:
- Claude Desktop
- Cursor IDE
- Windsurf
- Any MCP-compatible AI agent

This is zero-registration, instant stock analysis for AI agents.
"""

import json
import httpx
from datetime import datetime

# MCP Server implementation using the MCP SDK pattern
# Install: pip install mcp httpx

MCP_SERVER_CONFIG = {
    "name": "bde-score",
    "version": "1.0.0",
    "description": "BDE Score™ - Multi-market stock analysis API for AI agents. US/HK/A-share, 73 stocks, transparent scoring.",
}

BDE_API_BASE = "https://atlantic-remains-atomic-floor.trycloudflare.com"

# Tool definitions for MCP
TOOLS = [
    {
        "name": "bde_score_snapshot",
        "description": "Get current BDE scores for stocks in a specific market (US, HK, CN) or all markets. Returns transparent multi-factor scores based on momentum, mean reversion, volume, volatility, and trend.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "market": {
                    "type": "string",
                    "enum": ["US", "HK", "CN", "ALL"],
                    "description": "Market to query. US=NASDAQ/NYSE, HK=Hong Kong, CN=China A-shares, ALL=all markets."
                }
            },
            "required": ["market"]
        }
    },
    {
        "name": "bde_score_stock",
        "description": "Get detailed BDE score for a specific stock symbol. Returns factor breakdown and overall score.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol (e.g., AAPL, NVDA, 00700, SH600519)"
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "bde_score_history",
        "description": "Get historical BDE scores for a stock over the past N days.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days of history (default: 30)",
                    "default": 30
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "bde_score_compare",
        "description": "Compare BDE scores across multiple stocks from different markets. Returns ranked comparison.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of stock symbols to compare (e.g., [\"AAPL\", \"00700\", \"SH600519\"])"
                }
            },
            "required": ["symbols"]
        }
    },
    {
        "name": "bde_score_top_movers",
        "description": "Get stocks with the highest and lowest BDE scores, plus biggest score changes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "market": {
                    "type": "string",
                    "enum": ["US", "HK", "CN", "ALL"],
                    "description": "Market to query"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of top/bottom stocks to return (default: 5)",
                    "default": 5
                }
            },
            "required": ["market"]
        }
    }
]


async def handle_tool_call(tool_name: str, arguments: dict) -> dict:
    """Handle MCP tool calls and route to BDE API."""
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            if tool_name == "bde_score_snapshot":
                market = arguments.get("market", "ALL")
                resp = await client.get(f"{BDE_API_BASE}/api/snapshot", params={"market": market})
                return {"content": [{"type": "text", "text": json.dumps(resp.json(), indent=2)}]}

            elif tool_name == "bde_score_stock":
                symbol = arguments.get("symbol", "AAPL")
                resp = await client.get(f"{BDE_API_BASE}/api/score", params={"symbol": symbol})
                if resp.status_code == 200:
                    data = resp.json()
                    text = f"""BDE Score for {symbol}:
Overall Score: {data.get('bde_score', 'N/A')}/100

Factor Breakdown:
- Momentum: {data.get('factors', {}).get('momentum', 'N/A')}/100
- Mean Reversion: {data.get('factors', {}).get('mean_reversion', 'N/A')}/100
- Volume: {data.get('factors', {}).get('volume', 'N/A')}/100
- Volatility: {data.get('factors', {}).get('volatility', 'N/A')}/100
- Trend: {data.get('factors', {}).get('trend', 'N/A')}/100

⚠️ This is a technical analysis tool, not financial advice."""
                    return {"content": [{"type": "text", "text": text}]}
                return {"content": [{"type": "text", "text": f"Error: Stock {symbol} not found"}], "isError": True}

            elif tool_name == "bde_score_history":
                symbol = arguments.get("symbol", "AAPL")
                days = arguments.get("days", 30)
                resp = await client.get(f"{BDE_API_BASE}/api/history", params={"symbol": symbol, "days": days})
                return {"content": [{"type": "text", "text": json.dumps(resp.json(), indent=2)}]}

            elif tool_name == "bde_score_compare":
                symbols = arguments.get("symbols", [])
                results = []
                for sym in symbols:
                    resp = await client.get(f"{BDE_API_BASE}/api/score", params={"symbol": sym})
                    if resp.status_code == 200:
                        data = resp.json()
                        results.append({
                            "symbol": sym,
                            "bde_score": data.get("bde_score"),
                            "factors": data.get("factors", {})
                        })
                results.sort(key=lambda x: x.get("bde_score", 0), reverse=True)
                text = "Stock Comparison (ranked by BDE Score):\n\n"
                for i, r in enumerate(results, 1):
                    text += f"{i}. {r['symbol']}: {r['bde_score']}/100\n"
                    for factor, value in r.get("factors", {}).items():
                        text += f"   {factor}: {value}\n"
                    text += "\n"
                text += "⚠️ Technical analysis only, not financial advice."
                return {"content": [{"type": "text", "text": text}]}

            elif tool_name == "bde_score_top_movers":
                market = arguments.get("market", "ALL")
                limit = arguments.get("limit", 5)
                resp = await client.get(f"{BDE_API_BASE}/api/snapshot", params={"market": market})
                if resp.status_code == 200:
                    data = resp.json()
                    stocks = data.get("stocks", [])
                    stocks.sort(key=lambda x: x.get("bde_score", 0), reverse=True)
                    top = stocks[:limit]
                    bottom = stocks[-limit:] if len(stocks) > limit else []

                    text = f"Top {limit} Stocks by BDE Score ({market}):\n"
                    for s in top:
                        text += f"  📈 {s['symbol']}: {s['bde_score']}/100\n"
                    if bottom:
                        text += f"\nBottom {limit}:\n"
                        for s in bottom:
                            text += f"  📉 {s['symbol']}: {s['bde_score']}/100\n"
                    text += "\n⚠️ Technical analysis only, not financial advice."
                    return {"content": [{"type": "text", "text": text}]}
                return {"content": [{"type": "text", "text": "Error fetching data"}], "isError": True}

            else:
                return {"content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}], "isError": True}

        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error: {str(e)}"}], "isError": True}


# === Full MCP Server Implementation ===
# To run: python mcp_server.py
# Requires: pip install mcp httpx uvicorn

MCP_SERVER_CODE = '''
"""
Standalone MCP Server for BDE Score™

Usage:
1. pip install mcp httpx
2. python -m bde_score_mcp_server

Configuration for Claude Desktop (claude_desktop_config.json):
{
    "mcpServers": {
        "bde-score": {
            "command": "python",
            "args": ["-m", "bde_score_mcp_server"],
            "env": {}
        }
    }
}

Configuration for Cursor (.cursor/mcp.json):
{
    "mcpServers": {
        "bde-score": {
            "command": "python",
            "args": ["-m", "bde_score_mcp_server"]
        }
    }
}
"""

import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from bde_score_tools import TOOLS, handle_tool_call, MCP_SERVER_CONFIG

app = Server(MCP_SERVER_CONFIG["name"])

@app.list_tools()
async def list_tools():
    return [Tool(
        name=t["name"],
        description=t["description"],
        inputSchema=t["inputSchema"]
    ) for t in TOOLS]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    return await handle_tool_call(name, arguments)

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream)

if __name__ == "__main__":
    asyncio.run(main())
'''


# Setup instructions
SETUP_GUIDE = """
# BDE Score™ MCP Server Setup Guide

## What is MCP?

Model Context Protocol (MCP) is an open standard that lets AI agents discover and use external tools.
By running the BDE Score MCP server, you give AI agents direct access to stock analysis capabilities.

## Quick Setup

### For Claude Desktop

1. Install dependencies:
```bash
pip install mcp httpx
```

2. Create the server file:
```bash
# Save the MCP server code as a Python module
pip install bde-score-mcp  # (when published to PyPI)
```

3. Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\\Claude\\claude_desktop_config.json` (Windows):
```json
{
    "mcpServers": {
        "bde-score": {
            "command": "python",
            "args": ["-c", "from bde_score_mcp import main; import asyncio; asyncio.run(main())"]
        }
    }
}
```

4. Restart Claude Desktop

### For Cursor IDE

1. Create `.cursor/mcp.json` in your project:
```json
{
    "mcpServers": {
        "bde-score": {
            "command": "python",
            "args": ["-c", "from bde_score_mcp import main; import asyncio; asyncio.run(main())"]
        }
    }
}
```

2. BDE Score tools will appear in Cursor's AI chat

### For Any MCP Client

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="python",
    args=["-c", "from bde_score_mcp import main; import asyncio; asyncio.run(main())"]
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        
        # List available tools
        tools = await session.list_tools()
        
        # Get stock score
        result = await session.call_tool("bde_score_stock", {"symbol": "AAPL"})
        print(result)
```

## Available Tools

| Tool | Description |
|------|-------------|
| `bde_score_snapshot` | Get all scores for a market |
| `bde_score_stock` | Get detailed score for one stock |
| `bde_score_history` | Get historical scores |
| `bde_score_compare` | Compare multiple stocks |
| `bde_score_top_movers` | Get top/bottom performers |

## Coverage

- **US Market**: AAPL, MSFT, GOOG, AMZN, META, NVDA, AMD, AVGO, ARM, + more
- **HK Market**: 00700, 09988, 00005, 01810, 02318, + more
- **A-Share Market**: SH600519, SH601318, SZ000858, SZ300750, + more

## Notes

- No API key required for basic access
- Free tier: 3 queries/day
- All scores are transparent (5 explainable factors)
- EU AI Act Article 50 compliant
- ⚠️ Not financial advice
"""
