#!/usr/bin/env python3
"""Portable Seed Stone & Profile Hydration for the Recursive Field.

Expands a lightweight, declarative seed into an agent's active runtime
profile and behavioral directives (``behaviour.md``).

Usage:
    python3 hydrate_profile.py <agent_slug> <seed_name_or_path> [--force]

Exit codes:
    0  profile hydrated successfully
    1  field root not found or runtime error
    2  invalid arguments or agent not found
    3  profile already exists (use --force to re-hydrate)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
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
SCHEMA_VERSION = "1.0.0"
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

DEFAULT_SEED = {
    "seed_name": "sentinel_observer",
    "schema_version": "1.0.0",
    "reasoning_mode": "internal_cot",
    "security_profile": "restricted",
    "behaviour_directives": (
        "# Field Sentinel Orientation\n\n"
        "- Primary Objective: Observe local field changes and maintain log integrity.\n"
        "- Config-First Discipline: Orient before action by reading local environment state.\n"
        "- Verification Rule: Assert state through empirical checks rather than assumption."
    ),
    "active_prompt_includes": ["agent_identity", "config_first_orientation"],
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_string(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _short_uuid(uuid_str: str, length: int = 8) -> str:
    return uuid_str[:length] + "..." if len(uuid_str) > length else uuid_str


def _resolve_seed(
    root: Path, seed_name_or_path: str
) -> tuple[dict, Path]:
    """Resolve a seed definition by name or direct path.

    Looks up ``state/seeds/<seed_name>.json`` first, then tries the
    given string as a direct file path.

    Returns:
        A tuple of (seed_dict, seed_file_path).

    Raises:
        FileNotFoundError: If the seed cannot be located.
    """
    # Try state/seeds/<name>.json
    seeds_dir = root / "state" / "seeds"
    candidate = seeds_dir / f"{seed_name_or_path}.json"

    if candidate.is_file():
        return _read_json(candidate), candidate

    # Try as a direct file path.
    direct = Path(seed_name_or_path)
    if direct.is_absolute():
        if direct.is_file():
            return _read_json(direct), direct
    else:
        # Try relative to cwd.
        if direct.is_file():
            return _read_json(direct), direct
        # Try relative to field root.
        root_relative = root / direct
        if root_relative.is_file():
            return _read_json(root_relative), root_relative

    raise FileNotFoundError(
        f"Seed not found: {seed_name_or_path!r}. "
        f"Looked in {candidate} and as a direct path."
    )


def _ensure_default_seed(root: Path) -> None:
    """Ensure the default sentinel_observer seed exists in state/seeds/."""
    seeds_dir = root / "state" / "seeds"
    default_path = seeds_dir / "sentinel_observer.json"

    if not default_path.is_file():
        seeds_dir.mkdir(parents=True, exist_ok=True)
        default_path.write_text(
            json.dumps(DEFAULT_SEED, indent=2) + "\n",
            encoding="utf-8",
        )


def _hydrate_prompt_includes(
    agent_dir: Path,
    seed: dict,
    identity: dict,
) -> list[str]:
    """Hydrate initial prompt files based on active_prompt_includes.

    Returns a list of created prompt file names.
    """
    prompts_dir = agent_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    created: list[str] = []
    includes = seed.get("active_prompt_includes", [])

    prompt_contents: dict[str, str] = {
        "agent_identity": (
            f"# Agent Identity\n\n"
            f"- Slug: {identity.get('slug', '')}\n"
            f"- Agent ID: {identity.get('agent_id', '')}\n"
            f"- Role: {identity.get('role', '')}\n"
            f"- Created: {identity.get('created_at', '')}\n"
        ),
        "config_first_orientation": (
            "# Config-First Orientation\n\n"
            "- Read local environment state before acting.\n"
            "- Use find_field_root to discover the field root.\n"
            "- Verify runtime context via tmp/field_env.json.\n"
        ),
    }

    for include_name in includes:
        if include_name in prompt_contents:
            prompt_path = prompts_dir / f"{include_name}.md"
            prompt_path.write_text(
                prompt_contents[include_name] + "\n",
                encoding="utf-8",
            )
            created.append(f"{include_name}.md")

    return created


def hydrate_profile(
    agent_slug: str,
    seed_name_or_path: str,
    force: bool = False,
    start: str | os.PathLike[str] | None = None,
) -> dict:
    """Hydrate an agent's profile from a seed definition.

    Args:
        agent_slug: Slug of the target agent.
        seed_name_or_path: Seed name (looked up in state/seeds/) or path.
        force: If True, re-hydrate even if profile.json already exists.
        start: Directory to begin root discovery from. Defaults to cwd.

    Returns:
        A dict with hydration metadata.

    Raises:
        RuntimeError: If the field root cannot be discovered.
        FileNotFoundError: If the agent or seed cannot be found.
        FileExistsError: If the profile already exists and --force not given.
    """
    root = find_root(start)
    if root is None:
        raise RuntimeError(
            "Could not locate field root: no .recursive-field-root marker "
            "found in the current directory or any ancestor."
        )

    if not SLUG_PATTERN.match(agent_slug):
        raise ValueError(
            f"Invalid agent slug {agent_slug!r}: must be lowercase "
            "alphanumeric with hyphens."
        )

    # Verify agent existence.
    agent_dir = root / "agents" / agent_slug
    identity_path = agent_dir / "identity.json"
    if not identity_path.is_file():
        raise FileNotFoundError(
            f"Agent not found: {agent_slug!r} "
            f"(expected {identity_path})"
        )

    identity = _read_json(identity_path)

    # Ensure default seed exists.
    _ensure_default_seed(root)

    # Resolve seed.
    seed, seed_path = _resolve_seed(root, seed_name_or_path)
    seed_hash = _sha256_file(seed_path)

    # Check for existing profile.
    profile_path = agent_dir / "profile.json"
    if profile_path.is_file() and not force:
        raise FileExistsError(
            f"Profile already exists for agent {agent_slug!r}: "
            f"{profile_path}. Use --force to re-hydrate."
        )

    # Read genesis UUID.
    marker = _read_json(root / MARKER_FILENAME)
    genesis_uuid = marker.get("genesis_uuid", "")

    timestamp = _utc_now_iso()

    # Build and write profile.json.
    profile = {
        "agent_slug": agent_slug,
        "agent_id": identity.get("agent_id", ""),
        "field_genesis_uuid": genesis_uuid,
        "seed_name": seed.get("seed_name", ""),
        "seed_path": str(seed_path),
        "seed_hash": seed_hash,
        "reasoning_mode": seed.get("reasoning_mode", ""),
        "security_profile": seed.get("security_profile", ""),
        "active_prompt_includes": seed.get("active_prompt_includes", []),
        "hydrated_at": timestamp,
        "schema_version": SCHEMA_VERSION,
    }

    profile_path.write_text(
        json.dumps(profile, indent=2) + "\n",
        encoding="utf-8",
    )

    # Hydrate behaviour.md into memory/.
    memory_dir = agent_dir / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    behaviour_path = memory_dir / "behaviour.md"
    behaviour_directives = seed.get("behaviour_directives", "")
    behaviour_path.write_text(
        behaviour_directives + "\n",
        encoding="utf-8",
    )

    behaviour_hash = _sha256_string(behaviour_directives)

    # Hydrate prompt includes.
    created_prompts = _hydrate_prompt_includes(agent_dir, seed, identity)

    # Append profile_hydrated event to observation log.
    log_path = agent_dir / "observations" / "log.jsonl"
    event = {
        "event_type": "profile_hydrated",
        "timestamp": timestamp,
        "agent_slug": agent_slug,
        "agent_id": identity.get("agent_id", ""),
        "seed_name": seed.get("seed_name", ""),
        "seed_hash": seed_hash,
        "behaviour_hash": behaviour_hash,
        "reasoning_mode": seed.get("reasoning_mode", ""),
        "security_profile": seed.get("security_profile", ""),
        "prompt_files_created": created_prompts,
    }

    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

    return {
        "agent_slug": agent_slug,
        "agent_dir": str(agent_dir),
        "profile_path": str(profile_path),
        "behaviour_path": str(behaviour_path),
        "seed_name": seed.get("seed_name", ""),
        "seed_hash": seed_hash,
        "behaviour_hash": behaviour_hash,
        "prompt_files_created": created_prompts,
        "hydrated_at": timestamp,
        "force": force,
    }


def _print_result(result: dict) -> None:
    print(f"Agent: {result['agent_slug']}")
    print(f"Agent Dir: {result['agent_dir']}")
    print(f"Profile: {result['profile_path']}")
    print(f"Behaviour: {result['behaviour_path']}")
    print(f"Seed: {result['seed_name']}")
    print(f"Seed Hash: {result['seed_hash'][:16]}...")
    print(f"Behaviour Hash: {result['behaviour_hash'][:16]}...")
    if result["prompt_files_created"]:
        print(f"\nPrompt files created ({len(result['prompt_files_created'])}):")
        for pf in result["prompt_files_created"]:
            print(f"  - {pf}")
    if result["force"]:
        print("\n(Re-hydrated with --force)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Portable Seed Stone & Profile Hydration"
    )
    parser.add_argument(
        "agent_slug",
        type=str,
        help="Slug of the target agent",
    )
    parser.add_argument(
        "seed_name_or_path",
        type=str,
        help="Seed name (looked up in state/seeds/) or direct JSON file path",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-hydrate even if profile.json already exists",
    )
    args = parser.parse_args(argv)

    try:
        result = hydrate_profile(
            args.agent_slug, args.seed_name_or_path, args.force
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
