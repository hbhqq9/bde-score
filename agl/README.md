# AGL — Accountability-Governance Layer

> **Layer ⑦** of the Enterprise AI OS architecture.  
> Implements drift-aware receipt schema for AI governance transparency.

## Overview

AGL provides an **immutable, append-only receipt system** that records every
AI decision as a tamper-evident governance receipt. The system implements
the **drift-aware extension** proposed by hegu-1 in
[enterprise-ai-os-architecture Issue #1](https://github.com/enterprise-ai-os-architecture).

### Core Principle

> **Never rewrite old receipts.** Append invalidation/supersession events so
> that current compliance state becomes a **derived view** over immutable
> receipts + current policy.

## Receipt Schema v2.0 — 6+3 Field Structure

### Base Fields (1–6): Enterprise AI OS Primitive Mapping

| # | Field | Enterprise AI OS Primitive | Description |
|---|-------|--------------------------|-------------|
| 1 | `disclosure` | Policy-facing transparency event | AI system info, compliance markers, disclaimers |
| 2 | `identity` | Agent/runtime principal | Who/what made the decision |
| 3 | `policy_decision` | Governance decision receipt | What governance rule was applied |
| 4 | `execution` | Action/tool receipt | What tool/action was executed |
| 5 | `outcome` | Result/evidence state | What was the result |
| 6 | `on_chain` | Tamper-evidence anchor | SHA-256 hash chain / proof-of-existence |

### Drift-Aware Fields (7–9): New in v2.0

| # | Field | Sub-fields | Purpose |
|---|-------|-----------|---------|
| 7 | `policy_version` | `rule_set_id`, `schema_version`, `compliance_framework`, `effective_from` | Exact compliance/rule set at decision time |
| 8 | `validity_window` | `valid_from`, `valid_until`, `context` | Temporal scope of decision validity |
| 9 | `supersedes_or_invalidates` | `receipt_id`, `reason`, `superseded_by` | Links to events that change receipt status |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                 MCP Tool Invocation                  │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│          wrap_with_receipt() (mcp_http_server.py)    │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │  disclosure  │  │   identity   │  │  policy    │ │
│  │  (Field 1)   │  │  (Field 2)   │  │ decision   │ │
│  └─────────────┘  └──────────────┘  │ (Field 3)  │ │
│  ┌─────────────┐  ┌──────────────┐  └────────────┘ │
│  │  execution   │  │   outcome    │  ┌────────────┐ │
│  │  (Field 4)   │  │  (Field 5)   │  │  on_chain  │ │
│  └─────────────┘  └──────────────┘  │ (Field 6)  │ │
│  ┌─────────────┐  ┌──────────────┐  └────────────┘ │
│  │   policy    │  │  validity    │  ┌────────────┐ │
│  │  _version   │  │  _window     │  │ supersede  │ │
│  │  (Field 7)  │  │  (Field 8)   │  │ (Field 9)  │ │
│  └─────────────┘  └──────────────┘  └────────────┘ │
└──────────────────┬──────────────────────────────────┘
                   │ append()
                   ▼
┌─────────────────────────────────────────────────────┐
│           ReceiptStore (append-only)                  │
│                                                      │
│  InMemoryReceiptStore  │  JsonFileReceiptStore       │
│  (volatile, testing)   │  (persistent, .jsonl)       │
│                                                      │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────────┐ │
│  │receipt1│→│receipt2│→│receipt3│→│invalidation  │ │
│  │ active │ │ active │ │supersed│→│event (new)   │ │
│  └────────┘ └────────┘ └────────┘ └──────────────┘ │
│                                                      │
│  current_compliance_view() → derived read-only view  │
└─────────────────────────────────────────────────────┘
```

## Files

| File | Description |
|------|-------------|
| `receipt_schema_v2.py` | Receipt v2.0 data model (dataclasses + factory) |
| `receipt_store.py` | Append-only receipt store (in-memory + JSON file) |
| `receipt_schema_v2.schema.json` | JSON Schema for validation |
| `README.md` | This file |

## Usage

### Creating a Receipt

```python
from agl.receipt_schema_v2 import create_receipt, PolicyVersion, ValidityWindow

receipt = create_receipt(
    disclosure={"generated_by": "My AI System v1.0", "ai_system": True},
    identity={"agent_name": "my-agent", "agent_version": "1.0"},
    policy_decision={"rule": "my-rule", "decision": "approve"},
    execution={"tool": "my_tool", "parameters": {"input": "data"}},
    outcome={"status": "completed", "result": {"score": 85}},
)
```

### Using the Store

```python
from agl.receipt_store import InMemoryReceiptStore, JsonFileReceiptStore

# In-memory (testing)
store = InMemoryReceiptStore()
rid = store.append(receipt)

# Persistent (production)
store = JsonFileReceiptStore("data/receipts.jsonl")
rid = store.append(receipt)

# Invalidation (appends new event, never modifies original)
inv_id = store.invalidate(rid, "Policy updated to v2")

# Current compliance view (derived, read-only)
view = store.current_compliance_view()
```

### MCP Integration

Every MCP tool call automatically generates a receipt:

```python
# In mcp_http_server.py
return wrap_with_receipt("get_bde_score", {"market": "US"}, result_json)
```

The response includes:
```json
{
  "ai_system_info": {
    "generated_by": "BDE Score AI Assessment Engine v1.0.2",
    "receipt_id": "01945a7b-...",
    "receipt_schema_version": "2.0.0",
    "policy_version": {
      "rule_set_id": "eu-ai-act-art50-2026-01",
      "schema_version": "2.0.0",
      "compliance_framework": "EU AI Act Art.50"
    }
  }
}
```

## Drift Detection Workflow

```
Time →
─────────────────────────────────────────────────────────
t0: Receipt R1 created (policy_version: art50-2024-01)
t1: Policy updates to art50-2026-01
t2: Receipt R2 created (policy_version: art50-2026-01)
    → R1 is NOT modified; it still records what was true at t0
t3: Invalidation event I1 appended
    → I1 references R1, reason: "superseded by new policy"
    → R1.status → SUPERSEDED (logical, data unchanged)
t4: current_compliance_view()
    → Returns only R2 as active
    → R1 excluded (superseded)
    → I1 excluded (it's an event, not a decision)
```

## Testing

```bash
cd BDE-Stock
python -m pytest tests/test_receipt_schema.py -v
```

## References

- [enterprise-ai-os-architecture Issue #1](https://github.com/enterprise-ai-os-architecture) — hegu-1 feedback
- [EU AI Act Art.50](https://hbhqq9.github.io/bde-score/compliance.html) — Compliance documentation
- BDE Score MCP Server — `mcp/mcp_http_server.py`
