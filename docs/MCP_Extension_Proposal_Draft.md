# MCP Extension Proposal: Agent Governance Layer (AGL)

> **Target**: MCP 2026-07-28 Specification Release  
> **Proposal Type**: Official MCP Extension  
> **Date**: 2026-07-15  
> **Status**: Draft for Submission  

---

## 1. Extension Overview

**Name**: `io.github.hbhqq9.bde-score.agl`  
**Type**: MCP Governance Extension  
**Version**: 1.0.0  
**Compatibility**: MCP 2026-07-28 (stateless core + extension framework)  

### One-Line Summary
AGL enables MCP servers to generate tamper-evident governance Receipts for every tool call at $0.000752/event on Base L2, providing verifiable compliance evidence for EU AI Act Art.50, China's Agent Governance Rules, and enterprise audit requirements.

---

## 2. Motivation

### 2.1 The Problem
MCP (Model Context Protocol) solves how AI agents discover and invoke tools. But it does NOT solve:
- **How do agents prove they followed regulatory rules when invoking tools?**
- **How do enterprises audit what their agents did, decided, and disclosed?**
- **How do regulators verify compliance claims without trusting self-reported logs?**

With EU AI Act Art.50 enforcing transparency obligations on 2026-08-02 (18 days away) and China's Agent Governance Rules effective today (2026-07-15), this gap is becoming a regulatory liability.

### 2.2 Why MCP Extensions Are the Right Place
The MCP 2026-07-28 specification introduces:
- **Stateless core**: Each request is independent → Receipt can anchor per-request
- **Extension framework**: reverse-DNS identifiers + capability negotiation → AGL registers as official extension
- **Explicit handle pattern**: Receipt hash can be passed as an opaque handle
- **W3C Trace Context propagation**: Receipt chain hash aligns with distributed tracing

AGL is designed to be a governance extension, not a competing transport layer. It composes with any MCP server.

---

## 3. Technical Architecture

### 3.1 Extension Registration
```
Extension ID: io.github.hbhqq9.bde-score.agl
Capabilities:
  - governance.receipt.generate
  - governance.receipt.verify  
  - governance.policy.check
  - governance.audit.query
```

### 3.2 New MCP Tools (when extension is enabled)

#### `agl_generate_receipt`
Generates a governance Receipt for a tool invocation.

**Input**:
```json
{
  "tool_name": "string — name of the MCP tool being invoked",
  "tool_input_hash": "string — SHA-256 of tool input parameters",
  "principal": "string — identity of the agent/user invoking",
  "policy_ref": "string — governance policy version applied",
  "disclosure": "object — Art.50 transparency disclosure content"
}
```

**Output**:
```json
{
  "receipt_id": "string — unique receipt identifier",
  "chain_tx_hash": "string — Base L2 transaction hash",
  "content_fingerprint": "string — SHA-256 of governed content",
  "timestamp": "ISO8601 — block timestamp",
  "cost_eth": "0.0000003 — actual gas cost (~$0.000752)",
  "verify_url": "string — public verification endpoint"
}
```

#### `agl_verify_receipt`
Verifies a Receipt's authenticity against the chain.

**Input**:
```json
{
  "receipt_id": "string"
}
```

**Output**:
```json
{
  "valid": true,
  "chain_confirmed": true,
  "block_number": 12345678,
  "content_intact": true,
  "policy_applied": "v2.0-drift-aware"
}
```

#### `agl_check_policy`
Checks whether a proposed action complies with a governance policy.

**Input**:
```json
{
  "action": "string — description of proposed action",
  "principal": "string — agent/user identity",
  "context": "object — additional context parameters"
}
```

**Output**:
```json
{
  "eligible": true,
  "reason": "COMPLIANT",
  "validity_window": {
    "valid_from": "ISO8601",
    "valid_until": "ISO8601"
  },
  "policy_version": "2.0"
}
```

### 3.3 Integration Model
```
┌─────────────────────────────────────────────────────┐
│  MCP Client (AI Agent)                              │
│                                                     │
│  1. Check policy: agl_check_policy(action)          │
│  2. If eligible → invoke tool normally              │
│  3. Generate receipt: agl_generate_receipt(...)      │
│  4. Include receipt in response to caller           │
│                                                     │
│  ┌───────────┐    ┌────────────┐    ┌───────────┐  │
│  │MCP Server │───→│AGL Extension│───→│ Base L2   │  │
│  │(any tool) │    │(governance) │    │(Receipt)  │  │
│  └───────────┘    └────────────┘    └───────────┘  │
└─────────────────────────────────────────────────────┘
```

### 3.4 Cost Model
- **Per-receipt cost**: $0.000752 (PoC-measured on Base L2)
- **No subscription fee**: Extension is MIT-licensed open source
- **No API key required**: Uses public Base L2 RPC endpoints
- **Optional premium**: Self-hosted aggregator for high-volume enterprise use

---

## 4. Compliance Mapping

### 4.1 EU AI Act Art.50 Transparency Obligations
| Art.50 Requirement | AGL Mechanism |
|---|---|
| Disclose AI system involvement | `disclosure` field in Receipt |
| Disclose decision logic | `policy_ref` + `content_fingerprint` |
| Tamper-evident records | SHA-256 anchored on Base L2 |
| Verifiable by regulators | `agl_verify_receipt` public endpoint |

### 4.2 China Agent Governance Rules (2026-07-15)
| Regulation Requirement | AGL Mechanism |
|---|---|
| Three-tier decision authorization | `agl_check_policy` with principal levels |
| High-risk domain filing | Receipt as filing evidence |
| Behavior control (guardrails) | Policy enforcement before tool invocation |
| Audit trail | Immutable chain-anchored Receipts |

### 4.3 Enterprise Audit Requirements
| Audit Need | AGL Mechanism |
|---|---|
| Who did what, when | Receipt: principal + timestamp + tool_name |
| Was it authorized | `policy_ref` + `eligible` status |
| Can records be tampered | Base L2 immutability |
| Cost of compliance | $0.000752 per operation |

---

## 5. Implementation Status

### 5.1 Deployed Components
- **MCP Server**: https://tex-adequate-date-facing.trycloudflare.com/mcp (auth-gated)
- **BDE API**: https://bathroom-ebooks-isa-accommodation.trycloudflare.com
- **Agent Registry**: https://appropriate-movie-skin-formats.trycloudflare.com (MCP Registry v1.0.3)
- **GitHub**: https://github.com/hbhqq9/bde-score (MIT license)
- **Base L2 Contract**: `0x0d52e20A8F3c9d91E8f650c2FC193DB983B5B6c7` (Sourcify Full Match verified)

### 5.2 Standards Interoperability
- **ERC-8226**: IComplianceProvider interface mapping complete (off-chain governance companion)
- **MCP Registry**: Listed with schema 2025-12-11
- **x402 Protocol**: USDC payment integration for paid API tiers
- **W3C Trace Context**: Receipt chain hash compatible with distributed tracing

---

## 6. Open Source & Community

- **License**: MIT
- **Repository**: https://github.com/hbhqq9/bde-score
- **Registry**: Official MCP Registry (`io.github.hbhqq9/bde-score`)
- **Pending Listings**: awesome-mcp-servers (90.6k⭐), awesome-ai-agents/e2b (9k⭐), best-of-python

---

## 7. Submission Checklist

- [x] Extension ID follows reverse-DNS format
- [x] Compatible with MCP 2026-07-28 stateless core
- [x] Tool definitions follow MCP tool schema
- [x] Open source (MIT license)
- [x] Deployed and functional
- [x] Cost model documented
- [x] Compliance mapping provided
- [ ] Submit to MCP specification repository
- [ ] Community feedback period (2 weeks)
- [ ] Formal review at MCP working group

---

## 8. Next Steps

1. **2026-07-15**: Finalize this proposal draft
2. **2026-07-18-24**: Present at IETF 126 agentproto BoF (gather feedback)
3. **2026-07-28**: Submit formal extension proposal aligned with new MCP spec release
4. **2026-08-02**: EU AI Act Art.50 enforcement begins (urgency driver)
5. **2026-08-15**: Community feedback period closes, iterate based on input

---

*This proposal is authored by the BDE Score project team. AGL is an open-source, community-driven governance layer for AI agent protocols. We welcome collaboration and feedback.*
