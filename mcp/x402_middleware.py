"""
x402 Payment Middleware for BDE Score
=====================================
Implements the x402 micropayment protocol as ASGI middleware.

Payment tiers:
  - Free: 3 queries/day per IP (tracked in x402_payments.db)
  - Premium: Unlimited with valid API Key (bcrypt-verified against api_keys.json)
  - No payment: HTTP 402 with payment instructions

x402 discovery: /.well-known/x402
Payment chain: Base (chainId 8453), USDC

This module is designed to be importable by both:
  - bde_api.py (FastAPI on port 8890)
  - mcp/mcp_http_server.py (Starlette/FastMCP on port 8891)
"""

import os
import json
import time
import sqlite3
import logging
import secrets
from datetime import datetime, timezone
from contextlib import contextmanager
from collections import defaultdict

logger = logging.getLogger('x402_middleware')

# ============================================================================
# Configuration
# ============================================================================

# Wallet & chain config
WALLET_ADDRESS = "0x349Eea0E2f4d3594797851758325Da3eb49D4343"
CHAIN_NAME = "Base"
CHAIN_ID = 8453
USDC_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

# Pricing
PER_QUERY_AMOUNT = "0.10"        # USDC per single query
MONTHLY_AMOUNT = "29.00"         # USDC per month (premium)
MONTHLY_ATOMIC = 29_000_000      # 29 USDC in atomic units (6 decimals)

# Free tier limits
FREE_QUERIES_PER_DAY = 3

# x402 discovery path
WELL_KNOWN_PATH = "/.well-known/x402"

# Payment header names
HEADER_PAY_TO = "X-Payments-Url"
HEADER_AMOUNT = "X-Payment-Amount"
HEADER_RESOURCE = "X-Payment-Resource"

# Base directory (BDE-Stock root)
_BDE_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_BDE_ROOT, 'x402_payments.db')
API_KEYS_PATH = os.path.join(_BDE_ROOT, 'api_keys.json')

# Endpoints that require payment check
PROTECTED_PREFIXES = [
    '/api/snapshot',
    '/api/analyze',
    '/mcp',  # MCP tool calls
]


# ============================================================================
# Database Layer
# ============================================================================

class PaymentDB:
    """SQLite-backed payment tracking. Thread-safe via context manager."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self):
        """Create tables if they don't exist (idempotent)."""
        with self._connect() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS x402_free_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_ip TEXT NOT NULL,
                    date TEXT NOT NULL,
                    usage_count INTEGER DEFAULT 0,
                    UNIQUE(client_ip, date)
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS x402_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tx_hash TEXT,
                    payer_address TEXT,
                    amount_usd REAL,
                    amount_atomic INTEGER,
                    network TEXT,
                    endpoint TEXT,
                    verified_at TEXT DEFAULT (datetime('now')),
                    status TEXT DEFAULT 'verified',
                    facilitator_response TEXT
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_x402_ip_date ON x402_free_usage(client_ip, date)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_x402_payer ON x402_payments(payer_address)')
            conn.commit()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_free_usage(self, client_ip: str) -> int:
        """Get today's usage count for an IP."""
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        with self._connect() as conn:
            row = conn.execute(
                'SELECT usage_count FROM x402_free_usage WHERE client_ip = ? AND date = ?',
                (client_ip, today)
            ).fetchone()
            return row['usage_count'] if row else 0

    def increment_free_usage(self, client_ip: str) -> int:
        """Increment usage count. Returns new count. Creates row if needed."""
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        with self._connect() as conn:
            # Use INSERT OR REPLACE for atomic upsert
            conn.execute('''
                INSERT INTO x402_free_usage (client_ip, date, usage_count)
                VALUES (?, ?, 1)
                ON CONFLICT(client_ip, date)
                DO UPDATE SET usage_count = usage_count + 1
            ''', (client_ip, today))
            # Return the new count
            row = conn.execute(
                'SELECT usage_count FROM x402_free_usage WHERE client_ip = ? AND date = ?',
                (client_ip, today)
            ).fetchone()
            return row['usage_count'] if row else 1

    def check_payment(self, payer_address: str) -> dict | None:
        """Check if an address has a valid payment."""
        with self._connect() as conn:
            row = conn.execute('''
                SELECT * FROM x402_payments
                WHERE payer_address = ? AND status = 'verified'
                ORDER BY verified_at DESC LIMIT 1
            ''', (payer_address,)).fetchone()
            if row:
                return dict(row)
            return None

    def record_payment(self, tx_hash: str, payer_address: str, amount_usd: float,
                       amount_atomic: int, network: str = 'Base',
                       endpoint: str = '', status: str = 'verified'):
        """Record a verified payment."""
        with self._connect() as conn:
            conn.execute('''
                INSERT INTO x402_payments
                (tx_hash, payer_address, amount_usd, amount_atomic, network, endpoint, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (tx_hash, payer_address, amount_usd, amount_atomic, network, endpoint, status))

    def get_premium_usage_today(self, payer_address: str) -> int:
        """Get today's query count for a premium user (for stats)."""
        # Premium is unlimited, but we track for analytics
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        with self._connect() as conn:
            row = conn.execute('''
                SELECT COUNT(*) as cnt FROM x402_payments
                WHERE payer_address = ? AND DATE(verified_at) = ?
            ''', (payer_address, today)).fetchone()
            return row['cnt'] if row else 0


# Singleton instance
payment_db = PaymentDB()


# ============================================================================
# API Key Manager (shared with bde_api.py KeyManager)
# ============================================================================

class X402KeyVerifier:
    """Verifies API keys against the bcrypt-hashed store in api_keys.json."""

    def __init__(self, keys_path: str = API_KEYS_PATH):
        self.keys_path = keys_path
        self._keys = {}
        self._load_time = 0
        self._reload_if_needed()

    def _reload_if_needed(self):
        """Reload keys file if modified."""
        try:
            mtime = os.path.getmtime(self.keys_path)
            if mtime > self._load_time:
                self._load()
                self._load_time = mtime
        except OSError:
            pass

    def _load(self):
        try:
            with open(self.keys_path, 'r') as f:
                data = json.load(f)
            self._keys = {}
            for item in data:
                if 'key' in item:
                    self._keys[item['key']] = item
                elif 'key_prefix' in item:
                    self._keys[item['key_prefix']] = item
        except (FileNotFoundError, json.JSONDecodeError):
            self._keys = {}

    def verify(self, api_key: str) -> str | None:
        """
        Verify an API key. Returns tier ('premium', 'institutional') or None.
        Supports both plaintext keys and bcrypt-hashed keys.
        """
        if not api_key:
            return None
        self._reload_if_needed()

        # Mode 1: Direct plaintext match
        entry = self._keys.get(api_key)
        if entry and entry.get('active'):
            return entry.get('tier', 'premium')

        # Mode 2: Prefix match + bcrypt verification
        for prefix, item in self._keys.items():
            if api_key.startswith(prefix) and item.get('active') and 'key_hash' in item:
                try:
                    import bcrypt
                    if bcrypt.checkpw(api_key.encode(), item['key_hash'].encode()):
                        return item.get('tier', 'premium')
                except Exception:
                    pass
        return None


# Singleton
key_verifier = X402KeyVerifier()


# ============================================================================
# Payment Check Logic
# ============================================================================

def get_client_ip(headers: dict, client_host: str = None) -> str:
    """Extract client IP from headers, respecting Cloudflare proxy."""
    cf_ip = headers.get('cf-connecting-ip', '')
    if cf_ip:
        return cf_ip.strip()
    forwarded = headers.get('x-forwarded-for', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return client_host or 'unknown'


def check_payment_status(api_key: str, client_ip: str) -> dict:
    """
    Check payment status for a request.

    Returns:
        dict with:
          - allowed: bool
          - tier: 'premium' | 'institutional' | 'free' | 'none'
          - remaining: int (free queries remaining today, -1 if unlimited)
          - reason: str (why blocked, if not allowed)
    """
    # 1. Check API Key (premium/institutional)
    if api_key:
        tier = key_verifier.verify(api_key)
        if tier and tier in ('premium', 'institutional'):
            return {
                'allowed': True,
                'tier': tier,
                'remaining': -1,  # unlimited
                'reason': None,
            }

    # 2. Check free tier quota
    usage = payment_db.get_free_usage(client_ip)
    remaining = FREE_QUERIES_PER_DAY - usage

    if remaining > 0:
        return {
            'allowed': True,
            'tier': 'free',
            'remaining': remaining,
            'reason': None,
        }

    # 3. Over quota, no valid key → 402
    return {
        'allowed': False,
        'tier': 'none',
        'remaining': 0,
        'reason': (
            f"Free tier limit reached ({FREE_QUERIES_PER_DAY} queries/day). "
            f"Upgrade to Premium for unlimited access."
        ),
    }


def consume_free_query(client_ip: str):
    """Record that a free-tier query was consumed."""
    payment_db.increment_free_usage(client_ip)


def build_402_response_body(resource_path: str = '') -> dict:
    """Build the JSON body for a 402 Payment Required response."""
    return {
        "error": "Payment required",
        "protocol": "x402",
        "message": (
            f"Free tier limit reached ({FREE_QUERIES_PER_DAY} queries/day). "
            "To continue, either: "
            "(1) Send USDC on Base chain for per-query payment, or "
            "(2) Subscribe to Premium for unlimited access."
        ),
        "payment_options": {
            "per_query": {
                "amount": f"{PER_QUERY_AMOUNT} USDC",
                "description": "Pay per API call",
                "instructions": "Send USDC on Base chain and include tx_hash in X-Payment header",
            },
            "monthly": {
                "amount": f"{MONTHLY_AMOUNT} USDC",
                "description": "Premium subscription - unlimited queries",
                "instructions": "Send USDC to activate API key, then use X-API-Key header",
            },
        },
        "payment_details": {
            "recipient": WALLET_ADDRESS,
            "chain": CHAIN_NAME,
            "chain_id": CHAIN_ID,
            "token": "USDC",
            "contract": USDC_CONTRACT,
            "amounts": {
                "per_query": PER_QUERY_AMOUNT,
                "monthly": MONTHLY_AMOUNT,
            },
        },
        "free_tier": {
            "queries_per_day": FREE_QUERIES_PER_DAY,
            "reset": "daily at 00:00 UTC",
        },
        "discovery_url": WELL_KNOWN_PATH,
    }


def build_402_headers(resource_path: str = '') -> dict:
    """Build headers for a 402 response."""
    return {
        HEADER_PAY_TO: f"https://bde-score.app{WELL_KNOWN_PATH}",
        HEADER_AMOUNT: f"USDC {PER_QUERY_AMOUNT} per query or USDC {MONTHLY_AMOUNT} per month",
        HEADER_RESOURCE: resource_path,
    }


# ============================================================================
# ASGI Middleware (for FastAPI / Starlette)
# ============================================================================

try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse

    class X402PaymentMiddleware(BaseHTTPMiddleware):
        """
        ASGI middleware that enforces x402 payment protocol.

        Checks (in order):
        1. Is the endpoint protected? (matches PROTECTED_PREFIXES)
        2. Does the request have a valid API Key? → allow unlimited
        3. Is the IP within free tier quota? → allow + consume
        4. Otherwise → 402 Payment Required

        For MCP Server integration, also checks /mcp path with
        method-level granularity (introspection = free, tool calls = paid).
        """

        def __init__(self, app, protected_prefixes: list = None):
            super().__init__(app)
            self.protected_prefixes = protected_prefixes or PROTECTED_PREFIXES

        def _is_protected(self, path: str) -> bool:
            """Check if the request path requires payment."""
            return any(path.startswith(prefix) for prefix in self.protected_prefixes)

        async def dispatch(self, request: Request, call_next):
            path = request.url.path

            # Skip payment check for non-protected paths
            if not self._is_protected(path):
                return await call_next(request)

            # Extract client IP and API key
            client_ip = get_client_ip(dict(request.headers), 
                                       request.client.host if request.client else None)
            api_key = request.headers.get('x-api-key', '')

            # Check payment status
            status = check_payment_status(api_key, client_ip)

            if status['allowed']:
                # Consume a free query if on free tier
                if status['tier'] == 'free':
                    consume_free_query(client_ip)

                # Process the request, add payment status headers
                response = await call_next(request)
                response.headers['X-Payment-Tier'] = status['tier']
                if status['remaining'] >= 0:
                    response.headers['X-Payment-Remaining'] = str(status['remaining'])
                return response

            # 402 Payment Required
            body = build_402_response_body(path)
            headers = build_402_headers(path)
            return JSONResponse(
                content=body,
                status_code=402,
                headers=headers,
            )

    HAS_STARLETTE = True

except ImportError:
    HAS_STARLETTE = False
    X402PaymentMiddleware = None


# ============================================================================
# Helper functions for direct use in route handlers
# ============================================================================

def check_and_respond_402(request_headers: dict, client_ip: str, resource_path: str):
    """
    Non-middleware payment check for use inside route handlers.
    Returns None if allowed, or (status_code, body, headers) tuple if 402.
    """
    api_key = request_headers.get('x-api-key', '')
    status = check_payment_status(api_key, client_ip)

    if status['allowed']:
        if status['tier'] == 'free':
            consume_free_query(client_ip)
        return None  # allowed

    body = build_402_response_body(resource_path)
    headers = build_402_headers(resource_path)
    return (402, body, headers)


def get_payment_summary(client_ip: str, api_key: str = '') -> dict:
    """Get payment/usage summary for a client."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    free_usage = payment_db.get_free_usage(client_ip)
    
    tier = 'free'
    if api_key:
        verified_tier = key_verifier.verify(api_key)
        if verified_tier:
            tier = verified_tier

    return {
        'tier': tier,
        'date': today,
        'free_usage_today': free_usage,
        'free_limit': FREE_QUERIES_PER_DAY,
        'remaining_today': max(0, FREE_QUERIES_PER_DAY - free_usage) if tier == 'free' else -1,
        'is_premium': tier in ('premium', 'institutional'),
    }


# ============================================================================
# Module-level exports
# ============================================================================

__all__ = [
    # Classes
    'PaymentDB', 'X402KeyVerifier', 'X402PaymentMiddleware',
    # Singletons
    'payment_db', 'key_verifier',
    # Functions
    'check_payment_status', 'consume_free_query',
    'build_402_response_body', 'build_402_headers',
    'get_client_ip', 'check_and_respond_402', 'get_payment_summary',
    # Config constants
    'WALLET_ADDRESS', 'CHAIN_NAME', 'CHAIN_ID', 'USDC_CONTRACT',
    'PER_QUERY_AMOUNT', 'MONTHLY_AMOUNT', 'MONTHLY_ATOMIC',
    'FREE_QUERIES_PER_DAY', 'WELL_KNOWN_PATH',
    'PROTECTED_PREFIXES',
]
