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
    ContinuationValidationError,
    atomic_write_document,
    canonical_json_bytes,
    canonical_sha256,
    seal_document,
    validate_document,
)
from resume_thread import EXIT_CODES, classify_intent


ROOT = Path(__file__).resolve().parent
AT = datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc)


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

    def _checkpoint(
        self,
        state: str = "armed",
        *,
        checkpoint_id: str | None = None,
        lease_state: str = "unclaimed",
        acquired_at: str = "2026-01-01T00:01:00+00:00",
        expires_at: str = "2026-01-01T00:10:00+00:00",
        previous: dict | None = None,
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
                "acquired_at": acquired_at,
                "expires_at": expires_at,
            }
        else:
            lease = {
                "state": lease_state,
                "holder": None,
                "attempt_id": None,
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
                "state": state,
                "security": {
                    "profile": security_profile,
                    "required_capabilities": capabilities or ["observe"],
                },
                "context_evidence": self._evidence(exists=exists),
                "effect_boundary": self._effect_boundary(),
                "lease": lease,
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
        return classify_intent(self.intent_id, start=self.root, at=AT)

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
        self.assertIn("current_lease_conflicts_with_state", self._classify().reasons)

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
