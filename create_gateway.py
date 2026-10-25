#!/usr/bin/env python3
"""Interface primitive for the Recursive Field.

Binds an external or internal translation interface to an individual agent
or a connected mesh topology by creating a Gateway Manifest
(``manifest.json``), initializing an append-only interface log
(``events.jsonl``), and appending a ``gateway_attached`` event to the
target's observation log (agent) or event queue (mesh).

Usage:
    python3 create_gateway.py <gateway_slug> <target_type> <target_slug> [gateway_type]

    <target_type>  MUST be either 'agent' or 'mesh'.
    <target_slug>  Slug of an existing agent or mesh.
    [gateway_type] Optional interface type (default: 'cli').

Exit codes:
    0  gateway created successfully
    1  field root not found
    2  invalid slug, target_type, or missing arguments
    3  gateway slug already exists
    4  target not found
"""

from __future__ import annotations

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
SCHEMA_VERSION = "1.0.0"
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VALID_TARGET_TYPES = {"agent", "mesh"}


def _utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string with timezone offset."""
    return datetime.now(timezone.utc).isoformat()


def validate_slug(slug: str) -> bool:
    """Return True if *slug* matches the lowercase alphanumeric + hyphen pattern."""
    return bool(SLUG_PATTERN.match(slug))


def _resolve_target(
    root: Path, target_type: str, target_slug: str
) -> tuple[str, Path]:
    """Verify target existence and return (target_id, target_dir).

    Raises:
        FileNotFoundError: If the target does not exist.
    """
    if target_type == "agent":
        identity_path = root / "agents" / target_slug / "identity.json"
        if not identity_path.is_file():
            raise FileNotFoundError(
                f"Agent target not found: {target_slug} "
                f"(expected {identity_path})"
            )
        identity = json.loads(identity_path.read_text(encoding="utf-8"))
        return identity["agent_id"], root / "agents" / target_slug

    # target_type == "mesh"
    channel_path = root / "mesh" / target_slug / "channel.json"
    if not channel_path.is_file():
        raise FileNotFoundError(
            f"Mesh target not found: {target_slug} "
            f"(expected {channel_path})"
        )
    channel = json.loads(channel_path.read_text(encoding="utf-8"))
    return channel["mesh_id"], root / "mesh" / target_slug


def _append_gateway_attached(
    target_dir: Path, target_type: str, gateway_id: str, gateway_slug: str
) -> None:
    """Append a gateway_attached event to the target's log or queue."""
    event = {
        "event_type": "gateway_attached",
        "timestamp": _utc_now_iso(),
        "gateway_id": gateway_id,
        "gateway_slug": gateway_slug,
        "target_type": target_type,
    }

    if target_type == "agent":
        log_path = target_dir / "observations" / "log.jsonl"
    else:  # mesh
        log_path = target_dir / "queue.jsonl"

    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def create_gateway(
    gateway_slug: str,
    target_type: str,
    target_slug: str,
    gateway_type: str = "cli",
    start: str | os.PathLike[str] | None = None,
) -> Path:
    """Provision a new gateway binding an interface to an agent or mesh.

    Args:
        gateway_slug: Lowercase alphanumeric + hyphens identifier.
        target_type: Either 'agent' or 'mesh'.
        target_slug: Slug of the existing agent or mesh to bind to.
        gateway_type: Interface type label (default 'cli').
        start: Directory to begin root discovery from. Defaults to cwd.

    Returns:
        The absolute :class:`~pathlib.Path` to the newly created gateway directory.

    Raises:
        RuntimeError: If the field root cannot be discovered.
        ValueError: If *gateway_slug* or *target_type* fails validation.
        FileExistsError: If the gateway directory already exists.
        FileNotFoundError: If the target agent or mesh does not exist.
    """
    root = find_root(start)
    if root is None:
        raise RuntimeError(
            "Could not locate field root: no .recursive-field-root marker "
            "found in the current directory or any ancestor."
        )

    if not validate_slug(gateway_slug):
        raise ValueError(
            f"Invalid gateway slug {gateway_slug!r}: must be lowercase "
            "alphanumeric with hyphens (e.g. 'sentinel-cli-gw')."
        )

    if target_type not in VALID_TARGET_TYPES:
        raise ValueError(
            f"Invalid target_type {target_type!r}: must be one of "
            f"{sorted(VALID_TARGET_TYPES)}."
        )

    if not validate_slug(target_slug):
        raise ValueError(
            f"Invalid target slug {target_slug!r}: must be lowercase "
            "alphanumeric with hyphens."
        )

    # Read genesis UUID from the marker.
    marker_path = root / MARKER_FILENAME
    marker_data = json.loads(marker_path.read_text(encoding="utf-8"))
    genesis_uuid = marker_data["genesis_uuid"]

    # Verify target existence and extract target_id.
    target_id, target_dir = _resolve_target(root, target_type, target_slug)

    # Gateway directory — prevent overwrites.
    gateway_dir = root / "gateways" / gateway_slug
    if gateway_dir.exists():
        raise FileExistsError(
            f"Gateway slug already exists: {gateway_dir}. "
            "Refusing to overwrite an existing gateway."
        )

    gateway_dir.mkdir(parents=True, exist_ok=True)

    # Write Gateway Manifest.
    gateway_id = str(uuid.uuid4())
    created_at = _utc_now_iso()

    manifest = {
        "gateway_id": gateway_id,
        "slug": gateway_slug,
        "field_genesis_uuid": genesis_uuid,
        "target_type": target_type,
        "target_slug": target_slug,
        "target_id": target_id,
        "gateway_type": gateway_type,
        "status": "active",
        "created_at": created_at,
        "schema_version": SCHEMA_VERSION,
    }

    (gateway_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    # Initialize append-only interface log.
    init_event = {
        "event_type": "gateway_initialized",
        "timestamp": created_at,
        "gateway_id": gateway_id,
        "gateway_slug": gateway_slug,
        "target_type": target_type,
        "target_slug": target_slug,
        "target_id": target_id,
        "gateway_type": gateway_type,
    }

    (gateway_dir / "events.jsonl").write_text(
        json.dumps(init_event) + "\n",
        encoding="utf-8",
    )

    # Append gateway_attached event to target's log/queue.
    _append_gateway_attached(
        target_dir, target_type, gateway_id, gateway_slug
    )

    return gateway_dir


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]

    if len(argv) < 3:
        print(
            "Usage: python3 create_gateway.py <gateway_slug> "
            "<target_type> <target_slug> [gateway_type]",
            file=sys.stderr,
        )
        return 2

    gateway_slug = argv[0]
    target_type = argv[1]
    target_slug = argv[2]
    gateway_type = argv[3] if len(argv) > 3 else "cli"

    try:
        gateway_dir = create_gateway(
            gateway_slug, target_type, target_slug, gateway_type
        )
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except FileExistsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 3
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 4

    manifest_path = gateway_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(json.dumps({"gateway_dir": str(gateway_dir), **manifest}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
