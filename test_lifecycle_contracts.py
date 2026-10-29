#!/usr/bin/env python3
"""Deterministic tests for the three non-actuating lifecycle records."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from lifecycle_contracts import (
    AuthorizationFreshness,
    LifecycleConflictError,
    LifecycleContractError,
    advance_execution_result,
    advance_turn_obligation,
    build_execution_result,
    build_turn_obligation,
    domain_sha256,
    mint_execution_authorization,
    validate_authorization_freshness,
    validate_execution_authorization,
    validate_execution_result,
    validate_result_transition,
    validate_turn_obligation,
    validate_turn_transition,
)

ROOT = Path(__file__).resolve().parent
U = {
    "field": "00000000-0000-4000-8000-000000000001",
    "obligation": "00000000-0000-4000-8000-000000000002",
    "intent": "00000000-0000-4000-8000-000000000003",
    "checkpoint": "00000000-0000-4000-8000-000000000004",
    "authorization": "00000000-0000-4000-8000-000000000005",
    "attempt": "00000000-0000-4000-8000-000000000006",
    "boot": "00000000-0000-4000-8000-000000000007",
    "result": "00000000-0000-4000-8000-000000000008",
    "run": "00000000-0000-4000-8000-000000000009",
    "claim": "00000000-0000-4000-8000-00000000000a",
    "gate": "00000000-0000-4000-8000-00000000000b",
    "reconcile": "00000000-0000-4000-8000-00000000000c",
}
H = {
    "checkpoint": "1" * 64,
    "config": "2" * 64,
    "policy": "3" * 64,
    "file": "4" * 64,
    "ledger": "5" * 64,
    "outcome": "6" * 64,
}


def sorted_evidence() -> list[dict]:
    values = [
        {"evidence_type": "file_exists", "path": "state/report.json", "expected_exists": True},
        {"evidence_type": "sha256_match", "path": "state/report.json", "expected_sha256": H["file"]},
        {
            "evidence_type": "ledger_entry_present",
            "ledger_path": "state/ledger.jsonl",
            "entry_id": "entry-1",
            "entry_sha256": H["ledger"],
        },
    ]
    return sorted(values, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


class LifecycleFixture(unittest.TestCase):
    def obligation(self):
        return build_turn_obligation(
            obligation_id=U["obligation"],
            field_genesis_uuid=U["field"],
            context_id="opaque context/id + punctuation",
            intent_id=U["intent"],
            checkpoint_id=U["checkpoint"],
            checkpoint_sha256=H["checkpoint"],
            recorded_at="2026-01-01T00:00:00+00:00",
        )

    def authorization(self):
        return mint_execution_authorization(
            authorization_id=U["authorization"],
            adapter_id="inspect_unit_cell",
            adapter_version="1.0.0",
            payload={},
            target_identity="field-sentinel",
            target_namespace="agents",
            acting_identity="formation-policy",
            acting_namespace="state/policy",
            security_profile="restricted",
            security_config_path="state/control_profile.json",
            security_config_sha256=H["config"],
            field_id="recursive-field",
            field_genesis_uuid=U["field"],
            obligation_id=U["obligation"],
            phase_generation=1,
            context_id="opaque context/id + punctuation",
            intent_id=U["intent"],
            intent_generation=4,
            checkpoint_id=U["checkpoint"],
            checkpoint_sha256=H["checkpoint"],
            checkpoint_sequence=7,
            lease={
                "holder": "formation-worker",
                "attempt_id": U["attempt"],
                "generation": 3,
                "boot_id": U["boot"],
                "acquired_at": "2026-01-01T00:00:00+00:00",
                "expires_at": "2026-01-01T00:10:00+00:00",
            },
            effect_class="observation",
            expected_evidence=sorted_evidence(),
            issued_at="2026-01-01T00:01:00+00:00",
            not_before="2026-01-01T00:01:00+00:00",
            expires_at="2026-01-01T00:09:00+00:00",
            issuer_id="formation-policy",
            policy_id="mvp-observation-policy",
            policy_version="1.0.0",
            policy_sha256=H["policy"],
        )

    def freshness(self, **changes):
        values = {
            "observed_at": "2026-01-01T00:02:00+00:00",
            "boot_id": U["boot"],
            "security_profile": "restricted",
            "security_config_path": "state/control_profile.json",
            "security_config_sha256": H["config"],
            "lease_generation": 3,
            "intent_generation": 4,
            "phase_generation": 1,
        }
        values.update(changes)
        return AuthorizationFreshness(**values)

    def claim(self):
        return {
            "claim_id": U["claim"],
            "holder": "formation-worker",
            "lease_generation": 3,
            "boot_id": U["boot"],
            "claimed_at": "2026-01-01T00:02:00+00:00",
            "expires_at": "2026-01-01T00:08:00+00:00",
        }


class CanonicalAndTurnTests(LifecycleFixture):
    def test_domain_hash_is_canonical_repeatable_and_separated(self):
        left = domain_sha256("a", {"é": [1, True], "a": 2})
        right = domain_sha256("a", {"a": 2, "é": [1, True]})
        self.assertEqual(left, right)
        self.assertNotEqual(left, domain_sha256("b", {"a": 2, "é": [1, True]}))
        with self.assertRaises(ValueError):
            domain_sha256("a", {"bad": float("nan")})

    def test_opaque_context_is_not_uuid_only(self):
        record = self.obligation()
        self.assertEqual(record.context_id, "opaque context/id + punctuation")
        validate_turn_obligation(record.to_document())

    def test_all_five_closed_evidence_variants(self):
        initial = self.obligation()
        cases = [
            (
                "waiting",
                {"evidence_type": "checkpoint_planted", "checkpoint_id": U["checkpoint"], "checkpoint_sha256": H["checkpoint"], "planted_at": "2026-01-01T00:01:00+00:00"},
                "incomplete",
            ),
            (
                "awaiting_human",
                {"evidence_type": "human_gate_reached", "gate_id": U["gate"], "reason_code": "authority_required", "reached_at": "2026-01-01T00:01:00+00:00", "human_observation_claimed": False},
                "incomplete",
            ),
            (
                "handed_off",
                {"evidence_type": "handed_off_to_intent", "intent_id": U["intent"], "checkpoint_id": U["checkpoint"], "checkpoint_sha256": H["checkpoint"], "handed_off_at": "2026-01-01T00:01:00+00:00"},
                "incomplete",
            ),
            (
                "reconciling",
                {"evidence_type": "reconciliation_claimed", "claim_id": U["reconcile"], "execution_result_id": U["result"], "claimed_at": "2026-01-01T00:01:00+00:00"},
                "incomplete",
            ),
            (
                "closed",
                {"evidence_type": "terminal_response_emitted", "message_ref": "assistant-history-record-7", "persisted_at": "2026-01-01T00:01:00+00:00", "delivery_claimed": False, "human_observation_claimed": False},
                "completed",
            ),
        ]
        for state, evidence, objective in cases:
            with self.subTest(state=state):
                result = advance_turn_obligation(
                    initial,
                    state=state,
                    recorded_at="2026-01-01T00:01:00+00:00",
                    advance_source="deterministic_policy",
                    closure_evidence=evidence,
                    objective_status=objective,
                )
                self.assertTrue(result.turn_closed)
                self.assertEqual(result.objective_status, objective)

    def test_message_persistence_cannot_claim_delivery_or_observation(self):
        evidence = {
            "evidence_type": "terminal_response_emitted",
            "message_ref": "history-1",
            "persisted_at": "2026-01-01T00:01:00+00:00",
            "delivery_claimed": True,
            "human_observation_claimed": False,
        }
        with self.assertRaisesRegex(LifecycleContractError, "cannot claim delivery"):
            advance_turn_obligation(
                self.obligation(), state="closed", recorded_at="2026-01-01T00:01:00+00:00",
                advance_source="deterministic_policy", closure_evidence=evidence,
            )

    def test_protocol_reflex_advances_same_obligation_and_phase(self):
        waiting = advance_turn_obligation(
            self.obligation(), state="waiting", recorded_at="2026-01-01T00:01:00+00:00",
            advance_source="deterministic_policy",
            closure_evidence={"evidence_type": "checkpoint_planted", "checkpoint_id": U["checkpoint"], "checkpoint_sha256": H["checkpoint"], "planted_at": "2026-01-01T00:01:00+00:00"},
        )
        active = advance_turn_obligation(
            waiting, state="active", recorded_at="2026-01-01T00:02:00+00:00", advance_source="protocol_reflex"
        )
        self.assertEqual(active.obligation_id, waiting.obligation_id)
        self.assertEqual(active.phase_generation, waiting.phase_generation + 1)
        self.assertEqual(active.generation, waiting.generation + 1)
        child = active.to_document()
        child["obligation_id"] = U["authorization"]
        child["turn_obligation_sha256"] = domain_sha256(
            "turn-obligation", {k: v for k, v in child.items() if k != "turn_obligation_sha256"}
        )
        with self.assertRaises(LifecycleConflictError):
            validate_turn_transition(waiting.to_document(), child)

    def test_turn_transition_rejects_stale_generation_and_illegal_reflex(self):
        with self.assertRaisesRegex(LifecycleContractError, "protocol_reflex"):
            advance_turn_obligation(
                self.obligation(), state="active", recorded_at="2026-01-01T00:01:00+00:00", advance_source="protocol_reflex"
            )
        current = advance_turn_obligation(
            self.obligation(), state="active", recorded_at="2026-01-01T00:01:00+00:00", advance_source="deterministic_policy"
        ).to_document()
        current["generation"] = 5
        current["turn_obligation_sha256"] = domain_sha256(
            "turn-obligation", {k: v for k, v in current.items() if k != "turn_obligation_sha256"}
        )
        with self.assertRaisesRegex(LifecycleConflictError, "CAS"):
            validate_turn_transition(self.obligation().to_document(), current)

    def test_closure_evidence_must_bind_checkpoint_and_not_postdate_record(self):
        wrong_checkpoint = {
            "evidence_type": "checkpoint_planted",
            "checkpoint_id": U["authorization"],
            "checkpoint_sha256": H["checkpoint"],
            "planted_at": "2026-01-01T00:01:00+00:00",
        }
        with self.assertRaisesRegex(LifecycleContractError, "bind the obligation checkpoint"):
            advance_turn_obligation(
                self.obligation(), state="waiting", recorded_at="2026-01-01T00:01:00+00:00",
                advance_source="deterministic_policy", closure_evidence=wrong_checkpoint,
            )
        future_gate = {
            "evidence_type": "human_gate_reached",
            "gate_id": U["gate"],
            "reason_code": "authority_required",
            "reached_at": "2026-01-01T00:02:00+00:00",
            "human_observation_claimed": False,
        }
        with self.assertRaisesRegex(LifecycleContractError, "cannot postdate"):
            advance_turn_obligation(
                self.obligation(), state="awaiting_human", recorded_at="2026-01-01T00:01:00+00:00",
                advance_source="deterministic_policy", closure_evidence=future_gate,
            )


class AuthorizationTests(LifecycleFixture):
    def test_authorization_binds_full_operational_digest_and_evidence_variants(self):
        first = self.authorization()
        second = self.authorization()
        self.assertEqual(first.to_document(), second.to_document())
        self.assertEqual({item["evidence_type"] for item in first.expected_evidence}, {"file_exists", "sha256_match", "ledger_entry_present"})
        self.assertEqual(first.field_identity["field_id"], "recursive-field")
        self.assertEqual(first.lineage["context_id"], "opaque context/id + punctuation")
        self.assertEqual(first.lineage["checkpoint_sequence"], 7)
        validate_execution_authorization(first.to_document())
        validate_authorization_freshness(first, self.freshness())

    def test_authorization_rejects_model_authority_unregistered_adapter_and_absolute_config(self):
        with self.assertRaisesRegex(LifecycleContractError, "deterministic registered adapter"):
            mint_execution_authorization(**{**self._auth_kwargs(), "adapter_id": "model_tool_call"})
        with self.assertRaisesRegex(LifecycleContractError, "unexpected fields"):
            mint_execution_authorization(**{**self._auth_kwargs(), "payload": {"model_proposal": "run"}})
        with self.assertRaisesRegex(LifecycleContractError, "relative to the discovered field root"):
            mint_execution_authorization(**{**self._auth_kwargs(), "security_config_path": "/a0/tmp/profile.json"})
        tampered = self.authorization().to_document()
        tampered["issuer"]["model_orientation_authority"] = True
        tampered["operational_digest_sha256"] = domain_sha256("execution-operational-binding", {
            key: copy.deepcopy(tampered[key]) for key in (
                "adapter", "payload", "payload_sha256", "target", "acting_identity", "security_posture",
                "field_identity", "lineage", "effect_class", "expected_evidence", "evidence_attestation_sha256", "validity", "issuer"
            )
        })
        tampered["authorization_sha256"] = domain_sha256("execution-authorization", {k: v for k, v in tampered.items() if k != "authorization_sha256"})
        with self.assertRaisesRegex(LifecycleContractError, "model orientation"):
            validate_execution_authorization(tampered)

    def _auth_kwargs(self):
        auth = self.authorization().to_document()
        return {
            "authorization_id": auth["authorization_id"], "adapter_id": auth["adapter"]["adapter_id"],
            "adapter_version": auth["adapter"]["adapter_version"], "payload": auth["payload"],
            "target_identity": auth["target"]["identity"], "target_namespace": auth["target"]["namespace"],
            "acting_identity": auth["acting_identity"]["identity"], "acting_namespace": auth["acting_identity"]["namespace"],
            "security_profile": auth["security_posture"]["profile"], "security_config_path": auth["security_posture"]["config_path"],
            "security_config_sha256": auth["security_posture"]["config_sha256"], "field_id": auth["field_identity"]["field_id"],
            "field_genesis_uuid": auth["field_identity"]["field_genesis_uuid"],
            "obligation_id": auth["lineage"]["obligation_id"], "phase_generation": auth["lineage"]["phase_generation"],
            "context_id": auth["lineage"]["context_id"],
            "intent_id": auth["lineage"]["intent_id"], "intent_generation": auth["lineage"]["intent_generation"],
            "checkpoint_id": auth["lineage"]["checkpoint_id"], "checkpoint_sha256": auth["lineage"]["checkpoint_sha256"],
            "checkpoint_sequence": auth["lineage"]["checkpoint_sequence"],
            "lease": auth["lineage"]["lease"], "effect_class": auth["effect_class"], "expected_evidence": auth["expected_evidence"],
            "issued_at": auth["validity"]["issued_at"], "not_before": auth["validity"]["not_before"], "expires_at": auth["validity"]["expires_at"],
            "issuer_id": auth["issuer"]["issuer_id"], "policy_id": auth["issuer"]["policy_id"],
            "policy_version": auth["issuer"]["policy_version"], "policy_sha256": auth["issuer"]["policy_sha256"],
        }

    def test_digest_tamper_is_rejected(self):
        cases = (
            ("payload", {"scope": "agent"}, "unexpected fields"),
            ("payload_sha256", "f" * 64, "payload hash mismatch"),
            ("operational_digest_sha256", "f" * 64, "digest mismatch"),
        )
        for field, mutation, message in cases:
            with self.subTest(field=field):
                tampered = self.authorization().to_document()
                tampered[field] = mutation
                with self.assertRaisesRegex(LifecycleContractError, message):
                    validate_execution_authorization(tampered)

    def test_freshness_expiry_boot_lease_config_intent_and_phase_drift(self):
        cases = [
            self.freshness(observed_at="2026-01-01T00:09:00+00:00"),
            self.freshness(boot_id="00000000-0000-4000-8000-00000000000d"),
            self.freshness(lease_generation=4),
            self.freshness(security_config_sha256="f" * 64),
            self.freshness(intent_generation=5),
            self.freshness(phase_generation=2),
        ]
        for snapshot in cases:
            with self.subTest(snapshot=snapshot):
                with self.assertRaises(LifecycleConflictError):
                    validate_authorization_freshness(self.authorization(), snapshot)


class ExecutionResultTests(LifecycleFixture):
    def claimed(self):
        ready = build_execution_result(result_id=U["result"], authorization=self.authorization(), ready_at="2026-01-01T00:01:00+00:00")
        return advance_execution_result(
            ready, state="claimed", at="2026-01-01T00:02:00+00:00", authorization=self.authorization(),
            freshness=self.freshness(), run_id=U["run"], claim=self.claim(),
        )

    def dispatched(self):
        return advance_execution_result(
            self.claimed(), state="dispatched", at="2026-01-01T00:03:00+00:00",
            authorization=self.authorization(), freshness=self.freshness(observed_at="2026-01-01T00:03:00+00:00"),
        )

    def test_ready_claimed_dispatched_completed_lifecycle(self):
        complete = advance_execution_result(
            self.dispatched(), state="completed", at="2026-01-01T00:04:00+00:00",
            authorization=self.authorization(), freshness=self.freshness(observed_at="2026-01-01T00:04:00+00:00"),
            observed_evidence=sorted_evidence(),
            terminal_result={"result_type": "completed", "outcome_sha256": H["outcome"], "summary_code": "verified"},
        )
        self.assertFalse(complete.physical_effect_exactly_once_claimed)
        self.assertNotIn("consumed", complete.to_document())
        validate_execution_result(complete.to_document())

    def test_ambiguous_boundaries_from_claimed_and_dispatched(self):
        for previous, last, at in (
            (self.claimed(), "claimed", "2026-01-01T00:03:00+00:00"),
            (self.dispatched(), "dispatched", "2026-01-01T00:04:00+00:00"),
            (self.claimed(), "claimed", "2026-01-01T00:10:00+00:00"),
        ):
            with self.subTest(last=last):
                result = advance_execution_result(
                    previous, state="ambiguous", at=at, authorization=self.authorization(),
                    freshness=self.freshness(observed_at=at),
                    ambiguity_boundary={"last_certain_state": last, "reason_code": "receipt_missing", "observed_at": at},
                    terminal_result={"result_type": "ambiguous", "reason_code": "receipt_missing", "reconciliation_required": True},
                )
                self.assertEqual(result.state, "ambiguous")

    def test_expiry_is_terminal_and_requires_validity_boundary(self):
        ready = build_execution_result(result_id=U["result"], authorization=self.authorization(), ready_at="2026-01-01T00:01:00+00:00")
        expired = advance_execution_result(
            ready, state="expired", at="2026-01-01T00:09:00+00:00", authorization=self.authorization(),
            terminal_result={"result_type": "expired", "reason_code": "authorization_expired"},
        )
        self.assertEqual(expired.state, "expired")
        with self.assertRaises(LifecycleContractError):
            advance_execution_result(
                ready, state="expired", at="2026-01-01T00:08:59+00:00", authorization=self.authorization(),
                terminal_result={"result_type": "expired", "reason_code": "authorization_expired"},
            )

    def test_claim_expiry_and_authorized_boot_generation_binding(self):
        claimed = self.claimed()
        expired = advance_execution_result(
            claimed, state="expired", at="2026-01-01T00:08:00+00:00", authorization=self.authorization(),
            terminal_result={"result_type": "expired", "reason_code": "claim_expired"},
        )
        self.assertEqual(expired.state, "expired")
        ready = build_execution_result(
            result_id=U["result"], authorization=self.authorization(), ready_at="2026-01-01T00:01:00+00:00"
        )
        for field, value in (("lease_generation", 2), ("holder", "other-worker")):
            stale_claim = self.claim()
            stale_claim[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                LifecycleConflictError, "authorized holder, boot, and lease generation"
            ):
                advance_execution_result(
                    ready, state="claimed", at="2026-01-01T00:02:00+00:00", authorization=self.authorization(),
                    freshness=self.freshness(), run_id=U["run"], claim=stale_claim,
                )

    def test_invalid_transition_stale_cas_and_late_certainty(self):
        ready = build_execution_result(result_id=U["result"], authorization=self.authorization(), ready_at="2026-01-01T00:01:00+00:00")
        with self.assertRaises(LifecycleContractError):
            advance_execution_result(
                ready, state="completed", at="2026-01-01T00:02:00+00:00", authorization=self.authorization(),
                terminal_result={"result_type": "completed", "outcome_sha256": H["outcome"], "summary_code": "invalid"},
                observed_evidence=sorted_evidence(),
            )
        current = self.claimed().to_document()
        current["generation"] = 9
        current["execution_result_sha256"] = domain_sha256("execution-result", {k: v for k, v in current.items() if k != "execution_result_sha256"})
        with self.assertRaisesRegex(LifecycleConflictError, "CAS"):
            validate_result_transition(ready.to_document(), current, self.authorization())
        with self.assertRaisesRegex(LifecycleConflictError, "late terminal certainty"):
            advance_execution_result(
                self.dispatched(), state="failed", at="2026-01-01T00:08:00+00:00", authorization=self.authorization(),
                freshness=self.freshness(observed_at="2026-01-01T00:08:00+00:00"),
                terminal_result={"result_type": "failed", "error_code": "timeout", "retryable": False},
            )


class SchemaContractTests(unittest.TestCase):
    def test_exactly_three_new_strict_schema_roots_parse(self):
        expected = {
            "turn-obligation.schema.json": "turn_obligation",
            "execution-authorization.schema.json": "execution_authorization",
            "execution-result.schema.json": "execution_result",
        }
        for filename, record_type in expected.items():
            with self.subTest(filename=filename):
                schema = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
                self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertFalse(schema["additionalProperties"])
                self.assertEqual(schema["properties"]["record_type"]["const"], record_type)
        lifecycle = sorted(path.name for path in (ROOT / "schemas").glob("*.schema.json") if path.name in expected)
        self.assertEqual(lifecycle, sorted(expected))

    def test_fixture_bytes_are_repeatable(self):
        fixture = LifecycleFixture(methodName="runTest")
        first_authorization = fixture.authorization()
        second_authorization = fixture.authorization()
        fixture_sets = (
            (fixture.obligation().to_document(), fixture.obligation().to_document()),
            (first_authorization.to_document(), second_authorization.to_document()),
            (
                build_execution_result(
                    result_id=U["result"], authorization=first_authorization,
                    ready_at="2026-01-01T00:01:00+00:00",
                ).to_document(),
                build_execution_result(
                    result_id=U["result"], authorization=second_authorization,
                    ready_at="2026-01-01T00:01:00+00:00",
                ).to_document(),
            ),
        )
        encode = lambda value: json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
        for first, second in fixture_sets:
            self.assertEqual(encode(first), encode(second))


if __name__ == "__main__":
    unittest.main(verbosity=2)
