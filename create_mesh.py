#!/usr/bin/env python3
"""Connectivity primitive for the Recursive Field.

Binds two or more identified agents into a communication topology by
creating a shared channel manifest (``channel.json``), initializing an
append-only event queue (``queue.jsonl``), and appending ``mesh_connected``
events to the observation logs of all participating agents.

Usage:
    python3 create_mesh.py <mesh_slug> <agent_slug_1> <agent_slug_2> [channel_type]

Exit codes:
    0  mesh created successfully
    1  field root not found
    2  invalid slug or missing arguments
    3  mesh slug already exists
    4  agent slug not found
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


def _utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string with timezone offset."""
    return datetime.now(timezone.utc).isoformat()


def validate_slug(slug: str) -> bool:
    """Return True if *slug* matches the lowercase alphanumeric + hyphen pattern."""
    return bool(SLUG_PATTERN.match(slug))


def _load_agent_identity(agents_dir: Path, slug: str) -> dict:
    """Read and return the identity manifest for an agent.

    Raises:
        FileNotFoundError: If the agent directory or identity.json does not exist.
    """
    identity_path = agents_dir / slug / "identity.json"
    if not identity_path.is_file():
        raise FileNotFoundError(
            f"Agent not found: {slug} (expected {identity_path})"
        )
    return json.loads(identity_path.read_text(encoding="utf-8"))


def create_mesh(
    mesh_slug: str,
    agent_slugs: list[str],
    channel_type: str = "peer-to-peer",
    start: str | os.PathLike[str] | None = None,
) -> Path:
    """Provision a new mesh connecting two or more agents.

    Args:
        mesh_slug: Lowercase alphanumeric + hyphens identifier for the mesh.
        agent_slugs: List of agent slugs to bind (minimum 2).
        channel_type: Channel type label (default 'peer-to-peer').
        start: Directory to begin root discovery from. Defaults to cwd.

    Returns:
        The absolute :class:`~pathlib.Path` to the newly created mesh directory.

    Raises:
        RuntimeError: If the field root cannot be discovered.
        ValueError: If *mesh_slug* fails validation or fewer than 2 agents given.
        FileExistsError: If the mesh directory already exists.
        FileNotFoundError: If any agent slug is not found.
    """
    root = find_root(start)
    if root is None:
        raise RuntimeError(
            "Could not locate field root: no .recursive-field-root marker "
            "found in the current directory or any ancestor."
        )

    if not validate_slug(mesh_slug):
        raise ValueError(
            f"Invalid mesh slug {mesh_slug!r}: must be lowercase alphanumeric "
            "with hyphens (e.g. 'sentinel-scout-mesh')."
        )

    if len(agent_slugs) < 2:
        raise ValueError("At least two agent slugs are required to form a mesh.")

    # Read genesis UUID from the marker.
    marker_path = root / MARKER_FILENAME
    marker_data = json.loads(marker_path.read_text(encoding="utf-8"))
    genesis_uuid = marker_data["genesis_uuid"]

    agents_dir = root / "agents"

    # Validate all agent slugs and read their identities.
    endpoints = []
    for slug in agent_slugs:
        if not validate_slug(slug):
            raise ValueError(
                f"Invalid agent slug {slug!r}: must be lowercase alphanumeric "
                "with hyphens."
            )
        identity = _load_agent_identity(agents_dir, slug)
        endpoints.append({
            "slug": slug,
            "agent_id": identity["agent_id"],
        })

    # Mesh directory — prevent overwrites.
    mesh_dir = root / "mesh" / mesh_slug
    if mesh_dir.exists():
        raise FileExistsError(
            f"Mesh slug already exists: {mesh_dir}. "
            "Refusing to overwrite an existing mesh."
        )

    mesh_dir.mkdir(parents=True, exist_ok=True)

    # Write Mesh Channel Manifest.
    mesh_id = str(uuid.uuid4())
    created_at = _utc_now_iso()

    channel = {
        "mesh_id": mesh_id,
        "slug": mesh_slug,
        "field_genesis_uuid": genesis_uuid,
        "endpoints": endpoints,
        "channel_type": channel_type,
        "created_at": created_at,
        "schema_version": SCHEMA_VERSION,
    }

    (mesh_dir / "channel.json").write_text(
        json.dumps(channel, indent=2) + "\n",
        encoding="utf-8",
    )

    # Initialize append-only event queue.
    queue_init = {
        "event_type": "queue_initialized",
        "timestamp": created_at,
        "mesh_id": mesh_id,
        "mesh_slug": mesh_slug,
    }

    (mesh_dir / "queue.jsonl").write_text(
        json.dumps(queue_init) + "\n",
        encoding="utf-8",
    )

    # Append mesh_connected event to each participating agent's observation log.
    for ep in endpoints:
        slug = ep["slug"]
        agent_id = ep["agent_id"]
        counterparts = [e for e in endpoints if e["slug"] != slug]

        event = {
            "event_type": "mesh_connected",
            "timestamp": created_at,
            "mesh_id": mesh_id,
            "mesh_slug": mesh_slug,
            "agent_slug": slug,
            "agent_id": agent_id,
            "counterparts": [
                {"slug": c["slug"], "agent_id": c["agent_id"]}
                for c in counterparts
            ],
            "channel_type": channel_type,
        }

        log_path = agents_dir / slug / "observations" / "log.jsonl"
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

    return mesh_dir


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]

    if len(argv) < 3:
        print(
            "Usage: python3 create_mesh.py <mesh_slug> <agent_slug_1> "
            "<agent_slug_2> [channel_type]",
            file=sys.stderr,
        )
        return 2

    mesh_slug = argv[0]
    agent_slugs = argv[1:-1] if len(argv) > 3 else argv[1:3]
    channel_type = argv[-1] if len(argv) > 3 else "peer-to-peer"

    try:
        mesh_dir = create_mesh(mesh_slug, list(agent_slugs), channel_type)
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

    channel_path = mesh_dir / "channel.json"
    channel = json.loads(channel_path.read_text(encoding="utf-8"))
    print(json.dumps({"mesh_dir": str(mesh_dir), **channel}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
