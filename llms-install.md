# BDE Score MCP Server - Installation Guide for AI Agents

## Overview
BDE Score™ provides multi-market stock analysis via MCP protocol. It covers US stocks, Hong Kong stocks, and China A-shares with unified BDE scoring (fundamental + technical + ESG).

## Prerequisites
- Python 3.10+
- pip or uv package manager
- Internet connection (API calls to market data)

## Installation Steps

### Step 1: Clone the repository
```bash
git clone https://github.com/hbhqq9/bde-score.git
cd bde-score
```

### Step 2: Install dependencies
```bash
pip install -r requirements.txt
```
Or with uv:
```bash
uv sync
```

### Step 3: Configure environment
No API keys required for basic usage. The server uses public market data endpoints.

Optional environment variables:
- `BDE_API_URL` - Custom API endpoint (defaults to built-in)
- `FUTU_HOST` / `FUTU_PORT` - Futu OpenD connection (for real-time HK/CN data)

### Step 4: Start the MCP server
```bash
python -m mcp.bde_score_mcp
```

### Step 5: Configure your MCP client
Add to your MCP configuration (Claude Desktop, Cursor, Cline, etc.):

```json
{
  "mcpServers": {
    "bde-score": {
      "command": "python",
      "args": ["/path/to/bde-score/mcp/bde_score_mcp.py"],
      "env": {}
    }
  }
}
```

### Step 6: Verify
Test the connection by calling `get_bde_score` with symbol "AAPL":
- Expected: JSON response with BDE score, fundamental score, technical score, risk score
- All scores are 0-100 scale

## Available Tools
| Tool | Description | Required Input |
|------|-------------|----------------|
| `get_bde_score` | Full BDE analysis | `symbol` (e.g., "AAPL", "00700.HK") |
| `get_multi_market_comparison` | Cross-market comparison | `symbol` |
| `get_stock_screener` | Screen by criteria | Optional filters |
| `get_esg_analysis` | ESG analysis | `symbol` |
| `get_sector_analysis` | Sector overview | Optional `sector` |

## Troubleshooting
- **Import errors**: Ensure all dependencies in requirements.txt are installed
- **Connection timeout**: Check internet connectivity; the server fetches live market data
- **No data for symbol**: Verify the symbol format (US: "AAPL", HK: "00700.HK", CN: "600519.SH")
- **China A-share data**: Requires Futu OpenD running locally for real-time data

## Supported Markets
- 🇺🇸 US Stocks (NYSE, NASDAQ)
- 🇭🇰 Hong Kong Stocks (HKEX)
- 🇨🇳 China A-shares (SSE, SZSE)

## License
MIT
