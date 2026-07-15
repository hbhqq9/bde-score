# ERC-8226 ↔ AGL Interface Compatibility Mapping

**Date**: 2026-07-15
**Status**: Analysis complete, implementation pending

## Overview

ERC-8226 (Regulated Agent Mandate / RAMS) defines on-chain compliance delegation for AI agents operating on regulated assets. AGL (Agent Governance Layer) provides off-chain governance transparency for EU AI Act Art.50 compliance.

These two standards are **complementary, not competing**:
- **ERC-8226**: On-chain principal eligibility verification (who can act)
- **AGL**: Off-chain governance transparency + audit trail (what happened and why)

## Interface Mapping

### ERC-8226 IComplianceProvider → AGL Receipt Schema v2.0

| ERC-8226 Interface | AGL Receipt Field | Mapping Logic |
|---|---|---|
| `checkPrincipal(principal, identityRef)` → `(eligible, reason, expiresAt)` | `policy_decision` + `validity_window` | ERC-8226's eligibility check = AGL's policy decision input |
| `grantPrincipal(principal, identityRef, expiresAt)` | `validity_window.valid_from` + `validity_window.valid_until` | Grant maps to validity window start |
| `revokePrincipal(principal, reason)` | `supersedes_or_invalidates` | Revocation = append new receipt with invalidation reference |
| `ReasonCode` enum (9 values) | `outcome.status` + `outcome.reason` | Direct mapping: COMPLIANT→success, others→failure with reason |
| `PrincipalGranted` event | `disclosure` + `identity` | Grant event = transparency disclosure |
| `PrincipalRevoked` event | `supersedes_or_invalidates` + `outcome` | Revocation = invalidation event |

### Key Synergies

1. **Temporal Alignment**
   - ERC-8226's `expiresAt` ↔ AGL's `validity_window.valid_until`
   - Both standards recognize that compliance is time-bounded and must be re-checked

2. **Invalidation Pattern**
   - ERC-8226: `revokePrincipal()` directly modifies state
   - AGL: Append-only — revocation expressed by new receipt via `supersedes_or_invalidates`
   - **Bridge**: ERC-8226 on-chain revocation triggers AGL off-chain receipt append

3. **Reason Codes → Audit Trail**
   - ERC-8226 returns `ReasonCode` in real-time check
   - AGL records full context (policy_version, factors[], confidence) in receipt
   - **Bridge**: ERC-8226's reason code becomes AGL's `outcome.reason`; AGL adds the "why"

4. **Identity Layer**
   - ERC-8226: `bytes32 identityRef` (DID hash or attestation ID)
   - AGL: `identity.agent_principal` + `identity.operator_address`
   - **Bridge**: Same principal address, different identity representations

## Gap Analysis

### What AGL Needs to Add for Full ERC-8226 Compatibility

1. **IComplianceProvider Interface Implementation**
   - Current AGL ComplianceEngine doesn't implement `IComplianceProvider`
   - Need to add: `checkPrincipal()`, `grantPrincipal()`, `revokePrincipal()`
   - Can be done as a wrapper around existing receipt store

2. **ERC165 Support**
   - ERC-8226 requires `IERC165` support
   - AGL contracts need `supportsInterface()` implementation

3. **On-Chain ReasonCode Enum**
   - Need to align AGL's outcome status codes with ERC-8226's ReasonCode enum
   - 9 values: COMPLIANT, KYC_EXPIRED, AML_FLAG, NOT_ACCREDITED, NOT_QUALIFIED, JURISDICTION_BLOCKED, IDENTITY_NOT_FOUND, ATTESTATION_REVOKED, OTHER

### What ERC-8226 Could Learn from AGL

1. **Drift-Aware Fields**
   - ERC-8226 doesn't track policy_version or rule_set changes
   - AGL's `policy_version` field enables audit of "what rules were in effect at decision time"

2. **Off-Chain Audit Trail**
   - ERC-8226 is purely on-chain; no detailed audit context
   - AGL's receipt provides full decision context (factors[], confidence, methodology)

3. **EU AI Act Art.50 Transparency**
   - ERC-8226 doesn't address Art.50 disclosure requirements
   - AGL's `disclosure` field provides pre-interaction transparency notices

## Implementation Path

### Phase 1: Interface Wrapper (Low Effort)
- Add `IComplianceProvider` wrapper around existing AGL receipt store
- Map `checkPrincipal()` to receipt `policy_decision` + `validity_window` check
- Map `grantPrincipal/revokePrincipal` to receipt append operations
- Estimated: 2-3 days

### Phase 2: Contract Upgrade (Medium Effort)
- Deploy new ComplianceEngine with ERC165 + IComplianceProvider
- Maintain backward compatibility with existing receipt schema
- Estimated: 1 week

### Phase 3: Cross-Standard Audit (High Value)
- Joint audit trail: ERC-8226 on-chain events + AGL off-chain receipts
- Unified compliance view for regulators
- Estimated: 2 weeks

## Relevance for IETF 126 BoF

This mapping demonstrates that:
1. Agent compliance standards (ERC-8226) and governance transparency (AGL/Art.50) are **complementary layers**
2. A single agent interaction can satisfy both: on-chain eligibility check + off-chain audit receipt
3. The receipt schema bridges blockchain-native compliance and traditional regulatory frameworks
4. Interoperability is achievable without either standard compromising its design principles

**Key message for BoF**: Agent protocol standardization should recognize the on-chain/off-chain duality. ERC-8226 handles the "who can act" layer; AGL handles the "what happened and was it compliant" layer. Both are needed for production-grade agent governance.

## References

- ERC-8226: https://ethereum-magicians.org/t/erc-8226-regulated-agent-mandate/28208
- ERC-8226 Reference Implementation: https://github.com/ethereum/ERCs/tree/master/assets/erc-8226
- AGL Receipt Schema v2.0: https://github.com/hbhqq9/bde-score/commit/908fd28
- EU AI Act Art.50: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R0168
