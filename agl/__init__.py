"""
AGL (Accountability-Governance Layer) — Receipt Schema v2.0
============================================================
Drift-aware receipt system for Enterprise AI OS Layer ⑦ governance.

Core principle: Never rewrite old receipts. Append invalidation/supersession
events so current compliance state becomes a derived view over
immutable receipts + current policy.

Reference: enterprise-ai-os-architecture Issue #1 feedback from hegu-1.
"""

from agl.receipt_schema_v2 import (
    ReceiptSchemaV2,
    PolicyVersion,
    ValidityWindow,
    SupersessionEvent,
    create_receipt,
)
from agl.receipt_store import ReceiptStore

__version__ = "2.0.0"
__all__ = [
    "ReceiptSchemaV2",
    "PolicyVersion",
    "ValidityWindow",
    "SupersessionEvent",
    "create_receipt",
    "ReceiptStore",
]
