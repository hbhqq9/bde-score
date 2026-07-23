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
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# AGL Receipt Schema v2.0 — drift-aware governance receipts
_agl_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _agl_root not in sys.path:
    sys.path.insert(0, _agl_root)

from agl.receipt_schema_v2 import (
    create_receipt,
    create_bde_receipt,
    PolicyVersion,
    ValidityWindow,
    BDE_DISCLOSURE_TEMPLATE,
    BDE_IDENTITY_TEMPLATE,
)
from agl.receipt_store import InMemoryReceiptStore

# Security: Audit logger (铁律V)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('bde-mcp')
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# x402 Payment Middleware
from x402_middleware import (
    check_payment_status,
    consume_free_query,
    build_402_response_body,
    build_402_headers,
    get_client_ip as x402_get_client_ip,
    FREE_QUERIES_PER_DAY,
)

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
# Accept Header Fix Middleware
# Fixes Glama compatibility: MCP Streamable HTTP SDK requires both
# application/json AND text/event-stream in Accept header.
# Some clients (Glama health check) only send application/json.
# ============================================================================

class AcceptFixMiddleware(BaseHTTPMiddleware):
    """Ensures Accept header includes both json and SSE for MCP SDK compatibility."""
    
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/mcp" and request.method == "POST":
            accept = request.headers.get("accept", "")
            if "text/event-stream" not in accept.lower():
                # Rebuild scope with fixed Accept header
                new_headers = list(request.scope.get("headers", []))
                new_headers = [
                    (k, v) for k, v in new_headers
                    if k.lower() != b"accept"
                ]
                new_headers.append((b"accept", b"application/json, text/event-stream"))
                request.scope["headers"] = new_headers
        return await call_next(request)

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
                # 1. x402 Payment Check
                # Supports: (a) server admin key, (b) premium API key, (c) free tier
                api_key = request.headers.get("X-API-Key", "")
                
                # Server admin key (from .env) → always allowed
                if api_key and secrets.compare_digest(api_key, MCP_API_KEY):
                    pass  # Admin access, skip payment check
                
                else:
                    # x402 payment check: API key or free tier
                    payment_status = check_payment_status(api_key, client_ip)
                    
                    if not payment_status['allowed']:
                        # 402 Payment Required
                        body_402 = build_402_response_body("/mcp")
                        headers_402 = build_402_headers("/mcp")
                        headers_402.update(self._security_headers())
                        return JSONResponse(
                            content=body_402,
                            status_code=402,
                            headers=headers_402,
                        )
                    
                    # Consume free query if on free tier
                    if payment_status['tier'] == 'free':
                        consume_free_query(client_ip)
            
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
        
        # 5. Security headers (Constitution v2.0 §5.2)
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
# AGL Receipt Schema v2.0 — Drift-Aware Governance Receipts
# ============================================================================
# Replaces the static ART50_DISCLOSURE with a full append-only receipt system.
# Every MCP tool call generates an immutable receipt with drift-aware fields.
# Reference: enterprise-ai-os-architecture Issue #1 (hegu-1 feedback).

# Initialize the in-memory receipt store (append-only, thread-safe)
_receipt_store = InMemoryReceiptStore()

# BDE-specific policy version (drift-aware field 7)
_BDE_POLICY_VERSION = PolicyVersion(
    rule_set_id="eu-ai-act-art50-2026-01",
    schema_version="2.0.0",
    compliance_framework="EU AI Act Art.50",
    effective_from="2026-01-01T00:00:00+00:00",
)

def wrap_with_receipt(tool_name: str, tool_params: dict, result_json: str) -> str:
    """
    Wrap MCP tool output with AGL Receipt Schema v2.0.

    Generates a full drift-aware receipt, appends it to the store,
    and embeds the receipt metadata in the response.

    This replaces the old wrap_with_art50() which only added a static
    disclosure block. The new version:
      1. Creates an immutable receipt for every tool invocation
      2. Appends to the append-only store (audit trail)
      3. Embeds receipt_id + ai_system_info in the response
    """
    try:
        data = json.loads(result_json)
        if not isinstance(data, dict):
            data = {"result": data}
    except (json.JSONDecodeError, TypeError):
        data = {"raw_output": result_json}

    # Create the full v2.0 receipt
    now = datetime.now(timezone.utc)
    receipt = create_bde_receipt(
        tool_name=tool_name,
        tool_params=tool_params,
        result_summary={
            "output_keys": list(data.keys()) if isinstance(data, dict) else [],
            "timestamp": now.isoformat(),
        },
    )

    # Override policy_version with BDE-specific version
    receipt.policy_version = _BDE_POLICY_VERSION

    # Set validity window (24h for market data, context includes tool info)
    receipt.validity_window = ValidityWindow(
        valid_from=now.isoformat(),
        valid_until=(now + timedelta(hours=24)).isoformat(),
        context={
            "tool": tool_name,
            "scope": "single-request",
            **{k: v for k, v in tool_params.items() if isinstance(v, (str, int, float, bool))},
        },
    )

    # Append to the immutable store
    receipt_id = _receipt_store.append(receipt)

    # Embed receipt metadata + disclosure in response
    data["ai_system_info"] = {
        **BDE_DISCLOSURE_TEMPLATE,
        "receipt_id": receipt_id,
        "receipt_schema_version": "2.0.0",
        "policy_version": _BDE_POLICY_VERSION.to_dict(),
    }

    return json.dumps(data, ensure_ascii=False, default=str)


# Backward-compatible alias for existing tool functions
def wrap_with_art50(result_json: str) -> str:
    """
    Backward-compatible wrapper.
    For new code, prefer wrap_with_receipt() which generates full receipts.
    """
    try:
        data = json.loads(result_json)
        if isinstance(data, dict) and "ai_system_info" not in data:
            data["ai_system_info"] = BDE_DISCLOSURE_TEMPLATE
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
    return wrap_with_receipt("get_bde_score", {"market": market}, json.dumps(result, ensure_ascii=False, default=str))


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
    return wrap_with_receipt("get_stock_analysis", {"symbol": symbol, "market": market}, json.dumps(result, ensure_ascii=False, default=str))


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
    return wrap_with_receipt("get_multi_market_comparison", {"symbol": symbol}, json.dumps(results, ensure_ascii=False, default=str))


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
    screener_result = {
        "count": len(filtered),
        "min_score": min_score,
        "market": market.upper(),
        "stocks": filtered[:50]  # Limit to top 50
    }
    return wrap_with_receipt("get_stock_screener", {"market": market, "min_score": min_score}, json.dumps(screener_result, ensure_ascii=False, default=str))


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
    print(f"x402 Payment: Free tier = {FREE_QUERIES_PER_DAY} queries/day, Premium = unlimited")
    print("x402 Discovery: /.well-known/x402")
    
    # Get the underlying Starlette app from FastMCP
    app = mcp.streamable_http_app()
    
    # Mount .well-known for x402 discovery + Glama
    # Priority: BDE-Stock/.well-known/ (x402 protocol discovery)
    from starlette.staticfiles import StaticFiles
    from starlette.responses import FileResponse
    
    _bde_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _well_known_dir = os.path.join(_bde_root, '.well-known')
    _docs_well_known = os.path.join(_bde_root, 'docs', '.well-known')
    
    # Serve x402 discovery file
    _x402_path = os.path.join(_well_known_dir, 'x402')
    if os.path.isfile(_x402_path):
        @app.route('/.well-known/x402', methods=['GET'])
        async def serve_x402(request):
            return FileResponse(_x402_path, media_type='application/json')
    
    # Mount docs/.well-known for glama.json etc.
    if os.path.isdir(_docs_well_known):
        @app.route('/.well-known/glama.json', methods=['GET'])
        async def serve_glama(request):
            glama_path = os.path.join(_docs_well_known, 'glama.json')
            if os.path.isfile(glama_path):
                return FileResponse(glama_path, media_type='application/json')
            return JSONResponse({"error": "not found"}, status_code=404)
    
    # Add middleware (Starlette applies in reverse order)
    # AcceptFix must be first (innermost) to fix headers before SDK checks
    app.add_middleware(AcceptFixMiddleware)
    app.add_middleware(SecurityMiddleware)
    
    # Run with uvicorn (no Server header leakage)
    uvicorn.run(app, host="127.0.0.1", port=8891, server_header=False)
