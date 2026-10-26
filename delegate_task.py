#!/usr/bin/env python3
"""Task Delegation Primitive for the Recursive Field.

Dispatches a unit of work from a sender agent to a recipient agent
across a connected mesh, enforcing security-gated capability dispatch
and bi-directional observational traceability.

Usage:
    python3 delegate_task.py <sender_slug> <recipient_slug> <mesh_slug> \
        "<task_payload>" [--payload-file <path>]

Exit codes:
    0  task delegated and result recorded successfully
    1  field root not found or runtime error
    2  invalid arguments or agent/mesh not found
    3  mesh does not connect sender and recipient
    4  security violation — capability not permitted under active profile
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Ensure the script's own directory is importable when invoked from
# a different working directory.
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from find_root import find_root  # noqa: E402

MARKER_FILENAME = ".recursive-field-root"
CONTROL_PROFILE_PATH = Path("state") / "control_profile.json"
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# Security capability requirements for delegation.
# lockdown caps capabilities to ['observe'] only — delegation requires 'coordinate'.
REQUIRED_CAPABILITY = "coordinate"
VALID_MODES = ("acknowledge", "async")
VALID_TASK_TYPES = ("inspect_unit_cell",)
VALID_EXECUTION_POLICIES = ("allowlisted",)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    events: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            events.append(json.loads(line))
    return events


def _append_event(log_path: Path, event: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(event, separators=(",", ":")) + "\n").encode("utf-8")
    fd = os.open(log_path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)


def _canonical_sha256(data: dict) -> str:
    encoded = json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _atomic_write_json(path: Path, data: dict) -> None:
    """Atomically replace a JSON artifact using a same-directory temp file."""
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


def _active_prompt_hash(agent_dir: Path) -> str | None:
    """Resolve the recipient's latest known active prompt hash, if present."""
    events = _read_jsonl(agent_dir / "observations" / "log.jsonl")
    for event in reversed(events):
        prompt_hash = event.get("prompt_hash") or event.get("content_hash")
        if isinstance(prompt_hash, str) and re.fullmatch(r"[0-9a-f]{64}", prompt_hash):
            return prompt_hash

    assembled_path = agent_dir / "assembled_system_prompt.md"
    if assembled_path.is_file():
        return hashlib.sha256(assembled_path.read_bytes()).hexdigest()
    return None


def _short_uuid(uuid_str: str, length: int = 8) -> str:
    return uuid_str[:length] + "..." if len(uuid_str) > length else uuid_str


def _read_control_profile(root: Path) -> dict:
    control_path = root / CONTROL_PROFILE_PATH
    if control_path.is_file():
        return _read_json(control_path)
    return {
        "active_security_profile": "open",
        "security_profiles": {},
        "prompt_includes": {},
    }


def _get_capabilities(control_profile: dict, security_level: str) -> list[str]:
    security_profiles = control_profile.get("security_profiles", {})
    if not isinstance(security_profiles, dict):
        return []
    active_sp = security_profiles.get(security_level, {})
    if not isinstance(active_sp, dict):
        return []
    capabilities = active_sp.get("capabilities", [])
    if not isinstance(capabilities, list) or not all(
        isinstance(capability, str) for capability in capabilities
    ):
        return []
    return capabilities


def _check_capability_allowed(
    control_profile: dict, required_capability: str
) -> tuple[bool, str]:
    """Check if the required capability is allowed under the active profile.

    Returns (allowed, active_profile_name).
    """
    active = control_profile.get("active_security_profile", "open")
    capabilities = _get_capabilities(control_profile, active)

    # 'all' capability means everything is allowed.
    if "all" in capabilities:
        return True, active

    if required_capability not in capabilities:
        return False, active

    return True, active


def _verify_mesh_connects(
    mesh_channel: dict, sender_slug: str, recipient_slug: str
) -> bool:
    """Verify that the mesh channel connects both sender and recipient."""
    endpoints = mesh_channel.get("endpoints", [])
    endpoint_slugs = {ep.get("slug", "") for ep in endpoints}
    return sender_slug in endpoint_slugs and recipient_slug in endpoint_slugs


def _validate_identity_graph(
    marker: dict,
    sender_identity: dict,
    recipient_identity: dict,
    mesh_channel: dict,
    sender_slug: str,
    recipient_slug: str,
    mesh_slug: str,
) -> None:
    """Fail closed before either delegation mode writes observable state."""
    genesis_uuid = marker.get("genesis_uuid")
    coordinates = (
        ("sender", sender_identity, "agent_id", sender_slug),
        ("recipient", recipient_identity, "agent_id", recipient_slug),
        ("mesh", mesh_channel, "mesh_id", mesh_slug),
    )
    for label, manifest, id_key, expected_slug in coordinates:
        if manifest.get("slug") != expected_slug:
            raise ValueError(f"{label.capitalize()} manifest slug mismatch")
        identifier = manifest.get(id_key)
        try:
            if not isinstance(identifier, str) or str(uuid.UUID(identifier)) != identifier:
                raise ValueError
        except ValueError as exc:
            raise ValueError(f"{label.capitalize()} {id_key} is not a canonical UUID") from exc
        if manifest.get("field_genesis_uuid") != genesis_uuid:
            raise ValueError(f"{label.capitalize()} genesis identity mismatch")

    endpoint_ids = {
        endpoint.get("slug"): endpoint.get("agent_id")
        for endpoint in mesh_channel.get("endpoints", [])
        if isinstance(endpoint, dict)
    }
    if endpoint_ids.get(sender_slug) != sender_identity.get("agent_id"):
        raise ValueError("Sender identity does not match its mesh endpoint")
    if endpoint_ids.get(recipient_slug) != recipient_identity.get("agent_id"):
        raise ValueError("Recipient identity does not match its mesh endpoint")


def delegate_task(
    sender_slug: str,
    recipient_slug: str,
    mesh_slug: str,
    task_payload: str = "",
    payload_file: str | None = None,
    start: str | os.PathLike[str] | None = None,
    mode: str = "acknowledge",
    task_type: str = "inspect_unit_cell",
    execution_policy: str = "allowlisted",
) -> dict:
    """Delegate a task from sender to recipient across a mesh.

    Args:
        sender_slug: Delegating agent slug.
        recipient_slug: Receiving agent slug.
        mesh_slug: Mesh slug connecting both agents.
        task_payload: Task description or payload string.
        payload_file: Optional path to a file containing the payload.
        start: Directory to begin root discovery from.
        mode: ``acknowledge`` preserves legacy simulated completion;
            ``async`` leaves execution to a recipient worker.
        task_type: Async adapter coordinate. Only inspect_unit_cell is supported.
        execution_policy: Async execution policy. Only allowlisted is supported.

    Returns:
        A dict with delegation metadata.

    Raises:
        RuntimeError: If field root cannot be discovered.
        FileNotFoundError: If agent or mesh not found.
        ValueError: If mesh does not connect sender and recipient, or
            security violation.
    """
    root = find_root(start)
    if root is None:
        raise RuntimeError(
            "Could not locate field root: no .recursive-field-root marker "
            "found in the current directory or any ancestor."
        )

    for slug, label in [
        (sender_slug, "sender"),
        (recipient_slug, "recipient"),
        (mesh_slug, "mesh"),
    ]:
        if not SLUG_PATTERN.match(slug):
            raise ValueError(
                f"Invalid {label} slug {slug!r}: must be lowercase "
                "alphanumeric with hyphens."
            )

    if mode not in VALID_MODES:
        raise ValueError(f"Invalid mode {mode!r}: must be one of {list(VALID_MODES)}")
    if task_type not in VALID_TASK_TYPES:
        raise ValueError(
            f"Invalid task type {task_type!r}: must be one of {list(VALID_TASK_TYPES)}"
        )
    if execution_policy not in VALID_EXECUTION_POLICIES:
        raise ValueError(
            "Invalid execution policy "
            f"{execution_policy!r}: must be one of {list(VALID_EXECUTION_POLICIES)}"
        )

    # Load payload from file if specified.
    if payload_file:
        payload_path = Path(payload_file)
        if not payload_path.is_absolute():
            payload_path = root / payload_path
        if not payload_path.is_file():
            raise FileNotFoundError(f"Payload file not found: {payload_path}")
        task_payload = payload_path.read_text(encoding="utf-8").strip()

    # Verify sender existence.
    sender_dir = root / "agents" / sender_slug
    sender_identity_path = sender_dir / "identity.json"
    if not sender_identity_path.is_file():
        raise FileNotFoundError(
            f"Sender agent not found: {sender_slug!r} "
            f"(expected {sender_identity_path})"
        )
    sender_identity = _read_json(sender_identity_path)
    sender_id = sender_identity.get("agent_id", "")

    # Verify recipient existence.
    recipient_dir = root / "agents" / recipient_slug
    recipient_identity_path = recipient_dir / "identity.json"
    if not recipient_identity_path.is_file():
        raise FileNotFoundError(
            f"Recipient agent not found: {recipient_slug!r} "
            f"(expected {recipient_identity_path})"
        )
    recipient_identity = _read_json(recipient_identity_path)
    recipient_id = recipient_identity.get("agent_id", "")

    # Verify mesh existence and connectivity.
    mesh_dir = root / "mesh" / mesh_slug
    mesh_channel_path = mesh_dir / "channel.json"
    if not mesh_channel_path.is_file():
        raise FileNotFoundError(
            f"Mesh not found: {mesh_slug!r} "
            f"(expected {mesh_channel_path})"
        )
    mesh_channel = _read_json(mesh_channel_path)
    mesh_id = mesh_channel.get("mesh_id", "")

    if not _verify_mesh_connects(mesh_channel, sender_slug, recipient_slug):
        raise ValueError(
            f"Mesh {mesh_slug!r} does not connect sender {sender_slug!r} "
            f"and recipient {recipient_slug!r}."
        )

    marker = _read_json(root / MARKER_FILENAME)
    _validate_identity_graph(
        marker,
        sender_identity,
        recipient_identity,
        mesh_channel,
        sender_slug,
        recipient_slug,
        mesh_slug,
    )

    # Security & capability gating.
    control_profile = _read_control_profile(root)
    allowed, active_security = _check_capability_allowed(
        control_profile, REQUIRED_CAPABILITY
    )

    if not allowed:
        raise PermissionError(
            f"Security violation: sender {sender_slug!r} is under "
            f"{active_security!r} profile which does not include the "
            f"{REQUIRED_CAPABILITY!r} capability required for delegation."
        )

    # Generate task ID and timestamp.
    task_id = str(uuid.uuid4())
    timestamp = _utc_now_iso()

    # Compute payload hash for audit.
    payload_hash = hashlib.sha256(
        task_payload.encode("utf-8")
    ).hexdigest()

    # --- Message Queue & Event Logging ---

    queue_path = mesh_dir / "queue.jsonl"
    sender_log_path = sender_dir / "observations" / "log.jsonl"
    recipient_log_path = recipient_dir / "observations" / "log.jsonl"

    task_envelope: dict | None = None
    task_path: Path | None = None
    if mode == "async":
        marker = _read_json(root / MARKER_FILENAME)
        task_envelope = {
            "schema_version": "1.0.0",
            "task_id": task_id,
            "task_payload": task_payload,
            "payload_sha256": payload_hash,
            "sender_slug": sender_slug,
            "sender_id": sender_id,
            "recipient_slug": recipient_slug,
            "recipient_id": recipient_id,
            "mesh_slug": mesh_slug,
            "mesh_id": mesh_id,
            "field_genesis_uuid": marker.get("genesis_uuid", ""),
            "required_capability": REQUIRED_CAPABILITY,
            "active_prompt_hash": _active_prompt_hash(recipient_dir),
            "dispatched_at": timestamp,
            "task_type": task_type,
            "execution_policy": execution_policy,
        }
        task_envelope["envelope_sha256"] = _canonical_sha256(task_envelope)
        task_path = mesh_dir / "tasks" / f"{task_id}.json"
        _atomic_write_json(task_path, task_envelope)

    # 1. task_dispatched → mesh queue
    dispatch_event = {
        "event_type": "task_dispatched",
        "task_id": task_id,
        "timestamp": timestamp,
        "sender_slug": sender_slug,
        "sender_id": sender_id,
        "recipient_slug": recipient_slug,
        "recipient_id": recipient_id,
        "mesh_slug": mesh_slug,
        "mesh_id": mesh_id,
        "payload_hash": payload_hash,
        "payload_length": len(task_payload),
        "security_profile": active_security,
    }
    if mode == "async" and task_envelope is not None and task_path is not None:
        dispatch_event.update({
            "mode": mode,
            "task_type": task_type,
            "execution_policy": execution_policy,
            "required_capability": REQUIRED_CAPABILITY,
            "task_envelope": str(task_path.relative_to(root)),
            "task_envelope_sha256": task_envelope["envelope_sha256"],
        })
    _append_event(queue_path, dispatch_event)

    # 2. task_delegated → sender observation log
    delegated_event = {
        "event_type": "task_delegated",
        "task_id": task_id,
        "timestamp": timestamp,
        "agent_slug": sender_slug,
        "agent_id": sender_id,
        "recipient_slug": recipient_slug,
        "recipient_id": recipient_id,
        "mesh_slug": mesh_slug,
        "mesh_id": mesh_id,
        "payload_hash": payload_hash,
        "payload_length": len(task_payload),
        "security_profile": active_security,
    }
    if mode == "async":
        delegated_event.update({
            "mode": mode,
            "task_type": task_type,
            "execution_policy": execution_policy,
            "required_capability": REQUIRED_CAPABILITY,
        })
    _append_event(sender_log_path, delegated_event)

    # 3. task_received → recipient observation log
    received_event = {
        "event_type": "task_received",
        "task_id": task_id,
        "timestamp": timestamp,
        "agent_slug": recipient_slug,
        "agent_id": recipient_id,
        "sender_slug": sender_slug,
        "sender_id": sender_id,
        "mesh_slug": mesh_slug,
        "mesh_id": mesh_id,
        "payload_hash": payload_hash,
        "payload_length": len(task_payload),
        "security_profile": active_security,
    }
    if mode == "async":
        received_event.update({
            "mode": mode,
            "task_type": task_type,
            "execution_policy": execution_policy,
            "required_capability": REQUIRED_CAPABILITY,
        })
    _append_event(recipient_log_path, received_event)

    if mode == "async":
        return {
            "task_id": task_id,
            "sender_slug": sender_slug,
            "sender_id": sender_id,
            "recipient_slug": recipient_slug,
            "recipient_id": recipient_id,
            "mesh_slug": mesh_slug,
            "mesh_id": mesh_id,
            "payload_hash": payload_hash,
            "payload_length": len(task_payload),
            "security_profile": active_security,
            "required_capability": REQUIRED_CAPABILITY,
            "active_prompt_hash": task_envelope["active_prompt_hash"],
            "task_type": task_type,
            "execution_policy": execution_policy,
            "task_path": str(task_path),
            "task_envelope_sha256": task_envelope["envelope_sha256"],
            "dispatched_at": timestamp,
            "completed_at": None,
            "mode": mode,
            "status": "queued",
        }

    # 4. task_result → mesh queue (simulated completion)
    result_timestamp = _utc_now_iso()
    result_event = {
        "event_type": "task_result",
        "task_id": task_id,
        "timestamp": result_timestamp,
        "sender_slug": sender_slug,
        "sender_id": sender_id,
        "recipient_slug": recipient_slug,
        "recipient_id": recipient_id,
        "mesh_slug": mesh_slug,
        "mesh_id": mesh_id,
        "status": "completed",
        "result_summary": f"Task {task_id} dispatched and acknowledged by {recipient_slug}.",
        "security_profile": active_security,
    }
    _append_event(queue_path, result_event)

    # 5. task_result → sender observation log (result return)
    sender_result_event = {
        "event_type": "task_result",
        "task_id": task_id,
        "timestamp": result_timestamp,
        "agent_slug": sender_slug,
        "agent_id": sender_id,
        "recipient_slug": recipient_slug,
        "recipient_id": recipient_id,
        "mesh_slug": mesh_slug,
        "mesh_id": mesh_id,
        "status": "completed",
        "result_summary": f"Task {task_id} dispatched and acknowledged by {recipient_slug}.",
        "security_profile": active_security,
    }
    _append_event(sender_log_path, sender_result_event)

    return {
        "task_id": task_id,
        "sender_slug": sender_slug,
        "sender_id": sender_id,
        "recipient_slug": recipient_slug,
        "recipient_id": recipient_id,
        "mesh_slug": mesh_slug,
        "mesh_id": mesh_id,
        "payload_hash": payload_hash,
        "payload_length": len(task_payload),
        "security_profile": active_security,
        "dispatched_at": timestamp,
        "completed_at": result_timestamp,
        "status": "completed",
    }


def _print_result(result: dict) -> None:
    print(f"Task ID: {_short_uuid(result['task_id'], 12)}")
    print(f"Sender: {result['sender_slug']} [{_short_uuid(result['sender_id'])}]")
    print(f"Recipient: {result['recipient_slug']} [{_short_uuid(result['recipient_id'])}]")
    print(f"Mesh: {result['mesh_slug']} [{_short_uuid(result['mesh_id'])}]")
    print(f"Security: {result['security_profile']}")
    print(f"Payload Hash: {result['payload_hash'][:16]}...")
    print(f"Payload Length: {result['payload_length']} chars")
    print(f"Status: {result['status']}")
    print(f"Dispatched: {result['dispatched_at']}")
    if result.get("mode") == "async":
        print(f"Task Type: {result['task_type']}")
        print(f"Execution Policy: {result['execution_policy']}")
        print(f"Task Envelope: {result['task_path']}")
        print("Completed: pending worker execution")
    else:
        print(f"Completed: {result['completed_at']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Task Delegation Primitive for the Recursive Field"
    )
    parser.add_argument("sender_slug", type=str, help="Delegating agent slug")
    parser.add_argument("recipient_slug", type=str, help="Receiving agent slug")
    parser.add_argument("mesh_slug", type=str, help="Mesh slug connecting both agents")
    parser.add_argument(
        "task_payload", type=str, nargs="?", default="",
        help="Task description or payload string",
    )
    parser.add_argument(
        "--payload-file", type=str, default=None,
        help="Path to a file containing the task payload",
    )
    parser.add_argument(
        "--mode", choices=VALID_MODES, default="acknowledge",
        help="acknowledge (legacy immediate result) or async (durable worker queue)",
    )
    parser.add_argument(
        "--task-type", choices=VALID_TASK_TYPES, default="inspect_unit_cell",
        help="Allowlisted task adapter coordinate for async execution",
    )
    parser.add_argument(
        "--execution-policy", choices=VALID_EXECUTION_POLICIES,
        default="allowlisted", help="Async execution policy",
    )
    args = parser.parse_args(argv)

    try:
        result = delegate_task(
            args.sender_slug,
            args.recipient_slug,
            args.mesh_slug,
            args.task_payload,
            args.payload_file,
            mode=args.mode,
            task_type=args.task_type,
            execution_policy=args.execution_policy,
        )
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 3
    except PermissionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 4
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    _print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
