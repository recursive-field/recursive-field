#!/usr/bin/env python3
"""Tiered Memory & State Persist Engine for the Recursive Field.

Captures atomic snapshots of the field's primitives and maintains an
append-only state ledger using SHA-256 checksums for immutability and
drift detection.

Usage:
    python3 persist_state.py [--agent <agent_slug>] [--flush]

Exit codes:
    0  snapshot persisted successfully
    1  field root not found or runtime error
    2  integrity / validation failure
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
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
ENV_FILENAME = "field_env.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "Z"


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


def _count_jsonl(path: Path) -> int:
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _sha256(path: Path) -> str:
    if not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _hash_string(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _short_uuid(uuid_str: str, length: int = 8) -> str:
    return uuid_str[:length] + "..." if len(uuid_str) > length else uuid_str


def _ingest_agent(agent_dir: Path) -> dict:
    """Ingest a single agent's artifacts."""
    identity_path = agent_dir / "identity.json"
    log_path = agent_dir / "observations" / "log.jsonl"
    memory_dir = agent_dir / "memory"

    identity = _read_json(identity_path) if identity_path.is_file() else {}
    log_events = _read_jsonl(log_path)
    event_count = _count_jsonl(log_path)

    # Ingest memory directory contents.
    memory_files: list[dict] = []
    if memory_dir.is_dir():
        for mem_path in sorted(memory_dir.rglob("*")):
            if mem_path.is_file():
                memory_files.append({
                    "relative_path": str(mem_path.relative_to(agent_dir)),
                    "sha256": _sha256(mem_path),
                    "size": mem_path.stat().st_size,
                })

    slug = identity.get("slug", agent_dir.name)

    return {
        "slug": slug,
        "agent_id": identity.get("agent_id", ""),
        "role": identity.get("role", ""),
        "field_genesis_uuid": identity.get("field_genesis_uuid", ""),
        "created_at": identity.get("created_at", ""),
        "observation_event_count": event_count,
        "file_hashes": {
            "identity.json": _sha256(identity_path),
            "observations/log.jsonl": _sha256(log_path),
        },
        "memory_files": memory_files,
    }


def _ingest_mesh(mesh_dir: Path) -> dict:
    """Ingest a single mesh's artifacts."""
    channel_path = mesh_dir / "channel.json"
    queue_path = mesh_dir / "queue.jsonl"

    channel = _read_json(channel_path) if channel_path.is_file() else {}
    queue_count = _count_jsonl(queue_path)

    slug = channel.get("slug", mesh_dir.name)
    endpoints = [
        {"slug": ep.get("slug", ""), "agent_id": ep.get("agent_id", "")}
        for ep in channel.get("endpoints", [])
    ]

    return {
        "slug": slug,
        "mesh_id": channel.get("mesh_id", ""),
        "channel_type": channel.get("channel_type", ""),
        "endpoints": endpoints,
        "queue_event_count": queue_count,
        "file_hashes": {
            "channel.json": _sha256(channel_path),
            "queue.jsonl": _sha256(queue_path),
        },
    }


def _ingest_gateway(gw_dir: Path) -> dict:
    """Ingest a single gateway's artifacts."""
    manifest_path = gw_dir / "manifest.json"
    events_path = gw_dir / "events.jsonl"

    manifest = _read_json(manifest_path) if manifest_path.is_file() else {}
    event_count = _count_jsonl(events_path)

    slug = manifest.get("slug", gw_dir.name)

    return {
        "slug": slug,
        "gateway_id": manifest.get("gateway_id", ""),
        "target_type": manifest.get("target_type", ""),
        "target_slug": manifest.get("target_slug", ""),
        "target_id": manifest.get("target_id", ""),
        "gateway_type": manifest.get("gateway_type", ""),
        "status": manifest.get("status", ""),
        "event_count": event_count,
        "file_hashes": {
            "manifest.json": _sha256(manifest_path),
            "events.jsonl": _sha256(events_path),
        },
    }


def _collect_all_hashes(
    agents: list[dict], meshes: list[dict], gateways: list[dict]
) -> dict[str, str]:
    """Flatten all file hashes into a single dict for the ledger."""
    all_hashes: dict[str, str] = {}
    for agent in agents:
        for fname, h in agent.get("file_hashes", {}).items():
            key = f"agents/{agent['slug']}/{fname}"
            all_hashes[key] = h
        for mem_file in agent.get("memory_files", []):
            key = f"agents/{agent['slug']}/{mem_file['relative_path']}"
            all_hashes[key] = mem_file["sha256"]
    for mesh in meshes:
        for fname, h in mesh.get("file_hashes", {}).items():
            key = f"mesh/{mesh['slug']}/{fname}"
            all_hashes[key] = h
    for gw in gateways:
        for fname, h in gw.get("file_hashes", {}).items():
            key = f"gateways/{gw['slug']}/{fname}"
            all_hashes[key] = h
    return all_hashes


def _flush_scratch(tmp_dir: Path) -> list[str]:
    """Clean stale scratch files in tmp/, preserving field_env.json.

    Returns a list of removed file paths (as strings).
    """
    removed: list[str] = []
    if not tmp_dir.is_dir():
        return removed

    for item in sorted(tmp_dir.iterdir()):
        # Preserve the env file.
        if item.name == ENV_FILENAME:
            continue
        # Preserve hidden files (like .gitkeep).
        if item.name.startswith("."):
            continue
        if item.is_file():
            item.unlink()
            removed.append(str(item))
        elif item.is_dir():
            # Remove directory tree.
            import shutil
            shutil.rmtree(item)
            removed.append(str(item))

    return removed


def persist_state(
    agent_slug: str | None = None,
    flush: bool = False,
    start: str | os.PathLike[str] | None = None,
) -> dict:
    """Capture a state snapshot and append to the state ledger.

    Args:
        agent_slug: If given, scope ingestion to this agent only.
        flush: If True, clean stale scratch files in tmp/.
        start: Directory to begin root discovery from. Defaults to cwd.

    Returns:
        A dict with snapshot metadata and flush results.
    """
    root = find_root(start)
    if root is None:
        raise RuntimeError(
            "Could not locate field root: no .recursive-field-root marker "
            "found in the current directory or any ancestor."
        )

    # Read genesis marker.
    marker_path = root / MARKER_FILENAME
    marker = _read_json(marker_path)
    genesis_uuid = marker.get("genesis_uuid", "")

    # Verify env file.
    env_path = root / "tmp" / ENV_FILENAME
    env = _read_json(env_path) if env_path.is_file() else None
    if env is None:
        raise FileNotFoundError(
            f"Runtime environment file not found: {env_path}. "
            "Run init_field_environment.py first."
        )

    # Ingest agents.
    agents_dir = root / "agents"
    agents_data: list[dict] = []
    if agents_dir.is_dir():
        if agent_slug:
            # Scope to a single agent.
            agent_dir = agents_dir / agent_slug
            if agent_dir.is_dir():
                agents_data.append(_ingest_agent(agent_dir))
        else:
            for agent_path in sorted(agents_dir.iterdir()):
                if agent_path.is_dir() and (agent_path / "identity.json").is_file():
                    agents_data.append(_ingest_agent(agent_path))

    # Ingest meshes.
    mesh_dir = root / "mesh"
    meshes_data: list[dict] = []
    if mesh_dir.is_dir():
        # If scoped to a single agent, only include meshes that agent is part of.
        if agent_slug:
            agent_slugs = {agent_slug}
        else:
            agent_slugs = None

        for mesh_path in sorted(mesh_dir.iterdir()):
            if not mesh_path.is_dir():
                continue
            channel_path = mesh_path / "channel.json"
            if not channel_path.is_file():
                continue
            channel = _read_json(channel_path)
            endpoints = channel.get("endpoints", [])
            ep_slugs = {ep.get("slug") for ep in endpoints}
            if agent_slugs and not agent_slugs & ep_slugs:
                continue
            meshes_data.append(_ingest_mesh(mesh_path))

    # Ingest gateways.
    gw_dir = root / "gateways"
    gateways_data: list[dict] = []
    if gw_dir.is_dir():
        for gw_path in sorted(gw_dir.iterdir()):
            if not gw_path.is_dir():
                continue
            manifest_path = gw_path / "manifest.json"
            if not manifest_path.is_file():
                continue
            manifest = _read_json(manifest_path)
            # If scoped to a single agent, only include gateways targeting that agent or its meshes.
            if agent_slug:
                t_type = manifest.get("target_type", "")
                t_slug = manifest.get("target_slug", "")
                if t_type == "agent" and t_slug != agent_slug:
                    continue
                if t_type == "mesh":
                    # Include only if this mesh involves the agent.
                    mesh_channel_path = mesh_dir / t_slug / "channel.json"
                    if mesh_channel_path.is_file():
                        mc = _read_json(mesh_channel_path)
                        mc_ep_slugs = {ep.get("slug") for ep in mc.get("endpoints", [])}
                        if agent_slug not in mc_ep_slugs:
                            continue
                    else:
                        continue
            gateways_data.append(_ingest_gateway(gw_path))

    # Collect all file hashes.
    all_hashes = _collect_all_hashes(agents_data, meshes_data, gateways_data)

    # Calculate total event count.
    total_events = sum(a["observation_event_count"] for a in agents_data)
    total_events += sum(m["queue_event_count"] for m in meshes_data)
    total_events += sum(g["event_count"] for g in gateways_data)

    # Generate snapshot.
    snapshot_id = str(uuid.uuid4())
    timestamp = _utc_now_iso()
    timestamp_compact = _utc_now_compact()

    snapshot = {
        "snapshot_id": snapshot_id,
        "genesis_uuid": genesis_uuid,
        "timestamp": timestamp,
        "primitives": {
            "agents": agents_data,
            "meshes": meshes_data,
            "gateways": gateways_data,
        },
        "total_event_count": total_events,
    }

    # Write snapshot file.
    snapshots_dir = root / "state" / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    snapshot_filename = f"snap_{timestamp_compact}.json"
    snapshot_path = snapshots_dir / snapshot_filename
    snapshot_path.write_text(
        json.dumps(snapshot, indent=2) + "\n",
        encoding="utf-8",
    )

    # Compute snapshot file hash.
    snapshot_hash = _sha256(snapshot_path)

    # Append to ledger.
    ledger_path = root / "state" / "ledger.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)

    ledger_entry = {
        "event_type": "state_snapshot",
        "snapshot_id": snapshot_id,
        "timestamp": timestamp,
        "genesis_uuid": genesis_uuid,
        "total_event_count": total_events,
        "snapshot_file": snapshot_filename,
        "snapshot_sha256": snapshot_hash,
        "file_hashes": all_hashes,
        "file_count": len(all_hashes),
        "agent_scoped": agent_slug,
    }

    with ledger_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(ledger_entry) + "\n")

    # Flush scratch if requested.
    flushed_files: list[str] = []
    if flush:
        flushed_files = _flush_scratch(root / "tmp")

    return {
        "snapshot_id": snapshot_id,
        "snapshot_path": str(snapshot_path),
        "snapshot_sha256": snapshot_hash,
        "ledger_path": str(ledger_path),
        "total_event_count": total_events,
        "file_count": len(all_hashes),
        "agents_captured": len(agents_data),
        "meshes_captured": len(meshes_data),
        "gateways_captured": len(gateways_data),
        "flushed_files": flushed_files,
        "agent_scoped": agent_slug,
    }


def _print_result(result: dict) -> None:
    print(f"Snapshot ID: {_short_uuid(result['snapshot_id'], 12)}")
    print(f"Snapshot Path: {result['snapshot_path']}")
    print(f"Snapshot SHA-256: {result['snapshot_sha256'][:16]}...")
    print(f"Ledger Path: {result['ledger_path']}")
    print(f"Total Event Count: {result['total_event_count']}")
    print(f"Files Hashed: {result['file_count']}")
    print(
        f"Captured: {result['agents_captured']} agents, "
        f"{result['meshes_captured']} meshes, "
        f"{result['gateways_captured']} gateways"
    )
    if result["agent_scoped"]:
        print(f"Agent Scoped: {result['agent_scoped']}")
    if result["flushed_files"]:
        print(f"\nFlushed scratch files ({len(result['flushed_files'])}):")
        for f_path in result["flushed_files"]:
            print(f"  - {f_path}")
    else:
        print("Flushed: none")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Tiered Memory & State Persist Engine"
    )
    parser.add_argument(
        "--agent",
        type=str,
        default=None,
        help="Scope ingestion to a single agent slug",
    )
    parser.add_argument(
        "--flush",
        action="store_true",
        help="Clean stale scratch files in tmp/ (preserves field_env.json)",
    )
    args = parser.parse_args(argv)

    try:
        result = persist_state(agent_slug=args.agent, flush=args.flush)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    _print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
