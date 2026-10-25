#!/usr/bin/env python3
"""System Prompt Extension Pipeline for the Recursive Field.

A governance-aware, location-agnostic assembly engine that reads the
active control_profile.json, filters enabled versus restricted prompt
includes, and laminates prompt layers into a compact, bounded system
prompt with token budgeting and SHA-256 audit logging.

Usage:
    python3 build_prompt_pipeline.py <agent_slug> [--out-file <path>] [--json]

Exit codes:
    0  prompt assembled successfully
    1  field root not found or runtime error
    2  agent not found or invalid arguments
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
CONTROL_PROFILE_PATH = Path("state") / "control_profile.json"
ENV_FILENAME = "field_env.json"
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CHARS_PER_TOKEN = 4


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").rstrip()


def _sha256_string(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def _short_uuid(uuid_str: str, length: int = 8) -> str:
    return uuid_str[:length] + "..." if len(uuid_str) > length else uuid_str


def _build_layer_1_identity(agent_dir: Path, identity: dict) -> tuple[str, list[str]]:
    parts: list[str] = []
    sources: list[str] = []
    parts.append("# Layer 1: Substrate Identity\n")
    parts.append(f"- Agent ID: {identity.get('agent_id', '')}")
    parts.append(f"- Slug: {identity.get('slug', '')}")
    parts.append(f"- Role: {identity.get('role', '')}")
    parts.append(f"- Field Genesis UUID: {identity.get('field_genesis_uuid', '')}")
    parts.append(f"- Created: {identity.get('created_at', '')}")
    sources.append("agents/<slug>/identity.json")
    ai_path = agent_dir / "prompts" / "agent_identity.md"
    ai_text = _read_text(ai_path)
    if ai_text:
        parts.append("")
        parts.append(ai_text)
        sources.append("agents/<slug>/prompts/agent_identity.md")
    return "\n".join(parts), sources


def _build_layer_2_behaviour(agent_dir: Path) -> tuple[str, list[str]]:
    behaviour_path = agent_dir / "memory" / "behaviour.md"
    text = _read_text(behaviour_path)
    sources: list[str] = []
    if text:
        sources.append("agents/<slug>/memory/behaviour.md")
        return f"# Layer 2: Behavioral Directives\n\n{text}", sources
    return "# Layer 2: Behavioral Directives\n\n(No behavioural directives hydrated.)", sources


def _build_layer_3_security(control_profile: dict, agent_profile: dict | None) -> tuple[str, list[str]]:
    active = control_profile.get("active_security_profile", "open")
    security_profiles = control_profile.get("security_profiles", {})
    active_sp = security_profiles.get(active, {})
    capabilities = active_sp.get("capabilities", [])
    disabled = active_sp.get("disabled_includes", [])
    parts: list[str] = [
        "# Layer 3: Active Security Posture\n",
        f"- Active Profile: {active}",
        f"- Capabilities: {', '.join(capabilities) if capabilities else 'none'}",
        f"- Disabled Includes: {', '.join(disabled) if disabled else 'none'}",
    ]
    if agent_profile:
        hydrated_sp = agent_profile.get("security_profile", "")
        if hydrated_sp:
            parts.append(f"- Hydrated Security Profile: {hydrated_sp}")
            match = "MATCH" if hydrated_sp == active else "MISMATCH"
            parts.append(f"- Profile Match: {match}")
    sources = ["state/control_profile.json"]
    if agent_profile:
        sources.append("agents/<slug>/profile.json")
    return "\n".join(parts), sources


def _build_layer_4_includes(
    agent_dir: Path,
    control_profile: dict,
    knowledge_dir: str = "",
    field_root: Path | None = None,
) -> tuple[str, list[str]]:
    active = control_profile.get("active_security_profile", "open")
    security_profiles = control_profile.get("security_profiles", {})
    active_sp = security_profiles.get(active, {})
    disabled_includes = set(active_sp.get("disabled_includes", []))
    include_flags = control_profile.get("prompt_includes", {})
    parts: list[str] = ["# Layer 4: Filtered Prompt Includes & Domain Knowledge\n"]
    sources: list[str] = []
    included_count = 0
    excluded_count = 0

    # Load domain knowledge from KNOWLEDGE_DIR if set.
    if knowledge_dir:
        kd_path = Path(knowledge_dir)
        if not kd_path.is_absolute() and field_root is not None:
            kd_path = field_root / kd_path
        domain_md = kd_path / "domain.md"
        if domain_md.is_file():
            content = _read_text(domain_md)
            if content:
                parts.append(f"\n## Domain Knowledge ({kd_path.name})\n")
                parts.append(content)
                sources.append(f"knowledge/{kd_path.name}/domain.md")
                included_count += 1

    prompts_dir = agent_dir / "prompts"
    if not prompts_dir.is_dir():
        if included_count == 0:
            return "# Layer 4: Filtered Prompt Includes & Domain Knowledge\n\n(No prompt includes or domain knowledge found.)", []
        # Still return what we have from domain knowledge.
        parts.append("")
        parts.append(f"- Included: {included_count} | Excluded: {excluded_count} | Security: {active}")
        return "\n".join(parts), sources
    for prompt_path in sorted(prompts_dir.glob("*.md")):
        include_name = prompt_path.stem
        if include_name in disabled_includes:
            excluded_count += 1
            parts.append(f"- [EXCLUDED by {active} profile] {include_name}")
            continue
        if include_name in include_flags and not include_flags[include_name]:
            excluded_count += 1
            parts.append(f"- [DISABLED by control flag] {include_name}")
            continue
        content = _read_text(prompt_path)
        if content:
            parts.append(f"\n## {include_name}\n")
            parts.append(content)
            sources.append(f"agents/<slug>/prompts/{include_name}.md")
            included_count += 1
    parts.append("")
    parts.append(f"- Included: {included_count} | Excluded: {excluded_count} | Security: {active}")
    return "\n".join(parts), sources


def _build_layer_5_vantage(env: dict | None) -> tuple[str, list[str]]:
    if env is None:
        return "# Layer 5: Vantage Point Anchor\n\n(field_env.json not found)", []
    parts: list[str] = [
        "# Layer 5: Vantage Point Anchor\n",
        f"- Field Root: {env.get('field_root', '')}",
        f"- Agents Dir: {env.get('agents_dir', '')}",
        f"- Mesh Dir: {env.get('mesh_dir', '')}",
        f"- Gateways Dir: {env.get('gateways_dir', '')}",
        f"- State Dir: {env.get('state_dir', '')}",
        f"- Genesis UUID: {env.get('genesis_uuid', '')}",
        f"- Initialized: {env.get('initialized_at', '')}",
    ]
    return "\n".join(parts), [f"tmp/{ENV_FILENAME}"]


def build_prompt_pipeline(
    agent_slug: str,
    out_file: str | None = None,
    as_json: bool = False,
    start: str | os.PathLike[str] | None = None,
) -> dict:
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
    agent_dir = root / "agents" / agent_slug
    identity_path = agent_dir / "identity.json"
    if not identity_path.is_file():
        raise FileNotFoundError(
            f"Agent not found: {agent_slug!r} (expected {identity_path})"
        )
    identity = _read_json(identity_path)
    profile_path = agent_dir / "profile.json"
    agent_profile = _read_json(profile_path) if profile_path.is_file() else None
    control_path = root / CONTROL_PROFILE_PATH
    control_profile = _read_json(control_path) if control_path.is_file() else {
        "active_security_profile": "open",
        "security_profiles": {},
        "prompt_includes": {},
    }
    env_path = root / "tmp" / ENV_FILENAME
    env = _read_json(env_path) if env_path.is_file() else None
    knowledge_dir = env.get("knowledge_dir", "") if env else ""

    layer_1, sources_1 = _build_layer_1_identity(agent_dir, identity)
    layer_2, sources_2 = _build_layer_2_behaviour(agent_dir)
    layer_3, sources_3 = _build_layer_3_security(control_profile, agent_profile)
    layer_4, sources_4 = _build_layer_4_includes(agent_dir, control_profile, knowledge_dir, root)
    layer_5, sources_5 = _build_layer_5_vantage(env)

    layers = [layer_1, layer_2, layer_3, layer_4, layer_5]
    all_sources = sources_1 + sources_2 + sources_3 + sources_4 + sources_5
    assembled = "\n\n---\n\n".join(layers) + "\n"
    byte_length = len(assembled.encode("utf-8"))
    token_estimate = _estimate_tokens(assembled)
    content_hash = _sha256_string(assembled)
    timestamp = _utc_now_iso()
    active_security = control_profile.get("active_security_profile", "open")

    if as_json:
        result = {
            "agent_slug": agent_slug,
            "assembled_prompt": assembled,
            "byte_length": byte_length,
            "token_estimate": token_estimate,
            "content_hash": content_hash,
            "layer_count": len(layers),
            "active_security_profile": active_security,
            "sources": all_sources,
            "assembled_at": timestamp,
        }
        print(json.dumps(result, indent=2))
        return result

    if out_file:
        out_path = Path(out_file)
        if not out_path.is_absolute():
            out_path = root / out_path
    else:
        out_path = agent_dir / "assembled_system_prompt.md"

    out_path.write_text(assembled, encoding="utf-8")

    log_path = agent_dir / "observations" / "log.jsonl"
    event = {
        "event_type": "prompt_pipeline_assembled",
        "timestamp": timestamp,
        "agent_slug": agent_slug,
        "agent_id": identity.get("agent_id", ""),
        "prompt_hash": content_hash,
        "byte_length": byte_length,
        "token_estimate": token_estimate,
        "layer_count": len(layers),
        "active_security_profile": active_security,
        "output_path": str(out_path),
        "sources": all_sources,
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

    return {
        "agent_slug": agent_slug,
        "output_path": str(out_path),
        "byte_length": byte_length,
        "token_estimate": token_estimate,
        "content_hash": content_hash,
        "layer_count": len(layers),
        "active_security_profile": active_security,
        "sources": all_sources,
        "assembled_at": timestamp,
    }


def _print_result(result: dict) -> None:
    print(f"Agent: {result['agent_slug']}")
    print(f"Output: {result['output_path']}")
    print(f"Byte Length: {result['byte_length']}")
    print(f"Token Estimate: {result['token_estimate']}")
    print(f"Content Hash: {result['content_hash'][:16]}...")
    print(f"Layers: {result['layer_count']}")
    print(f"Security: {result['active_security_profile']}")
    print(f"Sources: {len(result['sources'])}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="System Prompt Extension Pipeline"
    )
    parser.add_argument("agent_slug", type=str, help="Target agent slug")
    parser.add_argument("--out-file", type=str, default=None, help="Custom output path")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output JSON")
    args = parser.parse_args(argv)

    try:
        result = build_prompt_pipeline(
            args.agent_slug, args.out_file, args.as_json
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

    if not args.as_json:
        _print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
