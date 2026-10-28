#!/usr/bin/env python3
"""Regression contracts for formation-owned continuation classification."""

from __future__ import annotations

import copy
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from continuation_schema import (
    PROHIBITED_EFFECTS,
    ContinuationConflictError,
    ContinuationValidationError,
    advance_intent,
    atomic_write_document,
    build_checkpoint,
    build_context_evidence,
    build_dispatch,
    build_intent,
    build_lease,
    build_retry_budget,
    build_token_snapshot,
    build_work_snapshot,
    canonical_json_bytes,
    canonical_sha256,
    checkpoint_pointer,
    compare_and_swap_intent,
    create_immutable_document,
    read_json_document,
    seal_document,
    validate_document,
    validate_transition,
)
from checkpoint_intent import arm_intent, record_checkpoint
from continuation_reflex import (
    ContinuationReflexBlocked,
    claim_reflex_request,
    prepare_reflex_request,
    record_reflex_fired,
)
from generate_continuation_fixtures import CLASSIFICATIONS, generate_fixtures
from resume_thread import EXIT_CODES, classify_intent


ROOT = Path(__file__).resolve().parent
AT = datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc)
BOOT_ID = "00000000-0000-4000-8000-000000000002"


class ContinuationFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="recursive-field-continuity-")
        self.root = Path(self.temporary.name)
        self.genesis_uuid = str(uuid.uuid4())
        self.intent_id = str(uuid.uuid4())
        self.context_id = "caller supplied/context id + punctuation"
        self._write_json(
            self.root / ".recursive-field-root",
            {
                "genesis_uuid": self.genesis_uuid,
                "inception_timestamp": "2026-01-01T00:00:00+00:00",
                "schema_version": "1.0.0",
            },
        )
        self._write_json(
            self.root / "state" / "control_profile.json",
            {
                "active_security_profile": "restricted",
                "security_profiles": {
                    "open": {"capabilities": ["all"]},
                    "restricted": {
                        "capabilities": ["observe", "coordinate", "persist"]
                    },
                    "lockdown": {"capabilities": ["observe"]},
                },
                "prompt_includes": {},
            },
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_json(self, path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def _effect_boundary(self) -> dict:
        return {
            "mode": "classification_only",
            "allows_actuation": False,
            "allowed_effects": [],
            "prohibited_effects": list(PROHIBITED_EFFECTS),
        }

    def _evidence(
        self,
        *,
        exists: bool = True,
        observed_at: str = "2026-01-01T00:00:00+00:00",
        history: str = "a" * 64,
    ) -> dict:
        return {
            "source": "formation_attestation",
            "context_id": self.context_id,
            "observed_at": observed_at,
            "exists": exists,
            "history_sha256": history,
        }

    def _continuity_metadata(
        self,
        *,
        interruption_class: str = "self_initiated",
        token_source: str = "test-capped-plan",
        token_model: str = "capped",
        maximum_attempts: int = 3,
        attempts_used: int = 0,
    ) -> dict:
        return {
            "interruption_class": interruption_class,
            "token_snapshot": {
                "token_source": token_source,
                "token_model": token_model,
            },
            "retry_budget": {
                "maximum_attempts": maximum_attempts,
                "attempts_used": attempts_used,
            },
            "work_snapshot": {
                "work_vector": "Continue the bounded Step 3 work vector.",
                "file_state": [
                    {
                        "path": "continuation_schema.py",
                        "status": "modified",
                        "sha256": "c" * 64,
                    }
                ],
                "git_commit": "c70b317ffeec568ea663e7fc5319b84cf3e69d4e",
                "subordinate_context_ids": ["opaque-subordinate-context"],
                "parallel_references": [
                    {
                        "job_id": "job-1",
                        "context_id": "opaque-subordinate-context",
                        "state": "success",
                        "result_ref": "results/job-1.json",
                    }
                ],
            },
        }

    def _checkpoint(
        self,
        state: str = "armed",
        *,
        checkpoint_id: str | None = None,
        lease_state: str = "unclaimed",
        acquired_at: str = "2026-01-01T00:01:00+00:00",
        expires_at: str = "2026-01-01T00:10:00+00:00",
        previous: dict | None = None,
        sequence: int | None = None,
        exists: bool = True,
        security_profile: str = "restricted",
        capabilities: list[str] | None = None,
        recorded_at: str = "2026-01-01T00:01:00+00:00",
    ) -> dict:
        if checkpoint_id is None:
            checkpoint_id = str(uuid.uuid4())
        if lease_state == "held":
            lease = {
                "state": "held",
                "holder": "formation-worker-1",
                "attempt_id": str(uuid.uuid4()),
                "generation": 1,
                "boot_id": BOOT_ID,
                "acquired_at": acquired_at,
                "expires_at": expires_at,
            }
        else:
            lease = {
                "state": lease_state,
                "holder": None,
                "attempt_id": None,
                "generation": None,
                "boot_id": None,
                "acquired_at": None,
                "expires_at": None,
            }
        return seal_document(
            {
                "schema_version": "1.0.0",
                "artifact_type": "continuation_checkpoint",
                "checkpoint_id": checkpoint_id,
                "intent_id": self.intent_id,
                "field_genesis_uuid": self.genesis_uuid,
                "context_id": self.context_id,
                "recorded_at": recorded_at,
                "sequence": sequence if sequence is not None else (1 if previous is None else previous["sequence"] + 1),
                "state": state,
                **self._continuity_metadata(),
                "security": {
                    "profile": security_profile,
                    "required_capabilities": capabilities or ["observe"],
                },
                "context_evidence": self._evidence(exists=exists),
                "effect_boundary": self._effect_boundary(),
                "lease": lease,
                "dispatch": {"state": "none", "dispatch_id": None, "effect_sha256": None, "observed_at": None},
                "previous_checkpoint": previous,
            },
            "checkpoint",
        )

    def _intent(
        self,
        status: str = "armed",
        *,
        checkpoint: dict | None = None,
        exists: bool = True,
        security_profile: str = "restricted",
        capabilities: list[str] | None = None,
    ) -> dict:
        latest = None
        if checkpoint is not None:
            latest = {
                "checkpoint_id": checkpoint["checkpoint_id"],
                "checkpoint_sha256": checkpoint["checkpoint_sha256"],
                "sequence": checkpoint["sequence"],
            }
        return seal_document(
            {
                "schema_version": "1.0.0",
                "artifact_type": "continuation_intent",
                "intent_id": self.intent_id,
                "field_genesis_uuid": self.genesis_uuid,
                "context_id": self.context_id,
                "created_at": "2026-01-01T00:00:00+00:00",
                "status": status,
                **self._continuity_metadata(),
                "security": {
                    "profile": security_profile,
                    "required_capabilities": capabilities or ["observe"],
                },
                "context_evidence": self._evidence(exists=exists),
                "effect_boundary": self._effect_boundary(),
                "latest_checkpoint": latest,
            },
            "intent",
        )

    def _install(self, intent: dict, *checkpoints: dict) -> None:
        for checkpoint in checkpoints:
            self._write_json(
                self.root
                / "state"
                / "continuations"
                / "checkpoints"
                / f"{checkpoint['checkpoint_id']}.json",
                checkpoint,
            )
        self._write_json(
            self.root
            / "state"
            / "continuations"
            / "intents"
            / f"{self.intent_id}.json",
            intent,
        )

    def _classify(self):
        return classify_intent(self.intent_id, start=self.root, at=AT, boot_id=BOOT_ID)

    def _tree_bytes(self) -> dict[str, bytes]:
        return {
            str(path.relative_to(self.root)): path.read_bytes()
            for path in sorted(self.root.rglob("*"))
            if path.is_file()
        }


class SchemaAndWriteTest(ContinuationFixture):
    def test_checked_in_schemas_are_valid_json_with_expected_identity(self) -> None:
        for name in ("continuation-intent", "continuation-checkpoint"):
            schema = json.loads((ROOT / "schemas" / f"{name}.schema.json").read_text())
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertFalse(schema["additionalProperties"])

    def test_canonical_json_and_hash_are_order_independent(self) -> None:
        left = {"z": [3, 2, 1], "a": {"β": True}}
        right = {"a": {"β": True}, "z": [3, 2, 1]}
        self.assertEqual(canonical_json_bytes(left), canonical_json_bytes(right))
        self.assertEqual(canonical_sha256(left), canonical_sha256(right))
        self.assertNotIn(b" ", canonical_json_bytes(left))

    def test_atomic_write_is_canonical_private_and_validated(self) -> None:
        intent = self._intent()
        target = self.root / "state" / "continuations" / "intents" / "artifact.json"
        atomic_write_document(target, intent, "intent")
        self.assertEqual(target.read_bytes(), canonical_json_bytes(intent) + b"\n")
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
        before = target.read_bytes()
        invalid = copy.deepcopy(intent)
        invalid["status"] = "corrupt"
        with self.assertRaises(ContinuationValidationError):
            atomic_write_document(target, invalid, "intent")
        self.assertEqual(target.read_bytes(), before)
        self.assertEqual(list(target.parent.glob(".*.tmp")), [])

    def test_hash_context_effect_and_lease_invariants_fail_closed(self) -> None:
        cases: list[tuple[str, dict, str]] = []
        tampered = self._intent()
        tampered["status"] = "active"
        cases.append(("intent hash", tampered, "intent"))

        evidence = self._intent()
        evidence["context_evidence"]["history_sha256"] = "b" * 64
        evidence["intent_sha256"] = canonical_sha256(
            {key: value for key, value in evidence.items() if key != "intent_sha256"}
        )
        cases.append(("evidence hash", evidence, "intent"))

        boundary = self._intent()
        boundary["effect_boundary"]["prohibited_effects"].pop()
        boundary = seal_document(boundary, "intent")
        cases.append(("effect boundary", boundary, "intent"))

        lease = self._checkpoint("active", lease_state="held")
        lease["lease"]["expires_at"] = lease["lease"]["acquired_at"]
        lease = seal_document(lease, "checkpoint")
        cases.append(("lease ordering", lease, "checkpoint"))

        for label, artifact, kind in cases:
            with self.subTest(label=label), self.assertRaises(ContinuationValidationError):
                validate_document(artifact, kind)

    def test_context_identifier_is_opaque_not_engine_grammar(self) -> None:
        intent = self._intent()
        self.assertEqual(validate_document(intent, "intent")["context_id"], self.context_id)

    def test_json_schema_boolean_and_rfc3339_semantics_are_strict(self) -> None:
        numeric_false = self._intent()
        numeric_false["effect_boundary"]["allows_actuation"] = 0
        numeric_false = seal_document(numeric_false, "intent")
        with self.assertRaises(ContinuationValidationError):
            validate_document(numeric_false, "intent")

        non_rfc3339 = self._intent()
        non_rfc3339["created_at"] = "2026-01-01 00:00:00+00:00"
        non_rfc3339 = seal_document(non_rfc3339, "intent")
        with self.assertRaises(ContinuationValidationError):
            validate_document(non_rfc3339, "intent")

    def test_artifact_read_errors_are_normalized_as_validation_failures(self) -> None:
        intent = self._intent()
        target = self.root / "state" / "continuations" / "intents" / "artifact.json"
        self._write_json(target, intent)
        original_read_text = Path.read_text

        def controlled_read_text(path: Path, *args, **kwargs):
            if path == target:
                raise PermissionError("denied for test")
            return original_read_text(path, *args, **kwargs)

        with (
            patch.object(Path, "read_text", new=controlled_read_text),
            self.assertRaises(ContinuationValidationError),
        ):
            from continuation_schema import read_json_document

            read_json_document(target, "intent")


class ClassificationTest(ContinuationFixture):
    def test_resumable_without_checkpoint(self) -> None:
        self._install(self._intent("armed"))
        result = self._classify()
        self.assertEqual((result.classification, result.exit_code), ("resumable", 0))
        self.assertEqual(result.reasons, ("armed_without_checkpoint",))

    def test_resumable_with_unclaimed_checkpoint(self) -> None:
        checkpoint = self._checkpoint("armed")
        self._install(self._intent("armed", checkpoint=checkpoint), checkpoint)
        result = self._classify()
        self.assertEqual(result.classification, "resumable")
        output = result.as_dict()
        self.assertEqual(output["checkpoint_id"], checkpoint["checkpoint_id"])
        self.assertTrue(output["eligible"])
        self.assertEqual(output["blocking_conditions"], [])
        self.assertFalse(output["would_claim"])
        self.assertFalse(output["would_dispatch"])
        self.assertFalse(output["would_write"])
        self.assertFalse(output["would_execute"])

    def test_active_requires_current_lease(self) -> None:
        checkpoint = self._checkpoint("active", lease_state="held")
        self._install(self._intent("active", checkpoint=checkpoint), checkpoint)
        result = self._classify()
        self.assertEqual((result.classification, result.exit_code), ("active", 10))

    def test_awaiting_human_is_never_resumable(self) -> None:
        checkpoint = self._checkpoint("awaiting_human")
        self._install(self._intent("awaiting_human", checkpoint=checkpoint), checkpoint)
        result = self._classify()
        self.assertEqual((result.classification, result.exit_code), ("awaiting_human", 11))

    def test_all_terminal_states_are_terminal(self) -> None:
        for state in ("completed", "cancelled", "blocked", "failed"):
            with self.subTest(state=state):
                checkpoint = self._checkpoint(state)
                self._install(self._intent(state, checkpoint=checkpoint), checkpoint)
                result = self._classify()
                self.assertEqual((result.classification, result.exit_code), ("terminal", 12))

    def test_expired_or_inconsistent_lease_needs_reconciliation(self) -> None:
        expired = self._checkpoint(
            "active",
            lease_state="held",
            expires_at="2026-01-01T00:04:59+00:00",
        )
        self._install(self._intent("active", checkpoint=expired), expired)
        result = self._classify()
        self.assertEqual((result.classification, result.exit_code), ("needs_reconciliation", 20))
        self.assertIn("lease_expired", result.reasons)

        armed_with_lease = self._checkpoint("armed", lease_state="held")
        self._install(self._intent("armed", checkpoint=armed_with_lease), armed_with_lease)
        self.assertEqual(self._classify().classification, "invalid")
        self.assertIn("checkpoint_artifact_invalid", self._classify().reasons)

    def test_status_and_security_drift_need_reconciliation(self) -> None:
        checkpoint = self._checkpoint("armed")
        self._install(self._intent("active", checkpoint=checkpoint), checkpoint)
        self.assertIn("intent_checkpoint_state_drift", self._classify().reasons)

        checkpoint = self._checkpoint("armed")
        self._install(
            self._intent("armed", checkpoint=checkpoint, security_profile="open"),
            checkpoint,
        )
        result = self._classify()
        self.assertEqual(result.classification, "needs_reconciliation")
        self.assertIn("security_profile_drift", result.reasons)

    def test_missing_capability_needs_reconciliation(self) -> None:
        checkpoint = self._checkpoint("armed", capabilities=["coordinate"])
        self._install(
            self._intent("armed", checkpoint=checkpoint, capabilities=["coordinate"]),
            checkpoint,
        )
        control_path = self.root / "state" / "control_profile.json"
        control = json.loads(control_path.read_text())
        control["security_profiles"]["restricted"]["capabilities"] = ["observe"]
        self._write_json(control_path, control)
        result = self._classify()
        self.assertEqual(result.classification, "needs_reconciliation")
        self.assertIn("required_capability_unavailable", result.reasons)

    def test_unavailable_inputs_are_distinguished_from_invalid_artifacts(self) -> None:
        missing = self._classify()
        self.assertEqual((missing.classification, missing.exit_code), ("unavailable", 40))

        self._install(self._intent(exists=False))
        self.assertEqual(self._classify().classification, "unavailable")

        checkpoint = self._checkpoint("armed")
        self._install(self._intent(checkpoint=checkpoint))
        self.assertEqual(self._classify().classification, "unavailable")

        invalid = self._intent()
        invalid["status"] = "active"
        self._install(invalid)
        result = self._classify()
        self.assertEqual((result.classification, result.exit_code), ("invalid", 30))

    def test_genesis_and_checkpoint_linkage_tamper_are_invalid(self) -> None:
        intent = self._intent()
        intent["field_genesis_uuid"] = str(uuid.uuid4())
        intent = seal_document(intent, "intent")
        self._install(intent)
        self.assertIn("intent_genesis_mismatch", self._classify().reasons)

        checkpoint = self._checkpoint("armed")
        intent = self._intent(checkpoint=checkpoint)
        intent["latest_checkpoint"]["checkpoint_sha256"] = "f" * 64
        intent = seal_document(intent, "intent")
        self._install(intent, checkpoint)
        self.assertIn("checkpoint_link_hash_mismatch", self._classify().reasons)

    def test_checkpoint_chain_is_validated_through_genesis(self) -> None:
        first = self._checkpoint(
            "armed", recorded_at="2026-01-01T00:00:30+00:00"
        )
        previous = {
            "checkpoint_id": first["checkpoint_id"],
            "checkpoint_sha256": first["checkpoint_sha256"],
            "sequence": first["sequence"],
        }
        second = self._checkpoint("armed", previous=previous)
        self._install(self._intent(checkpoint=second), first, second)
        self.assertEqual(self._classify().classification, "resumable")

        first["state"] = "completed"
        self._write_json(
            self.root
            / "state"
            / "continuations"
            / "checkpoints"
            / f"{first['checkpoint_id']}.json",
            first,
        )
        self.assertEqual(self._classify().classification, "invalid")

    def test_noncanonical_intent_id_and_missing_root(self) -> None:
        invalid = classify_intent("../escape", start=self.root, at=AT)
        self.assertEqual((invalid.classification, invalid.exit_code), ("invalid", 30))
        with tempfile.TemporaryDirectory() as empty:
            unavailable = classify_intent(self.intent_id, start=empty, at=AT)
        self.assertEqual(unavailable.classification, "unavailable")

    def test_symlinked_runtime_path_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory(prefix="continuation-outside-") as outside:
            outside_path = Path(outside)
            self._write_json(outside_path / f"{self.intent_id}.json", self._intent())
            parent = self.root / "state" / "continuations"
            parent.mkdir(parents=True)
            (parent / "intents").symlink_to(outside_path, target_is_directory=True)
            result = self._classify()
        self.assertEqual(result.classification, "invalid")
        self.assertEqual(result.reasons, ("intent_path_invalid",))


class DryRunCLITest(ContinuationFixture):
    def test_cli_is_stable_read_only_and_uses_documented_exit_code(self) -> None:
        checkpoint = self._checkpoint("active", lease_state="held")
        self._install(self._intent("active", checkpoint=checkpoint), checkpoint)
        before = self._tree_bytes()
        command = [
            sys.executable,
            str(ROOT / "resume_thread.py"),
            self.intent_id,
            "--dry-run",
            "--start",
            str(self.root),
            "--at",
            "2026-01-01T00:05:00+00:00",
            "--boot-id",
            BOOT_ID,
        ]
        first = subprocess.run(command, check=False, capture_output=True)
        middle = self._tree_bytes()
        second = subprocess.run(command, check=False, capture_output=True)
        after = self._tree_bytes()

        self.assertEqual(first.returncode, EXIT_CODES["active"])
        self.assertEqual(second.returncode, first.returncode)
        self.assertEqual(second.stdout, first.stdout)
        self.assertEqual(first.stderr, b"")
        payload = json.loads(first.stdout)
        self.assertEqual(
            set(payload),
            {
                "blocking_conditions",
                "checkpoint_id",
                "classification",
                "eligible",
                "exit_code",
                "intent_id",
                "reasons",
                "schema_version",
                "would_claim",
                "would_dispatch",
                "would_execute",
                "would_write",
            },
        )
        self.assertEqual(payload["classification"], "active")
        self.assertEqual(payload["exit_code"], EXIT_CODES["active"])
        self.assertEqual(payload["checkpoint_id"], checkpoint["checkpoint_id"])
        self.assertFalse(payload["eligible"])
        self.assertEqual(payload["blocking_conditions"], ["current_lease_held"])
        self.assertFalse(payload["would_claim"])
        self.assertFalse(payload["would_dispatch"])
        self.assertFalse(payload["would_execute"])
        self.assertFalse(payload["would_write"])
        self.assertEqual(before, middle)
        self.assertEqual(middle, after)

    def test_source_has_no_engine_or_network_actuation_imports(self) -> None:
        source = (ROOT / "resume_thread.py").read_text(encoding="utf-8")
        forbidden = (
            "import requests",
            "import flask",
            "from agent import",
            "/api/message",
            "/api/api_message",
            "call_subordinate",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)


class Step3ConstructorAndPersistenceTest(ContinuationFixture):
    def test_reusable_constructors_bind_sequence_boot_and_effect_boundary(self) -> None:
        evidence = build_context_evidence(
            context_id=self.context_id,
            observed_at="2026-01-01T00:00:00+00:00",
            history_sha256="a" * 64,
        )
        intent = build_intent(
            intent_id=self.intent_id,
            field_genesis_uuid=self.genesis_uuid,
            context_id=self.context_id,
            created_at="2026-01-01T00:00:00+00:00",
            security_profile="restricted",
            required_capabilities=["persist", "observe", "observe"],
            context_evidence=evidence,
            interruption_class="self_initiated",
            token_snapshot=build_token_snapshot(
                token_source="test-capped-plan",
                token_model="capped",
            ),
            retry_budget=build_retry_budget(maximum_attempts=3),
            work_snapshot=build_work_snapshot(
                work_vector="Continue constructor verification.",
                git_commit="c70b317ffeec568ea663e7fc5319b84cf3e69d4e",
                file_state=[],
                subordinate_context_ids=["child-b", "child-a"],
                parallel_references=[],
            ),
        )
        checkpoint = build_checkpoint(
            checkpoint_id=str(uuid.uuid4()),
            intent=intent,
            recorded_at="2026-01-01T00:01:00+00:00",
            state="active",
            lease=build_lease(
                state="held",
                holder="worker",
                attempt_id=str(uuid.uuid4()),
                generation=1,
                boot_id=BOOT_ID,
                acquired_at="2026-01-01T00:01:00+00:00",
                expires_at="2026-01-01T00:10:00+00:00",
            ),
        )
        validate_transition(intent, checkpoint, None)
        self.assertEqual(intent["security"]["required_capabilities"], ["observe", "persist"])
        self.assertEqual(checkpoint["sequence"], 1)
        self.assertEqual(checkpoint["lease"]["boot_id"], BOOT_ID)
        self.assertEqual(tuple(checkpoint["effect_boundary"]["prohibited_effects"]), PROHIBITED_EFFECTS)
        self.assertEqual(validate_document(advance_intent(intent, checkpoint), "intent")["latest_checkpoint"], checkpoint_pointer(checkpoint))

    def test_sequence_pointer_and_terminal_human_barriers_fail_closed(self) -> None:
        intent = self._intent()
        first = self._checkpoint("armed")
        validate_transition(intent, first, None)
        advanced = advance_intent(intent, first)
        bad = self._checkpoint(
            "armed",
            previous=checkpoint_pointer(first),
            sequence=3,
            recorded_at="2026-01-01T00:02:00+00:00",
        )
        with self.assertRaises(ContinuationValidationError):
            validate_document(bad, "checkpoint")

        human = self._checkpoint("awaiting_human")
        human_intent = advance_intent(intent, human)
        successor = self._checkpoint(
            "armed",
            previous=checkpoint_pointer(human),
            recorded_at="2026-01-01T00:02:00+00:00",
        )
        with self.assertRaisesRegex(ContinuationValidationError, "authority barrier"):
            validate_transition(human_intent, successor, human)

        terminal = self._checkpoint("completed")
        terminal_intent = advance_intent(intent, terminal)
        successor = self._checkpoint(
            "armed",
            previous=checkpoint_pointer(terminal),
            recorded_at="2026-01-01T00:02:00+00:00",
        )
        with self.assertRaisesRegex(ContinuationValidationError, "terminal"):
            validate_transition(terminal_intent, successor, terminal)

    def test_active_lease_renewal_requires_stable_attempt_boot_and_generation(self) -> None:
        intent = self._intent()
        first = self._checkpoint("active", lease_state="held")
        advanced = advance_intent(intent, first)
        lease = copy.deepcopy(first["lease"])
        lease["generation"] = 2
        lease["expires_at"] = "2026-01-01T00:20:00+00:00"
        second = build_checkpoint(
            checkpoint_id=str(uuid.uuid4()),
            intent=advanced,
            recorded_at="2026-01-01T00:02:00+00:00",
            state="active",
            lease=lease,
            previous_checkpoint=checkpoint_pointer(first),
        )
        validate_transition(advanced, second, first)
        changed = copy.deepcopy(second)
        changed["lease"]["boot_id"] = str(uuid.uuid4())
        changed = seal_document(changed, "checkpoint")
        with self.assertRaisesRegex(ContinuationValidationError, "preserve boot_id"):
            validate_transition(advanced, changed, first)

    def test_immutable_create_is_idempotent_and_never_overwrites_conflict(self) -> None:
        target = self.root / "state" / "continuations" / "intents" / f"{self.intent_id}.json"
        intent = self._intent()
        self.assertEqual(create_immutable_document(target, intent, "intent"), "created")
        before = target.read_bytes()
        self.assertEqual(create_immutable_document(target, intent, "intent"), "identical")
        conflict = seal_document({**intent, "status": "active"}, "intent")
        with self.assertRaises(ContinuationConflictError):
            create_immutable_document(target, conflict, "intent")
        self.assertEqual(target.read_bytes(), before)
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)

    def test_compare_and_swap_rejects_stale_writer(self) -> None:
        target = self.root / "state" / "continuations" / "intents" / f"{self.intent_id}.json"
        intent = self._intent()
        atomic_write_document(target, intent, "intent")
        first = seal_document({**intent, "status": "awaiting_human"}, "intent")
        self.assertEqual(compare_and_swap_intent(target, first, expected_intent_sha256=intent["intent_sha256"]), "updated")
        second = seal_document({**intent, "status": "completed"}, "intent")
        with self.assertRaises(ContinuationConflictError):
            compare_and_swap_intent(target, second, expected_intent_sha256=intent["intent_sha256"])
        self.assertEqual(read_json_document(target, "intent")["status"], "awaiting_human")

    def test_boot_mismatch_and_unreconciled_dispatch_require_reconciliation(self) -> None:
        checkpoint = self._checkpoint("active", lease_state="held")
        self._install(self._intent("active", checkpoint=checkpoint), checkpoint)
        mismatch = classify_intent(
            self.intent_id,
            start=self.root,
            at=AT,
            boot_id="00000000-0000-4000-8000-000000000003",
        )
        self.assertIn("lease_boot_id_mismatch", mismatch.reasons)

        intent = self._intent()
        dispatched = build_checkpoint(
            checkpoint_id=str(uuid.uuid4()),
            intent=intent,
            recorded_at="2026-01-01T00:01:00+00:00",
            state="armed",
            lease=build_lease(),
            dispatch=build_dispatch(
                state="unreconciled",
                dispatch_id=str(uuid.uuid4()),
                effect_sha256="b" * 64,
                observed_at="2026-01-01T00:01:00+00:00",
            ),
        )
        self._install(advance_intent(intent, dispatched), dispatched)
        result = self._classify()
        self.assertEqual(result.classification, "needs_reconciliation")
        self.assertIn("consequential_dispatch_unreconciled", result.reasons)


class Step3EndToEndTest(ContinuationFixture):
    def _arm_kwargs(self) -> dict:
        return {
            "start": self.root,
            "intent_id": self.intent_id,
            "context_id": self.context_id,
            "history_sha256": "a" * 64,
            "observed_at": "2026-01-01T00:00:00+00:00",
            "created_at": "2026-01-01T00:00:00+00:00",
            "required_capabilities": ["observe", "persist"],
            "attest_context_exists": True,
            "interruption_class": "self_initiated",
            "token_source": "test-capped-plan",
            "token_model": "capped",
            "maximum_retry_attempts": 3,
            "work_vector": "Continue Step 3 without reconstructing chat history.",
            "git_commit": "c70b317ffeec568ea663e7fc5319b84cf3e69d4e",
            "file_state": [],
            "subordinate_context_ids": ["opaque-child-context"],
            "parallel_references": [],
        }

    def test_arm_checkpoint_terminal_flow_and_retry(self) -> None:
        intent, disposition, _ = arm_intent(**self._arm_kwargs())
        self.assertEqual(disposition, "created")
        self.assertEqual(arm_intent(**self._arm_kwargs())[1], "identical")
        self.assertEqual(self._classify().classification, "resumable")

        attempt_id = str(uuid.uuid4())
        active, cp_disposition, head_disposition, _ = record_checkpoint(
            start=self.root,
            intent_id=self.intent_id,
            expected_intent_sha256=intent["intent_sha256"],
            checkpoint_id=str(uuid.uuid4()),
            recorded_at="2026-01-01T00:01:00+00:00",
            state="active",
            lease=build_lease(
                state="held",
                holder="formation-worker",
                attempt_id=attempt_id,
                generation=1,
                boot_id=BOOT_ID,
                acquired_at="2026-01-01T00:01:00+00:00",
                expires_at="2026-01-01T00:10:00+00:00",
            ),
        )
        self.assertEqual((cp_disposition, head_disposition), ("created", "updated"))
        self.assertEqual(self._classify().classification, "active")
        active_intent = read_json_document(
            self.root / "state" / "continuations" / "intents" / f"{self.intent_id}.json",
            "intent",
        )
        terminal, _, _, _ = record_checkpoint(
            start=self.root,
            intent_id=self.intent_id,
            expected_intent_sha256=active_intent["intent_sha256"],
            checkpoint_id=str(uuid.uuid4()),
            recorded_at="2026-01-01T00:06:00+00:00",
            state="completed",
            lease=build_lease(state="released"),
        )
        self.assertEqual(terminal["sequence"], active["sequence"] + 1)
        self.assertEqual(self._classify().classification, "terminal")

    def test_checkpoint_cli_exact_retry_is_idempotent(self) -> None:
        intent, _, _ = arm_intent(**self._arm_kwargs())
        checkpoint_id = str(uuid.uuid4())
        command = [
            sys.executable,
            str(ROOT / "checkpoint_intent.py"),
            "checkpoint",
            self.intent_id,
            "--expected-intent-sha256", intent["intent_sha256"],
            "--checkpoint-id", checkpoint_id,
            "--recorded-at", "2026-01-01T00:01:00+00:00",
            "--state", "armed",
            "--start", str(self.root),
        ]
        first = subprocess.run(command, check=False, capture_output=True)
        second = subprocess.run(command, check=False, capture_output=True)
        self.assertEqual((first.returncode, second.returncode), (0, 0))
        self.assertEqual(json.loads(second.stdout)["checkpoint_disposition"], "identical")
        self.assertEqual(json.loads(second.stdout)["intent_disposition"], "identical")

    def test_fixture_generator_spans_exactly_all_seven_classifications(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fixture-parent-") as parent:
            output = Path(parent) / "generated"
            manifest = generate_fixtures(output)
            observed = {}
            at = datetime.fromisoformat(manifest["at"])
            for expected, record in manifest["fixtures"].items():
                result = classify_intent(
                    record["intent_id"],
                    start=record["field_root"],
                    at=at,
                    boot_id=manifest["boot_id"],
                    current_token_source=manifest["current_token_source"],
                    current_token_model=manifest["current_token_model"],
                )
                observed[expected] = result.classification
            self.assertEqual(tuple(manifest["fixtures"]), CLASSIFICATIONS)
            self.assertEqual(observed, {name: name for name in CLASSIFICATIONS})
            self.assertTrue((output / "manifest.json").is_file())

    def test_fixture_generator_refuses_live_project_and_existing_output(self) -> None:
        with self.assertRaises(ValueError):
            generate_fixtures(ROOT / "state" / "continuations")
        with tempfile.TemporaryDirectory() as existing:
            with self.assertRaises(FileExistsError):
                generate_fixtures(Path(existing))

    def test_step3_sources_have_no_engine_network_or_service_actuation(self) -> None:
        forbidden = (
            "import requests",
            "import flask",
            "from agent import",
            "/api/message",
            "call_subordinate",
            "systemctl",
            "docker compose",
        )
        for filename in ("checkpoint_intent.py", "generate_continuation_fixtures.py"):
            source = (ROOT / filename).read_text(encoding="utf-8")
            for token in forbidden:
                with self.subTest(filename=filename, token=token):
                    self.assertNotIn(token, source)



class Step3IntentContinuityRefinementTest(ContinuationFixture):
    def _arm_refined(self, **overrides) -> dict:
        values = {
            "start": self.root,
            "intent_id": self.intent_id,
            "context_id": self.context_id,
            "history_sha256": "a" * 64,
            "observed_at": "2026-01-01T00:00:00+00:00",
            "created_at": "2026-01-01T00:00:00+00:00",
            "required_capabilities": ["observe", "persist"],
            "attest_context_exists": True,
            "interruption_class": "self_initiated",
            "token_source": "test-capped-plan",
            "token_model": "capped",
            "maximum_retry_attempts": 2,
            "work_vector": "Continue from the durable Step 3 vector.",
            "git_commit": "c70b317ffeec568ea663e7fc5319b84cf3e69d4e",
            "file_state": [
                {"path": "continuation_schema.py", "status": "modified", "sha256": "d" * 64}
            ],
            "subordinate_context_ids": ["child-z", "child-a"],
            "parallel_references": [
                {
                    "job_id": "job-z",
                    "context_id": "child-z",
                    "state": "running",
                    "result_ref": None,
                }
            ],
        }
        values.update(overrides)
        return arm_intent(**values)[0]

    def test_external_capped_to_metered_drift_and_missing_snapshot_wait_for_human(self) -> None:
        self._arm_refined(interruption_class="external")
        missing = classify_intent(
            self.intent_id,
            start=self.root,
            at=AT,
            boot_id=BOOT_ID,
        )
        self.assertEqual((missing.classification, missing.exit_code), ("awaiting_human", 11))
        self.assertIn("current_token_snapshot_unavailable", missing.reasons)
        drift = classify_intent(
            self.intent_id,
            start=self.root,
            at=AT,
            boot_id=BOOT_ID,
            current_token_source="metered-api",
            current_token_model="metered",
        )
        self.assertEqual((drift.classification, drift.exit_code), ("awaiting_human", 11))
        self.assertIn("external_capped_to_metered_drift", drift.reasons)
        stable = classify_intent(
            self.intent_id,
            start=self.root,
            at=AT,
            boot_id=BOOT_ID,
            current_token_source="test-capped-plan",
            current_token_model="capped",
        )
        self.assertEqual(stable.classification, "resumable")

    def test_retry_exhaustion_requires_and_classifies_awaiting_human(self) -> None:
        intent = self._arm_refined(maximum_retry_attempts=1)
        checkpoint, _, _, _ = record_checkpoint(
            start=self.root,
            intent_id=self.intent_id,
            expected_intent_sha256=intent["intent_sha256"],
            checkpoint_id=str(uuid.uuid4()),
            recorded_at="2026-01-01T00:01:00+00:00",
            state="awaiting_human",
            lease=build_lease(),
            attempts_used=1,
        )
        self.assertEqual(checkpoint["retry_budget"]["attempts_used"], 1)
        result = self._classify()
        self.assertEqual((result.classification, result.exit_code), ("awaiting_human", 11))
        self.assertIn("retry_budget_exhausted", result.reasons)

    def test_work_snapshot_is_self_contained_and_stably_ordered(self) -> None:
        intent = self._arm_refined()
        snapshot = intent["work_snapshot"]
        self.assertEqual(snapshot["subordinate_context_ids"], ["child-a", "child-z"])
        self.assertEqual(snapshot["git_commit"], "c70b317ffeec568ea663e7fc5319b84cf3e69d4e")
        self.assertTrue(snapshot["work_vector"])
        self.assertEqual(snapshot["parallel_references"][0]["context_id"], "child-z")
        self.assertEqual(snapshot["file_state"][0]["path"], "continuation_schema.py")

    def test_reflex_handoff_claim_and_fired_receipt_are_idempotent_and_fail_closed(self) -> None:
        self._arm_refined()
        request, disposition, request_path = prepare_reflex_request(
            root=self.root,
            intent_id=self.intent_id,
            at=AT,
            boot_id=BOOT_ID,
            current_token_source="test-capped-plan",
            current_token_model="capped",
            persist=True,
        )
        self.assertEqual(disposition, "created")
        self.assertTrue(request_path.is_file())
        self.assertEqual(request["system_protocol"]["role"], "system")
        self.assertEqual(request["system_protocol"]["maximum_new_turns"], 1)
        self.assertFalse(request["system_protocol"]["user_message_sent"])
        self.assertEqual(
            prepare_reflex_request(
                root=self.root,
                intent_id=self.intent_id,
                at=AT,
                boot_id=BOOT_ID,
                current_token_source="test-capped-plan",
                current_token_model="capped",
                persist=True,
            )[1],
            "identical",
        )
        with self.assertRaises(ContinuationReflexBlocked):
            claim_reflex_request(
                root=self.root,
                request_id=request["request_id"],
                attempt=1,
                claim_id=str(uuid.uuid4()),
                adapter_instance="adapter-1",
                boot_id=BOOT_ID,
                claimed_at="2026-01-01T00:05:00+00:00",
                expires_at="2026-01-01T00:06:00+00:00",
                context_id=self.context_id,
                context_exists=True,
                context_running=True,
            )
        claim_id = str(uuid.uuid4())
        claim_kwargs = {
            "root": self.root,
            "request_id": request["request_id"],
            "attempt": 1,
            "claim_id": claim_id,
            "adapter_instance": "adapter-1",
            "boot_id": BOOT_ID,
            "claimed_at": "2026-01-01T00:05:00+00:00",
            "expires_at": "2026-01-01T00:06:00+00:00",
            "context_id": self.context_id,
            "context_exists": True,
            "context_running": False,
        }
        claim, claim_disposition, _ = claim_reflex_request(**claim_kwargs)
        self.assertEqual(claim_disposition, "created")
        self.assertEqual(claim_reflex_request(**claim_kwargs)[1], "identical")
        receipt_kwargs = {
            "root": self.root,
            "request_id": request["request_id"],
            "attempt": 1,
            "receipt_id": str(uuid.uuid4()),
            "turn_id": "turn-1",
            "fired_at": "2026-01-01T00:05:30+00:00",
            "context_id": self.context_id,
            "context_exists": True,
            "context_was_running": False,
            "injection_role": "system",
            "maximum_new_turns": 1,
            "user_message_sent": False,
        }
        receipt, receipt_disposition, _ = record_reflex_fired(**receipt_kwargs)
        self.assertEqual(receipt_disposition, "created")
        self.assertEqual(receipt["event_type"], "continuation_reflex_fired")
        self.assertEqual(receipt["fired"]["claim_id"], claim["claim"]["claim_id"])
        self.assertEqual(record_reflex_fired(**receipt_kwargs)[1], "identical")

    def test_reflex_request_dry_run_writes_nothing_and_human_gate_never_prepares(self) -> None:
        intent = self._arm_refined()
        before = self._tree_bytes()
        request, disposition, path = prepare_reflex_request(
            root=self.root,
            intent_id=self.intent_id,
            at=AT,
            boot_id=BOOT_ID,
            current_token_source="test-capped-plan",
            current_token_model="capped",
            persist=False,
        )
        self.assertEqual(disposition, "dry_run")
        self.assertFalse(path.exists())
        self.assertEqual(before, self._tree_bytes())
        record_checkpoint(
            start=self.root,
            intent_id=self.intent_id,
            expected_intent_sha256=intent["intent_sha256"],
            checkpoint_id=str(uuid.uuid4()),
            recorded_at="2026-01-01T00:01:00+00:00",
            state="awaiting_human",
            lease=build_lease(),
        )
        with self.assertRaises(ContinuationReflexBlocked) as raised:
            prepare_reflex_request(
                root=self.root,
                intent_id=self.intent_id,
                at=AT,
                boot_id=BOOT_ID,
                current_token_source="test-capped-plan",
                current_token_model="capped",
                persist=True,
            )
        self.assertEqual(raised.exception.classification, "awaiting_human")

    def test_entrypoint_has_handoff_only_and_no_agent_zero_engine_import(self) -> None:
        source = (ROOT / "entrypoint.py").read_text(encoding="utf-8")
        reflex_source = (ROOT / "continuation_reflex.py").read_text(encoding="utf-8")
        self.assertIn('"adapter_status": "handoff_only"', source)
        for text in (source, reflex_source):
            self.assertNotIn("from agent import", text)
            self.assertNotIn("UserMessage(", text)
            self.assertNotIn("communicate(", text)
            self.assertNotIn("call_chat_model_turn", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
