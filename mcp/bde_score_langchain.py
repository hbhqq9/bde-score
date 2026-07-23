"""
BDE Score™ LangChain Integration
=================================
Makes BDE Score directly usable as a LangChain tool for AI agent workflows.

Usage:
    from langchain_community.tools import BDEScoreTool
    
    # Or import directly
    from bde_score_langchain import get_bde_tools
    
    tools = get_bde_tools()
    agent = create_react_agent(llm, tools)
"""

import json
import httpx
from typing import Optional, List
from pydantic import BaseModel, Field

BDE_API_BASE = "https://lightbox-essence-complement-learned.trycloudflare.com"


# Pydantic models for input validation
class SnapshotInput(BaseModel):
    """Input for getting market snapshot."""
    market: str = Field(
        default="ALL",
        description="Market to query: US, HK, CN, or ALL"
    )


class StockScoreInput(BaseModel):
    """Input for getting a single stock score."""
    symbol: str = Field(
        description="Stock symbol (e.g., AAPL, NVDA, 00700, SH600519)"
    )


class StockHistoryInput(BaseModel):
    """Input for getting stock score history."""
    symbol: str = Field(description="Stock symbol")
    days: int = Field(default=30, description="Number of days of history")


class CompareStocksInput(BaseModel):
    """Input for comparing multiple stocks."""
    symbols: List[str] = Field(
        description="List of stock symbols to compare"
    )


# LangChain Tool implementations
# These follow the LangChain Tool interface pattern

class BDESnapshotTool:
    """Get current BDE scores for all stocks in a market."""
    name = "bde_score_snapshot"
    description = "Get current BDE scores for stocks in a market (US/HK/CN/ALL). Returns multi-factor scores based on momentum, mean reversion, volume, volatility, and trend."
    args_schema = SnapshotInput
    
    async def _arun(self, market: str = "ALL") -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{BDE_API_BASE}/api/snapshot", params={"market": market})
            return json.dumps(resp.json(), indent=2)
    
    def _run(self, market: str = "ALL") -> str:
        resp = httpx.get(f"{BDE_API_BASE}/api/snapshot", params={"market": market}, timeout=30)
        return json.dumps(resp.json(), indent=2)


class BDEStockScoreTool:
    """Get detailed BDE score for a specific stock."""
    name = "bde_score_stock"
    description = "Get detailed BDE score and factor breakdown for a specific stock. Returns overall score and 5 factor scores (momentum, mean reversion, volume, volatility, trend)."
    args_schema = StockScoreInput
    
    async def _arun(self, symbol: str) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{BDE_API_BASE}/api/score", params={"symbol": symbol})
            if resp.status_code == 200:
                data = resp.json()
                return f"""BDE Score for {data.get('symbol', symbol)}:
Overall: {data.get('bde_score', 'N/A')}/100
Factors:
- Momentum: {data.get('factors', {}).get('momentum', 'N/A')}
- Mean Reversion: {data.get('factors', {}).get('mean_reversion', 'N/A')}
- Volume: {data.get('factors', {}).get('volume', 'N/A')}
- Volatility: {data.get('factors', {}).get('volatility', 'N/A')}
- Trend: {data.get('factors', {}).get('trend', 'N/A')}
Note: Technical analysis only, not financial advice."""
            return f"Error: Could not fetch score for {symbol}"
    
    def _run(self, symbol: str) -> str:
        resp = httpx.get(f"{BDE_API_BASE}/api/score", params={"symbol": symbol}, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return f"""BDE Score for {data.get('symbol', symbol)}:
Overall: {data.get('bde_score', 'N/A')}/100
Factors:
- Momentum: {data.get('factors', {}).get('momentum', 'N/A')}
- Mean Reversion: {data.get('factors', {}).get('mean_reversion', 'N/A')}
- Volume: {data.get('factors', {}).get('volume', 'N/A')}
- Volatility: {data.get('factors', {}).get('volatility', 'N/A')}
- Trend: {data.get('factors', {}).get('trend', 'N/A')}
Note: Technical analysis only, not financial advice."""
        return f"Error: Could not fetch score for {symbol}"


class BDEHistoryTool:
    """Get historical BDE scores for a stock."""
    name = "bde_score_history"
    description = "Get historical BDE scores for a stock over the past N days. Useful for trend analysis and score trajectory."
    args_schema = StockHistoryInput
    
    def _run(self, symbol: str, days: int = 30) -> str:
        resp = httpx.get(
            f"{BDE_API_BASE}/api/history",
            params={"symbol": symbol, "days": days},
            timeout=30
        )
        return json.dumps(resp.json(), indent=2)
    
    async def _arun(self, symbol: str, days: int = 30) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{BDE_API_BASE}/api/history",
                params={"symbol": symbol, "days": days}
            )
            return json.dumps(resp.json(), indent=2)


class BDECompareTool:
    """Compare BDE scores across multiple stocks."""
    name = "bde_score_compare"
    description = "Compare BDE scores across multiple stocks from different markets. Returns ranked comparison with factor breakdowns."
    args_schema = CompareStocksInput
    
    def _run(self, symbols: List[str]) -> str:
        results = []
        for sym in symbols:
            resp = httpx.get(f"{BDE_API_BASE}/api/score", params={"symbol": sym}, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                results.append({"symbol": sym, "score": data.get("bde_score"), "factors": data.get("factors", {})})
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        text = "Stock Comparison (ranked by BDE Score):\n"
        for i, r in enumerate(results, 1):
            text += f"{i}. {r['symbol']}: {r['score']}/100\n"
        text += "\nNote: Technical analysis only, not financial advice."
        return text
    
    async def _arun(self, symbols: List[str]) -> str:
        return self._run(symbols)


def get_bde_tools() -> list:
    """Get all BDE Score tools for use with LangChain agents.
    
    Usage:
        from bde_score_langchain import get_bde_tools
        
        tools = get_bde_tools()
        # Use with any LangChain agent
        agent = initialize_agent(llm, tools, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION)
    """
    return [
        BDESnapshotTool(),
        BDEStockScoreTool(),
        BDEHistoryTool(),
        BDECompareTool(),
    ]


# Example usage with LangChain
EXAMPLE_USAGE = '''
from langchain.agents import initialize_agent, AgentType
from langchain_openai import ChatOpenAI
from bde_score_langchain import get_bde_tools

# Initialize
llm = ChatOpenAI(model="gpt-4", temperature=0)
tools = get_bde_tools()
agent = initialize_agent(
    llm, tools,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Now the agent can analyze stocks!
result = agent.run("Compare NVDA and AAPL stock scores. Which has stronger momentum?")
result = agent.run("What are the top 5 US stocks by BDE Score today?")
result = agent.run("Show me the 30-day BDE score history for Tencent (00700)")
'''
