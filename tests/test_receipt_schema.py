"""
Unit tests for AGL Receipt Schema v2.0 and Receipt Store.
=========================================================
Tests cover:
  - Receipt creation and serialization
  - Append-only immutability
  - Invalidation chain
  - Derived view correctness
  - Drift-aware fields
  - JSON file persistence
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta

# Ensure project root is on path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from agl.receipt_schema_v2 import (
    ReceiptSchemaV2,
    PolicyVersion,
    ValidityWindow,
    SupersessionEvent,
    ReceiptStatus,
    create_receipt,
    create_bde_receipt,
    generate_uuid_v7,
)
from agl.receipt_store import InMemoryReceiptStore, JsonFileReceiptStore


class TestReceiptCreation(unittest.TestCase):
    """Test receipt creation and serialization."""

    def test_create_receipt_with_defaults(self):
        """Receipt can be created with minimal params and defaults are populated."""
        receipt = create_receipt(
            disclosure={"generated_by": "test", "assessment_type": "test", "ai_system": True},
            identity={"agent_name": "test-agent", "agent_version": "1.0"},
            policy_decision={"rule": "test-rule", "decision": "approve"},
            execution={"tool": "test_tool"},
            outcome={"status": "completed"},
        )
        self.assertIsNotNone(receipt.receipt_id)
        self.assertIsNotNone(receipt.timestamp)
        self.assertIsNotNone(receipt.content_hash)
        self.assertEqual(receipt.status, ReceiptStatus.ACTIVE)
        self.assertIsNotNone(receipt.policy_version)
        self.assertIsNotNone(receipt.validity_window)
        self.assertIsNone(receipt.supersedes_or_invalidates)

    def test_receipt_to_dict_roundtrip(self):
        """Receipt survives serialization/deserialization roundtrip."""
        original = create_receipt(
            disclosure={"generated_by": "test", "assessment_type": "test", "ai_system": True},
            identity={"agent_name": "test-agent", "agent_version": "1.0"},
            policy_decision={"rule": "test-rule", "decision": "approve"},
            execution={"tool": "test_tool"},
            outcome={"status": "completed"},
        )
        d = original.to_dict()
        restored = ReceiptSchemaV2.from_dict(d)
        self.assertEqual(original.receipt_id, restored.receipt_id)
        self.assertEqual(original.content_hash, restored.content_hash)
        self.assertEqual(original.disclosure, restored.disclosure)

    def test_create_bde_receipt(self):
        """BDE convenience factory creates valid receipt."""
        receipt = create_bde_receipt(
            tool_name="get_bde_score",
            tool_params={"market": "US"},
            result_summary={"count": 25, "top_score": 92.5},
        )
        self.assertEqual(receipt.execution["tool"], "get_bde_score")
        self.assertEqual(receipt.identity["agent_name"], "bde-score-mcp-server")
        self.assertIn("eu_ai_act_art50", receipt.disclosure)

    def test_content_hash_changes_with_content(self):
        """Different content produces different hashes."""
        r1 = create_receipt(
            disclosure={"a": 1},
            identity={"agent_name": "test", "agent_version": "1.0"},
            policy_decision={"rule": "r1", "decision": "d1"},
            execution={"tool": "t1"},
            outcome={"status": "completed"},
        )
        r2 = create_receipt(
            disclosure={"a": 2},
            identity={"agent_name": "test", "agent_version": "1.0"},
            policy_decision={"rule": "r1", "decision": "d1"},
            execution={"tool": "t1"},
            outcome={"status": "completed"},
        )
        self.assertNotEqual(r1.content_hash, r2.content_hash)

    def test_policy_version_fields(self):
        """Policy version drift-aware field is correctly structured."""
        pv = PolicyVersion(
            rule_set_id="eu-ai-act-art50-2026-06",
            schema_version="2.0.0",
            compliance_framework="EU AI Act Art.50",
            effective_from="2026-06-01T00:00:00+00:00",
        )
        d = pv.to_dict()
        self.assertEqual(d["rule_set_id"], "eu-ai-act-art50-2026-06")
        self.assertEqual(d["schema_version"], "2.0.0")

    def test_validity_window_fields(self):
        """Validity window drift-aware field is correctly structured."""
        now = datetime.now(timezone.utc)
        vw = ValidityWindow(
            valid_from=now.isoformat(),
            valid_until=(now + timedelta(hours=24)).isoformat(),
            context={"market": "US", "symbol": "AAPL"},
        )
        d = vw.to_dict()
        self.assertEqual(d["context"]["symbol"], "AAPL")
        self.assertIsNotNone(d["valid_until"])

    def test_supersession_event(self):
        """Supersession event correctly references another receipt."""
        se = SupersessionEvent(
            receipt_id="abc-123",
            reason="Policy update",
            superseded_by="def-456",
        )
        d = se.to_dict()
        self.assertEqual(d["receipt_id"], "abc-123")
        self.assertEqual(d["reason"], "Policy update")


class TestAppendOnlyImmutability(unittest.TestCase):
    """Test that receipts cannot be modified once appended."""

    def setUp(self):
        self.store = InMemoryReceiptStore()

    def test_append_returns_id(self):
        """Append returns the receipt_id."""
        receipt = create_receipt(
            disclosure={"generated_by": "test"},
            identity={"agent_name": "test", "agent_version": "1.0"},
            policy_decision={"rule": "r", "decision": "d"},
            execution={"tool": "t"},
            outcome={"status": "completed"},
        )
        rid = self.store.append(receipt)
        self.assertEqual(rid, receipt.receipt_id)

    def test_duplicate_append_raises(self):
        """Appending the same receipt twice raises ValueError."""
        receipt = create_receipt(
            disclosure={"generated_by": "test"},
            identity={"agent_name": "test", "agent_version": "1.0"},
            policy_decision={"rule": "r", "decision": "d"},
            execution={"tool": "t"},
            outcome={"status": "completed"},
        )
        self.store.append(receipt)
        with self.assertRaises(ValueError) as ctx:
            self.store.append(receipt)
        self.assertIn("already exists", str(ctx.exception))

    def test_get_returns_correct_receipt(self):
        """Get retrieves the correct receipt by ID."""
        receipt = create_receipt(
            disclosure={"generated_by": "test"},
            identity={"agent_name": "test", "agent_version": "1.0"},
            policy_decision={"rule": "r", "decision": "d"},
            execution={"tool": "my_tool"},
            outcome={"status": "completed"},
        )
        self.store.append(receipt)
        fetched = self.store.get(receipt.receipt_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.execution["tool"], "my_tool")

    def test_get_nonexistent_returns_none(self):
        """Get returns None for unknown receipt ID."""
        self.assertIsNone(self.store.get("nonexistent-id"))

    def test_get_all_preserves_order(self):
        """get_all returns receipts in append order."""
        ids = []
        for i in range(5):
            r = create_receipt(
                disclosure={"idx": i},
                identity={"agent_name": "test", "agent_version": "1.0"},
                policy_decision={"rule": "r", "decision": "d"},
                execution={"tool": f"tool_{i}"},
                outcome={"status": "completed"},
            )
            self.store.append(r)
            ids.append(r.receipt_id)

        all_receipts = self.store.get_all()
        self.assertEqual(len(all_receipts), 5)
        for i, r in enumerate(all_receipts):
            self.assertEqual(r.receipt_id, ids[i])


class TestInvalidationChain(unittest.TestCase):
    """Test invalidation/supersession creates new receipt, doesn't modify old."""

    def setUp(self):
        self.store = InMemoryReceiptStore()
        self.original = create_receipt(
            disclosure={"generated_by": "BDE v1.0"},
            identity={"agent_name": "test", "agent_version": "1.0"},
            policy_decision={"rule": "score-rule", "decision": "approve"},
            execution={"tool": "get_bde_score"},
            outcome={"status": "completed", "score": 85},
        )
        self.store.append(self.original)

    def test_invalidate_creates_new_receipt(self):
        """Invalidation appends a new receipt, doesn't delete the old one."""
        inv_id = self.store.invalidate(self.original.receipt_id, "Policy update v2")
        self.assertIsNotNone(inv_id)
        self.assertNotEqual(inv_id, self.original.receipt_id)
        # Original still retrievable
        original = self.store.get(self.original.receipt_id)
        self.assertIsNotNone(original)

    def test_invalidation_receipt_has_supersession(self):
        """The invalidation receipt references the original."""
        inv_id = self.store.invalidate(self.original.receipt_id, "Policy drift detected")
        inv_receipt = self.store.get(inv_id)
        self.assertIsNotNone(inv_receipt.supersedes_or_invalidates)
        self.assertEqual(
            inv_receipt.supersedes_or_invalidates.receipt_id,
            self.original.receipt_id,
        )
        self.assertEqual(
            inv_receipt.supersedes_or_invalidates.reason,
            "Policy drift detected",
        )

    def test_original_marked_superseded(self):
        """After invalidation, original receipt status is SUPERSEDED."""
        self.store.invalidate(self.original.receipt_id, "Superseded by new policy")
        self.assertEqual(self.original.status, ReceiptStatus.SUPERSEDED)

    def test_invalidate_nonexistent_raises(self):
        """Invalidating a nonexistent receipt raises ValueError."""
        with self.assertRaises(ValueError):
            self.store.invalidate("nonexistent-id", "reason")

    def test_chain_of_invalidations(self):
        """Multiple invalidations create a chain of events."""
        # Use a fresh store to avoid setUp's receipt
        fresh_store = InMemoryReceiptStore()
        r1 = create_receipt(
            disclosure={"v": 1},
            identity={"agent_name": "test", "agent_version": "1.0"},
            policy_decision={"rule": "r", "decision": "d"},
            execution={"tool": "t1"},
            outcome={"status": "completed"},
        )
        fresh_store.append(r1)
        inv1_id = fresh_store.invalidate(r1.receipt_id, "First invalidation")
        inv2_id = fresh_store.invalidate(r1.receipt_id, "Second invalidation")

        all_receipts = fresh_store.get_all()
        # 1 original + 2 invalidation events = 3
        self.assertEqual(len(all_receipts), 3)

    def test_total_receipt_count_after_invalidation(self):
        """Store count increases by 1 per invalidation."""
        initial_count = len(self.store.get_all())
        self.store.invalidate(self.original.receipt_id, "Test")
        self.assertEqual(len(self.store.get_all()), initial_count + 1)


class TestDerivedView(unittest.TestCase):
    """Test current_compliance_view derived view."""

    def setUp(self):
        self.store = InMemoryReceiptStore()

    def _make_receipt(self, tool_name="test_tool", valid_hours=24):
        now = datetime.now(timezone.utc)
        return create_receipt(
            disclosure={"generated_by": "test"},
            identity={"agent_name": "test", "agent_version": "1.0"},
            policy_decision={"rule": "r", "decision": "d"},
            execution={"tool": tool_name},
            outcome={"status": "completed"},
            validity_window=ValidityWindow(
                valid_from=now.isoformat(),
                valid_until=(now + timedelta(hours=valid_hours)).isoformat(),
                context={"scope": "test"},
            ),
        )

    def test_empty_store_view(self):
        """Empty store returns no-active-decisions status."""
        view = self.store.current_compliance_view()
        self.assertEqual(view["compliance_status"], "no-active-decisions")
        self.assertEqual(view["total_receipts"], 0)
        self.assertEqual(view["active_receipts"], 0)

    def test_active_receipt_in_view(self):
        """Active receipt with valid window appears in derived view."""
        r = self._make_receipt()
        self.store.append(r)
        view = self.store.current_compliance_view()
        self.assertEqual(view["compliance_status"], "compliant")
        self.assertEqual(view["active_receipts"], 1)
        self.assertEqual(view["total_receipts"], 1)

    def test_invalidated_receipt_excluded_from_view(self):
        """After invalidation, original is excluded from derived view."""
        r = self._make_receipt()
        self.store.append(r)
        self.store.invalidate(r.receipt_id, "Policy update")

        view = self.store.current_compliance_view()
        self.assertEqual(view["active_receipts"], 0)
        self.assertEqual(view["invalidated_count"], 1)
        self.assertEqual(view["total_receipts"], 2)  # original + invalidation event

    def test_expired_receipt_excluded_from_view(self):
        """Receipt past its validity_window is excluded from derived view."""
        now = datetime.now(timezone.utc)
        expired = create_receipt(
            disclosure={"generated_by": "test"},
            identity={"agent_name": "test", "agent_version": "1.0"},
            policy_decision={"rule": "r", "decision": "d"},
            execution={"tool": "expired_tool"},
            outcome={"status": "completed"},
            validity_window=ValidityWindow(
                valid_from=(now - timedelta(hours=48)).isoformat(),
                valid_until=(now - timedelta(hours=24)).isoformat(),
                context={"scope": "expired"},
            ),
        )
        self.store.append(expired)
        view = self.store.current_compliance_view()
        self.assertEqual(view["active_receipts"], 0)

    def test_mixed_active_and_invalidated(self):
        """Derived view correctly filters mixed active/invalidated receipts."""
        r1 = self._make_receipt(tool_name="tool_1")
        r2 = self._make_receipt(tool_name="tool_2")
        self.store.append(r1)
        self.store.append(r2)
        self.store.invalidate(r1.receipt_id, "Superseded")

        view = self.store.current_compliance_view()
        self.assertEqual(view["active_receipts"], 1)
        self.assertEqual(view["invalidated_count"], 1)

    def test_view_includes_policy_version(self):
        """Derived view includes current policy version info."""
        view = self.store.current_compliance_view()
        self.assertIn("policy_version", view)
        self.assertIn("schema_version", view["policy_version"])


class TestJsonFileStore(unittest.TestCase):
    """Test JSON file persistence store."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._filepath = os.path.join(self._tmpdir, "receipts.jsonl")
        self.store = JsonFileReceiptStore(self._filepath)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_persist_and_reload(self):
        """Receipts survive store restart (file reload)."""
        r = create_receipt(
            disclosure={"generated_by": "persist-test"},
            identity={"agent_name": "test", "agent_version": "1.0"},
            policy_decision={"rule": "r", "decision": "d"},
            execution={"tool": "persist_tool"},
            outcome={"status": "completed"},
        )
        self.store.append(r)

        # Create new store instance pointing to same file
        store2 = JsonFileReceiptStore(self._filepath)
        loaded = store2.get(r.receipt_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.execution["tool"], "persist_tool")

    def test_file_is_jsonl(self):
        """File is valid JSON Lines format."""
        r1 = create_receipt(
            disclosure={"idx": 1},
            identity={"agent_name": "test", "agent_version": "1.0"},
            policy_decision={"rule": "r", "decision": "d"},
            execution={"tool": "t1"},
            outcome={"status": "completed"},
        )
        r2 = create_receipt(
            disclosure={"idx": 2},
            identity={"agent_name": "test", "agent_version": "1.0"},
            policy_decision={"rule": "r", "decision": "d"},
            execution={"tool": "t2"},
            outcome={"status": "completed"},
        )
        self.store.append(r1)
        self.store.append(r2)

        with open(self._filepath, 'r') as f:
            lines = [l for l in f.readlines() if l.strip()]
        self.assertEqual(len(lines), 2)
        for line in lines:
            parsed = json.loads(line)
            self.assertIn("receipt_id", parsed)

    def test_duplicate_after_reload_rejected(self):
        """Duplicate detection works even after store reload."""
        r = create_receipt(
            disclosure={"generated_by": "dup-test"},
            identity={"agent_name": "test", "agent_version": "1.0"},
            policy_decision={"rule": "r", "decision": "d"},
            execution={"tool": "dup_tool"},
            outcome={"status": "completed"},
        )
        self.store.append(r)
        store2 = JsonFileReceiptStore(self._filepath)
        with self.assertRaises(ValueError):
            store2.append(r)


class TestUUIDv7(unittest.TestCase):
    """Test UUID generation."""

    def test_uuid_is_string(self):
        uid = generate_uuid_v7()
        self.assertIsInstance(uid, str)

    def test_uuids_are_unique(self):
        uids = {generate_uuid_v7() for _ in range(100)}
        self.assertEqual(len(uids), 100)

    def test_uuid_is_time_sortable(self):
        """UUIDs generated later should sort after earlier ones (v7 property)."""
        import time
        uid1 = generate_uuid_v7()
        time.sleep(0.01)
        uid2 = generate_uuid_v7()
        self.assertLess(uid1, uid2)


class TestJSONSchema(unittest.TestCase):
    """Test that JSON Schema file is valid and consistent."""

    def test_schema_is_valid_json(self):
        """Schema file is valid JSON."""
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "agl", "receipt_schema_v2.schema.json"
        )
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        self.assertEqual(schema["title"], "AGL Receipt Schema v2.0")
        self.assertIn("policy_version", schema["properties"])
        self.assertIn("validity_window", schema["properties"])
        self.assertIn("supersedes_or_invalidates", schema["properties"])

    def test_receipt_validates_against_schema_structure(self):
        """Receipt dict has all required fields from schema."""
        receipt = create_receipt(
            disclosure={"generated_by": "test", "assessment_type": "test", "ai_system": True},
            identity={"agent_name": "test", "agent_version": "1.0"},
            policy_decision={"rule": "r", "decision": "d"},
            execution={"tool": "t"},
            outcome={"status": "completed"},
        )
        d = receipt.to_dict()
        # Check all required fields exist
        for field in ["receipt_id", "timestamp", "disclosure", "identity",
                       "policy_decision", "execution", "outcome", "on_chain",
                       "policy_version", "validity_window", "status", "content_hash"]:
            self.assertIn(field, d, f"Missing required field: {field}")


if __name__ == "__main__":
    unittest.main()
