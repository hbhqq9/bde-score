"""
BDE Score™ Remote MCP Server (Streamable HTTP)
================================================
Provides BDE Score tools via MCP protocol over HTTP.
Mounted as a standalone server behind Cloudflare Tunnel.

Security (Constitution v2.0 §5 compliant):
- API Key authentication (X-API-Key header)
- Rate limiting (10 req/min per IP)
- Security headers on all responses
- No docs exposure
"""

import asyncio
import json
import os
import sys
import time
import hashlib
import secrets
import logging
import httpx
from datetime import datetime
from collections import defaultdict

# Security: Audit logger (铁律V)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('bde-mcp')
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# ============================================================================
# Security Configuration
# ============================================================================

# Load API key from .env
def load_env():
    """Load environment variables from .env file."""
    # Handle both direct execution and module import
    _this_file = os.path.abspath(__file__) if '__file__' in dir() else os.path.abspath(sys.argv[0])
    env_path = os.path.join(os.path.dirname(os.path.dirname(_this_file)), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    os.environ.setdefault(key.strip(), value.strip())

load_env()

MCP_API_KEY = os.environ.get('MCP_API_KEY', '')
if not MCP_API_KEY:
    raise RuntimeError(
        "FATAL: MCP_API_KEY not set. "
        "Generate one with: python3 -c \"import secrets; print(secrets.token_urlsafe(32))\" "
        "and add to BDE-Stock/.env"
    )

# Rate limiting config (same as BDE API)
MAX_REQUESTS = 10
WINDOW_SECONDS = 60

# Rate limiter state
_rate_limiter = defaultdict(list)

def check_rate_limit(client_ip: str) -> bool:
    """Check if client is within rate limit. Returns True if allowed."""
    now = time.time()
    # Clean old entries
    _rate_limiter[client_ip] = [t for t in _rate_limiter[client_ip] if now - t < WINDOW_SECONDS]
    if len(_rate_limiter[client_ip]) >= MAX_REQUESTS:
        return False
    _rate_limiter[client_ip].append(now)
    return True

def get_client_ip(request: Request) -> str:
    """Extract client IP, respecting Cloudflare headers."""
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

# ============================================================================
# Authentication & Security Middleware
# ============================================================================

class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Security middleware for MCP Server (Constitution v2.0 §5.2 compliant):
    - API Key validation (X-API-Key header)
    - Rate limiting (10 req/min per IP)
    - Security headers on all responses
    """
    
    @staticmethod
    def _security_headers() -> dict:
        """Return security headers to add to every response."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        }
    
    async def dispatch(self, request: Request, call_next):
        # Client IP for logging (always computed)
        client_ip = get_client_ip(request)
        
        # Only protect /mcp endpoint
        if request.url.path == "/mcp":
            # 0. Introspection methods are PUBLIC (no auth required)
            # This is the standard MCP security pattern:
            # - Discovery (tools/list, resources/list, etc.) = open
            # - Execution (tools/call) = authenticated
            # This allows Glama and other directories to verify the server
            introspection_methods = {
                "initialize", "tools/list", "resources/list", 
                "prompts/list", "notifications/initialized"
            }
            
            # Try to read method from JSON body
            method_name = None
            try:
                body = await request.body()
                if body:
                    json_data = json.loads(body)
                    method_name = json_data.get("method", "")
            except (json.JSONDecodeError, Exception):
                pass  # Not JSON, will require auth below
            
            # If this is an introspection method, skip auth
            is_introspection = method_name in introspection_methods
            
            if not is_introspection:
                # 1. API Key authentication (required for tool execution)
                api_key = request.headers.get("X-API-Key", "")
                if not api_key:
                    return JSONResponse(
                        {"error": "Authentication required. Provide X-API-Key header. Introspection (tools/list) is public."},
                        status_code=401,
                        headers={"WWW-Authenticate": "ApiKey", **self._security_headers()}
                    )
                if not secrets.compare_digest(api_key, MCP_API_KEY):
                    return JSONResponse(
                        {"error": "Invalid API key."},
                        status_code=403,
                        headers=self._security_headers()
                    )
            
            # 2. Rate limiting (applies to all requests including introspection)
            if not check_rate_limit(client_ip):
                return JSONResponse(
                    {"error": f"Rate limit exceeded. Max {MAX_REQUESTS} requests per {WINDOW_SECONDS}s."},
                    status_code=429,
                    headers={"Retry-After": str(WINDOW_SECONDS), **self._security_headers()}
                )
        
        # 3. Audit log (铁律V - 审计日志)
        logger.info(f"MCP request: {request.method} {request.url.path} from {client_ip}")
        
        # 4. Process request
        response = await call_next(request)
        
        # 4. Security headers (Constitution v2.0 §5.2)
        for key, value in self._security_headers().items():
            response.headers[key] = value
        # Remove Server header to prevent version leakage
        if "Server" in response.headers:
            del response.headers["Server"]
        
        return response

# ============================================================================
# MCP Server Setup
# ============================================================================

# Disable DNS rebinding protection for Cloudflare tunnel
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
        except httpx.HTTPStatusError as e:
            logger.warning(f"API error for {endpoint}: HTTP {e.response.status_code}")
            return {"error": f"Data service returned an error. Please check symbol/market and try again."}
        except httpx.RequestError as e:
            logger.error(f"Request failed for {endpoint}: {type(e).__name__}")
            return {"error": "Data service temporarily unavailable. Please try again later."}
        except Exception as e:
            logger.error(f"Unexpected error in {endpoint}: {type(e).__name__}: {str(e)}")
            return {"error": "Internal error. Please try again or check your parameters."}


# ============================================================================
# EU AI Act Art.50 — AI System Disclosure
# ============================================================================

ART50_DISCLOSURE = {
    "ai_system_info": {
        "generated_by": "BDE Score AI Assessment Engine v1.0.2",
        "assessment_type": "automated-multi-factor-scoring",
        "methodology": "rule-based + LLM-enhanced analysis",
        "ai_system": True,
        "eu_ai_act_art50": "compliant",
        "compliance_page": "https://hbhqq9.github.io/bde-score/compliance.html",
        "disclaimer": "AI-generated analysis. Not investment advice."
    }
}

def wrap_with_art50(result_json: str) -> str:
    """Wrap MCP tool output with Art.50 AI disclosure."""
    try:
        data = json.loads(result_json)
        if isinstance(data, dict) and "ai_system_info" not in data:
            data["ai_system_info"] = ART50_DISCLOSURE["ai_system_info"]
            return json.dumps(data, ensure_ascii=False, default=str)
    except (json.JSONDecodeError, TypeError):
        pass
    return result_json

# ============================================================================
# Tools (all readOnly)
# ============================================================================

@mcp.tool(
    title="Get BDE Scores",
    annotations=ToolAnnotations(
        title="Get BDE Scores",
        readOnlyHint=True,
        idempotentHint=True,
        destructiveHint=False,
        openWorldHint=False
    )
)
async def get_bde_score(market: str = "ALL") -> str:
    """Get BDE Score composite analysis (0-100) for stocks in a specific market.
    Returns multi-factor quantitative scores covering momentum, volatility, value, and quality.
    
    Args:
        market: "US", "HK", "CN", or "ALL" (default: ALL). Returns up to 25 stocks per market.
    """
    result = await call_bde_api("/api/snapshot", {"market": market.upper()})
    if "error" in result:
        return json.dumps({"error": result["error"]})
    return wrap_with_art50(json.dumps(result, ensure_ascii=False, default=str))


@mcp.tool(
    title="Analyze Stock",
    annotations=ToolAnnotations(
        title="Analyze Stock",
        readOnlyHint=True,
        idempotentHint=True,
        destructiveHint=False,
        openWorldHint=False
    )
)
async def get_stock_analysis(symbol: str, market: str = "US") -> str:
    """Get detailed BDE analysis for a specific stock including factor breakdown.
    
    Args:
        symbol: Stock ticker symbol (e.g., AAPL, 00700, SH600519)
        market: Market code - "US", "HK", or "CN"
    """
    result = await call_bde_api("/api/analyze", {"symbol": symbol.upper(), "market": market.upper()})
    if "error" in result:
        return json.dumps({"error": result["error"]})
    return wrap_with_art50(json.dumps(result, ensure_ascii=False, default=str))


@mcp.tool(
    title="Compare Markets",
    annotations=ToolAnnotations(
        title="Compare Markets",
        readOnlyHint=True,
        idempotentHint=True,
        destructiveHint=False,
        openWorldHint=False
    )
)
async def get_multi_market_comparison(symbol: str) -> str:
    """Compare the same company's BDE scores across US/HK/CN markets.
    
    Args:
        symbol: Company name or ticker to compare across markets
    """
    results = {}
    for market in ["US", "HK", "CN"]:
        result = await call_bde_api("/api/snapshot", {"market": market})
        if "error" not in result:
            results[market] = result
    return wrap_with_art50(json.dumps(results, ensure_ascii=False, default=str))


@mcp.tool(
    title="Screen Stocks",
    annotations=ToolAnnotations(
        title="Screen Stocks",
        readOnlyHint=True,
        idempotentHint=True,
        destructiveHint=False,
        openWorldHint=False
    )
)
async def get_stock_screener(market: str = "ALL", min_score: int = 70) -> str:
    """Screen stocks by BDE score threshold. Returns top 50 stocks meeting criteria.
    
    Args:
        market: Filter by market ("US", "HK", "CN", "ALL")
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
    return wrap_with_art50(json.dumps({
        "count": len(filtered),
        "min_score": min_score,
        "market": market.upper(),
        "stocks": filtered[:50]  # Limit to top 50
    }, ensure_ascii=False, default=str))


@mcp.tool(
    title="Sector Analysis",
    annotations=ToolAnnotations(
        title="Sector Analysis",
        readOnlyHint=True,
        idempotentHint=True,
        destructiveHint=False,
        openWorldHint=False
    )
)
async def get_sector_analysis(market: str = "US") -> str:
    """Get sector-level BDE analysis and rankings. Shows average scores per sector.
    
    Args:
        market: Market to analyze ("US", "HK", "CN")
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


@mcp.tool(
    title="ESG Analysis",
    annotations=ToolAnnotations(
        title="ESG Analysis",
        readOnlyHint=True,
        idempotentHint=True,
        destructiveHint=False,
        openWorldHint=False
    )
)
async def get_esg_analysis(symbol: str) -> str:
    """Get ESG (Environmental, Social, Governance) analysis for a stock.
    Note: ESG data is derived from quantitative factors, not dedicated ESG ratings.
    
    Args:
        symbol: Stock ticker symbol (e.g., AAPL, 00700)
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


# ============================================================================
# Secure Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("Starting BDE Score MCP Server (streamable-http) on port 8891...")
    print("Security: API Key authentication enabled")
    print(f"Security: Rate limiting {MAX_REQUESTS} req/{WINDOW_SECONDS}s per IP")
    print("Security: Security headers on all responses")
    
    # Get the underlying Starlette app from FastMCP
    app = mcp.streamable_http_app()
    
    # Add security middleware
    app.add_middleware(SecurityMiddleware)
    
    # Run with uvicorn (no Server header leakage)
    uvicorn.run(app, host="127.0.0.1", port=8891, server_header=False)
