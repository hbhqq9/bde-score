# How I Made My Stock Analysis API Callable by Claude, Cursor, and Any AI Agent

*The future of developer tools isn't APIs — it's AI-agent-callable tools. Here's how to make any API work with MCP, LangChain, and OpenAI function calling.*

---

## The Problem: APIs Are Built for Humans, Not AI

We've spent the last decade building APIs for developers. REST endpoints, JSON responses, API keys, rate limits, SDK installations. But a new paradigm is emerging: **AI agents that use tools**.

When Claude Desktop, Cursor, or a LangChain agent needs stock data, they don't want to:
1. Sign up for an API key
2. Install an SDK
3. Handle authentication headers
4. Parse raw JSON

They want a **tool** — a function with a name, description, and typed inputs that they can call directly.

## The Solution: Three Integration Layers

I built BDE Score™ as an open-source stock analysis API. To make it AI-agent-callable, I implemented three integration layers:

1. **MCP (Model Context Protocol)** — For Claude Desktop, Cursor, Windsurf
2. **LangChain Tools** — For any LangChain-based agent
3. **OpenAI Function Schema** — For ChatGPT plugins and GPTs

The result? Any AI agent can now analyze stocks across US, HK, and China A-share markets with a single function call.

## Layer 1: MCP Server

MCP is the emerging standard for AI tool integration. Think of it as "USB for AI" — one protocol that works everywhere.

### The Server (simplified)

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import httpx, json

BDE_API = "https://atlantic-remains-atomic-floor.trycloudflare.com"

app = Server("bde-score")

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="bde_score_stock",
            description="Get BDE score for a stock. Returns overall score + 5 factor breakdown.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (AAPL, 00700, SH600519)"
                    }
                },
                "required": ["symbol"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "bde_score_stock":
        resp = httpx.get(f"{BDE_API}/api/score", params={"symbol": arguments["symbol"]})
        data = resp.json()
        return TextContent(text=json.dumps(data, indent=2))
```

### Usage in Claude Desktop

Add to `claude_desktop_config.json`:
```json
{
    "mcpServers": {
        "bde-score": {
            "command": "python",
            "args": ["-m", "bde_score_mcp"]
        }
    }
}
```

Now Claude can directly call:
- "What's NVDA's BDE score?" → calls `bde_score_stock(symbol="NVDA")`
- "Compare Apple and Tencent" → calls `bde_score_compare(symbols=["AAPL", "00700"])`
- "Show me top 5 US stocks" → calls `bde_score_top_movers(market="US", limit=5)`

## Layer 2: LangChain Tools

For the LangChain ecosystem, the integration is even simpler:

```python
from bde_score_langchain import get_bde_tools
from langchain.agents import initialize_agent, AgentType
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4")
tools = get_bde_tools()
agent = initialize_agent(llm, tools, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION)

# The agent can now reason about stocks
result = agent.run(
    "I'm comparing NVDA (US) with 00700 (HK). "
    "Which has stronger momentum? Are their volatility profiles similar?"
)
```

The agent will automatically:
1. Call `bde_score_stock` for NVDA
2. Call `bde_score_stock` for 00700
3. Compare the factor breakdowns
4. Generate a natural language analysis

## Layer 3: OpenAI Function Calling

For custom GPTs or ChatGPT plugins:

```python
functions = [{
    "name": "bde_score",
    "description": "Get transparent multi-factor stock scores (US/HK/A-shares)",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["snapshot", "score", "history", "compare"]
            },
            "symbol": {"type": "string"},
            "market": {"type": "string", "enum": ["US", "HK", "CN", "ALL"]}
        },
        "required": ["action"]
    }
}]

# OpenAI will call this function when the user asks about stocks
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "What's the top stock by BDE score today?"}],
    functions=functions,
    function_call="auto"
)
```

## Why This Is Disruptive

### Traditional API Distribution
```
Developer → Register → Get API Key → Install SDK → Write Code → Call API → Parse Response
```

### AI-Agent Distribution
```
AI Agent → Call Tool → Get Result → Reason → Answer User
```

The second path eliminates **every friction point**. No registration, no SDK, no code. The AI agent discovers the tool, calls it, and uses the result.

### The Numbers

| Distribution Channel | Traditional | AI-Agent |
|---------------------|-------------|----------|
| Steps to first call | 5-8 | 0-1 |
| Registration required | Yes | No |
| Code required | Yes | No |
| Potential users | Developers | Everyone with AI |

## The BDE Score Implementation

Here's what we built:

**5 tools across 3 protocols:**

| Tool | What it does |
|------|-------------|
| `bde_score_snapshot` | All scores for a market |
| `bde_score_stock` | One stock's detailed breakdown |
| `bde_score_history` | Score trajectory over N days |
| `bde_score_compare` | Ranked comparison of multiple stocks |
| `bde_score_top_movers` | Top/bottom performers |

**Coverage:**
- US: 25 stocks (AAPL, NVDA, MSFT, GOOG, ...)
- HK: 20 stocks (00700, 09988, 00005, ...)
- A-shares: 28 stocks (SH600519, SZ000858, ...)

**All free, all transparent, all AI-agent-callable.**

## How to Build Your Own

### Step 1: Define your tools
Think about what an AI agent would need. Not "what endpoints do I have" but "what questions would an AI need answered?"

### Step 2: Implement MCP
MCP is the most universal standard. One implementation works across Claude, Cursor, and any MCP client.

```bash
pip install mcp httpx
```

### Step 3: Implement LangChain
LangChain is the most popular agent framework. If your tool works with LangChain, it works with thousands of existing agents.

### Step 4: Document for AI
Traditional docs are for humans. Add examples that AI agents can learn from:
- "What's the BDE score for AAPL?" → `bde_score_stock(symbol="AAPL")`
- "Compare stocks across markets" → `bde_score_compare(symbols=[...])`

## Key Takeaways

1. **AI agents are the new users** — Design your tools for agents, not just developers
2. **MCP is the universal standard** — One protocol, all AI platforms
3. **LangChain is the ecosystem** — Thousands of existing agents ready to use your tools
4. **Zero friction wins** — No registration, no API keys, no SDK installation
5. **Transparency matters** — AI agents need explainable data to give good advice

## Resources

- **GitHub**: [github.com/hbhqq9/bde-score](https://github.com/hbhqq9/bde-score)
- **MCP + LangChain Code**: [mcp/ directory](https://github.com/hbhqq9/bde-score/tree/master/mcp)
- **Live Dashboard**: [hbhqq9.github.io/bde-score](https://hbhqq9.github.io/bde-score/)

---

*This article is part of the BDE Score™ open-source project. All code is MIT licensed. Stock analysis tools are for educational purposes only — not financial advice.*

**Tags**: #MCP #LangChain #AIAgents #Claude #Cursor #StockAnalysis #OpenSource #DeveloperTools #Python #FunctionCalling
