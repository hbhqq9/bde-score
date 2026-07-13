"""
Self-register BDE Score as the first agent in its own registry.
Bootstrap the network from within.
"""

import json
import time
import sys
import urllib.request

REGISTRY_BASE = "http://localhost:8892"
BDE_SCORE_API = "https://bathroom-ebooks-isa-accommodation.trycloudflare.com"
BDE_SCORE_MCP = "https://tex-adequate-date-facing.trycloudflare.com"

def self_register():
    payload = {
        "name": "BDE Score Financial Analysis Engine",
        "description": "Comprehensive stock analysis with EU AI Act Art.50 compliance. 6 MCP tools: stock analysis, compliance check, risk assessment. Agent-native discovery via .well-known protocols.",
        "primary_endpoint": BDE_SCORE_API + "/.well-known/agent.json",
        "category": ["finance", "stock-analysis", "compliance", "mcp", "ai-agent"],
        "protocols": {
            "a2a": BDE_SCORE_API + "/.well-known/agent.json",
            "mcp": BDE_SCORE_MCP + "/.well-known/mcp.json",
            "openai_plugin": BDE_SCORE_API + "/.well-known/ai-plugin.json"
        },
        "capabilities": [
            "stock-analysis",
            "compliance-check",
            "risk-assessment",
            "eu-ai-act-art50",
            "mcp-tools",
            "agent-discovery"
        ],
        "contact": {
            "github": "https://github.com/hbhqq9/bde-score",
            "registry": "https://github.com/hbhqq9/bde-score/tree/master/agent-registry"
        }
    }

    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        REGISTRY_BASE + "/api/v1/agents/register",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    sys.stdout.write("[Bootstrap] Registering BDE Score as founding agent...\n")
    sys.stdout.write("[Bootstrap] Endpoint: " + payload["primary_endpoint"] + "\n")
    sys.stdout.flush()

    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        sys.stdout.write("[Bootstrap] Status: " + str(resp.status) + "\n")
        sys.stdout.write("[Bootstrap] Agent ID: " + data.get("agent_id", "?") + "\n")
        sys.stdout.write("[Bootstrap] Message: " + data.get("message", "?") + "\n")
        sys.stdout.flush()
        return data
    except urllib.error.HTTPError as e:
        sys.stdout.write("[Bootstrap] HTTP Error: " + str(e.code) + "\n")
        sys.stdout.write("[Bootstrap] Body: " + e.read().decode() + "\n")
        sys.stdout.flush()
        return None
    except Exception as e:
        sys.stdout.write("[Bootstrap] Error: " + str(e) + "\n")
        sys.stdout.flush()
        return None


def verify():
    sys.stdout.write("\n[Bootstrap] Verifying...\n")
    sys.stdout.flush()
    try:
        resp = urllib.request.urlopen(REGISTRY_BASE + "/api/v1/stats", timeout=5)
        data = json.loads(resp.read())
        sys.stdout.write("[Bootstrap] Total agents: " + str(data["total_agents"]) + "\n")
        sys.stdout.write("[Bootstrap] Healthy: " + str(data["healthy_agents"]) + "\n")
        sys.stdout.write("[Bootstrap] Categories: " + json.dumps(data["categories"]) + "\n")
        sys.stdout.flush()
    except Exception as e:
        sys.stdout.write("[Bootstrap] Verify error: " + str(e) + "\n")
        sys.stdout.flush()


if __name__ == '__main__':
    sys.stdout.write("=" * 50 + "\n")
    sys.stdout.write("BDE Score Agent Registry - Bootstrap\n")
    sys.stdout.write("=" * 50 + "\n")
    sys.stdout.flush()

    # Wait for registry
    for i in range(5):
        try:
            urllib.request.urlopen(REGISTRY_BASE + "/api/v1/stats", timeout=2)
            break
        except Exception:
            sys.stdout.write("[Bootstrap] Waiting for registry... (" + str(i+1) + "/5)\n")
            sys.stdout.flush()
            time.sleep(2)
    else:
        sys.stdout.write("[Bootstrap] Registry not reachable.\n")
        sys.stdout.flush()
        sys.exit(1)

    result = self_register()
    if result:
        verify()
        sys.stdout.write("\n[Bootstrap] Network bootstrap complete!\n")
        sys.stdout.flush()
    else:
        sys.stdout.write("[Bootstrap] Registration failed.\n")
        sys.stdout.flush()
