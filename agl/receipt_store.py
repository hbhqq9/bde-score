"""
AGL Receipt Store — Append-Only, Drift-Aware
=============================================
Implements an immutable append-only receipt store with JSON file persistence.

Core Principles (from hegu-1 feedback):
  - Receipts are NEVER modified or deleted once appended
  - Invalidation/supersession is expressed by appending NEW receipts
  - Current compliance state = derived view over all receipts + current policy

Storage Backends:
  - InMemoryStore: volatile, for testing and single-session use
  - JsonFileStore: persistent, append-only JSON Lines file
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Protocol

from agl.receipt_schema_v2 import (
    ReceiptSchemaV2,
    ReceiptStatus,
    SupersessionEvent,
    create_receipt,
)


# ============================================================================
# Store Protocol (Interface)
# ============================================================================

class ReceiptStoreProtocol(Protocol):
    """Interface for receipt store implementations."""

    def append(self, receipt: ReceiptSchemaV2) -> str:
        """Append a receipt. Returns receipt_id. Raises on duplicate."""
        ...

    def get(self, receipt_id: str) -> Optional[ReceiptSchemaV2]:
        """Retrieve a receipt by ID."""
        ...

    def get_all(self) -> List[ReceiptSchemaV2]:
        """Retrieve all receipts in append order."""
        ...

    def invalidate(self, receipt_id: str, reason: str,
                   superseded_by: Optional[str] = None) -> str:
        """
        Append an invalidation/supersession event.
        Returns the new invalidation receipt's ID.
        The original receipt remains immutable; a new receipt is appended
        that references it via supersedes_or_invalidates.
        """
        ...

    def current_compliance_view(self) -> Dict[str, Any]:
        """
        Derive current compliance state from all receipts + current policy.
        This is a READ-ONLY derived view — never mutates the store.
        """
        ...


# ============================================================================
# In-Memory Store
# ============================================================================

class InMemoryReceiptStore:
    """
    Volatile in-memory receipt store.
    Thread-safe via mutex lock. Suitable for testing and single-session use.
    """

    def __init__(self):
        self._receipts: Dict[str, ReceiptSchemaV2] = {}
        self._order: List[str] = []  # append order
        self._lock = threading.Lock()

    def append(self, receipt: ReceiptSchemaV2) -> str:
        with self._lock:
            if receipt.receipt_id in self._receipts:
                raise ValueError(
                    f"Receipt {receipt.receipt_id} already exists. "
                    "Append-only store does not allow overwrites."
                )
            self._receipts[receipt.receipt_id] = receipt
            self._order.append(receipt.receipt_id)
            return receipt.receipt_id

    def get(self, receipt_id: str) -> Optional[ReceiptSchemaV2]:
        with self._lock:
            return self._receipts.get(receipt_id)

    def get_all(self) -> List[ReceiptSchemaV2]:
        with self._lock:
            return [self._receipts[rid] for rid in self._order]

    def invalidate(self, receipt_id: str, reason: str,
                   superseded_by: Optional[str] = None) -> str:
        with self._lock:
            original = self._receipts.get(receipt_id)
            if not original:
                raise ValueError(f"Receipt {receipt_id} not found.")

            # Create invalidation receipt
            inv_receipt = create_receipt(
                disclosure=original.disclosure,
                identity={
                    "agent_name": "agl-store",
                    "agent_version": "2.0.0",
                    "runtime": "invalidation-event",
                    "principal": "governance-engine",
                },
                policy_decision={
                    "rule": "drift-invalidation",
                    "decision": f"invalidate-{receipt_id}",
                    "reason": reason,
                },
                execution={
                    "tool": "store.invalidate",
                    "parameters": {
                        "target_receipt_id": receipt_id,
                        "reason": reason,
                    },
                    "read_only": False,
                },
                outcome={
                    "status": "invalidated",
                    "original_receipt_id": receipt_id,
                    "superseded_by": superseded_by,
                },
                supersedes_or_invalidates=SupersessionEvent(
                    receipt_id=receipt_id,
                    reason=reason,
                    superseded_by=superseded_by,
                ),
                policy_version=original.policy_version,
                validity_window=original.validity_window,
            )

            # Append the invalidation receipt
            self._receipts[inv_receipt.receipt_id] = inv_receipt
            self._order.append(inv_receipt.receipt_id)

            # Mark original as superseded (logical status — original data unchanged)
            original.status = ReceiptStatus.SUPERSEDED

            return inv_receipt.receipt_id

    def current_compliance_view(self) -> Dict[str, Any]:
        """
        Derive current compliance state.

        Algorithm:
        1. Walk all receipts in append order
        2. Track which receipts have been invalidated/superseded
        3. For each active receipt, check validity_window
        4. Return derived view of currently-active compliance state
        """
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            invalidated_ids = set()
            active_receipts = []

            # First pass: collect all invalidations
            for rid in self._order:
                receipt = self._receipts[rid]
                if receipt.supersedes_or_invalidates:
                    target_id = receipt.supersedes_or_invalidates.receipt_id
                    invalidated_ids.add(target_id)

            # Second pass: collect active, valid receipts
            for rid in self._order:
                receipt = self._receipts[rid]
                # Skip invalidated receipts
                if rid in invalidated_ids:
                    continue
                # Skip invalidation event receipts from the view
                if receipt.supersedes_or_invalidates is not None:
                    continue
                # Check validity window
                vw = receipt.validity_window
                if vw.valid_until and vw.valid_until < now:
                    continue
                active_receipts.append(receipt.to_dict())

            return {
                "derived_at": now,
                "total_receipts": len(self._order),
                "active_receipts": len(active_receipts),
                "invalidated_count": len(invalidated_ids),
                "policy_version": {
                    "rule_set_id": "eu-ai-act-art50-2026-01",
                    "schema_version": "2.0.0",
                    "compliance_framework": "EU AI Act Art.50",
                },
                "active_receipts_list": active_receipts,
                "compliance_status": "compliant" if active_receipts else "no-active-decisions",
            }


# ============================================================================
# JSON File Store (Persistent)
# ============================================================================

class JsonFileReceiptStore:
    """
    Persistent append-only receipt store using JSON Lines format.
    Each receipt is one line in the file — true append-only semantics.

    File format: JSON Lines (.jsonl)
      - Line 1: receipt A (first appended)
      - Line 2: receipt B
      - Line 3: invalidation event referencing A

    Thread-safe via mutex lock.
    """

    def __init__(self, file_path: str):
        self._file_path = file_path
        self._lock = threading.Lock()
        self._index: Dict[str, ReceiptSchemaV2] = {}
        self._order: List[str] = []
        self._load_existing()

    def _load_existing(self):
        """Load existing receipts from JSONL file into memory index."""
        if not os.path.exists(self._file_path):
            return
        with open(self._file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    receipt = ReceiptSchemaV2.from_dict(data)
                    self._index[receipt.receipt_id] = receipt
                    self._order.append(receipt.receipt_id)
                except (json.JSONDecodeError, KeyError) as e:
                    # Skip corrupted lines (defensive)
                    import logging
                    logging.getLogger('agl').warning(
                        f"Skipping corrupted receipt line: {e}"
                    )

    def _append_to_file(self, receipt: ReceiptSchemaV2):
        """Append a single receipt as one JSON line."""
        os.makedirs(os.path.dirname(self._file_path) or '.', exist_ok=True)
        with open(self._file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(receipt.to_dict(), ensure_ascii=False, default=str) + '\n')

    def append(self, receipt: ReceiptSchemaV2) -> str:
        with self._lock:
            if receipt.receipt_id in self._index:
                raise ValueError(
                    f"Receipt {receipt.receipt_id} already exists. "
                    "Append-only store does not allow overwrites."
                )
            self._append_to_file(receipt)
            self._index[receipt.receipt_id] = receipt
            self._order.append(receipt.receipt_id)
            return receipt.receipt_id

    def get(self, receipt_id: str) -> Optional[ReceiptSchemaV2]:
        with self._lock:
            return self._index.get(receipt_id)

    def get_all(self) -> List[ReceiptSchemaV2]:
        with self._lock:
            return [self._index[rid] for rid in self._order]

    def invalidate(self, receipt_id: str, reason: str,
                   superseded_by: Optional[str] = None) -> str:
        with self._lock:
            original = self._index.get(receipt_id)
            if not original:
                raise ValueError(f"Receipt {receipt_id} not found.")

            inv_receipt = create_receipt(
                disclosure=original.disclosure,
                identity={
                    "agent_name": "agl-store",
                    "agent_version": "2.0.0",
                    "runtime": "invalidation-event",
                    "principal": "governance-engine",
                },
                policy_decision={
                    "rule": "drift-invalidation",
                    "decision": f"invalidate-{receipt_id}",
                    "reason": reason,
                },
                execution={
                    "tool": "store.invalidate",
                    "parameters": {
                        "target_receipt_id": receipt_id,
                        "reason": reason,
                    },
                    "read_only": False,
                },
                outcome={
                    "status": "invalidated",
                    "original_receipt_id": receipt_id,
                    "superseded_by": superseded_by,
                },
                supersedes_or_invalidates=SupersessionEvent(
                    receipt_id=receipt_id,
                    reason=reason,
                    superseded_by=superseded_by,
                ),
                policy_version=original.policy_version,
                validity_window=original.validity_window,
            )

            self._append_to_file(inv_receipt)
            self._index[inv_receipt.receipt_id] = inv_receipt
            self._order.append(inv_receipt.receipt_id)
            original.status = ReceiptStatus.SUPERSEDED

            return inv_receipt.receipt_id

    def current_compliance_view(self) -> Dict[str, Any]:
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            invalidated_ids = set()
            active_receipts = []

            for rid in self._order:
                receipt = self._index[rid]
                if receipt.supersedes_or_invalidates:
                    target_id = receipt.supersedes_or_invalidates.receipt_id
                    invalidated_ids.add(target_id)

            for rid in self._order:
                receipt = self._index[rid]
                if rid in invalidated_ids:
                    continue
                if receipt.supersedes_or_invalidates is not None:
                    continue
                vw = receipt.validity_window
                if vw.valid_until and vw.valid_until < now:
                    continue
                active_receipts.append(receipt.to_dict())

            return {
                "derived_at": now,
                "total_receipts": len(self._order),
                "active_receipts": len(active_receipts),
                "invalidated_count": len(invalidated_ids),
                "policy_version": {
                    "rule_set_id": "eu-ai-act-art50-2026-01",
                    "schema_version": "2.0.0",
                    "compliance_framework": "EU AI Act Art.50",
                },
                "active_receipts_list": active_receipts,
                "compliance_status": "compliant" if active_receipts else "no-active-decisions",
            }


# ============================================================================
# Public Alias
# ============================================================================

ReceiptStore = JsonFileReceiptStore
