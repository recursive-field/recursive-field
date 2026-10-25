#!/usr/bin/env python3
"""Dynamic System Control Switchboard for the Recursive Field.

A governance layer that manages runtime security profiles (open,
restricted, lockdown) and prompt-module switching without container
restarts. Integrates with unit cell observation logs and hydrated seed
profiles.

Usage:
    python3 system_control.py [--agent <agent_slug>] \
        [--set-security <open|restricted|lockdown>] \
        [--toggle-include <include_name>] [--status]

Exit codes:
    0  operation completed successfully
    1  field root not found or runtime error
    2  invalid arguments or agent not found
    3  security profile or include name invalid
"""

from __future__ import annotations

import argparse
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
CONTROL_PROFILE_PATH = Path("state") / "control_profile.json"

VALID_SECURITY_PROFILES = ("open", "restricted", "lockdown")

DEFAULT_CONTROL_PROFILE: dict = {
    "active_security_profile": "open",
    "security_profiles": {
        "open": {
            "prompt_includes": {},
            "capabilities": ["all"],
            "disabled_includes": [],
        },
        "restricted": {
            "disabled_includes": ["godmode", "plinian_matrix"],
            "capabilities": ["observe", "coordinate", "persist"],
        },
        "lockdown": {
            "disabled_includes": [
                "godmode",
                "plinian_matrix",
                "system_control_tools",
            ],
            "capabilities": ["observe"],
        },
    },
    "prompt_includes": {
        "agent_identity": True,
        "config_first_orientation": True,
        "godmode": False,
    },
    "updated_at": "",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _ensure_control_profile(root: Path, genesis_uuid: str) -> tuple[dict, Path]:
    """Read or create the control profile, returning (profile, path).

    Falls back to DEFAULT_CONTROL_PROFILE if the file is missing.
    Injects genesis_uuid into the profile on first creation.
    """
    profile_path = root / CONTROL_PROFILE_PATH
    if profile_path.is_file():
        profile = _read_json(profile_path)
    else:
        profile = dict(DEFAULT_CONTROL_PROFILE)
        profile["genesis_uuid"] = genesis_uuid
        profile["updated_at"] = _utc_now_iso()
        _write_json(profile_path, profile)
    return profile, profile_path


def _get_agent_security_from_profile(
    agent_dir: Path,
) -> str | None:
    """Read an agent's profile.json and return its security_profile field."""
    profile_path = agent_dir / "profile.json"
    if not profile_path.is_file():
        return None
    profile = _read_json(profile_path)
    return profile.get("security_profile")


def _apply_security_to_includes(
    profile: dict, security_level: str
) -> list[str]:
    """Apply security-level restrictions to prompt includes.

    Disables includes listed under the active security profile's
    'disabled_includes'.  Returns a list of include names that were
    toggled off (for the observation event).
    """
    security_profiles = profile.get("security_profiles", {})
    active = security_profiles.get(security_level, {})
    disabled = active.get("disabled_includes", [])

    toggled_off: list[str] = []
    includes = profile.get("prompt_includes", {})
    for name in disabled:
        if name in includes and includes[name]:
            includes[name] = False
            toggled_off.append(name)
        elif name not in includes:
            includes[name] = False

    return toggled_off


def _append_control_event(
    agent_dir: Path | None,
    old_profile: str | None,
    new_profile: str,
    toggled_includes: list[str],
    timestamp: str,
) -> None:
    """Append a control_profile_changed event to an agent's observation log."""
    if agent_dir is None:
        return
    log_path = agent_dir / "observations" / "log.jsonl"
    if not log_path.parent.is_dir():
        return
    event = {
        "event_type": "control_profile_changed",
        "timestamp": timestamp,
        "old_security_profile": old_profile,
        "new_security_profile": new_profile,
        "toggled_includes": toggled_includes,
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def _print_status(profile: dict, profile_path: Path) -> None:
    """Print a human-readable status summary."""
    active = profile.get("active_security_profile", "unknown")
    includes = profile.get("prompt_includes", {})
    security = profile.get("security_profiles", {})

    print(f"Control Profile: {profile_path}")
    print(f"Active Security: {active}")
    print(f"Genesis UUID: {profile.get('genesis_uuid', 'N/A')}")
    print(f"Updated: {profile.get('updated_at', 'N/A')}")
    print()

    print("Security Profiles:")
    for name in VALID_SECURITY_PROFILES:
        if name in security:
            sp = security[name]
            disabled = sp.get("disabled_includes", [])
            caps = sp.get("capabilities", [])
            marker = " <- ACTIVE" if name == active else ""
            print(f"  {name}{marker}")
            if disabled:
                print(f"    disabled_includes: {disabled}")
            if caps:
                print(f"    capabilities: {caps}")
    print()

    print("Prompt Includes:")
    for name in sorted(includes):
        state = "ON" if includes[name] else "off"
        print(f"  {name}: {state}")


def system_control(
    agent_slug: str | None = None,
    set_security: str | None = None,
    toggle_include: str | None = None,
    status_only: bool = False,
    start: str | os.PathLike[str] | None = None,
) -> dict:
    """Execute a control operation.

    Args:
        agent_slug: Target agent (None for global).
        set_security: Set the active security profile.
        toggle_include: Toggle a prompt include on/off.
        status_only: Only print status, no mutations.
        start: Directory to begin root discovery from.

    Returns:
        A dict describing the operation result.
    """
    root = find_root(start)
    if root is None:
        raise RuntimeError(
            "Could not locate field root: no .recursive-field-root marker "
            "found in the current directory or any ancestor."
        )

    # Read genesis UUID.
    marker = _read_json(root / MARKER_FILENAME)
    genesis_uuid = marker.get("genesis_uuid", "")

    # Load or create control profile.
    profile, profile_path = _ensure_control_profile(root, genesis_uuid)
    old_security = profile.get("active_security_profile", "open")

    # Status-only mode.
    if status_only:
        _print_status(profile, profile_path)
        return {
            "profile_path": str(profile_path),
            "active_security_profile": old_security,
            "operation": "status",
        }

    # Validate set_security.
    if set_security is not None and set_security not in VALID_SECURITY_PROFILES:
        raise ValueError(
            f"Invalid security profile: {set_security!r}. "
            f"Must be one of {list(VALID_SECURITY_PROFILES)}."
        )

    # Resolve target agent directory.
    agent_dir: Path | None = None
    if agent_slug:
        agent_dir = root / "agents" / agent_slug
        if not (agent_dir / "identity.json").is_file():
            raise FileNotFoundError(
                f"Agent not found: {agent_slug!r} "
                f"(expected {agent_dir / 'identity.json'})"
            )

    changes_made = False
    toggled_includes: list[str] = []
    new_security = old_security

    # Apply security change.
    if set_security is not None:
        if set_security != old_security:
            profile["active_security_profile"] = set_security
            new_security = set_security
            # Apply security restrictions to prompt includes.
            disabled = _apply_security_to_includes(profile, set_security)
            toggled_includes.extend(disabled)
            changes_made = True

    # Apply include toggle.
    if toggle_include is not None:
        includes = profile.setdefault("prompt_includes", {})
        current = includes.get(toggle_include, False)
        includes[toggle_include] = not current
        toggled_includes.append(toggle_include)
        changes_made = True

    # Write profile if changes were made.
    if changes_made:
        timestamp = _utc_now_iso()
        profile["updated_at"] = timestamp
        _write_json(profile_path, profile)

        # Append observation event.
        _append_control_event(
            agent_dir,
            old_security if set_security else None,
            new_security,
            toggled_includes,
            timestamp,
        )

        # If global change (no agent_slug), append to all agents.
        if agent_slug is None:
            agents_dir = root / "agents"
            if agents_dir.is_dir():
                for ap in sorted(agents_dir.iterdir()):
                    if ap.is_dir() and (ap / "identity.json").is_file():
                        _append_control_event(
                            ap, old_security, new_security,
                            toggled_includes, timestamp,
                        )

    return {
        "profile_path": str(profile_path),
        "old_security_profile": old_security,
        "new_security_profile": new_security,
        "changes_made": changes_made,
        "toggled_includes": toggled_includes,
        "agent_slug": agent_slug,
        "operation": "set_security" if set_security else (
            "toggle_include" if toggle_include else "noop"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Dynamic System Control Switchboard"
    )
    parser.add_argument(
        "--agent", type=str, default=None,
        help="Target agent slug (omit for global)",
    )
    parser.add_argument(
        "--set-security", type=str, default=None,
        choices=VALID_SECURITY_PROFILES,
        help="Set the active security profile",
    )
    parser.add_argument(
        "--toggle-include", type=str, default=None,
        help="Toggle a prompt include on/off",
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Print current control profile status",
    )
    args = parser.parse_args(argv)

    try:
        result = system_control(
            agent_slug=args.agent,
            set_security=args.set_security,
            toggle_include=args.toggle_include,
            status_only=args.status,
        )
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except (ValueError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not args.status:
        if result["changes_made"]:
            print(f"Control profile updated: {result['profile_path']}")
            print(f"  Security: {result['old_security_profile']} -> {result['new_security_profile']}")
            if result["toggled_includes"]:
                print(f"  Toggled includes: {result['toggled_includes']}")
            if result["agent_slug"]:
                print(f"  Agent: {result['agent_slug']}")
        else:
            print("No changes made.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
