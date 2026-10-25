#!/usr/bin/env python3
"""Identity & Observation primitive for the Recursive Field.

Creates a new agent identity under ``agents/<agent_slug>/`` with a canonical
Identity Manifest (``identity.json``) and an append-only observation log
(``observations/log.jsonl``) seeded with a ``genesis_observation`` event.

Usage:
    python3 create_agent.py <agent_slug> [role_description]

Exit codes:
    0  agent created successfully
    1  field root not found
    2  invalid slug or missing argument
    3  agent slug already exists
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


def create_agent(slug: str, role: str = "", start: str | os.PathLike[str] | None = None) -> Path:
    """Provision a new agent identity under the discovered field root.

    Args:
        slug: Lowercase alphanumeric + hyphens identifier.
        role: Optional human-readable role description.
        start: Directory to begin root discovery from. Defaults to cwd.

    Returns:
        The absolute :class:`~pathlib.Path` to the newly created agent directory.

    Raises:
        RuntimeError: If the field root cannot be discovered.
        ValueError: If *slug* fails validation.
        FileExistsError: If the agent directory already exists.
    """
    root = find_root(start)
    if root is None:
        raise RuntimeError(
            "Could not locate field root: no .recursive-field-root marker "
            "found in the current directory or any ancestor."
        )

    if not validate_slug(slug):
        raise ValueError(
            f"Invalid agent slug {slug!r}: must be lowercase alphanumeric "
            "with hyphens (e.g. 'field-sentinel')."
        )

    # Read genesis UUID from the marker.
    marker_path = root / MARKER_FILENAME
    marker_data = json.loads(marker_path.read_text(encoding="utf-8"))
    genesis_uuid = marker_data["genesis_uuid"]

    # Agent directory.
    agent_dir = root / "agents" / slug
    if agent_dir.exists():
        raise FileExistsError(
            f"Agent slug already exists: {agent_dir}. "
            "Refusing to overwrite an existing agent."
        )

    # Provision subdirectories.
    (agent_dir / "observations").mkdir(parents=True, exist_ok=True)
    (agent_dir / "memory").mkdir(parents=True, exist_ok=True)

    # Write Identity Manifest.
    agent_id = str(uuid.uuid4())
    created_at = _utc_now_iso()

    identity = {
        "agent_id": agent_id,
        "slug": slug,
        "field_genesis_uuid": genesis_uuid,
        "created_at": created_at,
        "role": role,
        "schema_version": SCHEMA_VERSION,
    }

    (agent_dir / "identity.json").write_text(
        json.dumps(identity, indent=2) + "\n",
        encoding="utf-8",
    )

    # Initialize append-only observation log.
    genesis_event = {
        "event_type": "genesis_observation",
        "timestamp": created_at,
        "agent_id": agent_id,
        "slug": slug,
        "detail": f"Agent '{slug}' initialized with role: {role or '(none)'}",
    }

    log_path = agent_dir / "observations" / "log.jsonl"
    log_path.write_text(
        json.dumps(genesis_event) + "\n",
        encoding="utf-8",
    )

    return agent_dir


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]

    if not argv or not argv[0]:
        print(
            "Usage: python3 create_agent.py <agent_slug> [role_description]",
            file=sys.stderr,
        )
        return 2

    slug = argv[0]
    role = argv[1] if len(argv) > 1 else ""

    try:
        agent_dir = create_agent(slug, role)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except FileExistsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 3

    identity_path = agent_dir / "identity.json"
    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    print(json.dumps({"agent_dir": str(agent_dir), **identity}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
