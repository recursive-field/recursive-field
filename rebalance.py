#!/usr/bin/env python3
"""Self-Maintenance & Rebalancing Engine for the Recursive Field.

Audits structural drift, validates state ledger consistency, repairs
hierarchy edges, prunes stale scratch files, and records field_rebalanced
events across all active agent observation logs.

Usage:
    python3 rebalance_field.py [--dry-run] [--prune-scratch] [--repair-hierarchy]

Exit codes:
    0  rebalance completed (issues may or may not have been found)
    1  field root not found or runtime error
    2  critical integrity failure detected
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
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
CONTROL_PROFILE_PATH = Path("state") / "control_profile.json"
HIERARCHY_PATH = Path("state") / "hierarchy.json"
LEDGER_PATH = Path("state") / "ledger.jsonl"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


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


def _scan_agents(agents_dir: Path) -> dict[str, dict]:
    agents: dict[str, dict] = {}
    if not agents_dir.is_dir():
        return agents
    for path in sorted(agents_dir.iterdir()):
        if not path.is_dir():
            continue
        identity_path = path / "identity.json"
        if not identity_path.is_file():
            continue
        identity = _read_json(identity_path)
        slug = identity.get("slug", path.name)
        agents[slug] = {
            "identity": identity,
            "dir": path,
            "agent_id": identity.get("agent_id", ""),
            "parent_id": identity.get("parent_id"),
            "parent_slug": identity.get("parent_slug"),
        }
    return agents


def _audit_meshes(
    root: Path, agents: dict[str, dict], dry_run: bool
) -> list[dict]:
    """Audit mesh channel.json for endpoint agent existence."""
    issues: list[dict] = []
    mesh_dir = root / "mesh"
    if not mesh_dir.is_dir():
        return issues
    for mesh_path in sorted(mesh_dir.iterdir()):
        if not mesh_path.is_dir():
            continue
        channel_path = mesh_path / "channel.json"
        if not channel_path.is_file():
            issues.append({
                "type": "missing_channel",
                "path": str(channel_path),
                "severity": "warning",
            })
            continue
        channel = _read_json(channel_path)
        endpoints = channel.get("endpoints", [])
        for ep in endpoints:
            ep_slug = ep.get("slug", "")
            if ep_slug not in agents:
                issues.append({
                    "type": "orphaned_mesh_endpoint",
                    "mesh_slug": channel.get("slug", mesh_path.name),
                    "missing_agent": ep_slug,
                    "severity": "critical",
                })
    return issues


def _audit_gateways(
    root: Path, agents: dict[str, dict], meshes: dict[str, dict],
    dry_run: bool,
) -> list[dict]:
    """Audit gateway manifest.json for target existence."""
    issues: list[dict] = []
    gw_dir = root / "gateways"
    if not gw_dir.is_dir():
        return issues
    for gw_path in sorted(gw_dir.iterdir()):
        if not gw_path.is_dir():
            continue
        manifest_path = gw_path / "manifest.json"
        if not manifest_path.is_file():
            issues.append({
                "type": "missing_manifest",
                "path": str(manifest_path),
                "severity": "warning",
            })
            continue
        manifest = _read_json(manifest_path)
        target_type = manifest.get("target_type", "")
        target_slug = manifest.get("target_slug", "")
        if target_type == "agent":
            if target_slug not in agents:
                issues.append({
                    "type": "orphaned_gateway_target",
                    "gateway_slug": manifest.get("slug", gw_path.name),
                    "target_type": "agent",
                    "missing": target_slug,
                    "severity": "critical",
                })
        elif target_type == "mesh":
            if target_slug not in meshes:
                issues.append({
                    "type": "orphaned_gateway_target",
                    "gateway_slug": manifest.get("slug", gw_path.name),
                    "target_type": "mesh",
                    "missing": target_slug,
                    "severity": "critical",
                })
    return issues


def _audit_hierarchy(
    root: Path, agents: dict[str, dict], dry_run: bool
) -> list[dict]:
    """Audit hierarchy.json against actual identity.json files."""
    issues: list[dict] = []
    hier_path = root / HIERARCHY_PATH
    if not hier_path.is_file():
        # If there are agents with parent_id but no hierarchy.json, report it.
        has_parents = any(a["parent_id"] for a in agents.values())
        if has_parents:
            issues.append({
                "type": "missing_hierarchy",
                "path": str(hier_path),
                "severity": "warning",
            })
        return issues

    hierarchy = _read_json(hier_path)
    nodes = hierarchy.get("nodes", {})

    # Check for agents in hierarchy but not on disk.
    for node_slug in nodes:
        if node_slug not in agents:
            issues.append({
                "type": "hierarchy_ghost_node",
                "missing_agent": node_slug,
                "severity": "warning",
            })

    # Check for agents on disk with parent_id not in hierarchy.
    for slug, info in agents.items():
        parent_slug = info.get("parent_slug")
        if parent_slug:
            if slug not in nodes:
                issues.append({
                    "type": "hierarchy_missing_child",
                    "agent_slug": slug,
                    "severity": "warning",
                })
            elif parent_slug not in nodes.get(slug, {}).get("parents", []):
                issues.append({
                    "type": "hierarchy_missing_parent_edge",
                    "agent_slug": slug,
                    "expected_parent": parent_slug,
                    "severity": "warning",
                })

    return issues


def _audit_ledger(root: Path, agents: dict[str, dict]) -> list[dict]:
    """Validate SHA-256 checksums against latest ledger snapshot."""
    issues: list[dict] = []
    ledger_path = root / LEDGER_PATH
    if not ledger_path.is_file():
        issues.append({
            "type": "missing_ledger",
            "path": str(ledger_path),
            "severity": "info",
        })
        return issues

    events = _read_jsonl(ledger_path)
    if not events:
        issues.append({
            "type": "empty_ledger",
            "path": str(ledger_path),
            "severity": "info",
        })
        return issues

    latest = events[-1]
    file_hashes = latest.get("file_hashes", {})

    # Verify agent identity manifests.
    for slug, info in agents.items():
        identity_path = info["dir"] / "identity.json"
        key = f"agents/{slug}/identity.json"
        if key in file_hashes:
            current_hash = _sha256_file(identity_path)
            if file_hashes[key] != current_hash:
                issues.append({
                    "type": "checksum_drift",
                    "file": key,
                    "ledger_hash": file_hashes[key][:16] + "...",
                    "current_hash": current_hash[:16] + "...",
                    "severity": "info",
                })

    # Verify control_profile.json.
    control_path = root / CONTROL_PROFILE_PATH
    if control_path.is_file():
        control_hash = _sha256_file(control_path)
        # The control profile may not be in the latest snapshot since
        # it was created after the last persist_state run.  Only report
        # if it was in the snapshot and now differs.
        for event in reversed(events):
            ctrl_key = "state/control_profile.json"
            if ctrl_key in event.get("file_hashes", {}):
                if event["file_hashes"][ctrl_key] != control_hash:
                    issues.append({
                        "type": "control_profile_drift",
                        "ledger_hash": event["file_hashes"][ctrl_key][:16] + "...",
                        "current_hash": control_hash[:16] + "...",
                        "severity": "info",
                    })
                break

    return issues


def _repair_hierarchy(
    root: Path, agents: dict[str, dict]
) -> list[str]:
    """Reconstruct hierarchy.json from identity.json parent fields."""
    marker = _read_json(root / MARKER_FILENAME)
    hierarchy = {
        "genesis_uuid": marker.get("genesis_uuid", ""),
        "nodes": {},
        "edges": [],
        "updated_at": _utc_now_iso(),
    }

    repaired: list[str] = []

    # Build nodes for all agents.
    for slug, info in agents.items():
        hierarchy["nodes"][slug] = {
            "agent_id": info["agent_id"],
            "slug": slug,
            "children": [],
            "parents": [],
        }

    # Reconstruct edges from parent_id / parent_slug.
    for slug, info in agents.items():
        parent_slug = info.get("parent_slug")
        parent_id = info.get("parent_id")
        if parent_slug and parent_id and parent_slug in agents:
            hierarchy["nodes"][slug]["parents"].append(parent_slug)
            if slug not in hierarchy["nodes"][parent_slug]["children"]:
                hierarchy["nodes"][parent_slug]["children"].append(slug)
            hierarchy["edges"].append({
                "parent": parent_slug,
                "parent_id": parent_id,
                "child": slug,
                "child_id": info["agent_id"],
                "timestamp": _utc_now_iso(),
            })
            repaired.append(f"{parent_slug} -> {slug}")

    _write_json(root / HIERARCHY_PATH, hierarchy)
    return repaired


def _prune_scratch(root: Path) -> list[str]:
    """Clean stale runtime files in tmp/, preserving field_env.json."""
    tmp_dir = root / "tmp"
    if not tmp_dir.is_dir():
        return []

    removed: list[str] = []
    for item in sorted(tmp_dir.iterdir()):
        if item.name == ENV_FILENAME:
            continue
        if item.name.startswith("."):
            continue
        if item.is_file():
            item.unlink()
            removed.append(str(item))
        elif item.is_dir():
            import shutil
            shutil.rmtree(item)
            removed.append(str(item))

    return removed


def rebalance(
    dry_run: bool = False,
    prune_scratch: bool = False,
    repair_hierarchy: bool = False,
    start: str | os.PathLike[str] | None = None,
) -> dict:
    """Execute field rebalancing.

    Args:
        dry_run: If True, audit only — no mutations.
        prune_scratch: If True, clean stale tmp/ files.
        repair_hierarchy: If True, reconstruct hierarchy.json.
        start: Directory to begin root discovery from.

    Returns:
        A dict with audit results and actions taken.
    """
    root = find_root(start)
    if root is None:
        raise RuntimeError(
            "Could not locate field root: no .recursive-field-root marker "
            "found in the current directory or any ancestor."
        )

    # Scan agents.
    agents = _scan_agents(root / "agents")

    # Scan meshes for gateway audit.
    meshes: dict[str, dict] = {}
    mesh_dir = root / "mesh"
    if mesh_dir.is_dir():
        for mp in sorted(mesh_dir.iterdir()):
            if mp.is_dir() and (mp / "channel.json").is_file():
                ch = _read_json(mp / "channel.json")
                meshes[ch.get("slug", mp.name)] = ch

    # Run audits.
    mesh_issues = _audit_meshes(root, agents, dry_run)
    gateway_issues = _audit_gateways(root, agents, meshes, dry_run)
    hierarchy_issues = _audit_hierarchy(root, agents, dry_run)
    ledger_issues = _audit_ledger(root, agents)

    all_issues = mesh_issues + gateway_issues + hierarchy_issues + ledger_issues
    critical_count = sum(1 for i in all_issues if i.get("severity") == "critical")
    warning_count = sum(1 for i in all_issues if i.get("severity") == "warning")
    info_count = sum(1 for i in all_issues if i.get("severity") == "info")

    # Actions.
    repaired_edges: list[str] = []
    pruned_files: list[str] = []

    if not dry_run:
        if repair_hierarchy:
            repaired_edges = _repair_hierarchy(root, agents)

        if prune_scratch:
            pruned_files = _prune_scratch(root)

    # Append field_rebalanced event to all agent observation logs.
    timestamp = _utc_now_iso()
    event = {
        "event_type": "field_rebalanced",
        "timestamp": timestamp,
        "dry_run": dry_run,
        "total_agents_audited": len(agents),
        "total_meshes_audited": len(meshes),
        "total_gateways_audited": len(
            list((root / "gateways").iterdir())
            if (root / "gateways").is_dir() else []
        ),
        "issues_found": len(all_issues),
        "critical_count": critical_count,
        "warning_count": warning_count,
        "info_count": info_count,
        "repaired_edges": repaired_edges if not dry_run else [],
        "pruned_files": pruned_files if not dry_run else [],
        "mode": "dry_run" if dry_run else "applied",
    }

    if not dry_run:
        for slug, info in agents.items():
            log_path = info["dir"] / "observations" / "log.jsonl"
            agent_event = dict(event)
            agent_event["agent_slug"] = slug
            agent_event["agent_id"] = info["agent_id"]
            _append_event(log_path, agent_event)

    return {
        "field_root": str(root),
        "dry_run": dry_run,
        "agents_audited": len(agents),
        "meshes_audited": len(meshes),
        "gateways_audited": len(
            list((root / "gateways").iterdir())
            if (root / "gateways").is_dir() else []
        ),
        "issues": all_issues,
        "critical_count": critical_count,
        "warning_count": warning_count,
        "info_count": info_count,
        "repaired_edges": repaired_edges,
        "pruned_files": pruned_files,
        "mode": "dry_run" if dry_run else "applied",
        "timestamp": timestamp,
    }


def _print_result(result: dict) -> None:
    mode = result["mode"].upper()
    print(f"Field Root: {result['field_root']}")
    print(f"Mode: {mode}")
    print(f"Timestamp: {result['timestamp']}")
    print()
    print(
        f"Audited: {result['agents_audited']} agents, "
        f"{result['meshes_audited']} meshes, "
        f"{result['gateways_audited']} gateways"
    )
    print(
        f"Issues: {result['critical_count']} critical, "
        f"{result['warning_count']} warnings, "
        f"{result['info_count']} info"
    )

    if result["issues"]:
        print("\nIssue details:")
        for issue in result["issues"]:
            sev = issue.get("severity", "info").upper()
            itype = issue.get("type", "unknown")
            detail = " | ".join(
                f"{k}={v}" for k, v in issue.items()
                if k not in ("type", "severity")
            )
            print(f"  [{sev}] {itype}: {detail}")

    if result["repaired_edges"]:
        print(f"\nRepaired hierarchy edges ({len(result['repaired_edges'])}):")
        for edge in result["repaired_edges"]:
            print(f"  + {edge}")

    if result["pruned_files"]:
        print(f"\nPruned scratch files ({len(result['pruned_files'])}):")
        for f_path in result["pruned_files"]:
            print(f"  - {f_path}")

    if not result["issues"] and not result["repaired_edges"] and not result["pruned_files"]:
        print("\nField health: CLEAN — no issues detected.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Self-Maintenance & Rebalancing Engine"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Audit only — no mutations",
    )
    parser.add_argument(
        "--prune-scratch", action="store_true",
        help="Clean stale tmp/ files (preserves field_env.json)",
    )
    parser.add_argument(
        "--repair-hierarchy", action="store_true",
        help="Reconstruct hierarchy.json from identity.json parent fields",
    )
    args = parser.parse_args(argv)

    try:
        result = rebalance(
            dry_run=args.dry_run,
            prune_scratch=args.prune_scratch,
            repair_hierarchy=args.repair_hierarchy,
        )
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    _print_result(result)

    # Exit 2 only on critical integrity failures that weren't repaired.
    if result["critical_count"] > 0 and result["mode"] == "applied":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
