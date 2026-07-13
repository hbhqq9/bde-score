"""
BDE Score™ Agent Registry v0.2.0 (Security Hardened)
Agent-native, zero-gatekeeper discovery service
Standard library only - no external dependencies needed.

Security: v4.1 compliant - SSRF protection + auth + rate limiting + input validation
"""

import json
import os
import hashlib
import threading
import ipaddress
import socket
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone
import urllib.request

REGISTRY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agents.json')
_lock = threading.Lock()

# === Security Constitution v4.1 - Rate Limiting ===
_rate_limiter = {}  # {ip: [timestamps]}
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_READ = 30    # requests per window
RATE_LIMIT_WRITE = 5    # requests per window (register/deregister)
MAX_TRACKED_IPS = 10000

# === Security Constitution v4.1 - Authentication ===
REGISTRY_API_KEY = os.environ.get('REGISTRY_API_KEY', '')

# === Security Constitution v4.1 - Input Validation ===
MAX_BODY_SIZE = 1_048_576  # 1MB
MAX_AGENTS = 1000
MAX_FIELD_LENGTHS = {
    'name': 100,
    'description': 500,
    'primary_endpoint': 500,
}

# === Security Constitution v4.1 - CORS ===
ALLOWED_ORIGINS = [
    'https://hbhqq9.github.io',
    'https://bde-score.com',
]

# === Security Constitution v4.1 - SSRF Protection ===
ALLOWED_URL_SCHEMES = ('https://',)
BLOCKED_IP_RANGES = [
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('169.254.0.0/16'),  # Link-local / AWS metadata
    ipaddress.ip_network('0.0.0.0/8'),
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('fe80::/10'),
    ipaddress.ip_network('fc00::/7'),
]

def load_registry():
    if os.path.exists(REGISTRY_FILE):
        with open(REGISTRY_FILE, 'r') as f:
            return json.load(f)
    return {"agents": {}, "metadata": {"created": datetime.now(timezone.utc).isoformat(), "version": "0.2.0"}}

def save_registry(data):
    with open(REGISTRY_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def validate_url(url):
    """Security Constitution v4.1 - SSRF Protection.
    Validates URL is safe to fetch: HTTPS only, no private/metadata IPs.
    """
    if not url or not isinstance(url, str):
        return False, "Invalid URL"
    
    # Scheme check
    if not any(url.startswith(s) for s in ALLOWED_URL_SCHEMES):
        return False, "Only HTTPS URLs allowed"
    
    # Length check
    if len(url) > MAX_FIELD_LENGTHS['primary_endpoint']:
        return False, "URL too long"
    
    # Parse and extract hostname
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False, "No hostname in URL"
        
        # Block obvious internal hostnames
        blocked_hosts = ['localhost', 'metadata.google.internal', '169.254.169.254']
        if hostname.lower() in blocked_hosts:
            return False, "Blocked hostname"
        
        # DNS resolution check
        try:
            resolved_ips = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            for family, type_, proto, canonname, sockaddr in resolved_ips:
                ip = ipaddress.ip_address(sockaddr[0])
                for network in BLOCKED_IP_RANGES:
                    if ip in network:
                        return False, f"URL resolves to blocked IP range"
        except socket.gaierror:
            return False, "Cannot resolve hostname"
        
        return True, "OK"
    except Exception:
        return False, "Invalid URL format"

def verify_endpoint(url, timeout=5):
    """Verify endpoint reachability with SSRF protection."""
    safe, msg = validate_url(url)
    if not safe:
        return False
    
    try:
        req = urllib.request.Request(url, method='GET')
        req.add_header('User-Agent', 'BDE-Score-Registry/0.2.0')
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status == 200
    except Exception:
        return False

def generate_agent_id(name, endpoint):
    raw = f"{name}:{endpoint}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def check_rate_limit(client_ip: str, is_write: bool = False) -> bool:
    """Security Constitution v4.1 - Rate limiting."""
    now = time.time()
    limit = RATE_LIMIT_WRITE if is_write else RATE_LIMIT_READ
    
    # Cleanup old entries if too many IPs tracked
    if len(_rate_limiter) > MAX_TRACKED_IPS:
        _rate_limiter.clear()
    
    if client_ip not in _rate_limiter:
        _rate_limiter[client_ip] = []
    
    # Remove expired timestamps
    _rate_limiter[client_ip] = [t for t in _rate_limiter[client_ip] if now - t < RATE_LIMIT_WINDOW]
    
    if len(_rate_limiter[client_ip]) >= limit:
        return False
    
    _rate_limiter[client_ip].append(now)
    return True

def check_api_key(handler) -> bool:
    """Security Constitution v4.1 - API Key authentication for write operations."""
    if not REGISTRY_API_KEY:
        return True  # No key configured = open (dev mode, logged)
    
    auth = handler.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[7:].strip() == REGISTRY_API_KEY
    
    # Also check query parameter (for simple agents)
    _, qs = handler._parse_path()
    key = qs.get('api_key', [None])[0]
    if key:
        return key == REGISTRY_API_KEY
    
    return False

def get_client_ip(handler) -> str:
    """Extract client IP, respecting Cloudflare headers."""
    cf_ip = handler.headers.get('CF-Connecting-IP', '')
    if cf_ip:
        return cf_ip
    return handler.client_address[0] if handler.client_address else 'unknown'


class RegistryHandler(BaseHTTPRequestHandler):

    def _json_response(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        # Security headers (Constitution v4.1)
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        # CORS: restricted origins (Constitution v4.1)
        origin = self.headers.get('Origin', '')
        if origin in ALLOWED_ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin)
        # No wildcard CORS
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        # Security Constitution v4.1: Body size limit
        if length > MAX_BODY_SIZE:
            return None  # Will trigger 413
        if length < 0:
            return None
        if length:
            try:
                return json.loads(self.rfile.read(length))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return None
        return None

    def _parse_path(self):
        parsed = urlparse(self.path)
        return parsed.path, parse_qs(parsed.query)

    def _check_rate_and_auth(self, is_write=False):
        """Combined rate limit + auth check. Returns True if request should proceed."""
        client_ip = get_client_ip(self)
        
        if not check_rate_limit(client_ip, is_write):
            self._json_response(429, {
                "error": "Rate limit exceeded",
                "retry_after": RATE_LIMIT_WINDOW
            })
            return False
        
        if is_write and not check_api_key(self):
            self._json_response(401, {
                "error": "Authentication required",
                "hint": "Provide Bearer token in Authorization header"
            })
            return False
        
        return True

    def do_GET(self):
        path, qs = self._parse_path()
        
        # Rate limit check (read)
        client_ip = get_client_ip(self)
        if not check_rate_limit(client_ip, is_write=False):
            return self._json_response(429, {"error": "Rate limit exceeded"})

        if path == '/api/v1/agents':
            self._handle_list_agents(qs)
        elif path.startswith('/api/v1/agents/') and path.endswith('/health'):
            agent_id = path.split('/')[4]
            if not agent_id or len(agent_id) > 64:
                return self._json_response(400, {"error": "Invalid agent_id"})
            self._handle_agent_health(agent_id)
        elif path.startswith('/api/v1/agents/'):
            agent_id = path.split('/')[4]
            if not agent_id or len(agent_id) > 64:
                return self._json_response(400, {"error": "Invalid agent_id"})
            self._handle_get_agent(agent_id)
        elif path == '/api/v1/search':
            self._handle_search(qs)
        elif path == '/api/v1/stats':
            self._handle_stats()
        elif path in ('/.well-known/registry.json', '/api/v1/.well-known/registry.json'):
            self._handle_registry_discovery()
        elif path == '/':
            self._handle_root()
        else:
            self._json_response(404, {"error": "Not found"})

    def do_POST(self):
        path, qs = self._parse_path()
        
        # Body size check
        length = int(self.headers.get('Content-Length', 0))
        if length > MAX_BODY_SIZE:
            return self._json_response(413, {"error": "Request body too large", "max_bytes": MAX_BODY_SIZE})
        
        # Rate limit + auth check (write)
        if not self._check_rate_and_auth(is_write=True):
            return
        
        if path == '/api/v1/agents/register':
            self._handle_register()
        else:
            self._json_response(404, {"error": "Not found"})

    def do_DELETE(self):
        path, qs = self._parse_path()
        
        # Rate limit + auth check (write)
        if not self._check_rate_and_auth(is_write=True):
            return
        
        if path.startswith('/api/v1/agents/'):
            agent_id = path.split('/')[4]
            if not agent_id or len(agent_id) > 64:
                return self._json_response(400, {"error": "Invalid agent_id"})
            self._handle_deregister(agent_id)
        else:
            self._json_response(404, {"error": "Not found"})

    def do_OPTIONS(self):
        self.send_response(200)
        origin = self.headers.get('Origin', '')
        if origin in ALLOWED_ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()

    def _handle_root(self):
        self._json_response(200, {
            "service": "BDE Score Agent Registry",
            "version": "0.2.0",
            "description": "Agent-native, zero-gatekeeper discovery service",
            "philosophy": "From being listed to building the network",
            "security": "SSRF protection + API Key auth + rate limiting",
            "endpoints": {
                "POST /api/v1/agents/register": "Register a new agent (auth required)",
                "GET /api/v1/agents": "List all agents (filter: category, capability, protocol, q)",
                "GET /api/v1/agents/{id}": "Get agent details",
                "DELETE /api/v1/agents/{id}": "Deregister agent (auth required)",
                "GET /api/v1/agents/{id}/health": "Check agent health",
                "GET /api/v1/search?q=": "Search agents",
                "GET /api/v1/stats": "Registry statistics",
                "GET /.well-known/registry.json": "Registry discovery"
            }
        })

    def _handle_register(self):
        data = self._read_body()
        if data is None:
            return self._json_response(400, {"error": "Invalid or missing JSON body"})

        required = ['name', 'description', 'primary_endpoint', 'category']
        missing = [f for f in required if not data.get(f)]
        if missing:
            return self._json_response(400, {"error": "Missing: " + ", ".join(missing)})

        # Security Constitution v4.1: Input length validation
        for field, max_len in MAX_FIELD_LENGTHS.items():
            val = data.get(field, '')
            if isinstance(val, str) and len(val) > max_len:
                return self._json_response(400, {"error": f"Field '{field}' exceeds max length ({max_len})"})

        endpoint = data['primary_endpoint']
        
        # Security Constitution v4.1: SSRF validation
        safe, msg = validate_url(endpoint)
        if not safe:
            return self._json_response(422, {
                "error": f"Endpoint validation failed: {msg}",
                "hint": "URL must be HTTPS, resolve to public IP, not internal/metadata address"
            })
        
        healthy = verify_endpoint(endpoint)
        if not healthy:
            return self._json_response(422, {
                "error": f"Endpoint not reachable: {endpoint}",
                "hint": "Ensure your .well-known endpoint returns HTTP 200"
            })

        agent_id = generate_agent_id(data['name'], endpoint)

        with _lock:
            registry = load_registry()
            
            # Security Constitution v4.1: Capacity limit
            if len(registry['agents']) >= MAX_AGENTS and agent_id not in registry['agents']:
                return self._json_response(507, {
                    "error": "Registry capacity reached",
                    "max_agents": MAX_AGENTS
                })
            
            agent_record = {
                "id": agent_id,
                "name": data['name'][:MAX_FIELD_LENGTHS['name']],
                "description": data['description'][:MAX_FIELD_LENGTHS['description']],
                "primary_endpoint": endpoint[:MAX_FIELD_LENGTHS['primary_endpoint']],
                "category": data['category'] if isinstance(data['category'], list) else [data['category']],
                "protocols": data.get('protocols', {}),
                "capabilities": data.get('capabilities', [])[:20],  # Cap capabilities
                "contact": data.get('contact', {}),
                "registration_time": now_iso(),
                "health_status": "healthy",
                "last_verified": now_iso(),
                "verification_count": 1
            }
            registry['agents'][agent_id] = agent_record
            save_registry(registry)

        self._json_response(201, {
            "status": "registered",
            "agent_id": agent_id,
            "message": f"Agent '{data['name'][:50]}' registered",
            "discover_url": f"/api/v1/agents/{agent_id}",
            "registered_at": agent_record['registration_time']
        })

    def _handle_list_agents(self, qs):
        with _lock:
            registry = load_registry()
        agents = list(registry['agents'].values())

        cat = qs.get('category', [None])[0]
        if cat:
            agents = [a for a in agents if cat.lower() in [c.lower() for c in a.get('category', [])]]

        cap = qs.get('capability', [None])[0]
        if cap:
            agents = [a for a in agents if cap.lower() in [c.lower() for c in a.get('capabilities', [])]]

        proto = qs.get('protocol', [None])[0]
        if proto:
            agents = [a for a in agents if proto.lower() in a.get('protocols', {})]

        q = qs.get('q', [None])[0]
        if q:
            ql = q.lower()
            agents = [a for a in agents if ql in a['name'].lower() or ql in a['description'].lower()]

        self._json_response(200, {
            "count": len(agents),
            "agents": agents,
            "registry_version": registry['metadata']['version'],
            "timestamp": now_iso()
        })

    def _handle_get_agent(self, agent_id):
        with _lock:
            registry = load_registry()
        agent = registry['agents'].get(agent_id)
        if not agent:
            return self._json_response(404, {"error": f"Agent not found"})
        self._json_response(200, agent)

    def _handle_deregister(self, agent_id):
        with _lock:
            registry = load_registry()
            if agent_id not in registry['agents']:
                return self._json_response(404, {"error": f"Agent not found"})
            name = registry['agents'][agent_id]['name']
            del registry['agents'][agent_id]
            save_registry(registry)
        self._json_response(200, {"status": "deregistered", "message": f"Agent removed"})

    def _handle_agent_health(self, agent_id):
        with _lock:
            registry = load_registry()
            agent = registry['agents'].get(agent_id)
            if not agent:
                return self._json_response(404, {"error": f"Agent not found"})

            # SSRF protection: endpoint was validated at registration, re-validate before check
            safe, _ = validate_url(agent['primary_endpoint'])
            if not safe:
                agent['health_status'] = "invalid_endpoint"
                self._json_response(200, {
                    "agent_id": agent_id,
                    "name": agent['name'],
                    "status": "invalid_endpoint",
                    "last_verified": agent.get('last_verified'),
                    "verification_count": agent.get('verification_count', 0)
                })
                save_registry(registry)
                return

            healthy = verify_endpoint(agent['primary_endpoint'])
            agent['health_status'] = "healthy" if healthy else "unreachable"
            agent['last_verified'] = now_iso()
            agent['verification_count'] = agent.get('verification_count', 0) + 1
            save_registry(registry)

        self._json_response(200, {
            "agent_id": agent_id,
            "name": agent['name'],
            "endpoint": agent['primary_endpoint'],
            "status": agent['health_status'],
            "last_verified": agent['last_verified'],
            "verification_count": agent['verification_count']
        })

    def _handle_search(self, qs):
        q = qs.get('q', [''])[0]
        if not q:
            return self._json_response(400, {"error": "Query 'q' required"})
        if len(q) > 200:
            return self._json_response(400, {"error": "Query too long (max 200)"})

        with _lock:
            registry = load_registry()
        agents = list(registry['agents'].values())
        ql = q.lower()
        terms = ql.split()

        scored = []
        for agent in agents:
            score = 0
            searchable = f"{agent['name']} {agent['description']} {' '.join(agent.get('category', []))} {' '.join(agent.get('capabilities', []))}".lower()
            for term in terms:
                if term in searchable:
                    if term in agent['name'].lower():
                        score += 3
                    elif term in [c.lower() for c in agent.get('category', [])]:
                        score += 2
                    else:
                        score += 1
            if score > 0:
                scored.append((score, agent))

        scored.sort(key=lambda x: -x[0])
        self._json_response(200, {"query": q[:100], "count": len(scored), "results": [a for _, a in scored]})

    def _handle_stats(self):
        with _lock:
            registry = load_registry()
        agents = list(registry['agents'].values())
        cats = {}
        for a in agents:
            for c in a.get('category', []):
                cats[c] = cats.get(c, 0) + 1
        self._json_response(200, {
            "total_agents": len(agents),
            "healthy_agents": sum(1 for a in agents if a.get('health_status') == 'healthy'),
            "max_capacity": MAX_AGENTS,
            "categories": cats,
            "registry_version": registry['metadata']['version'],
            "created": registry['metadata']['created']
        })

    def _handle_registry_discovery(self):
        self._json_response(200, {
            "name": "BDE Score Agent Registry",
            "version": "0.2.0",
            "description": "Agent-native, zero-gatekeeper discovery service",
            "security": "SSRF protection + API Key auth + rate limiting + input validation",
            "endpoints": {
                "register": "/api/v1/agents/register",
                "discover": "/api/v1/agents",
                "search": "/api/v1/search",
                "health": "/api/v1/agents/{id}/health",
                "stats": "/api/v1/stats"
            },
            "registration_policy": "auto",
            "verification": "endpoint_reachability + ssrf_validation",
            "authentication": "Bearer token for write operations",
            "rate_limits": {
                "read": f"{RATE_LIMIT_READ}/min/IP",
                "write": f"{RATE_LIMIT_WRITE}/min/IP"
            },
            "philosophy": "From being listed to building the network"
        })

    def log_message(self, format, *args):
        pass  # Suppress default logging


if __name__ == '__main__':
    port = 8892
    server = HTTPServer(('127.0.0.1', port), RegistryHandler)  # Bind to localhost only (Constitution v4.1)
    import sys
    sys.stdout.write(f"=" * 60 + "\n")
    sys.stdout.write("BDE Score Agent Registry v0.2.0 (Security Hardened)\n")
    sys.stdout.write("Agent-native, zero-gatekeeper discovery service\n")
    sys.stdout.write(f"Listening on 127.0.0.1:{port} (localhost only)\n")
    sys.stdout.write("Security: SSRF protection + API Key + Rate Limiting\n")
    sys.stdout.write("Vision: From being listed to building the network\n")
    sys.stdout.write("=" * 60 + "\n")
    sys.stdout.flush()
    server.serve_forever()
