#!/usr/bin/env python3
"""Consume one durable asynchronous task from a Recursive Field mesh.

Usage:
    python3 consume_queue.py <agent_slug> <mesh_slug> --once

The worker accepts only the ``inspect_unit_cell`` adapter under the
``allowlisted`` execution policy. Task payloads are data, never shell input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from find_root import find_root  # noqa: E402
from persist_state import persist_state  # noqa: E402
from verify_unit_cell import verify_unit_cell  # noqa: E402

MARKER_FILENAME = ".recursive-field-root"
CONTROL_PROFILE_PATH = Path("state") / "control_profile.json"
REQUIRED_CAPABILITY = "coordinate"
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_TASK_TYPES = frozenset({"inspect_unit_cell"})
ALLOWED_EXECUTION_POLICIES = frozenset({"allowlisted"})
CLAIM_LEASE_SECONDS = 300


class TaskValidationError(ValueError):
    """Raised when a queued task fails integrity or identity validation."""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _claim_lease_expiry() -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=CLAIM_LEASE_SECONDS)).isoformat()


def _claim_is_stale(claim: dict) -> bool:
    lease_expires_at = claim.get("lease_expires_at")
    if not isinstance(lease_expires_at, str):
        return True
    try:
        expiry = datetime.fromisoformat(lease_expires_at)
    except ValueError:
        return True
    if expiry.tzinfo is None:
        return True
    return expiry <= datetime.now(timezone.utc)


def _read_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Missing file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TaskValidationError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise TaskValidationError(f"Expected a JSON object in {path}")
    return value


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing queue or log file: {path}")
    events: list[dict] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TaskValidationError(f"Invalid JSON at {path}:{lineno}: {exc}") from exc
        if not isinstance(event, dict):
            raise TaskValidationError(f"Expected JSON object at {path}:{lineno}")
        events.append(event)
    return events


def _canonical_sha256(data: dict) -> str:
    encoded = json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        fd = os.open(temp_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _append_jsonl(path: Path, event: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(event, separators=(",", ":")) + "\n").encode("utf-8")
    fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)


def _append_event_once(path: Path, event: dict) -> bool:
    existing = _read_jsonl(path) if path.is_file() else []
    for candidate in existing:
        if (
            candidate.get("event_type") == event.get("event_type")
            and candidate.get("task_id") == event.get("task_id")
        ):
            return False
    _append_jsonl(path, event)
    return True


def _validate_task_id(task_id: object) -> str:
    if not isinstance(task_id, str):
        raise TaskValidationError("Dispatch event task_id must be a UUID string")
    try:
        parsed = uuid.UUID(task_id)
    except ValueError as exc:
        raise TaskValidationError(f"Invalid task_id UUID: {task_id!r}") from exc
    if str(parsed) != task_id:
        raise TaskValidationError(f"task_id must use canonical UUID form: {task_id!r}")
    return task_id


def _load_cursor(
    cursor_path: Path,
    agent_slug: str,
    agent_id: str,
    mesh_slug: str,
    mesh_id: str,
) -> dict:
    if not cursor_path.is_file():
        return {
            "schema_version": "1.0.0",
            "agent_slug": agent_slug,
            "agent_id": agent_id,
            "mesh_slug": mesh_slug,
            "mesh_id": mesh_id,
            "next_event_index": 0,
        }
    cursor = _read_json(cursor_path)
    expected = {
        "agent_slug": agent_slug,
        "agent_id": agent_id,
        "mesh_slug": mesh_slug,
        "mesh_id": mesh_id,
    }
    for key, value in expected.items():
        if cursor.get(key) != value:
            raise TaskValidationError(
                f"Cursor {key} mismatch: expected {value!r}, got {cursor.get(key)!r}"
            )
    index = cursor.get("next_event_index")
    if not isinstance(index, int) or index < 0:
        raise TaskValidationError("Cursor next_event_index must be a non-negative integer")
    return cursor


def _advance_cursor(
    cursor_path: Path,
    cursor: dict,
    next_event_index: int,
    task_id: str | None = None,
    status: str = "idle",
) -> None:
    updated = dict(cursor)
    updated.update({
        "next_event_index": next_event_index,
        "last_task_id": task_id,
        "last_status": status,
        "updated_at": _utc_now_iso(),
    })
    _atomic_write_json(cursor_path, updated)
    cursor.clear()
    cursor.update(updated)


def _create_claim(
    claim_path: Path,
    task_id: str,
    agent_slug: str,
    agent_id: str,
    mesh_slug: str,
    mesh_id: str,
    envelope_sha256: str | None,
) -> tuple[dict, bool]:
    claim_path.parent.mkdir(parents=True, exist_ok=True)
    claim = {
        "schema_version": "1.0.0",
        "claim_id": str(uuid.uuid4()),
        "task_id": task_id,
        "agent_slug": agent_slug,
        "agent_id": agent_id,
        "mesh_slug": mesh_slug,
        "mesh_id": mesh_id,
        "envelope_sha256": envelope_sha256,
        "status": "claimed",
        "claimed_at": _utc_now_iso(),
        "lease_expires_at": _claim_lease_expiry(),
        "attempt": 1,
    }
    try:
        fd = os.open(claim_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        existing = _read_json(claim_path)
        for key, value in {
            "task_id": task_id,
            "agent_slug": agent_slug,
            "agent_id": agent_id,
            "mesh_slug": mesh_slug,
            "mesh_id": mesh_id,
            "envelope_sha256": envelope_sha256,
        }.items():
            if existing.get(key) != value:
                raise TaskValidationError(
                    f"Existing claim {key} mismatch for task {task_id}"
                )
        if existing.get("status") not in {"claimed", "completed", "failed"}:
            raise TaskValidationError(
                f"Existing claim status is invalid for task {task_id}"
            )
        return existing, False

    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(claim, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return claim, True


def _security_allows(root: Path, required_capability: str) -> tuple[bool, str]:
    profile_path = root / CONTROL_PROFILE_PATH
    if not profile_path.is_file():
        return False, "missing"
    profile = _read_json(profile_path)
    active = profile.get("active_security_profile", "missing")
    security_profiles = profile.get("security_profiles", {})
    if not isinstance(security_profiles, dict):
        return False, str(active)
    active_profile = security_profiles.get(active, {})
    if not isinstance(active_profile, dict):
        return False, str(active)
    capabilities = active_profile.get("capabilities", [])
    if not isinstance(capabilities, list) or not all(
        isinstance(capability, str) for capability in capabilities
    ):
        return False, str(active)
    if active == "lockdown":
        return False, active
    return ("all" in capabilities or required_capability in capabilities), active


def _validate_envelope(
    root: Path,
    mesh_dir: Path,
    event: dict,
    task_id: str,
    recipient_identity: dict,
    channel: dict,
    marker: dict,
) -> tuple[dict, Path]:
    expected_path = mesh_dir / "tasks" / f"{task_id}.json"
    advertised = event.get("task_envelope")
    if advertised != str(expected_path.relative_to(root)):
        raise TaskValidationError(
            f"Task envelope path mismatch for {task_id}: {advertised!r}"
        )
    envelope = _read_json(expected_path)

    stored_envelope_hash = envelope.get("envelope_sha256")
    if not isinstance(stored_envelope_hash, str) or not SHA256_PATTERN.fullmatch(
        stored_envelope_hash
    ):
        raise TaskValidationError(f"Task {task_id} has invalid envelope_sha256")
    hash_input = dict(envelope)
    hash_input.pop("envelope_sha256", None)
    actual_envelope_hash = _canonical_sha256(hash_input)
    if stored_envelope_hash != actual_envelope_hash:
        raise TaskValidationError(f"Task {task_id} envelope SHA-256 mismatch")
    if event.get("task_envelope_sha256") != stored_envelope_hash:
        raise TaskValidationError(f"Task {task_id} dispatch/envelope SHA-256 mismatch")

    payload = envelope.get("task_payload")
    if not isinstance(payload, str):
        raise TaskValidationError(f"Task {task_id} payload must be a string")
    payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    if envelope.get("payload_sha256") != payload_hash:
        raise TaskValidationError(f"Task {task_id} payload SHA-256 mismatch")
    if event.get("payload_hash") != payload_hash:
        raise TaskValidationError(f"Task {task_id} dispatch payload SHA-256 mismatch")

    if envelope.get("task_id") != task_id:
        raise TaskValidationError(f"Task {task_id} envelope task_id mismatch")
    if envelope.get("recipient_slug") != recipient_identity.get("slug"):
        raise TaskValidationError(f"Task {task_id} recipient slug mismatch")
    if envelope.get("recipient_id") != recipient_identity.get("agent_id"):
        raise TaskValidationError(f"Task {task_id} recipient identity mismatch")

    sender_slug = envelope.get("sender_slug")
    if not isinstance(sender_slug, str) or not SLUG_PATTERN.fullmatch(sender_slug):
        raise TaskValidationError(f"Task {task_id} sender slug is invalid")
    sender_identity = _read_json(root / "agents" / sender_slug / "identity.json")
    if envelope.get("sender_id") != sender_identity.get("agent_id"):
        raise TaskValidationError(f"Task {task_id} sender identity mismatch")
    if sender_identity.get("slug") != sender_slug:
        raise TaskValidationError(f"Task {task_id} sender manifest slug mismatch")

    endpoint_ids = {
        endpoint.get("slug"): endpoint.get("agent_id")
        for endpoint in channel.get("endpoints", [])
    }
    if endpoint_ids.get(sender_slug) != envelope.get("sender_id"):
        raise TaskValidationError(f"Task {task_id} sender is not an exact mesh endpoint")
    recipient_slug = recipient_identity.get("slug")
    if endpoint_ids.get(recipient_slug) != recipient_identity.get("agent_id"):
        raise TaskValidationError(f"Task {task_id} recipient is not an exact mesh endpoint")

    expected_values = {
        "mesh_slug": channel.get("slug"),
        "mesh_id": channel.get("mesh_id"),
        "field_genesis_uuid": marker.get("genesis_uuid"),
        "required_capability": REQUIRED_CAPABILITY,
    }
    for key, value in expected_values.items():
        if envelope.get(key) != value:
            raise TaskValidationError(
                f"Task {task_id} {key} mismatch: expected {value!r}"
            )

    for key in ("sender_slug", "sender_id", "recipient_slug", "recipient_id", "mesh_slug", "mesh_id"):
        if event.get(key) != envelope.get(key):
            raise TaskValidationError(f"Task {task_id} dispatch {key} mismatch")
    if event.get("mode") != "async":
        raise TaskValidationError(f"Task {task_id} is not an async dispatch")
    if envelope.get("task_type") not in ALLOWED_TASK_TYPES:
        raise TaskValidationError(f"Task {task_id} task_type is not allowlisted")
    if envelope.get("execution_policy") not in ALLOWED_EXECUTION_POLICIES:
        raise TaskValidationError(f"Task {task_id} execution policy is not allowlisted")
    if event.get("task_type") != envelope.get("task_type"):
        raise TaskValidationError(f"Task {task_id} dispatch task_type mismatch")
    if event.get("execution_policy") != envelope.get("execution_policy"):
        raise TaskValidationError(f"Task {task_id} dispatch execution policy mismatch")

    prompt_hash = envelope.get("active_prompt_hash")
    if prompt_hash is not None and (
        not isinstance(prompt_hash, str) or not SHA256_PATTERN.fullmatch(prompt_hash)
    ):
        raise TaskValidationError(f"Task {task_id} active prompt hash is invalid")
    return envelope, expected_path


def _run_adapter(task_type: str, root: Path) -> dict:
    if task_type != "inspect_unit_cell":
        raise TaskValidationError(f"No allowlisted adapter for task type {task_type!r}")
    verified_root, genesis_uuid, agents, meshes, gateways = verify_unit_cell(root)
    return {
        "adapter": "inspect_unit_cell",
        "field_root": str(verified_root),
        "genesis_uuid": genesis_uuid,
        "integrity": "ok",
        "agent_count": len(agents),
        "mesh_count": len(meshes),
        "gateway_count": len(gateways),
    }


def _validate_result_artifact(
    result_path: Path,
    task_id: str,
    envelope: dict,
    claim: dict,
) -> dict:
    artifact = _read_json(result_path)
    for key, expected in {
        "task_id": task_id,
        "sender_slug": envelope.get("sender_slug"),
        "sender_id": envelope.get("sender_id"),
        "recipient_slug": envelope.get("recipient_slug"),
        "recipient_id": envelope.get("recipient_id"),
        "mesh_slug": envelope.get("mesh_slug"),
        "mesh_id": envelope.get("mesh_id"),
        "task_type": envelope.get("task_type"),
        "execution_policy": envelope.get("execution_policy"),
    }.items():
        if artifact.get(key) != expected:
            raise TaskValidationError(f"Result artifact {key} mismatch for task {task_id}")
    if artifact.get("status") not in {"completed", "failed"}:
        raise TaskValidationError(f"Result artifact status is invalid for task {task_id}")
    result_payload = artifact.get("result")
    if not isinstance(result_payload, dict):
        raise TaskValidationError(f"Result payload is invalid for task {task_id}")
    if artifact.get("result_sha256") != _canonical_sha256(result_payload):
        raise TaskValidationError(f"Result payload SHA-256 mismatch for task {task_id}")
    artifact_sha256 = _file_sha256(result_path)
    claimed_artifact_hash = claim.get("result_artifact_sha256")
    if claimed_artifact_hash is not None and claimed_artifact_hash != artifact_sha256:
        raise TaskValidationError(f"Claim/result artifact SHA-256 mismatch for task {task_id}")
    artifact["artifact_sha256"] = artifact_sha256
    return artifact


def _write_result_artifact(
    result_path: Path,
    task_id: str,
    envelope: dict,
    status: str,
    result_payload: dict,
) -> dict:
    timestamp = _utc_now_iso()
    result_sha256 = _canonical_sha256(result_payload)
    artifact = {
        "schema_version": "1.0.0",
        "task_id": task_id,
        "status": status,
        "sender_slug": envelope.get("sender_slug"),
        "sender_id": envelope.get("sender_id"),
        "recipient_slug": envelope.get("recipient_slug"),
        "recipient_id": envelope.get("recipient_id"),
        "mesh_slug": envelope.get("mesh_slug"),
        "mesh_id": envelope.get("mesh_id"),
        "task_type": envelope.get("task_type"),
        "execution_policy": envelope.get("execution_policy"),
        "completed_at": timestamp,
        "result": result_payload,
        "result_sha256": result_sha256,
    }
    _atomic_write_json(result_path, artifact)
    artifact["artifact_sha256"] = _file_sha256(result_path)
    return artifact


def _record_terminal(
    root: Path,
    mesh_dir: Path,
    recipient_dir: Path,
    task_id: str,
    envelope: dict,
    status: str,
    result_payload: dict,
    claim_path: Path,
    claim: dict,
    existing_artifact: dict | None = None,
) -> dict:
    result_path = mesh_dir / "results" / f"{task_id}.json"
    if existing_artifact is None:
        artifact = _write_result_artifact(
            result_path, task_id, envelope, status, result_payload
        )
    else:
        if (
            existing_artifact.get("status") != status
            or existing_artifact.get("result") != result_payload
        ):
            raise TaskValidationError(
                f"Existing result content mismatch during recovery for task {task_id}"
            )
        # Recovery may repair missing events, claim state, and the cursor, but
        # the already-validated result artifact is immutable.
        artifact = existing_artifact
    event_type = "task_completed" if status == "completed" else "task_failed"
    recipient_event = {
        "event_type": event_type,
        "task_id": task_id,
        "timestamp": artifact["completed_at"],
        "agent_slug": envelope.get("recipient_slug"),
        "agent_id": envelope.get("recipient_id"),
        "author_slug": envelope.get("recipient_slug"),
        "author_id": envelope.get("recipient_id"),
        "sender_slug": envelope.get("sender_slug"),
        "sender_id": envelope.get("sender_id"),
        "mesh_slug": envelope.get("mesh_slug"),
        "mesh_id": envelope.get("mesh_id"),
        "task_type": envelope.get("task_type"),
        "status": status,
        "result_sha256": artifact["result_sha256"],
        "result_artifact_sha256": artifact["artifact_sha256"],
    }
    if status != "completed":
        recipient_event["error"] = result_payload.get("error")
    _append_event_once(recipient_dir / "observations" / "log.jsonl", recipient_event)

    queue_event = {
        "event_type": "task_result",
        "task_id": task_id,
        "timestamp": artifact["completed_at"],
        "sender_slug": envelope.get("sender_slug"),
        "sender_id": envelope.get("sender_id"),
        "recipient_slug": envelope.get("recipient_slug"),
        "recipient_id": envelope.get("recipient_id"),
        "author_slug": envelope.get("recipient_slug"),
        "author_id": envelope.get("recipient_id"),
        "mesh_slug": envelope.get("mesh_slug"),
        "mesh_id": envelope.get("mesh_id"),
        "status": status,
        "task_type": envelope.get("task_type"),
        "result_path": str(result_path.relative_to(root)),
        "result_sha256": artifact["result_sha256"],
        "result_artifact_sha256": artifact["artifact_sha256"],
    }
    _append_event_once(mesh_dir / "queue.jsonl", queue_event)

    updated_claim = dict(claim)
    updated_claim.update({
        "status": status,
        "finished_at": artifact["completed_at"],
        "result_path": str(result_path.relative_to(root)),
        "result_sha256": artifact["result_sha256"],
        "result_artifact_sha256": artifact["artifact_sha256"],
    })
    _atomic_write_json(claim_path, updated_claim)
    return {
        "result_path": str(result_path),
        "result_sha256": artifact["result_sha256"],
        "result_artifact_sha256": artifact["artifact_sha256"],
    }


def _persist_after_task(root: Path, agent_slug: str) -> dict:
    return persist_state(agent_slug=agent_slug, start=root)


def consume_queue(
    agent_slug: str,
    mesh_slug: str,
    once: bool = False,
    start: str | os.PathLike[str] | None = None,
) -> dict:
    """Consume at most one eligible async dispatch for an agent."""
    if not once:
        raise ValueError("Only bounded --once consumption is supported")
    for slug, label in ((agent_slug, "agent"), (mesh_slug, "mesh")):
        if not SLUG_PATTERN.fullmatch(slug):
            raise ValueError(f"Invalid {label} slug: {slug!r}")

    root = find_root(start)
    if root is None:
        raise RuntimeError("Could not locate field root")
    marker = _read_json(root / MARKER_FILENAME)
    recipient_dir = root / "agents" / agent_slug
    recipient_identity = _read_json(recipient_dir / "identity.json")
    if recipient_identity.get("slug") != agent_slug:
        raise TaskValidationError("Recipient identity manifest slug mismatch")

    mesh_dir = root / "mesh" / mesh_slug
    channel = _read_json(mesh_dir / "channel.json")
    if channel.get("slug") != mesh_slug:
        raise TaskValidationError("Mesh channel slug mismatch")
    endpoint_ids = {
        endpoint.get("slug"): endpoint.get("agent_id")
        for endpoint in channel.get("endpoints", [])
    }
    if endpoint_ids.get(agent_slug) != recipient_identity.get("agent_id"):
        raise TaskValidationError(f"Agent {agent_slug!r} is not an exact endpoint of {mesh_slug!r}")
    if channel.get("field_genesis_uuid") != marker.get("genesis_uuid"):
        raise TaskValidationError("Mesh genesis identity mismatch")

    queue_path = mesh_dir / "queue.jsonl"
    events = _read_jsonl(queue_path)
    cursor_path = recipient_dir / "worker_state" / f"{mesh_slug}.cursor.json"
    cursor = _load_cursor(
        cursor_path,
        agent_slug,
        recipient_identity.get("agent_id", ""),
        mesh_slug,
        channel.get("mesh_id", ""),
    )
    next_index = cursor["next_event_index"]
    if next_index > len(events):
        raise TaskValidationError(
            f"Cursor points beyond queue length ({next_index} > {len(events)})"
        )

    for index in range(next_index, len(events)):
        event = events[index]
        is_candidate = (
            event.get("event_type") == "task_dispatched"
            and event.get("mode") == "async"
            and event.get("recipient_slug") == agent_slug
        )
        if not is_candidate:
            _advance_cursor(cursor_path, cursor, index + 1)
            continue

        task_id = _validate_task_id(event.get("task_id"))
        claim_path = (
            recipient_dir / "worker_state" / "claims" / f"{task_id}.json"
        )
        result_path = mesh_dir / "results" / f"{task_id}.json"

        try:
            envelope, _ = _validate_envelope(
                root,
                mesh_dir,
                event,
                task_id,
                recipient_identity,
                channel,
                marker,
            )
        except (TaskValidationError, FileNotFoundError) as exc:
            rejection_envelope = {
                "task_id": task_id,
                "sender_slug": event.get("sender_slug"),
                "sender_id": event.get("sender_id"),
                "recipient_slug": agent_slug,
                "recipient_id": recipient_identity.get("agent_id"),
                "mesh_slug": mesh_slug,
                "mesh_id": channel.get("mesh_id"),
                "task_type": event.get("task_type"),
                "execution_policy": event.get("execution_policy"),
            }
            claim, created = _create_claim(
                claim_path,
                task_id,
                agent_slug,
                recipient_identity.get("agent_id", ""),
                mesh_slug,
                channel.get("mesh_id", ""),
                event.get("task_envelope_sha256"),
            )
            if not created and claim.get("status") in {"completed", "failed"}:
                _advance_cursor(cursor_path, cursor, index + 1, task_id, "replayed")
                return {"status": "replayed", "task_id": task_id}
            terminal = _record_terminal(
                root,
                mesh_dir,
                recipient_dir,
                task_id,
                rejection_envelope,
                "failed",
                {"failure_kind": "validation", "error": str(exc)},
                claim_path,
                claim,
            )
            _advance_cursor(cursor_path, cursor, index + 1, task_id, "failed")
            persisted = _persist_after_task(root, agent_slug)
            return {
                "status": "failed",
                "failure_kind": "validation",
                "error": str(exc),
                "task_id": task_id,
                "persistence": persisted,
                **terminal,
            }

        allowed, active_security = _security_allows(
            root, envelope["required_capability"]
        )
        if not allowed:
            return {
                "status": "blocked",
                "task_id": task_id,
                "security_profile": active_security,
                "required_capability": envelope["required_capability"],
                "cursor_advanced": False,
            }

        claim, created = _create_claim(
            claim_path,
            task_id,
            agent_slug,
            recipient_identity.get("agent_id", ""),
            mesh_slug,
            channel.get("mesh_id", ""),
            envelope.get("envelope_sha256"),
        )
        if result_path.is_file():
            existing_result = _validate_result_artifact(
                result_path, task_id, envelope, claim
            )
            terminal = _record_terminal(
                root,
                mesh_dir,
                recipient_dir,
                task_id,
                envelope,
                existing_result["status"],
                existing_result["result"],
                claim_path,
                claim,
                existing_artifact=existing_result,
            )
            _advance_cursor(
                cursor_path, cursor, index + 1, task_id, "replayed"
            )
            persisted = _persist_after_task(root, agent_slug)
            return {
                "status": "replayed",
                "task_id": task_id,
                "persistence": persisted,
                **terminal,
            }
        if not created:
            if claim.get("status") in {"completed", "failed"}:
                raise TaskValidationError(
                    f"Terminal claim has no result artifact for task {task_id}"
                )
            if not _claim_is_stale(claim):
                return {
                    "status": "claimed",
                    "task_id": task_id,
                    "cursor_advanced": False,
                }
            # Expired claims are recoverable because the only adapter is
            # read-only, lifecycle appends are deduplicated, and result writes
            # are atomic. Refresh the durable lease before resuming.
            claim = dict(claim)
            claim.update({
                "claimed_at": _utc_now_iso(),
                "lease_expires_at": _claim_lease_expiry(),
                "attempt": int(claim.get("attempt", 1)) + 1,
                "reclaimed": True,
            })
            _atomic_write_json(claim_path, claim)

        started_at = _utc_now_iso()
        _append_event_once(
            recipient_dir / "observations" / "log.jsonl",
            {
                "event_type": "task_started",
                "task_id": task_id,
                "timestamp": started_at,
                "agent_slug": agent_slug,
                "agent_id": recipient_identity.get("agent_id"),
                "author_slug": agent_slug,
                "author_id": recipient_identity.get("agent_id"),
                "sender_slug": envelope.get("sender_slug"),
                "sender_id": envelope.get("sender_id"),
                "mesh_slug": mesh_slug,
                "mesh_id": channel.get("mesh_id"),
                "task_type": envelope.get("task_type"),
                "security_profile": active_security,
            },
        )

        try:
            adapter_result = _run_adapter(envelope["task_type"], root)
        except Exception as exc:  # only adapter errors change semantic task status
            final_status = "failed"
            failure_kind = "execution"
            error = str(exc)
            result_payload = {"failure_kind": failure_kind, "error": error}
        else:
            final_status = "completed"
            failure_kind = None
            error = None
            result_payload = adapter_result

        # Terminal-write failures remain retryable claimed work; they do not
        # rewrite a successful adapter execution as a semantic task failure.
        terminal = _record_terminal(
            root,
            mesh_dir,
            recipient_dir,
            task_id,
            envelope,
            final_status,
            result_payload,
            claim_path,
            claim,
        )

        _advance_cursor(cursor_path, cursor, index + 1, task_id, final_status)
        persisted = _persist_after_task(root, agent_slug)
        result = {
            "status": final_status,
            "task_id": task_id,
            "security_profile": active_security,
            "persistence": persisted,
            **terminal,
        }
        if failure_kind:
            result.update({"failure_kind": failure_kind, "error": error})
        return result

    return {
        "status": "idle",
        "agent_slug": agent_slug,
        "mesh_slug": mesh_slug,
        "next_event_index": cursor["next_event_index"],
    }


def _print_result(result: dict) -> None:
    print(f"Status: {result['status']}")
    if result.get("task_id"):
        print(f"Task ID: {result['task_id']}")
    if result.get("result_path"):
        print(f"Result: {result['result_path']}")
        print(f"Result SHA-256: {result['result_sha256']}")
    if result.get("error"):
        print(f"Error: {result['error']}")
    if result.get("status") == "blocked":
        print(f"Security: {result['security_profile']}")
        print(f"Required Capability: {result['required_capability']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Consume one allowlisted asynchronous mesh task"
    )
    parser.add_argument("agent_slug", help="Recipient worker agent slug")
    parser.add_argument("mesh_slug", help="Mesh queue slug")
    parser.add_argument(
        "--once", action="store_true", help="Process at most one eligible task"
    )
    args = parser.parse_args(argv)
    if not args.once:
        parser.error("--once is required; unbounded worker loops are not implemented")

    try:
        result = consume_queue(args.agent_slug, args.mesh_slug, once=True)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except (ValueError, TaskValidationError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 3
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    _print_result(result)
    if result["status"] == "blocked":
        return 4
    if result["status"] == "failed":
        return 3 if result.get("failure_kind") == "validation" else 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
