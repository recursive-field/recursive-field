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
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


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
    active_sp = security_profiles.get(security_level, {})
    return active_sp.get("capabilities", [])


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


def delegate_task(
    sender_slug: str,
    recipient_slug: str,
    mesh_slug: str,
    task_payload: str = "",
    payload_file: str | None = None,
    start: str | os.PathLike[str] | None = None,
) -> dict:
    """Delegate a task from sender to recipient across a mesh.

    Args:
        sender_slug: Delegating agent slug.
        recipient_slug: Receiving agent slug.
        mesh_slug: Mesh slug connecting both agents.
        task_payload: Task description or payload string.
        payload_file: Optional path to a file containing the payload.
        start: Directory to begin root discovery from.

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
    import hashlib
    payload_hash = hashlib.sha256(
        task_payload.encode("utf-8")
    ).hexdigest()

    # --- Message Queue & Event Logging ---

    queue_path = mesh_dir / "queue.jsonl"
    sender_log_path = sender_dir / "observations" / "log.jsonl"
    recipient_log_path = recipient_dir / "observations" / "log.jsonl"

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
    _append_event(recipient_log_path, received_event)

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
    args = parser.parse_args(argv)

    try:
        result = delegate_task(
            args.sender_slug,
            args.recipient_slug,
            args.mesh_slug,
            args.task_payload,
            args.payload_file,
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
