from __future__ import annotations

import ast
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(
    os.environ.get("RECURSIVE_FIELD_PROJECT_ROOT", "/a0/usr/projects/recursive-field")
).resolve()
PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from checkpoint_intent import arm_intent, record_checkpoint
from continuation_reflex import (
    build_reflex_request,
    claim_reflex_request,
    prepare_reflex_request,
    record_reflex_fired,
)
from continuation_schema import build_lease, canonical_json_bytes

_RUNTIME_SPEC = importlib.util.spec_from_file_location(
    "continuation_reflex_runtime_under_test",
    PLUGIN_ROOT / "helpers" / "runtime.py",
)
if _RUNTIME_SPEC is None or _RUNTIME_SPEC.loader is None:
    raise RuntimeError("cannot load continuation reflex runtime under test")
runtime = importlib.util.module_from_spec(_RUNTIME_SPEC)
sys.modules[_RUNTIME_SPEC.name] = runtime
_RUNTIME_SPEC.loader.exec_module(runtime)

BOOT_ID = "11111111-1111-4111-8111-111111111111"
AT = __import__("datetime").datetime.fromisoformat("2026-01-01T00:10:00+00:00")


class FakeContext:
    def __init__(self, running: bool = False):
        self.running = running

    def is_running(self) -> bool:
        return self.running


class ContinuationReflexPluginTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copy2(PROJECT_ROOT / ".recursive-field-root", self.root / ".recursive-field-root")
        (self.root / "state").mkdir()
        shutil.copy2(
            PROJECT_ROOT / "state/control_profile.json",
            self.root / "state/control_profile.json",
        )
        self.intent_id = str(uuid.uuid4())
        self.context_id = "opaque-existing-context"
        self.intent = arm_intent(
            start=self.root,
            intent_id=self.intent_id,
            context_id=self.context_id,
            history_sha256="a" * 64,
            observed_at="2026-01-01T00:00:00+00:00",
            created_at="2026-01-01T00:00:00+00:00",
            required_capabilities=["observe"],
            attest_context_exists=True,
            interruption_class="self_initiated",
            token_source="test-capped-plan",
            token_model="capped",
            maximum_retry_attempts=2,
            work_vector="Continue from the saved work vector.",
            git_commit="c70b317ffeec568ea663e7fc5319b84cf3e69d4e",
            file_state=[],
            subordinate_context_ids=["opaque-subordinate"],
            parallel_references=[],
        )[0]

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _request(self) -> tuple[dict, Path]:
        request, _, path = prepare_reflex_request(
            root=self.root,
            intent_id=self.intent_id,
            at=AT,
            boot_id=BOOT_ID,
            current_token_source="test-capped-plan",
            current_token_model="capped",
            persist=True,
        )
        return request, path

    def _publish_request_for_intent(self, intent: dict) -> Path:
        request = build_reflex_request(intent)
        path = (
            self.root
            / "state/continuations/reflex/requests"
            / f"{request['request_id']}.json"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_json_bytes(request) + b"\n")
        return path

    def test_valid_request_is_ready_without_scan_side_effects(self) -> None:
        request, path = self._request()
        result = runtime.inspect_request(
            self.root,
            path,
            current_token_source="test-capped-plan",
            current_token_model="capped",
            context_lookup=lambda context_id: FakeContext(False)
            if context_id == self.context_id
            else None,
        )
        self.assertEqual(result.disposition, "ready")
        self.assertEqual(result.reasons, ())
        self.assertFalse(
            (self.root / "state/continuations/reflex/claims" / request["request_id"]).exists()
        )
        self.assertFalse(
            (self.root / "state/continuations/reflex/receipts" / f"{request['request_id']}.json").exists()
        )

    def test_context_lookup_is_strict_and_running_context_is_excluded(self) -> None:
        _, path = self._request()
        missing = runtime.inspect_request(self.root, path, context_lookup=lambda _: None)
        self.assertEqual(missing.reasons, ("existing_context_not_found",))
        running = runtime.inspect_request(
            self.root, path, context_lookup=lambda _: FakeContext(True)
        )
        self.assertEqual(running.reasons, ("context_already_running",))

    def test_request_tamper_is_invalid(self) -> None:
        request, path = self._request()
        request["system_protocol"]["maximum_new_turns"] = 2
        path.write_text(json.dumps(request), encoding="utf-8")
        result = runtime.inspect_request(self.root, path, context_lookup=lambda _: FakeContext())
        self.assertEqual(result.disposition, "invalid")
        self.assertIn("reflex_sha256 mismatch", result.reasons)

    def test_awaiting_human_is_never_eligible(self) -> None:
        checkpoint, _, _, _ = record_checkpoint(
            start=self.root,
            intent_id=self.intent_id,
            expected_intent_sha256=self.intent["intent_sha256"],
            checkpoint_id=str(uuid.uuid4()),
            recorded_at="2026-01-01T00:01:00+00:00",
            state="awaiting_human",
            lease=build_lease(),
        )
        intent = json.loads(
            (self.root / "state/continuations/intents" / f"{self.intent_id}.json").read_text()
        )
        path = self._publish_request_for_intent(intent)
        result = runtime.inspect_request(self.root, path, context_lookup=lambda _: FakeContext())
        self.assertEqual(result.disposition, "invalid")
        self.assertEqual(result.reasons, ("awaiting_human_excluded",))
        self.assertEqual(checkpoint["state"], "awaiting_human")

    def test_old_boot_held_lease_is_rejected_before_runtime_trigger(self) -> None:
        record_checkpoint(
            start=self.root,
            intent_id=self.intent_id,
            expected_intent_sha256=self.intent["intent_sha256"],
            checkpoint_id=str(uuid.uuid4()),
            recorded_at="2026-01-01T00:01:00+00:00",
            state="active",
            lease=build_lease(
                state="held",
                holder="formation",
                attempt_id=str(uuid.uuid4()),
                generation=1,
                boot_id=BOOT_ID,
                acquired_at="2026-01-01T00:01:00+00:00",
                expires_at="2026-01-01T01:01:00+00:00",
            ),
        )
        intent = json.loads(
            (self.root / "state/continuations/intents" / f"{self.intent_id}.json").read_text()
        )
        path = self._publish_request_for_intent(intent)
        original = runtime._read_boot_id
        runtime._read_boot_id = lambda: "22222222-2222-4222-8222-222222222222"
        try:
            result = runtime.inspect_request(
                self.root, path, context_lookup=lambda _: FakeContext()
            )
        finally:
            runtime._read_boot_id = original
        self.assertEqual(result.reasons, ("old_boot_lease_requires_reconciliation",))

    def test_external_capped_to_metered_is_rejected(self) -> None:
        other_id = str(uuid.uuid4())
        arm_intent(
            start=self.root,
            intent_id=other_id,
            context_id="external-context",
            history_sha256="b" * 64,
            observed_at="2026-01-01T00:00:00+00:00",
            created_at="2026-01-01T00:00:00+00:00",
            required_capabilities=["observe"],
            attest_context_exists=True,
            interruption_class="external",
            token_source="capped-plan",
            token_model="capped",
            maximum_retry_attempts=2,
            work_vector="Continue external work.",
            git_commit="c70b317ffeec568ea663e7fc5319b84cf3e69d4e",
            file_state=[],
            subordinate_context_ids=[],
            parallel_references=[],
        )
        request, _, path = prepare_reflex_request(
            root=self.root,
            intent_id=other_id,
            at=AT,
            boot_id=BOOT_ID,
            current_token_source="capped-plan",
            current_token_model="capped",
            persist=True,
        )
        result = runtime.inspect_request(
            self.root,
            path,
            current_token_source="metered-api",
            current_token_model="metered",
            context_lookup=lambda _: FakeContext(),
        )
        self.assertEqual(request["interruption_class"], "external")
        self.assertEqual(result.reasons, ("external_capped_to_metered_drift",))

    def test_existing_claim_and_fired_receipt_prevent_duplicate_trigger(self) -> None:
        request, path = self._request()
        claim_reflex_request(
            root=self.root,
            request_id=request["request_id"],
            attempt=1,
            claim_id="33333333-3333-4333-8333-333333333333",
            adapter_instance="test-adapter",
            boot_id=BOOT_ID,
            claimed_at="2026-01-01T00:11:00+00:00",
            expires_at="2026-01-01T00:20:00+00:00",
            context_id=self.context_id,
            context_exists=True,
            context_running=False,
        )
        claimed = runtime.inspect_request(
            self.root,
            path,
            current_token_source="test-capped-plan",
            current_token_model="capped",
            context_lookup=lambda _: FakeContext(),
        )
        self.assertEqual(claimed.disposition, "claimed")
        self.assertEqual(claimed.reasons, ("claim_exists",))

        record_reflex_fired(
            root=self.root,
            request_id=request["request_id"],
            attempt=1,
            receipt_id="44444444-4444-4444-8444-444444444444",
            turn_id="opaque-turn-id",
            fired_at="2026-01-01T00:12:00+00:00",
            context_id=self.context_id,
            context_exists=True,
            context_was_running=False,
            injection_role="system",
            maximum_new_turns=1,
            user_message_sent=False,
        )
        fired = runtime.inspect_request(
            self.root,
            path,
            current_token_source="test-capped-plan",
            current_token_model="capped",
            context_lookup=lambda _: FakeContext(),
        )
        self.assertEqual(fired.disposition, "already_fired")
        self.assertEqual(fired.reasons, ("receipt_exists",))

    def test_prepare_dispatch_claims_and_builds_closed_engine_request(self) -> None:
        request, _ = self._request()
        config = {
            "enabled": True,
            "field_root": str(self.root),
            "current_token_source": "test-capped-plan",
            "current_token_model": "capped",
            "adapter_instance": "test-api",
        }
        now = __import__("datetime").datetime.fromisoformat(
            "2026-01-01T00:11:00+00:00"
        )
        with patch.object(runtime, "_read_boot_id", return_value=BOOT_ID), patch.object(
            runtime, "_utc_now", return_value=now
        ):
            plan = runtime.prepare_dispatch(
                config,
                request["request_id"],
                context_lookup=lambda value: FakeContext(False)
                if value == self.context_id
                else None,
            )
            replay = runtime.prepare_dispatch(
                config,
                request["request_id"],
                context_lookup=lambda _value: FakeContext(False),
            )

        self.assertEqual(plan.claim_disposition, "created")
        self.assertEqual(replay.claim_disposition, "exists_identical")
        self.assertEqual(plan.claim, replay.claim)

        # An authenticated retry can reach the engine while the same claimed
        # continuation is active; the engine owns 202 in-progress replay and
        # distinguishes unrelated running work under its activity lock.
        with patch.object(runtime, "_read_boot_id", return_value=BOOT_ID), patch.object(
            runtime, "_utc_now", return_value=now
        ):
            active_replay = runtime.prepare_dispatch(
                config,
                request["request_id"],
                context_lookup=lambda _value: FakeContext(True),
            )
        self.assertEqual(active_replay.claim_disposition, "exists_identical")
        self.assertEqual(active_replay.claim, plan.claim)
        self.assertEqual(set(plan.engine_request), {
            "schema_version",
            "request_id",
            "context_id",
            "generation",
            "formation_reflex_sha256",
            "system_protocol",
        })
        self.assertEqual(plan.engine_request["request_id"], request["request_id"])
        self.assertEqual(plan.engine_request["formation_reflex_sha256"], request["reflex_sha256"])
        self.assertEqual(plan.engine_request["system_protocol"]["role"], "system")
        self.assertIs(plan.engine_request["system_protocol"]["user_message_sent"], False)

    def test_record_fired_is_separate_and_idempotent(self) -> None:
        request, _ = self._request()
        config = {
            "enabled": True,
            "field_root": str(self.root),
            "current_token_source": "test-capped-plan",
            "current_token_model": "capped",
        }
        now = __import__("datetime").datetime.fromisoformat(
            "2026-01-01T00:11:00+00:00"
        )
        with patch.object(runtime, "_read_boot_id", return_value=BOOT_ID), patch.object(
            runtime, "_utc_now", return_value=now
        ):
            plan = runtime.prepare_dispatch(
                config,
                request["request_id"],
                context_lookup=lambda _value: FakeContext(False),
            )
            engine_result = {
                "request_id": request["request_id"],
                "context_id": self.context_id,
                "generation": 1,
                "state": "completed",
                "terminal": True,
                "disposition": "completed",
                "receipt": {
                    "request_id": request["request_id"],
                    "context_id": self.context_id,
                    "generation": 1,
                    "state": "completed",
                    "terminal": True,
                    "formation_reflex_sha256": request["reflex_sha256"],
                    "protocol_text_sha256": request["system_protocol"]["text_sha256"],
                },
            }
            fired, disposition = runtime.record_fired(plan, engine_result)
            replay, replay_disposition = runtime.record_fired(plan, engine_result)
            prepared = runtime.prepare_dispatch(
                config,
                request["request_id"],
                context_lookup=lambda _value: FakeContext(False),
            )

        self.assertEqual(disposition, "created")
        self.assertEqual(replay_disposition, "exists_identical")
        self.assertEqual(replay, fired)
        self.assertEqual(fired["event_type"], "continuation_reflex_fired")
        self.assertEqual(fired["fired"]["injection_role"], "system")
        self.assertIs(fired["fired"]["user_message_sent"], False)
        self.assertEqual(prepared.existing_fired, fired)
        self.assertIsNone(prepared.claim)

    def test_record_fired_requires_exact_terminal_engine_evidence(self) -> None:
        request, _ = self._request()
        config = {
            "enabled": True,
            "field_root": str(self.root),
            "current_token_source": "test-capped-plan",
            "current_token_model": "capped",
        }
        with patch.object(runtime, "_read_boot_id", return_value=BOOT_ID):
            plan = runtime.prepare_dispatch(
                config,
                request["request_id"],
                context_lookup=lambda _value: FakeContext(False),
            )
        base = {
            "request_id": request["request_id"],
            "context_id": self.context_id,
            "generation": 1,
            "state": "completed",
            "terminal": True,
            "disposition": "completed",
            "receipt": {
                "request_id": request["request_id"],
                "context_id": self.context_id,
                "generation": 1,
                "state": "completed",
                "terminal": True,
                "formation_reflex_sha256": request["reflex_sha256"],
                "protocol_text_sha256": request["system_protocol"]["text_sha256"],
            },
        }
        for mutate, reason in (
            (lambda value: value.update(terminal=False), "engine_turn_not_completed"),
            (lambda value: value.update(generation=2), "engine_receipt_request_binding_mismatch"),
            (
                lambda value: value["receipt"].update(
                    formation_reflex_sha256="f" * 64
                ),
                "engine_receipt_evidence_mismatch",
            ),
        ):
            candidate = json.loads(json.dumps(base))
            mutate(candidate)
            with self.subTest(reason=reason), self.assertRaisesRegex(
                runtime.ReflexConflictError, reason
            ):
                runtime.record_fired(plan, candidate)

    def test_existing_claim_from_old_boot_is_conflict(self) -> None:
        request, _ = self._request()
        config = {
            "enabled": True,
            "field_root": str(self.root),
            "current_token_source": "test-capped-plan",
            "current_token_model": "capped",
        }
        now = __import__("datetime").datetime.fromisoformat(
            "2026-01-01T00:11:00+00:00"
        )
        with patch.object(runtime, "_read_boot_id", return_value=BOOT_ID), patch.object(
            runtime, "_utc_now", return_value=now
        ):
            runtime.prepare_dispatch(
                config,
                request["request_id"],
                context_lookup=lambda _value: FakeContext(False),
            )
        with patch.object(
            runtime,
            "_read_boot_id",
            return_value="22222222-2222-4222-8222-222222222222",
        ), patch.object(runtime, "_utc_now", return_value=now):
            with self.assertRaisesRegex(
                runtime.ReflexConflictError, "old_boot"
            ):
                runtime.prepare_dispatch(
                    config,
                    request["request_id"],
                    context_lookup=lambda _value: FakeContext(False),
                )

    def test_prepare_dispatch_requires_existing_idle_context(self) -> None:
        request, _ = self._request()
        config = {
            "enabled": True,
            "field_root": str(self.root),
            "current_token_source": "test-capped-plan",
            "current_token_model": "capped",
        }
        with self.assertRaises(runtime.ReflexNotFoundError):
            runtime.prepare_dispatch(config, request["request_id"], context_lookup=lambda _: None)
        with self.assertRaises(runtime.ReflexConflictError):
            runtime.prepare_dispatch(
                config,
                request["request_id"],
                context_lookup=lambda _: FakeContext(True),
            )
        self.assertFalse(
            (self.root / "state/continuations/reflex/claims" / request["request_id"]).exists()
        )

    def test_disabled_scan_is_inert(self) -> None:
        self._request()
        before = {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }
        self.assertEqual(runtime.scan_once({"enabled": False}, force=True), ())
        after = {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }
        self.assertEqual(before, after)

    def test_plugin_source_never_calls_user_message_or_model_entrypoints(self) -> None:
        forbidden = {"UserMessage", "communicate", "call_chat_model_turn", "monologue"}
        calls: list[str] = []
        for path in PLUGIN_ROOT.rglob("*.py"):
            if "tests" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if isinstance(node.func, ast.Name):
                    calls.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.append(node.func.attr)
        self.assertFalse(forbidden.intersection(calls), calls)


if __name__ == "__main__":
    unittest.main(verbosity=2)
