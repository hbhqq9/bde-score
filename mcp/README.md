# BDE Score™ AI Agent Integration

Make BDE Score directly callable by AI agents through industry-standard protocols.

## 🔌 Supported Integrations

| Protocol | Platform | Status | Setup |
|----------|----------|--------|-------|
| **MCP** | Claude Desktop, Cursor, Windsurf | ✅ Ready | [Guide](#mcp-setup) |
| **LangChain** | Any LangChain agent | ✅ Ready | [Guide](#langchain-setup) |
| **OpenAI Functions** | ChatGPT plugins, GPTs | 📋 Schema ready | [Guide](#openai-setup) |
| **REST API** | Any HTTP client | ✅ Live | [README](../README.md#api) |

## MCP Setup

### For Claude Desktop

1. Install:
```bash
pip install mcp httpx
```

2. Configure `claude_desktop_config.json`:
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

3. Restart Claude Desktop → BDE Score tools appear in tool list

### For Cursor IDE

Create `.cursor/mcp.json`:
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

### Available MCP Tools

- `bde_score_snapshot` — Get all scores for a market
- `bde_score_stock` — Detailed score for one stock
- `bde_score_history` — Historical score trend
- `bde_score_compare` — Compare multiple stocks
- `bde_score_top_movers` — Top/bottom performers

## LangChain Setup

```python
from bde_score_langchain import get_bde_tools
from langchain.agents import initialize_agent, AgentType
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4", temperature=0)
tools = get_bde_tools()
agent = initialize_agent(llm, tools, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION)

# AI agent can now analyze stocks directly
agent.run("Compare NVDA and AAPL - which has stronger momentum?")
agent.run("Top 5 US stocks by BDE Score today?")
```

## OpenAI Function Calling Schema

```json
{
    "name": "bde_score",
    "description": "Get transparent multi-factor stock scores across US/HK/A-share markets",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["snapshot", "score", "history", "compare"],
                "description": "Action to perform"
            },
            "symbol": {"type": "string", "description": "Stock symbol"},
            "market": {"type": "string", "enum": ["US", "HK", "CN", "ALL"]},
            "symbols": {"type": "array", "items": {"type": "string"}},
            "days": {"type": "integer", "default": 30}
        },
        "required": ["action"]
    }
}
```

## Why This Matters

Traditional stock analysis tools require:
- Manual API key management
- Complex SDK installation
- Platform-specific integrations

BDE Score's AI agent integration means:
- **Zero registration** — no API keys for basic use
- **Universal** — MCP/LangChain/OpenAI covers all major AI platforms
- **Transparent** — every score is explainable (5 factors)
- **Multi-market** — US, HK, A-shares in one call

## Architecture

```
┌─────────────────────────────────────┐
│         AI Agent (Claude, GPT)      │
├─────────────────────────────────────┤
│  MCP Protocol │ LangChain │ OpenAI  │  ← Integration Layer
├─────────────────────────────────────┤
│        BDE Score API Server         │  ← This project
├─────────────────────────────────────┤
│  Futu API │ Yahoo Finance │ Tushare │  ← Data Sources
├─────────────────────────────────────┤
│  US Market │ HK Market │ A-Share    │  ← Coverage
└─────────────────────────────────────┘
```

## Files

- `bde_score_mcp.py` — MCP server implementation
- `bde_score_langchain.py` — LangChain tool integration
- `openai_schema.json` — OpenAI function calling schema

---

*⚠️ BDE Score is for technical research only. Not financial advice.*
