from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from turn_obligation_adapter import (
    RecursiveFieldTurnObligationAdapter,
    TurnObligationAdapterError,
)


ROOT = Path(__file__).resolve().parent
OBLIGATION_ID = "11111111-1111-4111-8111-111111111111"
INGRESS_ID = "22222222-2222-4222-8222-222222222222"
INTENT_ID = "33333333-3333-4333-8333-333333333333"
CHECKPOINT_ID = "44444444-4444-4444-8444-444444444444"
AT = "2026-10-28T20:00:00Z"


def event() -> dict:
    return {
        "obligation_id": OBLIGATION_ID,
        "context_id": "opaque-context.01",
        "ingress_id": INGRESS_ID,
        "ingress_sha256": "a" * 64,
        "projection_sha256": "b" * 64,
        "ingressed_at": AT,
        "ingress_identity": "agent-zero:communicate:user-message",
        "recorded_at": AT,
    }


def checkpoint_evidence() -> dict:
    return {
        "evidence_type": "checkpoint_planted",
        "intent_id": INTENT_ID,
        "checkpoint_id": CHECKPOINT_ID,
        "checkpoint_sha256": "c" * 64,
        "planted_at": "2026-10-28T20:00:02Z",
    }


class RecursiveFieldTurnObligationAdapterTest(unittest.TestCase):
    def setUp(self):
        self.adapter = RecursiveFieldTurnObligationAdapter(ROOT)

    def test_ordinary_ingress_is_unbound_schema_1_1(self):
        record = self.adapter.build_ordinary_ingress(event())
        self.assertEqual(record["schema_version"], "1.1.0")
        self.assertEqual(record["state"], "open")
        self.assertEqual(record["lineage"]["lineage_mode"], "ordinary_ingress")
        self.assertEqual(record["lineage"]["context_id"], "opaque-context.01")
        self.assertNotIn("intent_id", record["lineage"])
        self.adapter.validate_record(record)

    def test_terminal_close_claims_persistence_only(self):
        initial = self.adapter.build_ordinary_ingress(event())
        active = self.adapter.advance_processing(
            initial, recorded_at="2026-10-28T20:00:01Z"
        )
        closed = self.adapter.close_terminal(
            active,
            message_ref="assistant-history-id",
            persisted_at="2026-10-28T20:00:02Z",
        )
        self.adapter.validate_transition(active, closed)
        evidence = closed["closure_evidence"]
        self.assertEqual(evidence["evidence_type"], "terminal_response_emitted")
        self.assertIs(evidence["delivery_claimed"], False)
        self.assertIs(evidence["human_observation_claimed"], False)
        self.assertEqual(closed["objective_status"], "incomplete")

    def test_checkpoint_handoff_binds_real_lineage_without_rebinding(self):
        initial = self.adapter.build_ordinary_ingress(event())
        waiting = self.adapter.apply_handoff(
            initial,
            evidence=checkpoint_evidence(),
            recorded_at="2026-10-28T20:00:02Z",
        )
        self.adapter.validate_transition(initial, waiting)
        self.assertEqual(waiting["lineage"]["lineage_mode"], "bound")
        self.assertEqual(waiting["lineage"]["intent_id"], INTENT_ID)
        changed = copy.deepcopy(checkpoint_evidence())
        changed["checkpoint_id"] = "55555555-5555-4555-8555-555555555555"
        with self.assertRaises(Exception):
            self.adapter.apply_handoff(
                waiting,
                evidence=changed,
                recorded_at="2026-10-28T20:00:03Z",
            )

    def test_protocol_reflex_requires_unique_bound_waiting_head_and_no_child(self):
        initial = self.adapter.build_ordinary_ingress(event())
        with self.assertRaisesRegex(TurnObligationAdapterError, "no bound waiting"):
            self.adapter.select_protocol_reflex(
                (initial,),
                formation_binding={
                    "intent_id": INTENT_ID,
                    "checkpoint": {
                        "checkpoint_id": CHECKPOINT_ID,
                        "checkpoint_sha256": "c" * 64,
                        "sequence": 1,
                    },
                },
            )
        waiting = self.adapter.apply_handoff(
            initial,
            evidence=checkpoint_evidence(),
            recorded_at="2026-10-28T20:00:02Z",
        )
        selected = self.adapter.select_protocol_reflex(
            (waiting,),
            formation_binding={
                "intent_id": INTENT_ID,
                "checkpoint": {
                    "checkpoint_id": CHECKPOINT_ID,
                    "checkpoint_sha256": "c" * 64,
                    "sequence": 1,
                },
            },
        )
        active = self.adapter.advance_protocol_reflex(
            selected, recorded_at="2026-10-28T20:00:03Z"
        )
        self.adapter.validate_transition(waiting, active)
        self.assertEqual(active["obligation_id"], waiting["obligation_id"])
        self.assertEqual(active["phase_generation"], waiting["phase_generation"] + 1)
        self.assertEqual(active["generation"], waiting["generation"] + 1)

    def test_hash_tamper_and_foreign_genesis_are_rejected(self):
        record = self.adapter.build_ordinary_ingress(event())
        tampered = copy.deepcopy(record)
        tampered["lineage"]["ingress"]["projection_sha256"] = "f" * 64
        with self.assertRaises(Exception):
            self.adapter.validate_record(tampered)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = json.loads((ROOT / ".recursive-field-root").read_text())
            marker["genesis_uuid"] = "66666666-6666-4666-8666-666666666666"
            (root / ".recursive-field-root").write_text(json.dumps(marker), encoding="utf-8")
            foreign = RecursiveFieldTurnObligationAdapter(
                root, contracts=self.adapter.contracts
            )
            with self.assertRaisesRegex(TurnObligationAdapterError, "another field genesis"):
                foreign.validate_record(record)

    def test_tracked_hook_is_install_source_not_active_project_state(self):
        hook = ROOT / "agent_zero_extensions/turn_obligation_contract/_10_recursive_field.py"
        self.assertTrue(hook.is_file())
        self.assertFalse(
            (ROOT / ".a0proj/extensions/python/turn_obligation_contract/_10_recursive_field.py").exists()
        )
        text = hook.read_text(encoding="utf-8")
        self.assertNotIn("/a0/usr/projects/recursive-field", text)
        self.assertIn("turn_obligation_adapter.py", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
