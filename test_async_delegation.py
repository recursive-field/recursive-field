#!/usr/bin/env python3
"""Isolated regression harness for bounded asynchronous delegation."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from consume_queue import consume_queue
from delegate_task import delegate_task
from verify_unit_cell import verify_unit_cell


class AsyncDelegationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="recursive-field-async-")
        self.root = Path(self.temp_dir.name)
        self.genesis_uuid = str(uuid.uuid4())
        self.sender_id = str(uuid.uuid4())
        self.recipient_id = str(uuid.uuid4())
        self.mesh_id = str(uuid.uuid4())
        self._build_field()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_json(self, path: Path, value: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def _write_jsonl(self, path: Path, events: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "".join(json.dumps(event) + "\n" for event in events),
            encoding="utf-8",
        )

    def _events(self, path: Path) -> list[dict]:
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _set_security(self, name: str) -> None:
        path = self.root / "state" / "control_profile.json"
        profile = json.loads(path.read_text(encoding="utf-8"))
        profile["active_security_profile"] = name
        self._write_json(path, profile)

    def _build_field(self) -> None:
        self._write_json(
            self.root / ".recursive-field-root",
            {
                "genesis_uuid": self.genesis_uuid,
                "inception_timestamp": "2026-01-01T00:00:00+00:00",
                "schema_version": "1.0.0",
            },
        )
        identities = {
            "sender": self.sender_id,
            "recipient": self.recipient_id,
        }
        for slug, agent_id in identities.items():
            agent_dir = self.root / "agents" / slug
            self._write_json(
                agent_dir / "identity.json",
                {
                    "agent_id": agent_id,
                    "slug": slug,
                    "field_genesis_uuid": self.genesis_uuid,
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "role": "test",
                    "schema_version": "1.0.0",
                },
            )
            self._write_jsonl(
                agent_dir / "observations" / "log.jsonl",
                [
                    {
                        "event_type": "genesis_observation",
                        "timestamp": "2026-01-01T00:00:00+00:00",
                        "agent_id": agent_id,
                    },
                    {
                        "event_type": "mesh_connected",
                        "timestamp": "2026-01-01T00:00:01+00:00",
                        "mesh_id": self.mesh_id,
                    },
                ],
            )
            (agent_dir / "memory").mkdir(parents=True, exist_ok=True)

        prompt = "active recipient prompt\n"
        (self.root / "agents" / "recipient" / "assembled_system_prompt.md").write_text(
            prompt, encoding="utf-8"
        )
        self.expected_prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()

        mesh_dir = self.root / "mesh" / "test-mesh"
        self._write_json(
            mesh_dir / "channel.json",
            {
                "mesh_id": self.mesh_id,
                "slug": "test-mesh",
                "field_genesis_uuid": self.genesis_uuid,
                "endpoints": [
                    {"slug": "sender", "agent_id": self.sender_id},
                    {"slug": "recipient", "agent_id": self.recipient_id},
                ],
                "channel_type": "peer-to-peer",
                "created_at": "2026-01-01T00:00:01+00:00",
                "schema_version": "1.0.0",
            },
        )
        self._write_jsonl(
            mesh_dir / "queue.jsonl",
            [
                {
                    "event_type": "queue_initialized",
                    "timestamp": "2026-01-01T00:00:01+00:00",
                    "mesh_id": self.mesh_id,
                }
            ],
        )
        (self.root / "gateways").mkdir()
        (self.root / "state" / "snapshots").mkdir(parents=True)
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
        self._write_json(
            self.root / "tmp" / "field_env.json",
            {
                "field_root": str(self.root),
                "genesis_uuid": self.genesis_uuid,
                "library": "test",
                "initialized_at": "2026-01-01T00:00:00+00:00",
            },
        )

    def _dispatch_async(self, payload: str) -> dict:
        return delegate_task(
            "sender",
            "recipient",
            "test-mesh",
            payload,
            start=self.root,
            mode="async",
        )

    def _claim_path(self, task_id: str) -> Path:
        return (
            self.root
            / "agents"
            / "recipient"
            / "worker_state"
            / "claims"
            / f"{task_id}.json"
        )

    def test_bounded_async_lifecycle(self) -> None:
        mesh_dir = self.root / "mesh" / "test-mesh"
        queue_path = mesh_dir / "queue.jsonl"
        recipient_log = self.root / "agents" / "recipient" / "observations" / "log.jsonl"

        # Default and explicit acknowledge modes retain legacy immediate completion.
        for mode in (None, "acknowledge"):
            kwargs = {} if mode is None else {"mode": mode}
            before = len(self._events(queue_path))
            result = delegate_task(
                "sender",
                "recipient",
                "test-mesh",
                "legacy acknowledgement",
                start=self.root,
                **kwargs,
            )
            self.assertEqual(result["status"], "completed")
            self.assertIsNotNone(result["completed_at"])
            self.assertEqual(
                [event["event_type"] for event in self._events(queue_path)[before:]],
                ["task_dispatched", "task_result"],
            )
            self.assertFalse((mesh_dir / "tasks" / f"{result['task_id']}.json").exists())

        # Async dispatch writes one durable envelope and no immediate result.
        before_queue = len(self._events(queue_path))
        async_result = self._dispatch_async("inspect the unit cell")
        task_id = async_result["task_id"]
        self.assertEqual(async_result["status"], "queued")
        self.assertIsNone(async_result["completed_at"])
        task_path = mesh_dir / "tasks" / f"{task_id}.json"
        envelope = json.loads(task_path.read_text(encoding="utf-8"))
        self.assertEqual(envelope["task_payload"], "inspect the unit cell")
        self.assertEqual(envelope["required_capability"], "coordinate")
        self.assertEqual(envelope["task_type"], "inspect_unit_cell")
        self.assertEqual(envelope["execution_policy"], "allowlisted")
        self.assertEqual(envelope["active_prompt_hash"], self.expected_prompt_hash)
        new_queue = self._events(queue_path)[before_queue:]
        self.assertEqual([event["event_type"] for event in new_queue], ["task_dispatched"])
        self.assertFalse((mesh_dir / "results" / f"{task_id}.json").exists())

        # A bounded worker executes exactly once and persists all worker artifacts.
        consumed = consume_queue("recipient", "test-mesh", once=True, start=self.root)
        self.assertEqual(consumed["status"], "completed")
        claim_path = self._claim_path(task_id)
        result_path = mesh_dir / "results" / f"{task_id}.json"
        cursor_path = (
            self.root
            / "agents"
            / "recipient"
            / "worker_state"
            / "test-mesh.cursor.json"
        )
        self.assertTrue(claim_path.is_file())
        self.assertTrue(result_path.is_file())
        self.assertTrue(cursor_path.is_file())
        result_artifact = json.loads(result_path.read_text(encoding="utf-8"))
        expected_result_hash = hashlib.sha256(
            json.dumps(
                result_artifact["result"],
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(result_artifact["result_sha256"], expected_result_hash)
        self.assertEqual(result_artifact["result"]["integrity"], "ok")
        self.assertEqual(json.loads(claim_path.read_text())["status"], "completed")

        recipient_events = self._events(recipient_log)
        self.assertEqual(
            sum(
                event.get("event_type") == "task_started"
                and event.get("task_id") == task_id
                for event in recipient_events
            ),
            1,
        )
        self.assertEqual(
            sum(
                event.get("event_type") == "task_completed"
                and event.get("task_id") == task_id
                for event in recipient_events
            ),
            1,
        )
        self.assertEqual(
            sum(
                event.get("event_type") == "task_result"
                and event.get("task_id") == task_id
                for event in self._events(queue_path)
            ),
            1,
        )

        # Replay only scans past the worker-authored result; it never re-executes.
        before_replay_log = recipient_log.read_bytes()
        before_replay_result = result_path.read_bytes()
        replay = consume_queue("recipient", "test-mesh", once=True, start=self.root)
        self.assertEqual(replay["status"], "idle")
        self.assertEqual(recipient_log.read_bytes(), before_replay_log)
        self.assertEqual(result_path.read_bytes(), before_replay_result)
        self.assertEqual(
            sum(
                event.get("event_type") == "task_result"
                and event.get("task_id") == task_id
                for event in self._events(queue_path)
            ),
            1,
        )

        # Payload tampering is rejected, claimed, failed, and never started.
        tampered = self._dispatch_async("original payload")
        tampered_id = tampered["task_id"]
        tampered_path = mesh_dir / "tasks" / f"{tampered_id}.json"
        tampered_envelope = json.loads(tampered_path.read_text(encoding="utf-8"))
        tampered_envelope["task_payload"] = "modified after dispatch"
        self._write_json(tampered_path, tampered_envelope)
        rejected = consume_queue("recipient", "test-mesh", once=True, start=self.root)
        self.assertEqual(rejected["status"], "failed")
        self.assertEqual(rejected["failure_kind"], "validation")
        tampered_events = [
            event
            for event in self._events(recipient_log)
            if event.get("task_id") == tampered_id
        ]
        self.assertNotIn("task_started", {event["event_type"] for event in tampered_events})
        self.assertIn("task_failed", {event["event_type"] for event in tampered_events})
        self.assertEqual(
            json.loads(self._claim_path(tampered_id).read_text())["status"],
            "failed",
        )

        # Move past the tamper result, then prove a current lockdown halts execution.
        self.assertEqual(
            consume_queue("recipient", "test-mesh", once=True, start=self.root)["status"],
            "idle",
        )
        blocked_task = self._dispatch_async("blocked by current posture")
        blocked_id = blocked_task["task_id"]
        self._set_security("lockdown")
        cursor_before_block = cursor_path.read_bytes()
        blocked = consume_queue("recipient", "test-mesh", once=True, start=self.root)
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(blocked["security_profile"], "lockdown")
        self.assertFalse(blocked["cursor_advanced"])
        self.assertEqual(cursor_path.read_bytes(), cursor_before_block)
        self.assertFalse(self._claim_path(blocked_id).exists())
        self.assertFalse((mesh_dir / "results" / f"{blocked_id}.json").exists())
        self.assertNotIn(
            "task_started",
            {
                event["event_type"]
                for event in self._events(recipient_log)
                if event.get("task_id") == blocked_id
            },
        )

        # New worker state does not alter the structural graph contract.
        verified_root, _, agents, meshes, gateways = verify_unit_cell(self.root)
        self.assertEqual(verified_root, self.root)
        self.assertEqual(set(agents), {"sender", "recipient"})
        self.assertEqual(set(meshes), {"test-mesh"})
        self.assertEqual(gateways, {})

        # Persisted snapshots include task, claim, result, and cursor artifacts.
        ledger_entries = self._events(self.root / "state" / "ledger.jsonl")
        latest_hashes = ledger_entries[-1]["file_hashes"]
        self.assertIn(
            f"mesh/test-mesh/tasks/{tampered_id}.json", latest_hashes
        )
        self.assertIn(
            f"mesh/test-mesh/results/{tampered_id}.json", latest_hashes
        )
        self.assertIn(
            "agents/recipient/worker_state/test-mesh.cursor.json", latest_hashes
        )
        self.assertIn(
            f"agents/recipient/worker_state/claims/{tampered_id}.json",
            latest_hashes,
        )
        self.assertFalse(any("mesh/test-mesh/claims/" in key for key in latest_hashes))

    def test_legacy_acknowledge_compatibility(self) -> None:
        result = delegate_task(
            "sender", "recipient", "test-mesh", "legacy", start=self.root
        )
        self.assertEqual(result["status"], "completed")
        task_events = [
            event["event_type"]
            for event in self._events(self.root / "mesh" / "test-mesh" / "queue.jsonl")
            if event.get("task_id") == result["task_id"]
        ]
        self.assertEqual(task_events, ["task_dispatched", "task_result"])

    def test_async_no_immediate_result(self) -> None:
        result = self._dispatch_async("inspect")
        task_id = result["task_id"]
        mesh_dir = self.root / "mesh" / "test-mesh"
        self.assertEqual(result["status"], "queued")
        self.assertTrue((mesh_dir / "tasks" / f"{task_id}.json").is_file())
        self.assertFalse((mesh_dir / "results" / f"{task_id}.json").exists())
        self.assertEqual(
            [
                event["event_type"]
                for event in self._events(mesh_dir / "queue.jsonl")
                if event.get("task_id") == task_id
            ],
            ["task_dispatched"],
        )

    def test_once_execution_and_noop_replay(self) -> None:
        task_id = self._dispatch_async("inspect")["task_id"]
        first = consume_queue("recipient", "test-mesh", once=True, start=self.root)
        self.assertEqual(first["status"], "completed")
        queue_path = self.root / "mesh" / "test-mesh" / "queue.jsonl"
        before = self._events(queue_path)
        second = consume_queue("recipient", "test-mesh", once=True, start=self.root)
        self.assertEqual(second["status"], "idle")
        after = self._events(queue_path)
        self.assertEqual(before, after)
        self.assertEqual(
            sum(
                event.get("event_type") == "task_result"
                and event.get("task_id") == task_id
                for event in after
            ),
            1,
        )

    def test_result_present_cursor_not_advanced_preserves_result_artifact(self) -> None:
        task_id = self._dispatch_async("recover existing result")["task_id"]
        mesh_dir = self.root / "mesh" / "test-mesh"
        queue_path = mesh_dir / "queue.jsonl"
        recipient_log = (
            self.root / "agents" / "recipient" / "observations" / "log.jsonl"
        )
        cursor_path = (
            self.root
            / "agents"
            / "recipient"
            / "worker_state"
            / "test-mesh.cursor.json"
        )
        result_path = mesh_dir / "results" / f"{task_id}.json"

        completed = consume_queue(
            "recipient", "test-mesh", once=True, start=self.root
        )
        self.assertEqual(completed["status"], "completed")
        dispatch_index = next(
            index
            for index, event in enumerate(self._events(queue_path))
            if event.get("event_type") == "task_dispatched"
            and event.get("task_id") == task_id
        )
        result_bytes = result_path.read_bytes()
        result_stat = result_path.stat()

        # Reconstruct the crash window after the atomic result write but before
        # terminal events, claim finalization, or cursor advancement.
        claim = json.loads(self._claim_path(task_id).read_text())
        claim["status"] = "claimed"
        for key in (
            "finished_at",
            "result_path",
            "result_sha256",
            "result_artifact_sha256",
        ):
            claim.pop(key, None)
        self._write_json(self._claim_path(task_id), claim)
        self._write_jsonl(
            queue_path,
            [
                event
                for event in self._events(queue_path)
                if not (
                    event.get("event_type") == "task_result"
                    and event.get("task_id") == task_id
                )
            ],
        )
        self._write_jsonl(
            recipient_log,
            [
                event
                for event in self._events(recipient_log)
                if not (
                    event.get("event_type") == "task_completed"
                    and event.get("task_id") == task_id
                )
            ],
        )
        cursor = json.loads(cursor_path.read_text())
        cursor.update(
            {
                "next_event_index": dispatch_index,
                "last_task_id": None,
                "last_status": "idle",
            }
        )
        self._write_json(cursor_path, cursor)

        with patch(
            "consume_queue._write_result_artifact",
            side_effect=AssertionError("recovery must not rewrite the result artifact"),
        ):
            recovered = consume_queue(
                "recipient", "test-mesh", once=True, start=self.root
            )

        self.assertEqual(recovered["status"], "replayed")
        self.assertEqual(result_path.read_bytes(), result_bytes)
        recovered_stat = result_path.stat()
        self.assertEqual(recovered_stat.st_ino, result_stat.st_ino)
        self.assertEqual(recovered_stat.st_mtime_ns, result_stat.st_mtime_ns)
        self.assertEqual(
            json.loads(self._claim_path(task_id).read_text())["status"],
            "completed",
        )
        self.assertEqual(
            json.loads(cursor_path.read_text())["next_event_index"],
            dispatch_index + 1,
        )
        self.assertEqual(
            sum(
                event.get("event_type") == "task_result"
                and event.get("task_id") == task_id
                for event in self._events(queue_path)
            ),
            1,
        )

    def test_tamper_rejection(self) -> None:
        task_id = self._dispatch_async("original")["task_id"]
        task_path = self.root / "mesh" / "test-mesh" / "tasks" / f"{task_id}.json"
        envelope = json.loads(task_path.read_text())
        envelope["task_payload"] = "tampered"
        self._write_json(task_path, envelope)
        result = consume_queue("recipient", "test-mesh", once=True, start=self.root)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failure_kind"], "validation")

    def test_lockdown_and_missing_capability_halt(self) -> None:
        for profile_name in ("lockdown", "restricted"):
            task_id = self._dispatch_async(profile_name)["task_id"]
            control_path = self.root / "state" / "control_profile.json"
            control = json.loads(control_path.read_text())
            if profile_name == "lockdown":
                control["active_security_profile"] = "lockdown"
            else:
                control["security_profiles"]["restricted"]["capabilities"] = [
                    "observe"
                ]
            self._write_json(control_path, control)
            result = consume_queue(
                "recipient", "test-mesh", once=True, start=self.root
            )
            self.assertEqual(result["status"], "blocked")
            self.assertFalse(self._claim_path(task_id).exists())
            # Restore posture and consume the pending task before the next case.
            self._set_security("restricted")
            control = json.loads(control_path.read_text())
            control["security_profiles"]["restricted"]["capabilities"] = [
                "observe", "coordinate", "persist"
            ]
            self._write_json(control_path, control)
            self.assertEqual(
                consume_queue("recipient", "test-mesh", once=True, start=self.root)[
                    "status"
                ],
                "completed",
            )
            consume_queue("recipient", "test-mesh", once=True, start=self.root)

    def test_expired_claim_is_resumed_idempotently(self) -> None:
        dispatched = self._dispatch_async("resume")
        task_id = dispatched["task_id"]
        mesh_dir = self.root / "mesh" / "test-mesh"
        envelope = json.loads(
            (mesh_dir / "tasks" / f"{task_id}.json").read_text()
        )
        self._write_json(
            self._claim_path(task_id),
            {
                "schema_version": "1.0.0",
                "claim_id": str(uuid.uuid4()),
                "task_id": task_id,
                "agent_slug": "recipient",
                "agent_id": self.recipient_id,
                "mesh_slug": "test-mesh",
                "mesh_id": self.mesh_id,
                "envelope_sha256": envelope["envelope_sha256"],
                "status": "claimed",
                "claimed_at": "2020-01-01T00:00:00+00:00",
                "lease_expires_at": "2020-01-01T00:05:00+00:00",
                "attempt": 1,
            },
        )
        result = consume_queue("recipient", "test-mesh", once=True, start=self.root)
        self.assertEqual(result["status"], "completed")
        claim = json.loads(self._claim_path(task_id).read_text())
        self.assertEqual(claim["status"], "completed")
        self.assertEqual(claim["attempt"], 2)

    def test_graph_integrity_with_async_runtime_trees(self) -> None:
        self._dispatch_async("pending")
        root, _, agents, meshes, gateways = verify_unit_cell(self.root)
        self.assertEqual(root, self.root)
        self.assertEqual(set(agents), {"sender", "recipient"})
        self.assertEqual(set(meshes), {"test-mesh"})
        self.assertEqual(gateways, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
