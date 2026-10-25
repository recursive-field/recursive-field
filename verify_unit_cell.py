#!/usr/bin/env python3
"""Unit Cell Assembly Validator for the Recursive Field.

Verifies the full topological graph and bi-directional observational
linkages across the field: Agent -> Mesh -> Gateway.

Usage:
    python3 verify_unit_cell.py [start_path]

Exit codes:
    0  all integrity checks passed
    1  field root not found or genesis marker invalid
    2  integrity failure detected (details printed to stderr)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure the script's own directory is importable when invoked from
# a different working directory.
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from find_root import find_root  # noqa: E402

MARKER_FILENAME = ".recursive-field-root"
EXPECTED_SCHEMA_VERSION = "1.0.0"


class IntegrityError(Exception):
    """Raised when a structural or observational integrity check fails."""


def _read_json(path: Path) -> dict:
    if not path.is_file():
        raise IntegrityError(f"Missing file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise IntegrityError(f"Invalid JSON in {path}: {exc}") from exc


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise IntegrityError(f"Missing log file: {path}")
    events: list[dict] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise IntegrityError(
                f"Invalid JSON at {path}:{lineno}: {exc}"
            ) from exc
    return events


def _short_uuid(uuid_str: str, length: int = 8) -> str:
    return uuid_str[:length] + "..." if len(uuid_str) > length else uuid_str


def verify_genesis(root: Path) -> dict:
    marker_path = root / MARKER_FILENAME
    marker = _read_json(marker_path)

    if "genesis_uuid" not in marker:
        raise IntegrityError("Genesis marker missing 'genesis_uuid'")
    if "schema_version" not in marker:
        raise IntegrityError("Genesis marker missing 'schema_version'")
    if marker["schema_version"] != EXPECTED_SCHEMA_VERSION:
        raise IntegrityError(
            f"Schema version mismatch: expected {EXPECTED_SCHEMA_VERSION!r}, "
            f"got {marker['schema_version']!r}"
        )

    return marker


def verify_agents(root: Path, genesis_uuid: str) -> dict[str, dict]:
    agents_dir = root / "agents"
    agents: dict[str, dict] = {}

    if not agents_dir.is_dir():
        raise IntegrityError(f"Agents directory not found: {agents_dir}")

    for agent_path in sorted(agents_dir.iterdir()):
        if not agent_path.is_dir():
            continue

        identity_path = agent_path / "identity.json"
        identity = _read_json(identity_path)

        slug = identity.get("slug", agent_path.name)

        if identity.get("field_genesis_uuid") != genesis_uuid:
            raise IntegrityError(
                f"Agent {slug!r} genesis_uuid mismatch: "
                f"expected {genesis_uuid}, got {identity.get('field_genesis_uuid')}"
            )

        if "agent_id" not in identity:
            raise IntegrityError(f"Agent {slug!r} missing 'agent_id'")

        log_path = agent_path / "observations" / "log.jsonl"
        events = _read_jsonl(log_path)

        genesis_events = [
            e for e in events if e.get("event_type") == "genesis_observation"
        ]
        if not genesis_events:
            raise IntegrityError(
                f"Agent {slug!r} missing 'genesis_observation' in {log_path}"
            )

        agents[slug] = {
            "identity": identity,
            "dir": agent_path,
            "log_events": events,
        }

    return agents


def verify_meshes(
    root: Path, genesis_uuid: str, agents: dict[str, dict]
) -> dict[str, dict]:
    mesh_dir = root / "mesh"
    meshes: dict[str, dict] = {}

    if not mesh_dir.is_dir():
        raise IntegrityError(f"Mesh directory not found: {mesh_dir}")

    for mesh_path in sorted(mesh_dir.iterdir()):
        if not mesh_path.is_dir():
            continue

        channel_path = mesh_path / "channel.json"
        channel = _read_json(channel_path)

        slug = channel.get("slug", mesh_path.name)

        if channel.get("field_genesis_uuid") != genesis_uuid:
            raise IntegrityError(
                f"Mesh {slug!r} genesis_uuid mismatch: expected "
                f"{genesis_uuid}, got {channel.get('field_genesis_uuid')}"
            )

        if "mesh_id" not in channel:
            raise IntegrityError(f"Mesh {slug!r} missing 'mesh_id'")

        endpoints = channel.get("endpoints", [])
        if len(endpoints) < 2:
            raise IntegrityError(
                f"Mesh {slug!r} has fewer than 2 endpoints"
            )

        for ep in endpoints:
            ep_slug = ep.get("slug")
            ep_agent_id = ep.get("agent_id")

            if ep_slug not in agents:
                raise IntegrityError(
                    f"Mesh {slug!r} references unknown agent: {ep_slug!r}"
                )

            actual_agent_id = agents[ep_slug]["identity"]["agent_id"]
            if ep_agent_id != actual_agent_id:
                raise IntegrityError(
                    f"Mesh {slug!r} endpoint {ep_slug!r} agent_id mismatch: "
                    f"expected {actual_agent_id}, got {ep_agent_id}"
                )

            mesh_connected_events = [
                e for e in agents[ep_slug]["log_events"]
                if e.get("event_type") == "mesh_connected"
                and e.get("mesh_id") == channel["mesh_id"]
            ]
            if not mesh_connected_events:
                raise IntegrityError(
                    f"Agent {ep_slug!r} missing 'mesh_connected' event "
                    f"for mesh {slug!r} (mesh_id={channel['mesh_id']})"
                )

        queue_path = mesh_path / "queue.jsonl"
        if not queue_path.is_file():
            raise IntegrityError(
                f"Mesh {slug!r} missing queue file: {queue_path}"
            )

        meshes[slug] = {
            "channel": channel,
            "dir": mesh_path,
            "queue_events": _read_jsonl(queue_path),
        }

    return meshes


def verify_gateways(
    root: Path,
    genesis_uuid: str,
    agents: dict[str, dict],
    meshes: dict[str, dict],
) -> dict[str, dict]:
    gw_dir = root / "gateways"
    gateways: dict[str, dict] = {}

    if not gw_dir.is_dir():
        raise IntegrityError(f"Gateways directory not found: {gw_dir}")

    for gw_path in sorted(gw_dir.iterdir()):
        if not gw_path.is_dir():
            continue

        manifest_path = gw_path / "manifest.json"
        manifest = _read_json(manifest_path)

        slug = manifest.get("slug", gw_path.name)

        if manifest.get("field_genesis_uuid") != genesis_uuid:
            raise IntegrityError(
                f"Gateway {slug!r} genesis_uuid mismatch: expected "
                f"{genesis_uuid}, got {manifest.get('field_genesis_uuid')}"
            )

        if "gateway_id" not in manifest:
            raise IntegrityError(f"Gateway {slug!r} missing 'gateway_id'")

        target_type = manifest.get("target_type")
        target_slug = manifest.get("target_slug")
        target_id = manifest.get("target_id")

        if target_type == "agent":
            if target_slug not in agents:
                raise IntegrityError(
                    f"Gateway {slug!r} targets unknown agent: {target_slug!r}"
                )
            actual_target_id = agents[target_slug]["identity"]["agent_id"]
            target_events = agents[target_slug]["log_events"]
        elif target_type == "mesh":
            if target_slug not in meshes:
                raise IntegrityError(
                    f"Gateway {slug!r} targets unknown mesh: {target_slug!r}"
                )
            actual_target_id = meshes[target_slug]["channel"]["mesh_id"]
            target_events = meshes[target_slug]["queue_events"]
        else:
            raise IntegrityError(
                f"Gateway {slug!r} invalid target_type: {target_type!r}"
            )

        if target_id != actual_target_id:
            raise IntegrityError(
                f"Gateway {slug!r} target_id mismatch: expected "
                f"{actual_target_id}, got {target_id}"
            )

        gateway_attached_events = [
            e for e in target_events
            if e.get("event_type") == "gateway_attached"
            and e.get("gateway_id") == manifest["gateway_id"]
        ]
        if not gateway_attached_events:
            raise IntegrityError(
                f"Target {target_slug!r} missing 'gateway_attached' event "
                f"for gateway {slug!r} "
                f"(gateway_id={manifest['gateway_id']})"
            )

        events_path = gw_path / "events.jsonl"
        if not events_path.is_file():
            raise IntegrityError(
                f"Gateway {slug!r} missing events file: {events_path}"
            )

        gateways[slug] = {
            "manifest": manifest,
            "dir": gw_path,
            "events": _read_jsonl(events_path),
        }

    return gateways


def print_topology(
    root: Path,
    genesis_uuid: str,
    agents: dict[str, dict],
    meshes: dict[str, dict],
    gateways: dict[str, dict],
) -> None:
    print(f"Field Root: {root} (Genesis: {_short_uuid(genesis_uuid)})")
    print(f"\u251c\u2500\u2500 Agents ({len(agents)})")
    agent_items = sorted(agents.items())
    for i, (slug, info) in enumerate(agent_items):
        agent_id = info["identity"]["agent_id"]
        prefix = "\u2502   \u251c\u2500\u2500" if i < len(agent_items) - 1 else "\u2502   \u2514\u2500\u2500"
        print(f"{prefix} {slug} [{_short_uuid(agent_id)}]")

    print(f"\u251c\u2500\u2500 Meshes ({len(meshes)})")
    mesh_items = sorted(meshes.items())
    for i, (slug, info) in enumerate(mesh_items):
        mesh_id = info["channel"]["mesh_id"]
        endpoints = info["channel"]["endpoints"]
        ep_slugs = [e["slug"] for e in endpoints]
        ep_str = " <-> ".join(ep_slugs)
        prefix = "\u2502   \u251c\u2500\u2500" if i < len(mesh_items) - 1 else "\u2502   \u2514\u2500\u2500"
        print(f"{prefix} {slug} [{_short_uuid(mesh_id)}] (Endpoints: {ep_str})")

    print(f"\u2514\u2500\u2500 Gateways ({len(gateways)})")
    gw_items = sorted(gateways.items())
    for i, (slug, info) in enumerate(gw_items):
        manifest = info["manifest"]
        gw_id = manifest["gateway_id"]
        target_type = manifest["target_type"]
        target_slug = manifest["target_slug"]
        type_label = target_type.capitalize()
        prefix = "    \u251c\u2500\u2500" if i < len(gw_items) - 1 else "    \u2514\u2500\u2500"
        print(
            f"{prefix} {slug} [{_short_uuid(gw_id)}] -> "
            f"{type_label}: {target_slug}"
        )

    print(f"Status: UNIT CELL INTEGRITY OK")


def verify_unit_cell(
    start: str | os.PathLike[str] | None = None,
) -> tuple[Path, str, dict, dict, dict]:
    root = find_root(start)
    if root is None:
        raise IntegrityError(
            "Could not locate field root: no .recursive-field-root marker "
            "found in the current directory or any ancestor."
        )

    marker = verify_genesis(root)
    genesis_uuid = marker["genesis_uuid"]

    agents = verify_agents(root, genesis_uuid)
    meshes = verify_meshes(root, genesis_uuid, agents)
    gateways = verify_gateways(root, genesis_uuid, agents, meshes)

    return root, genesis_uuid, agents, meshes, gateways


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    start = argv[0] if argv else None

    try:
        root, genesis_uuid, agents, meshes, gateways = verify_unit_cell(start)
    except IntegrityError as exc:
        print(f"Integrity failure: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print_topology(root, genesis_uuid, agents, meshes, gateways)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
