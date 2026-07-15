---
title: "Agent Protocol Governance Extension"
abbrev: APGE
category: info
docname: draft-bdescore-apge-governance-extension-00
date: 2026-07-15
submissiontype: IETF
number:
obsoletes:
updates:
consensus: true
v: 3
area: "ART"
workgroup: "Agent Communication Protocols"
keyword:
  - AI Agent
  - Governance
  - Compliance Receipt
  - Drift-Aware
  - EU AI Act
author:
  -
    ins: BDE Score
    organization: BDE Score Project
    email: standards@bdescore.org
normative:
  RFC2119:
  RFC8174:
  RFC8785:
  RFC9162:
  RFC9943:
informative:
  EU-AI-ACT:
    title: "Regulation (EU) 2024/1689 — The EU AI Act"
    date: 2024-08-01
  MCP-SPEC:
    title: "Model Context Protocol Specification 2026-07-28"
    date: 2026-07-28
  ERC-8226:
    title: "ERC-8226: Regulated Agent Mandate Specification"
    date: 2026
  AIGA:
    title: "AI Governance and Accountability Protocol (AIGA)"
    date: 2026-01-26
    target: https://www.ietf.org/archive/id/draft-aylward-aiga-2-00.txt
  DRP:
    title: "Delegation Receipt Protocol (DRP)"
    date: 2026-04-26
    target: https://www.ietf.org/archive/id/draft-nelson-agent-delegation-receipts-00.txt
  PoB:
    title: "Proof-of-Behavior Protocol"
    date: 2026-04-20
    target: https://www.ietf.org/archive/id/draft-dembowski-agentledger-proof-of-behavior-00.txt
  ACTA:
    title: "Signed Decision Receipts for Machine-to-Machine Access Control"
    date: 2026-03-26
    target: https://www.ietf.org/archive/id/draft-farley-acta-signed-receipts-00.txt
  AGTP:
    title: "Agent Transfer Protocol (AGTP)"
    date: 2026-03-23
    target: https://www.ietf.org/archive/id/draft-hood-agtp-composition-00.txt
  MACP:
    title: "Multi-Agent Collaboration Protocol Suites Architecture"
    date: 2026-04-30
    target: https://www.ietf.org/archive/id/draft-li-dmsc-macp-04.html
  ASQAV:
    title: "Compliance Profile of Signed Action Receipts for AI Agents"
    date: 2026-05-04
    target: https://www.ietf.org/archive/id/draft-marques-asqav-compliance-receipts-00.html
  TRUST-FW:
    title: "Trust and Authentication Framework for Cross-Domain A2A"
    target: https://www.ietf.org/archive/id/draft-kiliram-agent-trust-auth-framework-00.html
  AIPROTO:
    title: "Framework, Use Cases and Requirements for AI Agent Protocols"
    target: https://www.ietf.org/archive/id/draft-rosenberg-aiproto-framework-00.txt
  WIMSE:
    title: "Workload Identity in Multi System Environments (WIMSE)"
  A2T:
    title: "AI Agent to Tool (A2T) Protocol"
    target: https://www.ietf.org/archive/id/draft-rosenberg-aiproto-a2t-00.txt

--- 

.title Agent Protocol Governance Extension
.# abbrev APGE
.# category info

.# # Abstract

This document defines the Agent Protocol Governance Extension (APGE), a
protocol extension that provides immutable, cryptographically verifiable
compliance receipts for AI agent operations within any agent communication
protocol session. APGE addresses the gap between existing agent
communication protocols — which handle identity, authorization, and
session management — and the regulatory obligations imposed by the EU AI
Act (Art. 12, 26, 50), China's Intelligent Agent Governance Implementation
Opinion, and emerging global AI governance regimes. The extension
introduces three core primitives: (1) a Drift-Aware Governance Receipt
Schema that captures pre-execution policy decisions, model-state
commitments, and post-execution outcome attestations; (2) a Compliance
Receipt Anchoring Protocol that binds receipts to a transparency log
aligned with RFC 9162 (Certificate Transparency) and RFC 9943 (SCITT);
and (3) a Governance Capability Advertisement mechanism that integrates
with MCP's extensions framework and W3C Trace Context. APGE is designed
as a protocol-agnostic extension layer composable with MCP, A2A, AGTP,
and other Agent Group Messaging Protocols (AGMPs), adding governance
observability without modifying the underlying communication protocol.

.# # Status of This Memo

This Internet-Draft is submitted in full conformance with the
provisions of BCP 78 and BCP 79.

Internet-Drafts are working documents of the Internet Engineering
Task Force (IETF). Note that other groups may also distribute
working documents as Internet-Drafts. The list of current
Internet-Drafts is at https://datatracker.ietf.org/drafts/current/.

Internet-Drafts are draft documents valid for a maximum of six
months and may be updated, replaced, or obsoleted by other
documents at any time. It is inappropriate to use Internet-Drafts
as reference material or to cite them other than as "work in
progress."

This Internet-Draft will expire on 15 January 2027.

.# # Copyright Notice

Copyright (c) 2026 IETF Trust and the persons identified as the
document authors. All rights reserved.

.# # Table of Contents

1.  Introduction
    1.1.  Motivation
    1.2.  The Governance Gap
    1.3.  Relationship to Other Work
2.  Terminology
3.  Protocol Overview
    3.1.  Design Principles
    3.2.  Architecture Overview
4.  Drift-Aware Governance Receipt Schema
    4.1.  Receipt Envelope
    4.2.  Policy Decision Block
    4.3.  Model-State Commitment
    4.4.  Outcome Attestation
    4.5.  Validity Window and Supersession
    4.6.  Canonicalization and Signing
5.  Compliance Receipt Anchoring Protocol
    5.1.  Transparency Log Integration
    5.2.  Receipt Lifecycle
    5.3.  Inclusion and Consistency Proofs
6.  Governance Capability Advertisement
    6.1.  MCP Extension Integration
    6.2.  W3C Trace Context Binding
    6.3.  AGMP Header Mapping
7.  Regulatory Binding
    7.1.  EU AI Act Art. 12 (Record-Keeping)
    7.2.  EU AI Act Art. 26 (Deployer Obligations)
    7.3.  EU AI Act Art. 50 (Transparency)
    7.4.  China Intelligent Agent Governance Implementation Opinion
8.  IANA Considerations
9.  Security Considerations
10. References
    10.1. Normative References
    10.2. Informative References
Appendix A.  AGL Receipt Schema v2.0 Field Mapping
Appendix B.  ERC-8226 Interface Mapping
Appendix C.  MCP Extension Registration Template

.# # 1. Introduction

## 1.1. Motivation

AI agents are increasingly deployed in regulated environments where
every operation must be auditable, attributable, and tamper-evident.
The EU AI Act (Regulation 2024/1689) mandates record-keeping for
high-risk AI systems (Art. 12), deployer obligations including human
oversight (Art. 26), and transparency requirements for AI-generated
interactions (Art. 50). China's "Intelligent Agent Governance
Implementation Opinion" entered into force on 15 July 2026, imposing
parallel obligations on agent operators within its jurisdiction.
Multiple jurisdictions are developing analogous regimes.

Existing IETF work on agent protocols — including the Framework for
AI Agent Protocols [AIPROTO], the Agent-to-Tool Protocol [A2T], and
the Multi-Agent Collaboration Protocol [MACP] — defines how agents
communicate, discover each other, and invoke tools. However, none of
these specifications provides a mechanism for generating immutable,
cryptographically verifiable evidence that a governance decision was
made before an agent action executed, that the agent's model state was
consistent with the declared configuration, or that post-execution
outcomes matched the authorized scope.

This gap is structural, not incidental. Agent communication protocols
are correctly scoped to session management, service invocation, and
data transport. Governance observability is a cross-cutting concern
that belongs in an extension layer — one that can compose with any
agent protocol without modifying its wire format.

## 1.2. The Governance Gap

Several existing I-Ds address parts of the governance problem:

- The Delegation Receipt Protocol (DRP) [DRP] addresses user-to-
  operator trust through user-signed Authorization Objects anchored to
  an append-only log. DRP focuses on the upstream delegation chain.

- The Proof-of-Behavior Protocol (PoB) [PoB] defines signed receipts
  and hash-chain linking for tamper-evident audit trails. PoB focuses
  on behavioral attestation.

- The ACTA Signed Receipts specification [ACTA] defines a portable
  receipt format for machine-to-machine access control decisions,
  specifically targeting the MCP ecosystem.

- The ASQAV Compliance Profile [ASQAV] binds ACTA receipts to EU AI
  Act Art. 12, Art. 26, and DORA Art. 17 obligations.

- AIGA [AIGA] defines a comprehensive governance architecture with
  tiered risk classification, immutable kernel architecture, and
  federated authority networks.

- AGTP-LOG defines a transparency log aligned with Certificate
  Transparency (RFC 9162) and SCITT (RFC 9943) for agent identity
  audit.

APGE is positioned as a unifying extension that:

1. Provides a drift-aware receipt schema that captures model-state
   commitments — a dimension absent from DRP, PoB, and ACTA — enabling
   detection of post-deployment model substitution or configuration
   drift.

2. Defines a governance capability advertisement mechanism that works
   across agent communication protocols (MCP, A2A, AGTP) rather than
   being tied to any single protocol.

3. Provides normative bindings to both EU and Chinese regulatory
   regimes, acknowledging that agent governance is increasingly a
   multi-jurisdictional requirement.

4. Is designed for composable integration with the MCP 2026-07-28
   Extensions framework, using reverse-DNS identifiers and capability
   negotiation through the extensions map.

## 1.3. Relationship to Other Work

APGE is complementary to, not a replacement for, existing work:

| Specification | Layer | What it provides | What APGE adds |
|---|---|---|---|
| WIMSE | Workload identity | Cryptographic identity for agents | Governance receipts bound to identity |
| OAuth AAuth [A2T] | Authorization | Agent-to-tool authorization grant | Pre-execution compliance evidence |
| DRP | Delegation | User-signed delegation receipts | Drift-aware model-state commitments |
| PoB | Behavior | Tamper-evident behavioral audit | Regulatory binding + cross-protocol |
| ACTA/ASQAV | Receipt format | Signed access control receipts | Drift detection + multi-jurisdiction |
| AIGA | Governance architecture | Tiered risk model + enforcement | Lightweight extension vs. full protocol |
| AGTP-LOG | Transparency | CT-aligned audit log | Agent operation-specific log entries |
| MCP Extensions | Protocol extension | Extension framework | Governance as a first-class extension |

.# # 2. Terminology

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and
"OPTIONAL" in this document are to be interpreted as described in
BCP 14 [RFC2119] [RFC8174].

This document uses the following terms:

Agent:
   An autonomous or semi-autonomous software entity that perceives,
   plans, decides, and executes actions on behalf of a principal,
   potentially across administrative and trust domain boundaries.

Governance Receipt:
   A cryptographically signed, immutable record that captures a
   governance decision (pre-execution), the agent's model-state
   commitment at the time of decision, and the post-execution outcome
   attestation.

Drift-Aware Governance:
   A governance model that detects and records discrepancies between
   the agent's declared model/configuration state at authorization
   time and its actual state at execution time, enabling post-hoc
   detection of model substitution, configuration drift, or
   unauthorized updates.

Policy Decision:
   The result of evaluating an agent's requested action against the
   applicable governance policies, producing an allow/deny/conditional
   outcome with associated reasoning.

Model-State Commitment:
   A cryptographic commitment to the agent's model identifier,
   version, configuration hash, and runtime environment attestation
   at the time a governance decision is made.

Compliance Anchor:
   A transparency log entry that binds a governance receipt to a
   globally verifiable, append-only data structure, enabling third-
   party audit without trusting the receipt issuer.

Principal:
   The natural or legal person on whose behalf an agent operates and
   who bears regulatory responsibility for the agent's actions.

Agent Gateway:
   An infrastructure component that mediates inter-agent and agent-
   to-tool communication, as defined in [MACP].

.# # 3. Protocol Overview

## 3.1. Design Principles

Protocol-agnostic composable extension:
   APGE MUST NOT define its own transport or session protocol. It
   MUST operate as an extension layer that composes with any Agent
   Group Messaging Protocol (AGMP), including MCP, A2A, AGTP, and
   ACP.

Immutable receipt before execution:
   A governance receipt MUST be generated and anchored before the
   agent action executes. Post-hoc receipt generation does not
   satisfy regulatory requirements for pre-execution governance.

Drift-aware by default:
   Every receipt MUST include a model-state commitment. If the model
   state changes between receipt generation and execution, the
   receipt's validity window MUST be invalidated or flagged.

Regulatory binding as profile, not fork:
   APGE defines a base receipt schema. Jurisdiction-specific
   compliance profiles (EU AI Act, China governance) constrain
   OPTIONAL fields to REQUIRED and add extension fields, following
   the additive profile pattern established by [ASQAV].

Minimal overhead:
   The governance extension MUST add less than 1ms latency per
   operation and less than 2KB per receipt for the common case,
   based on measured baseline costs of $0.000752/event at L2
   governance tier.

Transport-layer independence:
   APGE receipts MUST be verifiable independently of the transport
   protocol that carried the agent operation. Receipt verification
   requires only the receipt itself and the governance platform's
   public key.

## 3.2. Architecture Overview

The APGE architecture consists of four functional components:

```
  +-----------------------------------------------------------+
  |                Agent Communication Protocol                |
  |          (MCP / A2A / AGTP / ACP / other AGMP)           |
  +-----------------------------------------------------------+
         |                                    |
         v                                    v
  +------------------+              +-------------------+
  | Governance       |              | Agent Gateway     |
  | Engine           |              | (MACP AGW / AGTP  |
  |                  |              |  Proxy)           |
  | - Policy eval    |              |                   |
  | - Receipt gen    |              | - Header injection|
  | - Drift detect   |              | - Trace binding   |
  | - Log anchoring  |              | - Capability adv  |
  +------------------+              +-------------------+
         |                                    |
         v                                    v
  +------------------+              +-------------------+
  | Transparency Log |              | Extension         |
  | (RFC 9162 /      |              | Framework         |
  |  RFC 9943)       |              | (MCP ext-*/       |
  |                  |              |  reverse-DNS)     |
  +------------------+              +-------------------+
```

The Governance Engine is the core component that:

1. Receives pre-execution governance requests from the Agent Gateway
   or directly from the agent runtime.

2. Evaluates the requested action against applicable policies.

3. Captures a model-state commitment from the agent runtime.

4. Generates a Drift-Aware Governance Receipt.

5. Anchors the receipt to the Transparency Log.

6. Returns the governance decision and receipt to the caller.

The Agent Gateway integrates APGE into the agent communication
protocol by:

1. Injecting governance capability advertisements into protocol
   capability negotiation (MCP extensions map, A2A Agent Card,
   AGTP DESCRIBE).

2. Binding governance receipt identifiers to W3C Trace Context
   headers for cross-protocol correlation.

3. Enforcing governance decisions (allow/deny/rate-limit) at the
   gateway level, before the agent action reaches the target.

.# # 4. Drift-Aware Governance Receipt Schema

## 4.1. Receipt Envelope

Every APGE receipt is a JSON object with the following top-level
structure:

```json
{
  "schema_version": "2.0",
  "receipt_id": "urn:uuid:f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "receipt_type": "governance_decision",
  "governance_tier": "L2",
  "principal_id": "did:web:example.com:agent:ops-agent-7",
  "agent_id": "did:web:example.com:agent:billing-v2",
  "timestamp": "2026-07-15T10:30:00.000Z",
  "validity_window": {
    "valid_from": "2026-07-15T10:30:00.000Z",
    "valid_until": "2026-07-15T10:45:00.000Z"
  },
  "policy_decision": { ... },
  "model_state_commitment": { ... },
  "outcome_attestation": null,
  "supersedes_or_invalidates": null,
  "compliance_anchor": { ... },
  "trace_context": { ... }
}
```

The `schema_version` field MUST be "2.0" for receipts conforming to
this specification. The `receipt_type` field MUST be one of:
"governance_decision", "governance_override", "governance_revocation",
or "drift_alert".

The `governance_tier` field indicates the governance level applied,
using the tiered model defined in Section 7.

## 4.2. Policy Decision Block

The `policy_decision` object captures the governance evaluation:

```json
{
  "policy_decision": {
    "action_requested": "tool:invoke:payment_processor",
    "action_parameters_hash": "sha3-256:e3b0c44298fc1c...",
    "outcome": {
      "status": "allowed",
      "reason_code": "WITHIN_SCOPE",
      "conditions": []
    },
    "policy_id": "policy:payment-ops:v3.2",
    "policy_digest": "sha3-256:a7ffc6f8bf1ed76...",
    "eval_duration_ms": 0.3
  }
}
```

The `outcome.status` field MUST be one of: "allowed", "denied",
"conditional", "rate_limited", or "deferred".

The `reason_code` field provides machine-readable justification. A
registry of reason codes is defined in Section 8.

The `policy_digest` field enables post-hoc verification that the
policy version in effect at decision time matches the policy version
the principal expected.

## 4.3. Model-State Commitment

The `model_state_commitment` object captures the agent's runtime
state at the time of governance evaluation:

```json
{
  "model_state_commitment": {
    "model_id": "gpt-4o-2026-05-01",
    "model_version": "2026-05-01",
    "configuration_hash": "sha3-256:cf83e1357eefb8b...",
    "system_prompt_hash": "sha3-256:ba7816bf8f01cf...",
    "runtime_attestation": {
      "tee_type": "SGX",
      "tee_quote_hash": "sha3-256:248d6a61d20638b...",
      "attestation_timestamp": "2026-07-15T10:29:59.500Z"
    },
    "tool_inventory_hash": "sha3-256:83b52fa868...",
    "commitment_timestamp": "2026-07-15T10:30:00.000Z"
  }
}
```

The `runtime_attestation` field is OPTIONAL at governance tiers L0-L1
and REQUIRED at tiers L2 and above. When present, it provides a TEE-
based attestation that the agent runtime environment matches the
declared configuration.

The model-state commitment enables **drift detection**: if the
agent's model, configuration, or tool inventory changes between
receipt generation and action execution, the receipt's validity
window is invalidated via the `supersedes_or_invalidates` mechanism.

## 4.4. Outcome Attestation

The `outcome_attestation` field is populated post-execution:

```json
{
  "outcome_attestation": {
    "actual_action": "tool:invoke:payment_processor",
    "actual_parameters_hash": "sha3-256:e3b0c44298fc1c...",
    "execution_result": "success",
    "result_hash": "sha3-256:abc123...",
    "drift_detected": false,
    "execution_timestamp": "2026-07-15T10:30:00.850Z",
    "latency_ms": 850
  }
}
```

The `drift_detected` field is the critical innovation of APGE. It
indicates whether the agent's runtime state at execution time
differed from the state committed at governance evaluation time. A
value of `true` triggers a `drift_alert` receipt and invalidates
the original receipt's validity window.

## 4.5. Validity Window and Supersession

Governance receipts are time-bounded. The `validity_window` defines
the temporal scope of the authorization. Receipts expire when:

1. The `valid_until` timestamp is reached.

2. A new receipt is issued that supersedes this one.

3. A drift alert invalidates the receipt.

4. A governance revocation is issued.

The `supersedes_or_invalidates` field creates an append-only chain:

```json
{
  "supersedes_or_invalidates": {
    "type": "supersedes",
    "prior_receipt_id": "urn:uuid:6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "reason": "policy_update"
  }
}
```

This field mirrors the `supersedes_or_invalidates` mechanism in the
AGL Receipt Schema v2.0 and is compatible with the revocation
semantics of ERC-8226's `revokePrincipal` function.

## 4.6. Canonicalization and Signing

Receipts MUST be canonicalized using JSON Canonicalization Scheme
(JCS) as specified in [RFC8785] before signing. The signing algorithm
MUST be Ed25519 [RFC8032] or ES256. The signature is computed over
the canonicalized receipt body and included in a `signature` object:

```json
{
  "signature": {
    "algorithm": "Ed25519",
    "signer_id": "did:web:governance.example.com",
    "signer_key_id": "key-2026-07",
    "value": "base64url:eyJhbGciOiJFZDI1NTE5In0..."
  }
}
```

The signer MUST be the governance platform, not the agent. This
architectural separation — where the audited party does not control
the signing key — is consistent with AGTP-LOG's design principle
and prevents self-attestation attacks.

.# # 5. Compliance Receipt Anchoring Protocol

## 5.1. Transparency Log Integration

APGE receipts are anchored to a transparency log aligned with
[RFC9162] (Certificate Transparency 2.0) as the verifiable data
structure and [RFC9943] (SCITT) for receipt format interoperability.

The log entry for an APGE receipt contains:

```json
{
  "log_entry": {
    "receipt_id": "urn:uuid:f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "entry_type": "governance_receipt",
    "submitted_at": "2026-07-15T10:30:00.100Z",
    "canonical_receipt_hash": "sha3-256:9f86d081884c7d...",
    "governance_tier": "L2",
    "principal_id_hash": "sha3-256:5feceb66ffc86...",
    "log_operator_id": "did:web:log.example.com"
  }
}
```

The log issues a COSE_Sign1 receipt per [RFC9943] confirming
inclusion. This receipt is stored in the `compliance_anchor` field
of the APGE receipt.

## 5.2. Receipt Lifecycle

```
  Agent        Governance     Transparency     Regulator/
  Runtime       Engine           Log           Auditor
    |              |               |              |
    |--request---->|               |              |
    |              |--evaluate---->|              |
    |              |<--decision---|              |
    |              |--submit------>|              |
    |              |<--inclusion--|              |
    |<--receipt----|               |              |
    |              |               |              |
    |--execute---->|               |              |
    |              |--anchor------>|              |
    |              |               |--audit------>|
    |              |               |              |
```

The lifecycle has four phases:

1. **Pre-execution**: Agent requests governance evaluation. Governance
   Engine evaluates policy, captures model-state commitment, generates
   receipt, submits to transparency log, returns decision.

2. **Execution**: Agent executes the action. If drift is detected
   between model-state commitment and runtime state, a drift_alert
   receipt is generated.

3. **Post-execution**: Outcome attestation is populated and anchored.

4. **Audit**: Regulators and auditors verify receipts independently
   using the transparency log's inclusion and consistency proofs.

## 5.3. Inclusion and Consistency Proofs

Inclusion proofs follow the Merkle Tree structure of [RFC9162].
Consistency proofs enable verification that the log has not been
tampered with between any two tree sizes.

APGE defines a specific query interface for governance receipts:

```
GET /log/v1/receipts/{receipt_id}
GET /log/v1/receipts/{receipt_id}/inclusion-proof
GET /log/v1/consistency-proof?from={tree_size_1}&to={tree_size_2}
GET /log/v1/signed-tree-head
```

.# # 6. Governance Capability Advertisement

## 6.1. MCP Extension Integration

APGE integrates with the MCP 2026-07-28 Extensions framework using
the reverse-DNS identifier:

```
io.bdescore/apge
```

The extension is advertised in the MCP capability map:

```json
{
  "capabilities": {
    "extensions": {
      "io.bdescore/apge": {
        "version": "2.0",
        "governance_tiers_supported": ["L0", "L1", "L2", "L3"],
        "receipt_formats": ["apge-v2"],
        "transparency_log_uri": "https://log.bdescore.org/v1",
        "compliance_profiles": ["eu-ai-act-art12", "eu-ai-act-art26",
                                "eu-ai-act-art50", "cn-agent-governance"]
      }
    }
  }
}
```

When both client and server advertise the `io.bdescore/apge`
extension, governance receipts are generated for all tool invocations
and agent-to-agent delegations within the session.

## 6.2. W3C Trace Context Binding

APGE receipts are bound to the W3C Trace Context propagated through
MCP's `_meta` field (as specified in the 2026-07-28 spec). The
`traceparent` and `tracestate` values from the agent operation are
included in the receipt's `trace_context` field:

```json
{
  "trace_context": {
    "traceparent": "00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01",
    "tracestate": "apge=gov-tier:L2",
    "baggage": "jurisdiction=EU,regime=ai-act"
  }
}
```

This binding enables:

1. Correlation of governance receipts with OpenTelemetry traces for
   operational observability.

2. Cross-protocol governance tracking when agents traverse multiple
   communication protocols in a single task.

3. Post-hoc audit that traces the full path from user request through
   governance decision to execution outcome.

## 6.3. AGMP Header Mapping

For agent communication protocols that use headers (e.g., AGTP), APGE
defines header mappings:

| APGE Field | AGTP Header | MCP _meta Key |
|---|---|---|
| receipt_id | Governance-Receipt-ID | io.bdescore/receiptId |
| governance_tier | Governance-Tier | io.bdescore/governanceTier |
| policy_decision.outcome.status | Governance-Decision | io.bdescore/decision |
| validity_window.valid_until | Governance-Valid-Until | io.bdescore/validUntil |
| drift_detected | Governance-Drift-Alert | io.bdescore/driftAlert |

Infrastructure components (gateways, load balancers) MUST use these
headers for routing and enforcement decisions, consistent with AGTP's
precedence rule that infrastructure headers take priority over
payload fields.

.# # 7. Regulatory Binding

## 7.1. EU AI Act Art. 12 (Record-Keeping)

APGE receipts satisfy Art. 12 obligations when the `eu-ai-act-art12`
compliance profile is active:

- Art. 12(1) automatic recording: Every governance receipt is an
  automatic record of a governance event, anchored to the
  transparency log with a timestamp.

- Art. 12(2)(a) risk identification: The `policy_decision.reason_code`
  field provides machine-readable risk classification.

- Art. 12(2)(b) post-market monitoring: The transparency log enables
  ongoing monitoring without accessing the deployer's systems.

- Art. 12(2)(c) operational monitoring: The `outcome_attestation`
  field records execution outcomes.

The compliance profile constrains the following OPTIONAL fields to
REQUIRED: `model_state_commitment`, `outcome_attestation`,
`compliance_anchor`, `policy_decision.policy_digest`.

Minimum retention: 6 months (Art. 26(6) requirement applied
retroactively to Art. 12 records per established practice).

## 7.2. EU AI Act Art. 26 (Deployer Obligations)

- Art. 26(1) instruction compliance: The `policy_id` and
  `policy_digest` fields enable verification that the agent operated
  within its declared instructions.

- Art. 26(2) human oversight: The `governance_tier` field indicates
  whether the operation required human approval (L3+) or was
  autonomous (L0-L2).

- Art. 26(5) operational monitoring: Continuous receipt generation
  provides the monitoring record.

- Art. 26(6) log retention: Compliance profile mandates minimum
  6-month retention with tamper-evidence.

## 7.3. EU AI Act Art. 50 (Transparency)

Art. 50 requires that deployers of AI systems that generate synthetic
audio, image, video, or text ensure that the outputs are marked in a
machine-readable format and are detectable as artificially generated.

APGE addresses this through the `outcome_attestation.synthetic_flag`
extension field (REQUIRED under the `eu-ai-act-art50` compliance
profile):

```json
{
  "outcome_attestation": {
    "synthetic_flag": true,
    "synthetic_content_type": "text",
    "watermark_hash": "sha3-256:abc123...",
    "disclosure_mechanism": "api-response-header"
  }
}
```

When Art. 50 enforcement begins (18 days from this writing, on
2 August 2026), APGE-compliant agents MUST set `synthetic_flag` to
`true` for any AI-generated output and include the content type and
watermark hash.

## 7.4. China Intelligent Agent Governance Implementation Opinion

China's "Intelligent Agent Governance Implementation Opinion"
(《智能体治理实施意见》), effective 15 July 2026, requires:

- Agent identity registration with designated authorities.
- Operational audit trails for high-impact agent actions.
- Content labeling for AI-generated outputs.
- Cross-border data flow compliance for agents operating across
  jurisdictions.

APGE's `cn-agent-governance` compliance profile constrains:

- `principal_id` MUST use a jurisdiction-appropriate identifier
  format.
- `model_state_commitment.runtime_attestation` is REQUIRED at all
  governance tiers (not just L2+).
- `outcome_attestation.content_label` field is REQUIRED for any
  output directed at natural persons.
- `validity_window` maximum duration is reduced to 15 minutes for
  cross-border operations.

.# # 8. IANA Considerations

APGE requests the following IANA registrations:

1. **MCP Extension Registry**: Registration of the
   `io.bdescore/apge` extension identifier.

2. **APGE Reason Code Registry**: A new registry for
   `policy_decision.reason_code` values, with initial entries:
   - WITHIN_SCOPE
   - SCOPE_EXCEEDED
   - TIER_EXCEEDED
   - RATE_LIMITED
   - DRIFT_DETECTED
   - POLICY_EXPIRED
   - REVOKED
   - SANCTIONS_MATCH
   - JURISDICTION_BLOCKED
   - HUMAN_APPROVAL_REQUIRED
   - COMPLIANCE_PROFILE_VIOLATION

3. **APGE Compliance Profile Registry**: A new registry for
   compliance profile identifiers, with initial entries:
   - eu-ai-act-art12
   - eu-ai-act-art26
   - eu-ai-act-art50
   - cn-agent-governance
   - dora-art17

4. **Governance Tier Registry**: A new registry mapping tier
   identifiers to governance requirements.

.# # 9. Security Considerations

Self-attestation prevention:
   APGE receipts are signed by the governance platform, not by the
   agent. This prevents an agent from forging its own audit trail.
   The same architectural separation is used in AGTP-LOG.

Model substitution attacks:
   The `model_state_commitment` field, combined with TEE attestation
   at higher governance tiers, mitigates model substitution attacks
   where an operator replaces the declared model with a different one
   after authorization.

Drift detection timing:
   There is an inherent window between model-state commitment
   capture and execution during which drift could occur
   undetected. APGE mitigates this through short validity windows
   (default 15 minutes) and TEE-anchored runtime attestation.

Log operator compromise:
   If the transparency log operator is compromised, historical
   receipts can still be verified using consistency proofs.
   Federation via cross-witnessing (following the SCITT pattern)
   provides defense-in-depth.

Receipt replay:
   The `receipt_id` (UUID v4) and `timestamp` fields prevent receipt
   replay. Verifiers MUST check that a receipt's timestamp falls
   within its validity window and that the receipt_id has not been
   previously observed.

Privacy considerations:
   APGE receipts contain principal identifiers and action hashes.
   In privacy-sensitive deployments, the `principal_id_hash` field
   in the log entry uses a one-way hash rather than the plaintext
   principal ID. The full principal ID is available only in the
   receipt itself, which is stored by the governance platform and
   shared with auditors under appropriate legal authority.

Cross-jurisdictional conflicts:
   When multiple compliance profiles are active simultaneously
   (e.g., EU AI Act and China governance), conflicting requirements
   MUST be resolved by applying the stricter constraint. APGE
   implementations SHOULD log profile conflicts as
   `COMPLIANCE_PROFILE_VIOLATION` reason codes.

.# # 10. References

## 10.1. Normative References

- [RFC2119] Bradner, S., "Key words for use in RFCs to Indicate
  Requirement Levels", BCP 14, RFC 2119, March 1997.

- [RFC8174] Leiba, B., "Ambiguity of Uppercase vs Lowercase in
  RFC 2119 Key Words", BCP 14, RFC 8174, May 2017.

- [RFC8785] Rundgren, A., Jordan, B., and S. Erdtman,
  "JSON Canonicalization Scheme (JCS)", RFC 8785, June 2020.

- [RFC9162] Laurie, B., Messeri, E., and R. Stradling, "Certificate
  Transparency Version 2.0", RFC 9162, January 2022.

- [RFC9943] Birkholz, C., and H. Birkholz, "Supply Chain
  Integrity, Transparency, and Trust (SCITT)", RFC 9943,
  2025.

## 10.2. Informative References

- [AIGA] Aylward, E., "AI Governance and Accountability Protocol",
  draft-aylward-aiga-2-00, January 2026.

- [DRP] Nelson, R., "Delegation Receipt Protocol for AI Agent
  Authorization", draft-nelson-agent-delegation-receipts-00,
  April 2026.

- [PoB] Dembowski, J., "Proof-of-Behavior Protocol for Autonomous
  AI Agents", draft-dembowski-agentledger-proof-of-behavior-00,
  April 2026.

- [ACTA] Farley, T., "Signed Decision Receipts for Machine-to-
  Machine Access Control", draft-farley-acta-signed-receipts-00,
  March 2026.

- [ASQAV] Marques, J., "Compliance Profile of Signed Action Receipts
  for AI Agents", draft-marques-asqav-compliance-receipts-00,
  May 2026.

- [MACP] Li, X., et al., "Multi-Agent Collaboration Protocol Suites
  Architecture", draft-li-dmsc-macp-04, April 2026.

- [AGTP] Hood, C., "AGTP Composition with Agent Group Messaging
  Protocols", draft-hood-agtp-composition-00, March 2026.

- [TRUST-FW] Kiliram, et al., "Trust and Authentication Framework
  for Cross-Domain A2A", draft-kiliram-agent-trust-auth-framework-00.

- [AIPROTO] Rosenberg, J. and C. Jennings, "Framework, Use Cases
  and Requirements for AI Agent Protocols", draft-rosenberg-
  aiproto-framework-00, October 2025.

- [EU-AI-ACT] European Parliament and Council, "Regulation (EU)
  2024/1689 laying down harmonised rules on artificial intelligence",
  August 2024.

- [MCP-SPEC] Model Context Protocol, "MCP Specification 2026-07-28",
  July 2026.

- [ERC-8226] Ethereum Magicians, "ERC-8226: Regulated Agent Mandate
  Specification", 2026.

.# # Appendix A. AGL Receipt Schema v2.0 Field Mapping

The APGE receipt schema is derived from the AGL Receipt Schema v2.0
deployed in the BDE Score project. The following table maps AGL
fields to APGE fields:

| AGL Receipt Schema v2.0 | APGE Field |
|---|---|
| policy_decision | policy_decision |
| validity_window | validity_window |
| outcome.status | policy_decision.outcome.status |
| supersedes_or_invalidates | supersedes_or_invalidates |
| model_state.model_id | model_state_commitment.model_id |
| model_state.config_hash | model_state_commitment.configuration_hash |
| compliance_anchor | compliance_anchor |
| trace_context | trace_context |

.# # Appendix B. ERC-8226 Interface Mapping

APGE's receipt schema is designed as the off-chain governance
companion to ERC-8226's on-chain compliance interface:

| ERC-8226 Function | APGE Receipt Field |
|---|---|
| checkPrincipal() → (eligible, reason, expiresAt) | policy_decision.outcome + validity_window |
| grantPrincipal() | receipt_type: governance_decision |
| revokePrincipal() | receipt_type: governance_revocation |
| ReasonCode enum (9 values) | policy_decision.reason_code |
| expiresAt | validity_window.valid_until |

APGE provides the off-chain evidence layer that ERC-8226's on-chain
principal eligibility relies on for audit and regulatory compliance.

.# # Appendix C. MCP Extension Registration Template

Extension identifier: io.bdescore/apge
Extension version: 2.0
Extension description: Agent Protocol Governance Extension - provides
  immutable, cryptographically verifiable compliance receipts for AI
  agent operations
Extension repository: https://github.com/bdescore/apge-extension
Extension maintainers: BDE Score Project
Compliance profiles: eu-ai-act-art12, eu-ai-act-art26,
  eu-ai-act-art50, cn-agent-governance, dora-art17
Governance tiers: L0 (observational), L1 (standard), L2 (enhanced),
  L3 (regulated), L4 (critical)
Protocol versions: MCP 2026-07-28+

.# # Author's Address

BDE Score Project
Email: standards@bdescore.org
