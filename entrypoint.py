#!/usr/bin/env python3
"""Native Container Entrypoint for the Recursive Field.

Acts as the primary activation script executed when an agent container
initializes. It bridges field-root discovery, health inspection, prompt assembly
and filesystem projection, an optional fail-closed continuation handoff, and the
formation activation event. It does not enter or mutate Agent Zero's in-memory
context loop.

Usage:
    python3 entrypoint.py <agent_slug> [--dry-run] [--skip-rebalance]

Exit codes:
    0  entrypoint activated successfully
    1  field root not found or runtime error
    2  agent not found or invalid arguments
    3  health audit failed (critical integrity issues)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure the script's own directory is importable when invoked from
# a different working directory.
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from find_root import find_root  # noqa: E402
from build_prompt_pipeline import build_prompt_pipeline  # noqa: E402
from rebalance import rebalance  # noqa: E402
from init_environment import init_environment  # noqa: E402
from continuation_reflex import prepare_reflex_request  # noqa: E402
from continuation_schema import parse_timestamp  # noqa: E402

MARKER_FILENAME = ".recursive-field-root"
ENV_FILENAME = "field_env.json"
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


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


def _read_control_profile(root: Path) -> dict:
    control_path = root / "state" / "control_profile.json"
    if control_path.is_file():
        return _read_json(control_path)
    return {
        "active_security_profile": "open",
        "security_profiles": {},
        "prompt_includes": {},
    }


def _validate_env(root: Path) -> dict | None:
    """Validate and refresh tmp/field_env.json for container path alignment."""
    env_path = root / "tmp" / ENV_FILENAME
    if not env_path.is_file():
        # Re-run init to regenerate.
        init_environment()
        if env_path.is_file():
            return _read_json(env_path)
        return None

    env = _read_json(env_path)
    # Verify paths still match the discovered root.
    expected_root = str(root)
    if env.get("field_root") != expected_root:
        # Paths drifted — re-initialize.
        init_environment()
        if env_path.is_file():
            return _read_json(env_path)
    return env


def _append_event(log_path: Path, event: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def _link_prompt_to_native(
    agent_dir: Path, assembled_path: Path
) -> str | None:
    """Link assembled_system_prompt.md to Agent Zero's native prompt location.

    Copies the assembled prompt to agents/<slug>/prompts/system_prompt.md
    so Agent Zero's prompt inclusion hook can pick it up.
    Returns the path of the linked file, or None on failure.
    """
    prompts_dir = agent_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    native_path = prompts_dir / "system_prompt.md"

    if assembled_path.is_file():
        content = assembled_path.read_text(encoding="utf-8")
        native_path.write_text(content, encoding="utf-8")
        return str(native_path)

    return None


def entrypoint(
    agent_slug: str,
    dry_run: bool = False,
    skip_rebalance: bool = False,
    start: str | os.PathLike[str] | None = None,
    continuation_intent_id: str | None = None,
    continuation_at: datetime | None = None,
    continuation_boot_id: str | None = None,
    current_token_source: str | None = None,
    current_token_model: str | None = None,
) -> dict:
    """Execute the container entrypoint activation sequence.

    Args:
        agent_slug: Target agent slug.
        dry_run: If True, audit only — no mutations or event logging.
        skip_rebalance: If True, skip health audit.
        start: Directory to begin root discovery from.
        continuation_intent_id: Optional explicit durable intent to hand off.
        continuation_at: Evaluation time for deterministic classification.
        continuation_boot_id: Current boot UUID override.
        current_token_source: Current token source for external-interruption guardrail.
        current_token_model: Current token economics model (capped or metered).

    Returns:
        A dict with activation metadata.

    Raises:
        RuntimeError: If field root cannot be discovered.
        FileNotFoundError: If agent not found.
        ValueError: If slug invalid.
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
            f"Agent not found: {agent_slug!r} (expected {identity_path})"
        )

    identity = _read_json(identity_path)
    agent_id = identity.get("agent_id", "")

    # Validate and refresh field_env.json.
    env = _validate_env(root)

    # Health audit (unless --skip-rebalance).
    audit_result = None
    if not skip_rebalance:
        audit_result = rebalance(
            dry_run=True,
            prune_scratch=False,
            repair_hierarchy=False,
            start=str(root),
        )
        if audit_result.get("critical_count", 0) > 0 and not dry_run:
            raise RuntimeError(
                f"Health audit failed: {audit_result['critical_count']} "
                "critical integrity issues detected."
            )

    # System prompt assembly.
    prompt_result = build_prompt_pipeline(
        agent_slug, start=str(root)
    )

    assembled_path = Path(prompt_result["output_path"])
    prompt_hash = prompt_result["content_hash"]

    # Read active security profile.
    control_profile = _read_control_profile(root)
    active_security = control_profile.get(
        "active_security_profile", "open"
    )

    # Link prompt to Agent Zero native location.
    native_prompt_path = None
    if not dry_run:
        native_prompt_path = _link_prompt_to_native(
            agent_dir, assembled_path
        )

    # A pre-runtime entrypoint cannot inject trusted protocol into an in-memory
    # Agent Zero context.  It can only prepare an immutable, fail-closed handoff
    # for a future in-process adapter.  No user message or model turn occurs here.
    continuation_handoff = None
    if continuation_intent_id is not None:
        request, disposition, request_path = prepare_reflex_request(
            root=root,
            intent_id=continuation_intent_id,
            at=continuation_at or datetime.now(timezone.utc),
            boot_id=continuation_boot_id,
            current_token_source=current_token_source,
            current_token_model=current_token_model,
            persist=not dry_run,
        )
        continuation_handoff = {
            "request_id": request["request_id"],
            "intent_id": request["intent_id"],
            "context_id": request["context_id"],
            "disposition": disposition,
            "path": str(request_path),
            "maximum_new_turns": request["system_protocol"]["maximum_new_turns"],
            "injection_role": request["system_protocol"]["role"],
            "user_message_sent": request["system_protocol"]["user_message_sent"],
            "adapter_status": "handoff_only",
        }

    # Container activation event.
    timestamp = _utc_now_iso()
    hostname = socket.gethostname()

    activation_event = {
        "event_type": "container_activated",
        "timestamp": timestamp,
        "agent_slug": agent_slug,
        "agent_id": agent_id,
        "container_host": hostname,
        "field_root": str(root),
        "prompt_hash": prompt_hash,
        "active_security_profile": active_security,
        "prompt_layers": prompt_result.get("layer_count", 0),
        "token_estimate": prompt_result.get("token_estimate", 0),
        "byte_length": prompt_result.get("byte_length", 0),
        "native_prompt_path": native_prompt_path,
        "dry_run": dry_run,
        "audit_critical_count": (
            audit_result.get("critical_count", 0)
            if audit_result else None
        ),
        "continuation_handoff": continuation_handoff,
    }

    if not dry_run:
        log_path = agent_dir / "observations" / "log.jsonl"
        _append_event(log_path, activation_event)

    return {
        "agent_slug": agent_slug,
        "agent_id": agent_id,
        "field_root": str(root),
        "container_host": hostname,
        "prompt_hash": prompt_hash,
        "active_security_profile": active_security,
        "assembled_prompt_path": str(assembled_path),
        "native_prompt_path": native_prompt_path,
        "audit_result": audit_result,
        "dry_run": dry_run,
        "timestamp": timestamp,
        "continuation_handoff": continuation_handoff,
    }


def _print_result(result: dict) -> None:
    mode = "DRY-RUN" if result["dry_run"] else "ACTIVATED"
    print(f"Entrypoint: {mode}")
    print(f"Agent: {result['agent_slug']} [{_short_uuid(result['agent_id'])}]")
    print(f"Field Root: {result['field_root']}")
    print(f"Container Host: {result['container_host']}")
    print(f"Security: {result['active_security_profile']}")
    print(f"Prompt Hash: {result['prompt_hash'][:16]}...")
    print(f"Assembled: {result['assembled_prompt_path']}")
    if result.get("native_prompt_path"):
        print(f"Native Link: {result['native_prompt_path']}")
    handoff = result.get("continuation_handoff")
    if handoff:
        print(
            "Continuation Handoff: "
            f"{handoff['request_id']} ({handoff['disposition']}; adapter required)"
        )
    audit = result.get("audit_result")
    if audit:
        print(
            f"Health Audit: {audit['critical_count']} critical, "
            f"{audit['warning_count']} warnings"
        )
    print(f"Timestamp: {result['timestamp']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Native Container Entrypoint for the Recursive Field"
    )
    parser.add_argument("agent_slug", type=str, help="Target agent slug")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Audit only — no mutations or event logging",
    )
    parser.add_argument(
        "--skip-rebalance", action="store_true",
        help="Skip health audit before activation",
    )
    parser.add_argument(
        "--continuation-intent-id",
        help="explicit continuation intent UUID; prepares a trusted-adapter handoff only",
    )
    parser.add_argument(
        "--continuation-at",
        type=lambda value: parse_timestamp(value, "--continuation-at"),
        help="timezone-aware continuation classification time",
    )
    parser.add_argument("--continuation-boot-id")
    parser.add_argument("--current-token-source")
    parser.add_argument(
        "--current-token-model",
        choices=("capped", "metered"),
    )
    args = parser.parse_args(argv)

    try:
        result = entrypoint(
            args.agent_slug,
            dry_run=args.dry_run,
            skip_rebalance=args.skip_rebalance,
            continuation_intent_id=args.continuation_intent_id,
            continuation_at=args.continuation_at,
            continuation_boot_id=args.continuation_boot_id,
            current_token_source=args.current_token_source,
            current_token_model=args.current_token_model,
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

    _print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
