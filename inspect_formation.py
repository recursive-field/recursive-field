#!/usr/bin/env python3
"""Autonomous Formation Self-Inspection for the Recursive Field.

A vantage-point analyzer that dynamically reconstructs situational
context, active topologies, and observational event counts without
hardcoded path assumptions.

Usage:
    python3 inspect_formation.py [--agent <agent_slug>] [--json]

Exit codes:
    0  inspection completed successfully
    1  field root not found or runtime error
    2  integrity / validation failure
"""

from __future__ import annotations

import argparse
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
ENV_FILENAME = "field_env.json"


def _read_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing log file: {path}")
    events: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            events.append(json.loads(line))
    return events


def _short_uuid(uuid_str: str, length: int = 8) -> str:
    return uuid_str[:length] + "..." if len(uuid_str) > length else uuid_str


def _count_jsonl(path: Path) -> int:
    if not path.is_file():
        return 0
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            count += 1
    return count


def _verify_env(root: Path) -> dict | None:
    env_path = root / "tmp" / ENV_FILENAME
    if not env_path.is_file():
        return None
    env = _read_json(env_path)
    for key in ("agents_dir", "mesh_dir", "gateways_dir", "state_dir"):
        if key not in env:
            return None
        if not Path(env[key]).is_dir():
            return None
    return env


def _scan_agents(agents_dir: Path) -> dict[str, dict]:
    agents: dict[str, dict] = {}
    if not agents_dir.is_dir():
        return agents
    for agent_path in sorted(agents_dir.iterdir()):
        if not agent_path.is_dir():
            continue
        identity_path = agent_path / "identity.json"
        if not identity_path.is_file():
            continue
        identity = _read_json(identity_path)
        slug = identity.get("slug", agent_path.name)
        log_path = agent_path / "observations" / "log.jsonl"
        event_count = _count_jsonl(log_path)
        agents[slug] = {
            "agent_id": identity.get("agent_id", ""),
            "slug": slug,
            "role": identity.get("role", ""),
            "created_at": identity.get("created_at", ""),
            "field_genesis_uuid": identity.get("field_genesis_uuid", ""),
            "event_count": event_count,
            "log_path": str(log_path),
            "identity_path": str(identity_path),
        }
    return agents


def _scan_meshes(mesh_dir: Path) -> dict[str, dict]:
    meshes: dict[str, dict] = {}
    if not mesh_dir.is_dir():
        return meshes
    for mesh_path in sorted(mesh_dir.iterdir()):
        if not mesh_path.is_dir():
            continue
        channel_path = mesh_path / "channel.json"
        if not channel_path.is_file():
            continue
        channel = _read_json(channel_path)
        slug = channel.get("slug", mesh_path.name)
        queue_path = mesh_path / "queue.jsonl"
        queue_count = _count_jsonl(queue_path)
        endpoints = [
            {"slug": ep.get("slug", ""), "agent_id": ep.get("agent_id", "")}
            for ep in channel.get("endpoints", [])
        ]
        meshes[slug] = {
            "mesh_id": channel.get("mesh_id", ""),
            "slug": slug,
            "channel_type": channel.get("channel_type", ""),
            "created_at": channel.get("created_at", ""),
            "endpoints": endpoints,
            "queue_event_count": queue_count,
            "queue_path": str(queue_path),
            "channel_path": str(channel_path),
        }
    return meshes


def _scan_gateways(gw_dir: Path) -> dict[str, dict]:
    gateways: dict[str, dict] = {}
    if not gw_dir.is_dir():
        return gateways
    for gw_path in sorted(gw_dir.iterdir()):
        if not gw_path.is_dir():
            continue
        manifest_path = gw_path / "manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = _read_json(manifest_path)
        slug = manifest.get("slug", gw_path.name)
        events_path = gw_path / "events.jsonl"
        event_count = _count_jsonl(events_path)
        gateways[slug] = {
            "gateway_id": manifest.get("gateway_id", ""),
            "slug": slug,
            "target_type": manifest.get("target_type", ""),
            "target_slug": manifest.get("target_slug", ""),
            "target_id": manifest.get("target_id", ""),
            "gateway_type": manifest.get("gateway_type", ""),
            "status": manifest.get("status", ""),
            "created_at": manifest.get("created_at", ""),
            "event_count": event_count,
            "events_path": str(events_path),
            "manifest_path": str(manifest_path),
        }
    return gateways


def _build_topology(root: Path) -> dict:
    genesis = _read_json(root / MARKER_FILENAME)

    agents_dir = root / "agents"
    mesh_dir = root / "mesh"
    gw_dir = root / "gateways"

    agents = _scan_agents(agents_dir)
    meshes = _scan_meshes(mesh_dir)
    gateways = _scan_gateways(gw_dir)

    # Build agent-centric mesh index for vantage-point mode.
    agent_meshes: dict[str, list[str]] = {slug: [] for slug in agents}
    for mesh_slug, mesh_info in meshes.items():
        for ep in mesh_info["endpoints"]:
            ep_slug = ep["slug"]
            if ep_slug in agent_meshes:
                agent_meshes[ep_slug].append(mesh_slug)

    # Build agent-centric gateway index.
    agent_gateways: dict[str, list[str]] = {slug: [] for slug in agents}
    mesh_gateways: dict[str, list[str]] = {slug: [] for slug in meshes}
    for gw_slug, gw_info in gateways.items():
        t_type = gw_info["target_type"]
        t_slug = gw_info["target_slug"]
        if t_type == "agent" and t_slug in agent_gateways:
            agent_gateways[t_slug].append(gw_slug)
        elif t_type == "mesh" and t_slug in mesh_gateways:
            mesh_gateways[t_slug].append(gw_slug)

    env = _verify_env(root)

    return {
        "field_root": str(root),
        "genesis_uuid": genesis.get("genesis_uuid", ""),
        "schema_version": genesis.get("schema_version", ""),
        "env_verified": env is not None,
        "agents": agents,
        "meshes": meshes,
        "gateways": gateways,
        "agent_meshes": agent_meshes,
        "agent_gateways": agent_gateways,
        "mesh_gateways": mesh_gateways,
    }


def _agent_vantage(topology: dict, agent_slug: str) -> dict | None:
    agents = topology["agents"]
    if agent_slug not in agents:
        return None

    agent = agents[agent_slug]
    log_path = Path(agent["log_path"])
    all_events = _read_jsonl(log_path) if log_path.is_file() else []
    recent_events = all_events[-10:]

    connected_meshes = topology["agent_meshes"].get(agent_slug, [])
    attached_gateways = topology["agent_gateways"].get(agent_slug, [])

    mesh_details = []
    for mesh_slug in connected_meshes:
        if mesh_slug in topology["meshes"]:
            mesh = topology["meshes"][mesh_slug]
            mesh_details.append({
                "slug": mesh_slug,
                "mesh_id": mesh["mesh_id"],
                "channel_type": mesh["channel_type"],
                "endpoints": mesh["endpoints"],
                "queue_event_count": mesh["queue_event_count"],
            })

    gateway_details = []
    for gw_slug in attached_gateways:
        if gw_slug in topology["gateways"]:
            gw = topology["gateways"][gw_slug]
            gateway_details.append({
                "slug": gw_slug,
                "gateway_id": gw["gateway_id"],
                "gateway_type": gw["gateway_type"],
                "status": gw["status"],
            })

    return {
        "vantage_agent": agent_slug,
        "agent_id": agent["agent_id"],
        "role": agent["role"],
        "created_at": agent["created_at"],
        "total_observation_events": agent["event_count"],
        "connected_meshes": mesh_details,
        "attached_gateways": gateway_details,
        "recent_events": recent_events,
    }


def _print_human(topology: dict) -> None:
    root = topology["field_root"]
    genesis = topology["genesis_uuid"]
    env_ok = topology["env_verified"]

    print(f"Field Root: {root}")
    print(f"Genesis: {_short_uuid(genesis)}  Schema: {topology['schema_version']}")
    print(f"Runtime env: {'verified' if env_ok else 'not found / invalid'}")
    print()

    agents = topology["agents"]
    print(f"Agents ({len(agents)}):")
    for slug, info in sorted(agents.items()):
        print(
            f"  {slug} [{_short_uuid(info['agent_id'])}] "
            f"role={info['role']!r}  events={info['event_count']}"
        )

    meshes = topology["meshes"]
    print(f"\nMeshes ({len(meshes)}):")
    for slug, info in sorted(meshes.items()):
        eps = [e["slug"] for e in info["endpoints"]]
        ep_str = " <-> ".join(eps)
        print(
            f"  {slug} [{_short_uuid(info['mesh_id'])}] "
            f"type={info['channel_type']}  endpoints={ep_str}  "
            f"queue_events={info['queue_event_count']}"
        )

    gateways = topology["gateways"]
    print(f"\nGateways ({len(gateways)}):")
    for slug, info in sorted(gateways.items()):
        print(
            f"  {slug} [{_short_uuid(info['gateway_id'])}] "
            f"-> {info['target_type']}: {info['target_slug']}  "
            f"type={info['gateway_type']}  status={info['status']}  "
            f"events={info['event_count']}"
        )

    total_agents = len(agents)
    total_meshes = len(meshes)
    total_gws = len(gateways)
    total_events = sum(a["event_count"] for a in agents.values())
    print(
        f"\nSummary: {total_agents} agents, {total_meshes} meshes, "
        f"{total_gws} gateways, {total_events} total observation events"
    )


def _print_agent_vantage(vp: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(vp, indent=2))
        return

    print(f"Vantage Agent: {vp['vantage_agent']}")
    print(f"  Agent ID: {_short_uuid(vp['agent_id'])}")
    print(f"  Role: {vp['role']!r}")
    print(f"  Created: {vp['created_at']}")
    print(f"  Total observation events: {vp['total_observation_events']}")

    meshes = vp["connected_meshes"]
    print(f"\n  Connected meshes ({len(meshes)}):")
    for m in meshes:
        eps = [e["slug"] for e in m["endpoints"]]
        print(
            f"    {m['slug']} [{_short_uuid(m['mesh_id'])}] "
            f"type={m['channel_type']}  endpoints={', '.join(eps)}  "
            f"queue_events={m['queue_event_count']}"
        )

    gws = vp["attached_gateways"]
    print(f"\n  Attached gateways ({len(gws)}):")
    for g in gws:
        print(
            f"    {g['slug']} [{_short_uuid(g['gateway_id'])}] "
            f"type={g['gateway_type']}  status={g['status']}"
        )

    events = vp["recent_events"]
    print(f"\n  Recent events ({len(events)}):")
    for e in events:
        etype = e.get("event_type", "?")
        ts = e.get("timestamp", "?")
        extra = ""
        if "mesh_slug" in e:
            extra = f" mesh={e['mesh_slug']}"
        elif "gateway_slug" in e:
            extra = f" gateway={e['gateway_slug']}"
        print(f"    [{ts}] {etype}{extra}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Autonomous Formation Self-Inspection"
    )
    parser.add_argument(
        "--agent",
        type=str,
        default=None,
        help="Agent slug for vantage-point mode",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Output structured JSON instead of human-readable text",
    )
    args = parser.parse_args(argv)

    root = find_root()
    if root is None:
        print(
            "Error: Could not locate field root (no .recursive-field-root "
            "marker found).",
            file=sys.stderr,
        )
        return 1

    try:
        topology = _build_topology(root)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.agent:
        vp = _agent_vantage(topology, args.agent)
        if vp is None:
            print(
                f"Error: Agent slug {args.agent!r} not found in field.",
                file=sys.stderr,
            )
            return 2
        _print_agent_vantage(vp, args.as_json)
    elif args.as_json:
        print(json.dumps(topology, indent=2))
    else:
        _print_human(topology)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
