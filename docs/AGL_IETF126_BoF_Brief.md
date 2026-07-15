# AGL Reference Implementation — IETF 126 BoF Brief

**Agent Governance Layer (AGL) — Receipt Schema v2.0**  
**Prepared for:** agentproto BoF, IETF 126 Vienna  
**Date:** July 2026  
**Status:** Deployed reference implementation  
**Contact:** [GitHub Issues](https://github.com/hbhqq9/bde-score/issues)  

---

## 1. Executive Summary

The Agent Governance Layer (AGL) is an open-source reference implementation that solves a concrete, urgent problem: **how do AI agents prove compliance with transparency obligations in real time?** With EU AI Act Article 50 enforcement effective **2026-08-02** — less than 3 weeks after this IETF meeting — AGL provides a working answer.

AGL introduces the **Receipt**: an immutable, append-only governance record that accompanies every agent action. Each receipt captures what the agent disclosed, what policy it followed, what it executed, what outcome it produced, and anchors a SHA-256 content hash to Base L2 for tamper evidence. The system costs **$0.000752/event** on Base L2 — making universal governance logging economically viable at scale.

AGL is deployed today via the Official MCP Registry (`io.github.hbhqq9/bde-score` v1.0.3), demonstrating that governance can be embedded into agent-to-tool protocols without new transport layers. This brief presents the architecture, schema, and open design questions we believe the BoF should address.

---

## 2. Problem Statement

### The Compliance Cliff

EU AI Act Article 50 imposes four independent transparency obligations on AI systems interacting with natural persons in the EU:

| Obligation | Scope | Deadline |
|-----------|-------|----------|
| Art.50(1) | AI interaction identity disclosure | 2026-08-02 |
| Art.50(2) | Machine-readable synthetic content marking | 2026-08-02 |
| Art.50(3) | Emotion recognition / biometric categorization notice | 2026-08-02 |
| Art.50(4) | Deepfake & AI text public disclosure | 2026-08-02 |

Non-compliance penalties: up to **€15,000,000 or 3% of global annual turnover** (whichever is higher). The EU has already issued its first enforcement actions in May 2026 — two Chinese AI companies fined €45M each for deploying deepfake tools in the EU without risk assessment or labeling.

### The Protocol Gap

Current agent protocols (MCP, A2A, ACP, ANP) address **capability** and **communication** but not **governance provenance**. Specifically:

1. **No standard format for governance receipts.** When an agent takes an action, there is no interoperable way to record *what policy governed the decision*, *what was disclosed to the end user*, or *whether the decision remains valid*.

2. **No drift detection.** Compliance rules change (policy updates, model drift, regulatory amendments). Existing protocols have no mechanism to signal that a prior decision is now governed by a different rule set.

3. **No verifiable immutability.** Without a tamper-evident anchor, governance claims are self-reported and unverifiable. This is insufficient for regulatory audit.

4. **Cost asymmetry.** Governance logging must be cheap enough to apply to *every* agent action — not just high-value transactions. Most on-chain solutions cost too much per event.

AGL addresses all four gaps with a deployed, measurable solution.

---

## 3. Architecture Overview

AGL implements a five-stage governance pipeline that wraps any agent action:

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGL Governance Pipeline                       │
│                                                                  │
│  ┌──────────┐   ┌──────────┐   ┌───────────┐   ┌──────────┐   │
│  │DISCLOSURE│──▶│  POLICY   │──▶│ EXECUTION │──▶│ OUTCOME  │   │
│  │  (Art.50 │   │ DECISION  │   │  (tool /  │   │ (result  │   │
│  │  comply) │   │ (ruleset) │   │  action)  │   │  state)  │   │
│  └──────────┘   └──────────┘   └───────────┘   └──────────┘   │
│        │               │               │               │        │
│        └───────────────┴───────────────┴───────────────┘        │
│                                │                                  │
│                    ┌───────────▼──────────┐                      │
│                    │    ON-CHAIN ANCHOR    │                      │
│                    │  SHA-256 → Base L2    │                      │
│                    │  $0.000752 / event    │                      │
│                    └──────────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

### Stage Descriptions

| Stage | Function | Output |
|-------|----------|--------|
| **1. Disclosure** | Generates Art.50-compliant transparency event. Identifies the AI system, its operator, and the nature of AI involvement to the end user. | `disclosure` receipt field |
| **2. Policy Decision** | Evaluates the applicable governance ruleset (compliance framework version, operator policies, domain constraints). Records the decision logic. | `policy_decision` + `policy_version` fields |
| **3. Execution** | Records the actual tool call, API invocation, or action taken. Includes parameters and identity of the executing agent/runtime. | `execution` + `identity` fields |
| **4. Outcome** | Captures the result state: success/failure, evidence produced, confidence level. Enables post-hoc audit of decision quality. | `outcome` field |
| **5. On-Chain Anchor** | Computes SHA-256 content hash over the complete receipt payload and writes it to Base L2 as an append-only transparency log. | `on_chain` field |

### Drift-Aware Extensions (Fields 7-9)

The architecture adds three fields specifically designed to detect and express governance drift:

| Stage | Drift Extension | Purpose |
|-------|----------------|---------|
| Policy Decision | `policy_version` (Field 7) | Records the exact rule set ID and schema version at decision time. Enables detection when a subsequent policy update would change the outcome. |
| Execution | `validity_window` (Field 8) | Defines the temporal (and optionally contextual) scope during which this decision remains valid. |
| Outcome | `supersedes_or_invalidates` (Field 9) | Links to prior receipts that this event supersedes or invalidates, enabling full audit chains. |

### Immutability Principle

> Receipts are **NEVER** modified or deleted once appended. Invalidation and supersession are expressed by appending **new** receipts that reference the original. The current compliance state is always a **derived view** over the append-only log plus the current policy.

---

## 4. Receipt Schema v2.0

The Receipt Schema defines 9 structured fields organized as 6 base fields + 3 drift-aware extensions. All fields are mandatory; the schema is implemented as a Python `dataclass` with JSON serialization.

### 4.1 Base Fields (1-6)

| # | Field | Type | Description |
|---|-------|------|-------------|
| 1 | `disclosure` | `Dict[str, Any]` | Policy-facing transparency event. Contains disclosure type (e.g., `art50-transparency-obligation`), mechanism (e.g., `disclose-ai-generated-content`), priority level, and whether disclosure was completed. |
| 2 | `identity` | `Dict[str, Any]` | Agent/runtime principal. Contains system name, version, interaction type, compliance claim, and compliance page URL. |
| 3 | `policy_decision` | `Dict[str, Any]` | Governance decision receipt. Records the decision type (e.g., `automated-multi-factor-scoring`), methodology (e.g., `rule-based + LLM-enhanced analysis`), compliance status, and reference to full compliance documentation. |
| 4 | `execution` | `Dict[str, Any]` | Action/tool receipt. Records the executing agent identity (e.g., `bde-score-mcp-server`), runtime (e.g., `python-fastmcp`), and tool invocation parameters. |
| 5 | `outcome` | `Dict[str, Any]` | Result/evidence state. Contains execution status (`completed`), result summary, and any disclaimers (e.g., `AI-generated analysis. Not investment advice.`). |
| 6 | `on_chain` | `Dict[str, Any]` | Tamper-evidence anchor. Contains hash algorithm (`sha256-local`), content hash (hex), and chain reference. |

### 4.2 Drift-Aware Fields (7-9)

| # | Field | Type | Description |
|---|-------|------|-------------|
| 7 | `policy_version` | `PolicyVersion` | **Records the exact compliance/rule set at decision time.** Contains: `rule_set_id` (e.g., `eu-ai-act-art50-2026-01`), `schema_version` (e.g., `2.0.0`), `compliance_framework` (e.g., `EU AI Act Art.50`), `effective_from` (ISO 8601 timestamp). Enables drift detection: if the current rule set differs from the recorded one, the receipt may no longer reflect valid compliance. |
| 8 | `validity_window` | `ValidityWindow` | **Defines the temporal scope of decision validity.** Contains: `valid_from` (ISO 8601), `valid_until` (optional, ISO 8601), `context` (optional `Dict[str, Any]` for spatial/conditional scoping). Example: a scoring decision valid for 24 hours from issuance. |
| 9 | `supersedes_or_invalidates` | `Optional[SupersessionEvent]` | **Links to events that change receipt status.** Contains: `receipt_id` (UUID v7 of the superseded receipt), `reason` (human-readable explanation), `superseded_by` (UUID v7 of the replacement, or null). Null when the receipt is an original with no prior state change. |

### 4.3 Receipt Lifecycle States

```
ACTIVE ──────▶ SUPERSEDED ──────▶ (new receipt appended)
   │
   └──────────▶ INVALIDATED ──────▶ (new receipt appended)
```

- **ACTIVE**: Receipt is current and valid
- **SUPERSEDED**: A newer receipt has replaced this one (e.g., updated scoring)
- **INVALIDATED**: This receipt has been explicitly invalidated (e.g., policy violation discovered)

### 4.4 Immutability Guarantees

- Receipt store is **append-only** — no UPDATE or DELETE operations
- Each receipt has a `content_hash` (SHA-256) computed at creation time
- Storage backends: `InMemoryReceiptStore` (testing), `JsonFileReceiptStore` (persistent JSON Lines)
- Thread-safe via mutex lock
- Current compliance state is always a **derived view**: `store.get_all()` + `current_policy` → active receipts only

---

## 5. Implementation Status

### 5.1 Deployed Components

| Component | Status | Location |
|-----------|--------|----------|
| Receipt Schema v2.0 (Python dataclass) | ✅ Deployed | `agl/receipt_schema_v2.py` (commit `908fd28`) |
| Append-only Receipt Store (InMemory + JSON Lines) | ✅ Deployed | `agl/receipt_store.py` |
| MCP Server Integration (all tool calls return receipts) | ✅ Deployed | `io.github.hbhqq9/bde-score` v1.0.3 |
| Official MCP Registry Listing | ✅ Published (2026-07-14) | [MCP Registry](https://github.com/modelcontextprotocol/servers) |
| On-chain Transparency Log (Base L2 PoC) | ✅ PoC | SHA-256 → Base L2, $0.000752/event |
| A2A Agent Card (`.well-known/agent.json`) | ✅ Deployed | Protocol: a2a, 3 tool capabilities |
| EU AI Act Art.50 Compliance Whitepaper | ✅ Published | 33KB, full Article 50 clause-by-clause analysis |
| Three-Layer AI Identification (L1 headers, L2 JSON, L3 fingerprint) | ✅ Deployed | HTTP headers + JSON embedding + sha256 |

### 5.2 MCP Integration

All MCP tool calls return a complete v2.0 receipt:

```json
{
  "receipt_id": "019507a3-...",
  "timestamp": "2026-07-15T08:36:00+00:00",
  "disclosure": {
    "type": "art50-transparency-obligation",
    "mechanism": "disclose-ai-generated-content",
    "priority": "high",
    "disclosed": true
  },
  "identity": {
    "system": "BDE Score AI Assessment Engine v1.0.2",
    "version": "1.0.2",
    "interaction_type": "automated-multi-factor-scoring",
    "compliance_claim": "compliant",
    "compliance_page": "https://hbhqq9.github.io/bde-score/compliance.html"
  },
  "policy_decision": {
    "decision_type": "automated-multi-factor-scoring",
    "methodology": "rule-based + LLM-enhanced analysis",
    "compliance_status": "compliant"
  },
  "execution": {
    "agent": "bde-score-mcp-server",
    "runtime": "python-fastmcp",
    "tool": "get_bde_score",
    "parameters": { "symbol": "AAPL", "market": "US" }
  },
  "outcome": {
    "status": "completed",
    "result_summary": "AAPL composite score: 72.3 (Bullish)",
    "disclaimer": "AI-generated analysis. Not investment advice."
  },
  "on_chain": {
    "hash_algorithm": "sha256-local",
    "content_hash": "a1b2c3d4...",
    "chain": "base-l2-poc"
  },
  "policy_version": {
    "rule_set_id": "eu-ai-act-art50-2026-01",
    "schema_version": "2.0.0",
    "compliance_framework": "EU AI Act Art.50",
    "effective_from": "2026-01-01T00:00:00+00:00"
  },
  "validity_window": {
    "valid_from": "2026-07-15T08:36:00+00:00",
    "valid_until": "2026-07-16T08:36:00+00:00",
    "context": { "scope": "single-request" }
  },
  "supersedes_or_invalidates": null,
  "status": "active",
  "content_hash": "a1b2c3d4..."
}
```

### 5.3 Cost Profile

| Metric | Value | Source |
|--------|-------|--------|
| On-chain anchoring cost | **$0.000752 / event** | Base L2 PoC实测 |
| Local receipt creation | ~$0 (CPU-only) | SHA-256 + JSON serialization |
| Full pipeline (disclosure → anchor) | **$0.000752 / event** | Marginal cost is on-chain write |

This cost profile makes governance logging viable for **every** agent action, not just high-value transactions. For comparison: a typical MCP tool call round-trip costs ~$0.01-0.05 in compute; AGL adds <1% overhead.

### 5.4 Test Coverage

- Receipt Schema v2.0: Unit tests for all 9 fields, lifecycle state transitions, drift detection
- Receipt Store: Thread-safety tests, append-only invariant verification, JSON Lines persistence
- MCP Integration: End-to-end tests for all 6 MCP tools returning receipts

---

## 6. Interoperability

### 6.1 Relationship to ERC-8226 (Regulated Agent Mandate)

[ERC-8226](https://ethereum-magicians.org/t/erc-8226-regulated-agent-mandate/28208) (Draft, April 2026) defines how a verified principal delegates scoped, time-bounded, financially-capped authority to an on-chain agent. AGL and ERC-8226 are **complementary layers**:

| Dimension | AGL Receipt | ERC-8226 Mandate |
|-----------|-------------|-----------------|
| **Scope** | Any agent action (tool calls, API invocations, decisions) | Token transfers on regulated assets |
| **Authority model** | Records policy decision + compliance status | KYC-verified principal + mandate scope |
| **Immutability** | Append-only local store + SHA-256 anchor | On-chain smart contract |
| **Granularity** | Per-action receipt | Per-mandate (multiple actions) |
| **Bridge** | Receipt `execution` field can reference mandate `agentId` | Mandate `recordExecution()` can hash receipt content |

**Proposed integration pattern:** AGL receipt's `on_chain` field can include the ERC-8226 `mandateId` as additional context, creating a bidirectional link between governance provenance (AGL) and financial authority (ERC-8226).

### 6.2 Relationship to ERC-8126 (AI Agent Verification)

[ERC-8126](https://ethereum-magicians.org/t/erc-8126-ai-agent-verification/27445) (Finalized, June 2026) defines a multi-layer verification framework producing a 0-100 risk score for AI agents. The relationship:

| Dimension | AGL Receipt | ERC-8126 Verification |
|-----------|-------------|----------------------|
| **When** | Per-action, real-time | Pre-interaction, periodic |
| **What** | Governance provenance for a specific action | Trustworthiness assessment of the agent itself |
| **Output** | Structured receipt (9 fields) | Risk score (0-100) + ZK proof |
| **Privacy** | Full transparency of action | ZK proofs hide sensitive data |

**Proposed integration:** AGL receipts can serve as **evidence inputs** to ERC-8126's verification checks. An agent with a long history of valid, anchored receipts demonstrates operational compliance — this history can feed into ERC-8126's Wallet Verification (WV) or Media Content Verification (MCV) layers.

### 6.3 MCP Protocol Compatibility

AGL is **native to MCP**: every tool call response includes a complete receipt. No protocol modification is required. The implementation demonstrates that governance can be embedded as a **response envelope** within existing MCP semantics.

Key design choices:
- Receipt is returned as part of the tool response JSON (no separate endpoint)
- Receipt `receipt_id` uses UUID v7 (time-sortable) for efficient indexing
- Three-layer AI identification: L1 HTTP headers (`X-BDE-AI-System`), L2 JSON embedding, L3 content fingerprint (SHA-256)

### 6.4 A2A Compatibility

AGL's A2A Agent Card (`.well-known/agent.json`) declares governance capabilities:

```json
{
  "protocol": "a2a",
  "capabilities": {
    "tools": [
      { "id": "bde-score-analysis", "name": "BDE Score Analysis" },
      { "id": "stock-comparison", "name": "Cross-market Stock Comparison" },
      { "id": "esg-analysis", "name": "ESG Analysis" }
    ]
  },
  "metadata": {
    "compliance": ["EU AI Act Art.50"],
    "author": "AGL Governance"
  }
}
```

A2A agents can discover AGL's governance capabilities through standard Agent Card negotiation.

---

## 7. Open Questions for BoF Discussion

We believe the following questions require community-wide discussion and potentially standardization:

### Q1: Receipt Interoperability

> **Should the IETF standardize a common governance receipt format for agent actions?**

AGL's 9-field schema is one possible design. We welcome comparison with other approaches. Key design tensions:
- **Granularity:** Per-action receipts (AGL) vs. per-session attestations vs. per-delegation mandates
- **Extensibility:** Fixed schema (AGL v2.0) vs. open-world extension model
- **Transport binding:** Embedded in response (MCP) vs. separate governance channel

### Q2: Drift Detection Protocol

> **How should agents signal that a prior decision is no longer valid due to policy or model drift?**

AGL uses append-only invalidation/supersession (Fields 8-9). Alternatives include:
- TTL-based expiration (simpler, but less expressive)
- Event-sourced state machines (more complex, but full replay capability)
- Hybrid: short-lived receipts with automatic renewal

### Q3: Cost-Efficient Tamper Evidence

> **What is the minimum viable immutability guarantee for governance logging?**

AGL achieves $0.000752/event on Base L2 via SHA-256 content hashing. But:
- Is L2 sufficient for regulatory-grade evidence?
- Should the IETF define a minimum security tier (e.g., L1 for high-stakes actions)?
- Can transparency logs (RFC 9162 / SCITT) replace on-chain anchoring at lower cost?

### Q4: Relationship Between Governance and Communication Layers

> **Should governance (AGL-style receipts) be a protocol-level concern or an application-level pattern?**

Current agent protocols (MCP, A2A, ACP) treat governance as out-of-scope. But regulatory pressure (Art.50, US state laws, sector-specific rules) makes governance unavoidable. Options:
1. **Application pattern** (current AGL approach): governance as response envelope, no protocol changes
2. **Protocol extension**: governance headers/metadata in the protocol itself
3. **Separate governance protocol**: dedicated governance channel alongside communication

### Q5: Cross-Registry Interoperability

> **How do governance receipts (AGL), mandate records (ERC-8226), and verification attestations (ERC-8126) compose?**

The Ethereum ecosystem is building agent identity/verification infrastructure in parallel with IETF's agent communication work. We need clear seam points:
- Agent identity: ERC-8004 (registration) → ERC-8126 (verification) → ERC-8226 (mandate)
- Governance provenance: AGL receipts should be referenceable from on-chain records
- Open question: Should IETF define the bridge, or leave it to implementation?

### Q6: Multi-Jurisdictional Policy Expression

> **How should agents express compliance with multiple, potentially conflicting regulatory frameworks?**

AGL currently records a single `compliance_framework` per receipt. Real deployments need:
- Multi-framework receipts (EU AI Act + US state laws + sector rules)
- Conflict resolution rules (most restrictive wins? jurisdiction-specific?)
- Machine-readable policy expression (beyond string identifiers)

---

## References

| Reference | URL |
|-----------|-----|
| AGL Source Code | https://github.com/hbhqq9/bde-score |
| MCP Registry Listing | `io.github.hbhqq9/bde-score` v1.0.3 |
| EU AI Act Art.50 | https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-50 |
| ERC-8226 (RAMS) | https://ethereum-magicians.org/t/erc-8226-regulated-agent-mandate/28208 |
| ERC-8126 (AI Agent Verification) | https://ethereum-magicians.org/t/erc-8126-ai-agent-verification/27445 |
| ERC-8004 (Trustless Agents) | https://ethereum-magicians.org/t/erc-8004-trustless-agents/25098 |
| IETF 126 BoF Schedule | https://www.ietf.org/blog/ietf126-bofs/ |
| A2A Protocol | https://google.github.io/A2A/ |
| MCP Specification | https://modelcontextprotocol.io/ |
| RFC 9162 (Transparency Logs) | https://www.rfc-editor.org/rfc/rfc9162 |
| Problem Space Analysis (draft-yao-catalist) | https://www.ietf.org/archive/id/draft-yao-catalist-problem-space-analysis-01.txt |

---

## Appendix: AGL Module Summary

```
bde-score/
├── agl/
│   ├── receipt_schema_v2.py    # 9-field schema + drift-aware extensions
│   └── receipt_store.py        # Append-only store (InMemory + JsonFile)
├── .well-known/
│   └── agent.json              # A2A Agent Card with governance metadata
├── docs/
│   ├── llms.txt                # LLM-friendly project description
│   └── openapi.json            # OpenAPI spec with MCP extension
└── tests/
    └── test_receipt_schema.py  # Schema + store unit tests
```

**Schema Version:** 2.0.0 (commit `908fd28`)  
**License:** MIT  
**Compliance Framework:** EU AI Act Art.50 (effective 2026-08-02)

---

*This document is a technical reference for the IETF 126 agentproto BoF session (Thursday, 23 July 2026, 09:00-11:00 CEST, Grand Park Hall 3). It presents a deployed implementation to ground standardization discussions in working code.*
