"""
BDE Score™ Remote MCP Server (Streamable HTTP)
================================================
Provides BDE Score tools via MCP protocol over HTTP.
Mounted as a standalone server that can be exposed via Cloudflare Tunnel.
"""

import asyncio
import json
import httpx
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# Disable DNS rebinding protection to allow dynamic Cloudflare tunnel URLs
security_settings = TransportSecuritySettings(
    enable_dns_rebinding_protection=False
)

# Create FastMCP instance
mcp = FastMCP(
    "bde-score",
    instructions="BDE Score provides multi-factor quantitative stock analysis for US, HK, and CN markets. Use these tools to get stock scores, compare markets, screen stocks, and perform sector analysis.",
    host="127.0.0.1",
    port=8891,
    streamable_http_path="/mcp",
    stateless_http=True,
    transport_security=security_settings
)

# BDE API base - local
BDE_API_BASE = "http://127.0.0.1:8890"

async def call_bde_api(endpoint: str, params: dict = None) -> dict:
    """Call the BDE API endpoint."""
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            if params:
                resp = await client.get(f"{BDE_API_BASE}{endpoint}", params=params)
            else:
                resp = await client.get(f"{BDE_API_BASE}{endpoint}")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}


@mcp.tool()
async def get_bde_score(market: str = "ALL") -> str:
    """Get BDE Score analysis for stocks in a specific market.
    
    Args:
        market: "US", "HK", "CN", or "ALL" (default: ALL)
    """
    result = await call_bde_api("/api/snapshot", {"market": market.upper()})
    if "error" in result:
        return json.dumps({"error": result["error"]})
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
async def get_stock_analysis(symbol: str, market: str = "US") -> str:
    """Get detailed BDE analysis for a specific stock.
    
    Args:
        symbol: Stock ticker symbol (e.g., AAPL, 00700, SH600519)
        market: Market code - US, HK, or CN
    """
    result = await call_bde_api("/api/analyze", {"symbol": symbol.upper(), "market": market.upper()})
    if "error" in result:
        return json.dumps({"error": result["error"]})
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
async def get_multi_market_comparison(symbol: str) -> str:
    """Compare the same company across US/HK/CN markets using BDE scoring.
    
    Args:
        symbol: Company name or ticker to compare across markets
    """
    results = {}
    for market in ["US", "HK", "CN"]:
        result = await call_bde_api("/api/snapshot", {"market": market})
        if "error" not in result:
            results[market] = result
    return json.dumps(results, ensure_ascii=False, default=str)


@mcp.tool()
async def get_stock_screener(market: str = "ALL", min_score: int = 70) -> str:
    """Screen stocks by BDE score criteria.
    
    Args:
        market: Filter by market (US, HK, CN, ALL)
        min_score: Minimum BDE score threshold (0-100, default 70)
    """
    snapshot = await call_bde_api("/api/snapshot", {"market": market.upper()})
    if "error" in snapshot:
        return json.dumps({"error": snapshot["error"]})
    
    # Filter by score
    filtered = []
    for stock in snapshot.get("stocks", []):
        score = stock.get("bde_score", 0)
        if isinstance(score, (int, float)) and score >= min_score:
            filtered.append(stock)
    
    filtered.sort(key=lambda x: x.get("bde_score", 0), reverse=True)
    return json.dumps({
        "count": len(filtered),
        "min_score": min_score,
        "market": market.upper(),
        "stocks": filtered[:50]  # Limit to top 50
    }, ensure_ascii=False, default=str)


@mcp.tool()
async def get_sector_analysis(market: str = "US") -> str:
    """Get sector-level BDE analysis and rankings.
    
    Args:
        market: Market to analyze (US, HK, CN)
    """
    snapshot = await call_bde_api("/api/snapshot", {"market": market.upper()})
    if "error" in snapshot:
        return json.dumps({"error": snapshot["error"]})
    
    # Aggregate by sector
    sectors = {}
    for stock in snapshot.get("stocks", []):
        sector = stock.get("sector", "Unknown")
        if sector not in sectors:
            sectors[sector] = {"stocks": [], "avg_score": 0, "count": 0}
        sectors[sector]["stocks"].append({
            "symbol": stock.get("symbol"),
            "score": stock.get("bde_score", 0)
        })
        sectors[sector]["count"] += 1
    
    for sector_data in sectors.values():
        scores = [s["score"] for s in sector_data["stocks"] if isinstance(s["score"], (int, float))]
        if scores:
            sector_data["avg_score"] = round(sum(scores) / len(scores), 1)
        sector_data["stocks"].sort(key=lambda x: x.get("score", 0), reverse=True)
    
    return json.dumps({
        "market": market.upper(),
        "sectors": dict(sorted(sectors.items(), key=lambda x: x[1]["avg_score"], reverse=True))
    }, ensure_ascii=False, default=str)


@mcp.tool()
async def get_esg_analysis(symbol: str) -> str:
    """Get ESG (Environmental, Social, Governance) analysis for a stock.
    
    Args:
        symbol: Stock ticker symbol
    """
    result = await call_bde_api("/api/analyze", {"symbol": symbol.upper(), "include_esg": "true"})
    if "error" in result:
        return json.dumps({"error": result["error"]})
    
    # Extract ESG-related data from analysis
    esg_data = {
        "symbol": symbol.upper(),
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "note": "ESG data is derived from quantitative factors. For comprehensive ESG ratings, consult dedicated ESG data providers."
    }
    
    if "factors" in result:
        factors = result["factors"]
        esg_data["momentum"] = factors.get("momentum", {}).get("score")
        esg_data["volatility"] = factors.get("volatility", {}).get("score")
        esg_data["value"] = factors.get("value", {}).get("score")
    
    return json.dumps(esg_data, ensure_ascii=False, default=str)


if __name__ == "__main__":
    print("Starting BDE Score MCP Server (streamable-http) on port 8891...")
    mcp.run(transport="streamable-http")
