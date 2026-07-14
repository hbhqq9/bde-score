"""
AGL Receipt Schema v2.0 — Drift-Aware Extension
=================================================
Extends the original 6-field receipt with 3 drift-aware fields per
hegu-1's feedback on enterprise-ai-os-architecture Issue #1.

6 Base Fields (Enterprise AI OS primitive mapping):
  1. disclosure     → policy-facing transparency event
  2. identity       → agent/runtime principal
  3. policy_decision→ governance decision receipt
  4. execution      → action/tool receipt
  5. outcome        → result/evidence state
  6. on_chain       → tamper-evidence anchor

3 Drift-Aware Fields (new):
  7. policy_version              → exact compliance/rule set at decision time
  8. validity_window             → temporal scope of decision validity
  9. supersedes_or_invalidates   → links to events that change receipt status

Immutability Principle:
  Old receipts are NEVER rewritten. Invalidation/supersession is expressed
  by appending new events. Current compliance state = derived view over
  all immutable receipts + current policy.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List


# ============================================================================
# Enums
# ============================================================================

class ReceiptStatus(str, Enum):
    """Lifecycle status of a receipt."""
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    INVALIDATED = "invalidated"


class ReceiptType(str, Enum):
    """Categories of receipts in the AGL system."""
    DISCLOSURE = "disclosure"
    POLICY_DECISION = "policy_decision"
    EXECUTION = "execution"
    OUTCOME = "outcome"


# ============================================================================
# Drift-Aware Sub-Schemas
# ============================================================================

@dataclass(frozen=True)
class PolicyVersion:
    """
    Field 7: policy_version
    Records the exact compliance/rule set used at decision time.
    Enables drift detection when policies evolve.
    """
    rule_set_id: str                    # e.g. "eu-ai-act-art50-2026-01"
    schema_version: str                 # e.g. "2.0.0"
    compliance_framework: str           # e.g. "EU AI Act Art.50"
    effective_from: str                 # ISO-8601 datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_set_id": self.rule_set_id,
            "schema_version": self.schema_version,
            "compliance_framework": self.compliance_framework,
            "effective_from": self.effective_from,
        }


@dataclass(frozen=True)
class ValidityWindow:
    """
    Field 8: validity_window
    Defines the temporal (and optionally spatial/contextual) scope
    during which this receipt's decision remains valid.
    """
    valid_from: str                     # ISO-8601 datetime
    valid_until: Optional[str]          # ISO-8601 datetime or null (infinite)
    context: Dict[str, Any]             # e.g. {"market": "US", "symbol": "AAPL"}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "context": self.context,
        }


@dataclass(frozen=True)
class SupersessionEvent:
    """
    Field 9: supersedes_or_invalidates
    Links to a prior receipt that this event supersedes or invalidates.
    Null when the receipt is an original (no prior state change).
    """
    receipt_id: str                     # UUID of the superseded receipt
    reason: str                         # Human-readable reason
    superseded_by: Optional[str]        # UUID of the replacement receipt (if any)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "reason": self.reason,
            "superseded_by": self.superseded_by,
        }


# ============================================================================
# Receipt Schema v2.0 — Core Data Model
# ============================================================================

@dataclass
class ReceiptSchemaV2:
    """
    AGL Receipt Schema v2.0 — 6+3 field structure.

    Fields 1-6 are the base transparency/execution receipts.
    Fields 7-9 are the drift-aware extensions.

    All receipts are immutable once appended to the store.
    """
    # === Identity ===
    receipt_id: str                     # UUID v7 (time-sortable)
    timestamp: str                      # ISO-8601 creation time

    # === Field 1: disclosure — policy-facing transparency event ===
    disclosure: Dict[str, Any]          # AI system info, compliance markers

    # === Field 2: identity — agent/runtime principal ===
    identity: Dict[str, Any]            # Who/what made the decision

    # === Field 3: policy_decision — governance decision receipt ===
    policy_decision: Dict[str, Any]     # What governance rule was applied

    # === Field 4: execution — action/tool receipt ===
    execution: Dict[str, Any]           # What tool/action was executed

    # === Field 5: outcome — result/evidence state ===
    outcome: Dict[str, Any]             # What was the result

    # === Field 6: on_chain — tamper-evidence anchor ===
    on_chain: Dict[str, Any]            # Hash chain / proof-of-existence

    # === Field 7: policy_version (DRIFT-AWARE) ===
    policy_version: PolicyVersion

    # === Field 8: validity_window (DRIFT-AWARE) ===
    validity_window: ValidityWindow

    # === Field 9: supersedes_or_invalidates (DRIFT-AWARE) ===
    supersedes_or_invalidates: Optional[SupersessionEvent]

    # === Metadata ===
    status: ReceiptStatus = ReceiptStatus.ACTIVE
    content_hash: str = ""              # SHA-256 of canonical JSON

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute SHA-256 hash of canonical (sorted-key) JSON representation."""
        canonical = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize receipt to dictionary."""
        d = {
            "receipt_id": self.receipt_id,
            "timestamp": self.timestamp,
            "disclosure": self.disclosure,
            "identity": self.identity,
            "policy_decision": self.policy_decision,
            "execution": self.execution,
            "outcome": self.outcome,
            "on_chain": self.on_chain,
            "policy_version": self.policy_version.to_dict(),
            "validity_window": self.validity_window.to_dict(),
            "supersedes_or_invalidates": (
                self.supersedes_or_invalidates.to_dict()
                if self.supersedes_or_invalidates
                else None
            ),
            "status": self.status.value,
            "content_hash": self.content_hash,
        }
        return d

    def to_json(self, indent: int = 2) -> str:
        """Serialize receipt to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ReceiptSchemaV2:
        """Deserialize receipt from dictionary."""
        pv = data["policy_version"]
        vw = data["validity_window"]
        soi = data.get("supersedes_or_invalidates")

        return cls(
            receipt_id=data["receipt_id"],
            timestamp=data["timestamp"],
            disclosure=data["disclosure"],
            identity=data["identity"],
            policy_decision=data["policy_decision"],
            execution=data["execution"],
            outcome=data["outcome"],
            on_chain=data["on_chain"],
            policy_version=PolicyVersion(**pv),
            validity_window=ValidityWindow(**vw),
            supersedes_or_invalidates=SupersessionEvent(**soi) if soi else None,
            status=ReceiptStatus(data.get("status", "active")),
            content_hash=data.get("content_hash", ""),
        )


# ============================================================================
# Factory Function
# ============================================================================

def generate_uuid_v7() -> str:
    """
    Generate a UUID v7 (time-sortable) identifier.
    Uses Python 3.12+ uuid7 if available, otherwise constructs one manually.
    """
    try:
        import uuid as _uuid
        if hasattr(_uuid, 'uuid7'):
            return str(_uuid.uuid7())
    except Exception:
        pass
    # Fallback: construct time-sortable UUID v7 manually (16 bytes)
    import time as _time
    import struct as _struct
    t_ms = int(_time.time() * 1000)
    # Start with a random UUID's bytes to get full 16 bytes of randomness
    rand = bytearray(uuid.uuid4().bytes)
    # Layout: [48-bit timestamp_ms][4-bit version=7][12-bit rand][2-bit variant=10][62-bit rand]
    # Bytes 0-5: timestamp (48 bits, big-endian)
    rand[0] = (t_ms >> 40) & 0xFF
    rand[1] = (t_ms >> 32) & 0xFF
    rand[2] = (t_ms >> 24) & 0xFF
    rand[3] = (t_ms >> 16) & 0xFF
    rand[4] = (t_ms >> 8) & 0xFF
    rand[5] = t_ms & 0xFF
    # Byte 6: version 7 (high nibble = 0x7_)
    rand[6] = (rand[6] & 0x0F) | 0x70
    # Byte 8: variant 10xx (high bits = 10)
    rand[8] = (rand[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(rand)))


def create_receipt(
    disclosure: Dict[str, Any],
    identity: Dict[str, Any],
    policy_decision: Dict[str, Any],
    execution: Dict[str, Any],
    outcome: Dict[str, Any],
    on_chain: Optional[Dict[str, Any]] = None,
    policy_version: Optional[PolicyVersion] = None,
    validity_window: Optional[ValidityWindow] = None,
    supersedes_or_invalidates: Optional[SupersessionEvent] = None,
    receipt_id: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> ReceiptSchemaV2:
    """
    Factory function to create a ReceiptSchemaV2 instance.

    Provides sensible defaults for BDE Score use case while allowing
    full customization for other Enterprise AI OS integrations.
    """
    now = datetime.now(timezone.utc)
    _receipt_id = receipt_id or generate_uuid_v7()
    _timestamp = timestamp or now.isoformat()

    # Default on_chain: local hash anchor
    if on_chain is None:
        payload = json.dumps({
            "receipt_id": _receipt_id,
            "timestamp": _timestamp,
            "outcome": outcome,
        }, sort_keys=True, default=str)
        on_chain = {
            "anchor_type": "sha256-local",
            "content_hash": hashlib.sha256(payload.encode()).hexdigest(),
            "chain_position": None,  # populated by store on append
        }

    # Default policy_version
    if policy_version is None:
        policy_version = PolicyVersion(
            rule_set_id="eu-ai-act-art50-2026-01",
            schema_version="2.0.0",
            compliance_framework="EU AI Act Art.50",
            effective_from="2026-01-01T00:00:00+00:00",
        )

    # Default validity_window
    if validity_window is None:
        from datetime import timedelta
        valid_until = now + timedelta(hours=24)
        validity_window = ValidityWindow(
            valid_from=_timestamp,
            valid_until=valid_until.isoformat(),
            context={"scope": "single-request"},
        )

    return ReceiptSchemaV2(
        receipt_id=_receipt_id,
        timestamp=_timestamp,
        disclosure=disclosure,
        identity=identity,
        policy_decision=policy_decision,
        execution=execution,
        outcome=outcome,
        on_chain=on_chain,
        policy_version=policy_version,
        validity_window=validity_window,
        supersedes_or_invalidates=supersedes_or_invalidates,
    )


# ============================================================================
# BDE Score — Default Disclosure Template
# ============================================================================

BDE_DISCLOSURE_TEMPLATE = {
    "generated_by": "BDE Score AI Assessment Engine v1.0.2",
    "assessment_type": "automated-multi-factor-scoring",
    "methodology": "rule-based + LLM-enhanced analysis",
    "ai_system": True,
    "eu_ai_act_art50": "compliant",
    "compliance_page": "https://hbhqq9.github.io/bde-score/compliance.html",
    "disclaimer": "AI-generated analysis. Not investment advice.",
}

BDE_IDENTITY_TEMPLATE = {
    "agent_name": "bde-score-mcp-server",
    "agent_version": "1.0.2",
    "runtime": "python-fastmcp",
    "principal": "bde-score-system",
}


def create_bde_receipt(
    tool_name: str,
    tool_params: Dict[str, Any],
    result_summary: Dict[str, Any],
) -> ReceiptSchemaV2:
    """
    Convenience factory for BDE Score MCP tool invocations.
    Generates a full v2.0 receipt with BDE-specific defaults.
    """
    return create_receipt(
        disclosure=BDE_DISCLOSURE_TEMPLATE,
        identity=BDE_IDENTITY_TEMPLATE,
        policy_decision={
            "rule": "art50-transparency-obligation",
            "decision": "disclose-ai-generated-content",
            "confidence": "high",
        },
        execution={
            "tool": tool_name,
            "parameters": tool_params,
            "read_only": True,
        },
        outcome={
            "status": "completed",
            "summary": result_summary,
        },
    )
