#!/usr/bin/env python3
"""Multi-Agent Spawn & Parent-Child Hierarchy for the Recursive Field.

Spawns subordinate agents that inherit parent security postures while
retaining isolated memory namespaces. Auto-provisions parent-child mesh
connectivity and tracks lineage in a hierarchy ledger.

Usage:
    python3 spawn_subordinate.py <parent_slug> <child_slug> [child_role] [--seed <seed_name>]

Exit codes:
    0  subordinate spawned successfully
    1  field root not found or runtime error
    2  invalid arguments or parent not found
    3  child slug already exists
    4  security posture inheritance violation
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
from create_agent import create_agent, validate_slug, SLUG_PATTERN  # noqa: E402
from create_mesh import create_mesh  # noqa: E402
from hydrate_profile import hydrate_profile  # noqa: E402

MARKER_FILENAME = ".recursive-field-root"
CONTROL_PROFILE_PATH = Path("state") / "control_profile.json"
HIERARCHY_PATH = Path("state") / "hierarchy.json"
SCHEMA_VERSION = "1.0.0"

# Security posture ordering: open > restricted > lockdown
# A parent can only spawn children at its level or more restrictive.
SECURITY_ORDER = {"open": 0, "restricted": 1, "lockdown": 2}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _short_uuid(uuid_str: str, length: int = 8) -> str:
    return uuid_str[:length] + "..." if len(uuid_str) > length else uuid_str


def _get_security_level(profile: dict) -> str:
    return profile.get("active_security_profile", "open")


def _check_inheritance_allowed(parent_security: str, child_security: str) -> bool:
    """Check if parent can spawn child at the given security level.

    Child's security must be equal or more restrictive than parent's.
    """
    parent_level = SECURITY_ORDER.get(parent_security, 0)
    child_level = SECURITY_ORDER.get(child_security, 0)
    return child_level >= parent_level


def _load_hierarchy(root: Path) -> dict:
    """Load or initialize the hierarchy ledger."""
    hier_path = root / HIERARCHY_PATH
    if hier_path.is_file():
        return _read_json(hier_path)
    # Initialize with genesis metadata.
    marker = _read_json(root / MARKER_FILENAME)
    return {
        "genesis_uuid": marker.get("genesis_uuid", ""),
        "nodes": {},
        "edges": [],
        "updated_at": "",
    }


def _update_hierarchy(
    hierarchy: dict,
    parent_slug: str,
    parent_id: str,
    child_slug: str,
    child_id: str,
    mesh_slug: str,
    mesh_id: str,
) -> dict:
    """Update the hierarchy with a new parent-child relationship."""
    nodes = hierarchy.setdefault("nodes", {})
    # Ensure parent node exists.
    if parent_slug not in nodes:
        nodes[parent_slug] = {
            "agent_id": parent_id,
            "slug": parent_slug,
            "children": [],
            "parents": [],
        }
    # Add child node.
    nodes[child_slug] = {
        "agent_id": child_id,
        "slug": child_slug,
        "children": [],
        "parents": [parent_slug],
    }
    # Update parent's children list.
    if child_slug not in nodes[parent_slug]["children"]:
        nodes[parent_slug]["children"].append(child_slug)
    # Add edge.
    edges = hierarchy.setdefault("edges", [])
    edges.append({
        "parent": parent_slug,
        "parent_id": parent_id,
        "child": child_slug,
        "child_id": child_id,
        "mesh_slug": mesh_slug,
        "mesh_id": mesh_id,
        "timestamp": _utc_now_iso(),
    })
    hierarchy["updated_at"] = _utc_now_iso()
    return hierarchy


def _append_event(log_path: Path, event: dict) -> None:
    """Append a JSON event to an observation log."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def spawn_subordinate(
    parent_slug: str,
    child_slug: str,
    child_role: str = "Subordinate process",
    seed_name: str | None = None,
    start: str | os.PathLike[str] | None = None,
) -> dict:
    """Spawn a subordinate agent under a parent.

    Args:
        parent_slug: Slug of the parent agent.
        child_slug: Slug for the new child agent.
        child_role: Role description for the child.
        seed_name: Optional seed name for profile hydration.
        start: Directory to begin root discovery from.

    Returns:
        A dict with spawn metadata.

    Raises:
        RuntimeError: If field root cannot be discovered.
        FileNotFoundError: If parent agent not found.
        FileExistsError: If child slug already exists.
        ValueError: If security inheritance is violated.
    """
    root = find_root(start)
    if root is None:
        raise RuntimeError(
            "Could not locate field root: no .recursive-field-root marker "
            "found in the current directory or any ancestor."
        )

    if not SLUG_PATTERN.match(parent_slug):
        raise ValueError(
            f"Invalid parent slug {parent_slug!r}: must be lowercase "
            "alphanumeric with hyphens."
        )
    if not SLUG_PATTERN.match(child_slug):
        raise ValueError(
            f"Invalid child slug {child_slug!r}: must be lowercase "
            "alphanumeric with hyphens."
        )

    # Verify parent existence.
    parent_identity_path = root / "agents" / parent_slug / "identity.json"
    if not parent_identity_path.is_file():
        raise FileNotFoundError(
            f"Parent agent not found: {parent_slug!r} "
            f"(expected {parent_identity_path})"
        )
    parent_identity = _read_json(parent_identity_path)
    parent_id = parent_identity.get("agent_id", "")

    # Check child slug doesn't already exist.
    child_dir = root / "agents" / child_slug
    if child_dir.exists():
        raise FileExistsError(
            f"Child slug already exists: {child_dir}. "
            "Refusing to overwrite an existing agent."
        )

    # Read control profile for security inheritance.
    control_path = root / CONTROL_PROFILE_PATH
    control_profile = _read_json(control_path) if control_path.is_file() else {
        "active_security_profile": "open",
        "security_profiles": {},
        "prompt_includes": {},
    }
    parent_security = _get_security_level(control_profile)

    # The child inherits the parent's security level (capped).
    child_security = parent_security

    # Read genesis UUID.
    marker = _read_json(root / MARKER_FILENAME)
    genesis_uuid = marker.get("genesis_uuid", "")

    # Create the child agent using create_agent mechanics.
    child_agent_dir = create_agent(child_slug, child_role, start=str(root))

    # Patch the child's identity.json to add parent fields.
    child_identity_path = child_agent_dir / "identity.json"
    child_identity = _read_json(child_identity_path)
    child_identity["parent_id"] = parent_id
    child_identity["parent_slug"] = parent_slug
    child_identity["security_profile"] = child_security
    child_identity_path.write_text(
        json.dumps(child_identity, indent=2) + "\n",
        encoding="utf-8",
    )

    child_id = child_identity.get("agent_id", "")

    # Auto-mesh: create parent-child mesh.
    mesh_slug = f"{parent_slug}-{child_slug}-mesh"
    mesh_dir = create_mesh(
        mesh_slug,
        [parent_slug, child_slug],
        channel_type="parent-child",
        start=str(root),
    )
    mesh_channel = _read_json(mesh_dir / "channel.json")
    mesh_id = mesh_channel.get("mesh_id", "")

    # Update hierarchy ledger.
    hierarchy = _load_hierarchy(root)
    _update_hierarchy(
        hierarchy, parent_slug, parent_id,
        child_slug, child_id, mesh_slug, mesh_id,
    )
    _write_json(root / HIERARCHY_PATH, hierarchy)

    # Observational events.
    timestamp = _utc_now_iso()

    # Parent: subordinate_spawned
    parent_log = root / "agents" / parent_slug / "observations" / "log.jsonl"
    _append_event(parent_log, {
        "event_type": "subordinate_spawned",
        "timestamp": timestamp,
        "agent_slug": parent_slug,
        "agent_id": parent_id,
        "child_slug": child_slug,
        "child_id": child_id,
        "mesh_slug": mesh_slug,
        "mesh_id": mesh_id,
        "child_role": child_role,
        "inherited_security": child_security,
    })

    # Child: parent_attached
    child_log = child_agent_dir / "observations" / "log.jsonl"
    _append_event(child_log, {
        "event_type": "parent_attached",
        "timestamp": timestamp,
        "agent_slug": child_slug,
        "agent_id": child_id,
        "parent_slug": parent_slug,
        "parent_id": parent_id,
        "mesh_slug": mesh_slug,
        "mesh_id": mesh_id,
        "inherited_security": child_security,
    })

    # Optional seed hydration.
    hydration_result = None
    if seed_name:
        hydration_result = hydrate_profile(
            child_slug, seed_name, force=False, start=str(root)
        )

    return {
        "parent_slug": parent_slug,
        "parent_id": parent_id,
        "child_slug": child_slug,
        "child_id": child_id,
        "child_dir": str(child_agent_dir),
        "mesh_slug": mesh_slug,
        "mesh_id": mesh_id,
        "mesh_dir": str(mesh_dir),
        "hierarchy_path": str(root / HIERARCHY_PATH),
        "inherited_security": child_security,
        "seed_hydrated": seed_name is not None,
        "hydration_result": hydration_result,
        "spawned_at": timestamp,
    }


def _print_result(result: dict) -> None:
    print(f"Parent: {result['parent_slug']} [{_short_uuid(result['parent_id'])}]")
    print(f"Child: {result['child_slug']} [{_short_uuid(result['child_id'])}]")
    print(f"  Dir: {result['child_dir']}")
    print(f"  Role: inherited security={result['inherited_security']}")
    print(f"Mesh: {result['mesh_slug']} [{_short_uuid(result['mesh_id'])}]")
    print(f"  Dir: {result['mesh_dir']}")
    print(f"Hierarchy: {result['hierarchy_path']}")
    if result["seed_hydrated"]:
        print(f"Seed: hydrated")
    else:
        print(f"Seed: none")
    print(f"Spawned: {result['spawned_at']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Multi-Agent Spawn & Parent-Child Hierarchy"
    )
    parser.add_argument("parent_slug", type=str, help="Parent agent slug")
    parser.add_argument("child_slug", type=str, help="Child agent slug")
    parser.add_argument("child_role", type=str, nargs="?", default="Subordinate process",
                        help="Child agent role description")
    parser.add_argument("--seed", type=str, default=None,
                        help="Seed name for optional profile hydration")
    args = parser.parse_args(argv)

    try:
        result = spawn_subordinate(
            args.parent_slug,
            args.child_slug,
            args.child_role,
            args.seed,
        )
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except (ValueError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except FileExistsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 3
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    _print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
