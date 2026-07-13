"""
BDE Score™ Agent Registry v0.1.0 (MVP)
Agent-native, zero-gatekeeper discovery service
Standard library only - no external dependencies needed.
"""

import json
import os
import hashlib
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone
import urllib.request

REGISTRY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agents.json')
_lock = threading.Lock()

def load_registry():
    if os.path.exists(REGISTRY_FILE):
        with open(REGISTRY_FILE, 'r') as f:
            return json.load(f)
    return {"agents": {}, "metadata": {"created": datetime.now(timezone.utc).isoformat(), "version": "0.1.0"}}

def save_registry(data):
    with open(REGISTRY_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def verify_endpoint(url, timeout=5):
    try:
        req = urllib.request.Request(url, method='GET')
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status == 200
    except Exception:
        return False

def generate_agent_id(name, endpoint):
    raw = f"{name}:{endpoint}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]

def now_iso():
    return datetime.now(timezone.utc).isoformat()


class RegistryHandler(BaseHTTPRequestHandler):

    def _json_response(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        if length:
            return json.loads(self.rfile.read(length))
        return None

    def _parse_path(self):
        parsed = urlparse(self.path)
        return parsed.path, parse_qs(parsed.query)

    def do_GET(self):
        path, qs = self._parse_path()

        if path == '/api/v1/agents':
            self._handle_list_agents(qs)
        elif path.startswith('/api/v1/agents/') and path.endswith('/health'):
            agent_id = path.split('/')[4]
            self._handle_agent_health(agent_id)
        elif path.startswith('/api/v1/agents/'):
            agent_id = path.split('/')[4]
            self._handle_get_agent(agent_id)
        elif path == '/api/v1/search':
            self._handle_search(qs)
        elif path == '/api/v1/stats':
            self._handle_stats()
        elif path == '/.well-known/registry.json' or path == '/api/v1/.well-known/registry.json':
            self._handle_registry_discovery()
        elif path == '/':
            self._handle_root()
        else:
            self._json_response(404, {"error": "Not found"})

    def do_POST(self):
        path, qs = self._parse_path()
        if path == '/api/v1/agents/register':
            self._handle_register()
        else:
            self._json_response(404, {"error": "Not found"})

    def do_DELETE(self):
        path, qs = self._parse_path()
        if path.startswith('/api/v1/agents/'):
            agent_id = path.split('/')[4]
            self._handle_deregister(agent_id)
        else:
            self._json_response(404, {"error": "Not found"})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def _handle_root(self):
        self._json_response(200, {
            "service": "BDE Score Agent Registry",
            "version": "0.1.0",
            "description": "Agent-native, zero-gatekeeper discovery service",
            "philosophy": "From being listed to building the network",
            "endpoints": {
                "POST /api/v1/agents/register": "Register a new agent",
                "GET /api/v1/agents": "List all agents (filter: category, capability, protocol, q)",
                "GET /api/v1/agents/{id}": "Get agent details",
                "DELETE /api/v1/agents/{id}": "Deregister agent",
                "GET /api/v1/agents/{id}/health": "Check agent health",
                "GET /api/v1/search?q=": "Search agents",
                "GET /api/v1/stats": "Registry statistics",
                "GET /.well-known/registry.json": "Registry discovery"
            }
        })

    def _handle_register(self):
        data = self._read_body()
        if not data:
            return self._json_response(400, {"error": "No JSON body"})

        required = ['name', 'description', 'primary_endpoint', 'category']
        missing = [f for f in required if not data.get(f)]
        if missing:
            return self._json_response(400, {"error": "Missing: " + ", ".join(missing)})

        endpoint = data['primary_endpoint']
        healthy = verify_endpoint(endpoint)
        if not healthy:
            return self._json_response(422, {
                "error": f"Endpoint not reachable: {endpoint}",
                "hint": "Ensure your .well-known endpoint returns HTTP 200"
            })

        agent_id = generate_agent_id(data['name'], endpoint)

        with _lock:
            registry = load_registry()
            agent_record = {
                "id": agent_id,
                "name": data['name'],
                "description": data['description'],
                "primary_endpoint": endpoint,
                "category": data['category'] if isinstance(data['category'], list) else [data['category']],
                "protocols": data.get('protocols', {}),
                "capabilities": data.get('capabilities', []),
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
            "message": f"Agent '{data['name']}' registered",
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
            return self._json_response(404, {"error": f"Agent '{agent_id}' not found"})
        self._json_response(200, agent)

    def _handle_deregister(self, agent_id):
        with _lock:
            registry = load_registry()
            if agent_id not in registry['agents']:
                return self._json_response(404, {"error": f"Agent '{agent_id}' not found"})
            name = registry['agents'][agent_id]['name']
            del registry['agents'][agent_id]
            save_registry(registry)
        self._json_response(200, {"status": "deregistered", "message": f"Agent '{name}' removed"})

    def _handle_agent_health(self, agent_id):
        with _lock:
            registry = load_registry()
            agent = registry['agents'].get(agent_id)
            if not agent:
                return self._json_response(404, {"error": f"Agent '{agent_id}' not found"})

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
        self._json_response(200, {"query": q, "count": len(scored), "results": [a for _, a in scored]})

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
            "categories": cats,
            "registry_version": registry['metadata']['version'],
            "created": registry['metadata']['created']
        })

    def _handle_registry_discovery(self):
        self._json_response(200, {
            "name": "BDE Score Agent Registry",
            "version": "0.1.0",
            "description": "Agent-native, zero-gatekeeper discovery service",
            "endpoints": {
                "register": "/api/v1/agents/register",
                "discover": "/api/v1/agents",
                "search": "/api/v1/search",
                "health": "/api/v1/agents/{id}/health",
                "stats": "/api/v1/stats"
            },
            "registration_policy": "auto",
            "verification": "endpoint_reachability",
            "philosophy": "From being listed to building the network"
        })

    def log_message(self, format, *args):
        pass  # Suppress default logging


if __name__ == '__main__':
    port = 8892
    server = HTTPServer(('0.0.0.0', port), RegistryHandler)
    import sys
    sys.stdout.write(f"=" * 60 + "\n")
    sys.stdout.write("BDE Score Agent Registry v0.1.0 (MVP)\n")
    sys.stdout.write("Agent-native, zero-gatekeeper discovery service\n")
    sys.stdout.write(f"Listening on port {port}\n")
    sys.stdout.write("Vision: From being listed to building the network\n")
    sys.stdout.write("=" * 60 + "\n")
    sys.stdout.flush()
    server.serve_forever()
