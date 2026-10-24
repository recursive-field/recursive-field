#!/usr/bin/env python3
"""Render one bounded, content-free effective-formation fixture.

The observer reads only a named JSON file beneath its repository-owned fixtures
folder and writes deterministic JSON to standard output. It does not import Agent
Zero, inspect live state, authorize operations, or mutate the observed formation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

INPUT_SCHEMA = "recursive-field/effective-formation-input/v0.2"
REPORT_SCHEMA = "recursive-field/effective-formation-report/v0.2"
IMPLEMENTATION_VERSION = "0.2.0"
FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures"

RESOURCE_KINDS = {
    "capability",
    "extension",
    "external_dependency",
    "instruction",
    "knowledge_source",
    "local_tool",
    "memory_projection",
    "obligation",
    "plugin",
    "profile",
    "prompt",
    "provider_dependency",
    "secret_reference",
    "settings",
    "skill",
    "state",
}
RESOURCE_NAMES = {
    "agent.profile",
    "agent.settings",
    "background.obligation",
    "external.service",
    "knowledge.corpus",
    "memory.retrieval",
    "model.provider",
    "observer.capability",
    "project.instructions",
    "provider.api.credentials",
    "system.main",
    "tool.access",
    "tool.policy.enforcement",
    "workspace.state",
    "bounded.inquiry",
}
SOURCE_REFS = {
    "bundled:extension:tool-policy",
    "bundled:plugin:tool-access",
    "bundled:profile:system-main",
    "framework:required",
    "fixture:external:service",
    "fixture:knowledge:corpus",
    "fixture:memory:retrieval",
    "fixture:obligation:background",
    "fixture:policy:observer",
    "fixture:profile:observer",
    "fixture:project:instructions",
    "fixture:provider:model",
    "fixture:secret-reference:provider",
    "fixture:settings:agent",
    "fixture:skill:bounded-inquiry",
    "fixture:state:workspace",
    "fixture:tool:observation",
    "project:profile:system-main",
    "project:alternate:system-main",
}
PRECEDENCE = {
    "project_profile": 10,
    "project": 20,
    "user_profile": 30,
    "plugin_profile": 40,
    "bundled_profile": 50,
    "user": 60,
    "plugin": 70,
    "bundled": 80,
    "framework_invariant": 90,
    "fixture": 100,
}
EVIDENCE_CLASSES = {
    "inaccessible",
    "sanitized_fixture",
    "source_verified",
    "unknown",
}
CONDITIONS = {"none", "satisfied", "unsatisfied", "unresolved"}
PROJECTION_STATUSES = {"projected", "not_projected", "conditional", "unknown"}
PROJECTION_SURFACES = {
    "execution_schema",
    "loaded_history",
    "model_context",
    "none",
    "retrieval_context",
    "runtime_state",
    "runtime_transport",
}
POLICY_DECISIONS = {"allow", "block", "unknown"}
POLICY_MODES = {"custom", "inherit", "invariant", "unknown"}
ENFORCEMENT_POINTS = {
    "downstream_unknown",
    "mcp_execution",
    "none",
    "pre_execution",
    "unknown",
}
OBSERVATION_REFS = {
    "context_ref": {"fixture:context:one"},
    "project_ref": {"fixture:project:one"},
    "profile_ref": {"fixture:profile:observer"},
}
UNKNOWN_CATALOG = {
    "downstream.consequence": (
        "verification",
        "No downstream side effect or post-success state was observed.",
    ),
    "extension.cache.generation": (
        "runtime",
        "The installed extension cache generation is outside this sanitized fixture.",
    ),
    "tool.argument.scope": (
        "authority",
        "A tool policy decision does not establish target or argument authority.",
    ),
}


class ObservationError(ValueError):
    """The fixture violates the bounded public-safe contract."""


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ObservationError(f"{label} must be an object")
    return value


def _array(value: Any, label: str, *, limit: int = 1000) -> list[Any]:
    if not isinstance(value, list):
        raise ObservationError(f"{label} must be an array")
    if len(value) > limit:
        raise ObservationError(f"{label} exceeds {limit} items")
    return value


def _exact_keys(value: dict[str, Any], allowed: set[str], label: str) -> None:
    extras = sorted(set(value) - allowed)
    if extras:
        raise ObservationError(f"{label} contains unsupported fields: {', '.join(extras)}")


def _choice(value: Any, choices: set[str] | dict[str, int], label: str) -> str:
    if not isinstance(value, str) or value not in choices:
        raise ObservationError(f"{label} contains an unrecognized public token")
    return value


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ObservationError(f"{label} must be a boolean")
    return value


def _timestamp(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.endswith(("Z", "+00:00", "-04:00", "-05:00")):
        raise ObservationError(f"{label} must be an RFC 3339 timestamp with an explicit offset")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ObservationError(f"{label} must be a valid RFC 3339 timestamp") from exc
    return value


def _revision(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
        raise ObservationError(f"{label} must be a 40-character lowercase Git revision")
    return value


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _implementation_fingerprint() -> str:
    return "sha256:" + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def validate_input(raw: Any) -> dict[str, Any]:
    """Validate one allowlisted, content-free observation fixture."""

    root = _object(raw, "root")
    _exact_keys(
        root,
        {"schema", "observation", "resources", "projections", "policies", "unknowns"},
        "root",
    )
    if root.get("schema") != INPUT_SCHEMA:
        raise ObservationError(f"schema must be {INPUT_SCHEMA}")

    observation = _object(root.get("observation"), "observation")
    _exact_keys(
        observation,
        {"context_ref", "project_ref", "profile_ref", "source_revision", "observed_at", "vantage"},
        "observation",
    )
    normalized_observation = {
        key: _choice(observation.get(key), choices, f"observation.{key}")
        for key, choices in OBSERVATION_REFS.items()
    }
    normalized_observation.update(
        source_revision=_revision(observation.get("source_revision"), "observation.source_revision"),
        observed_at=_timestamp(observation.get("observed_at"), "observation.observed_at"),
        vantage=_choice(observation.get("vantage"), {"sanitized_fixture"}, "observation.vantage"),
    )

    resources: list[dict[str, Any]] = []
    seen_resources: set[tuple[str, str, str]] = set()
    for index, item in enumerate(_array(root.get("resources"), "resources")):
        label = f"resources[{index}]"
        resource = _object(item, label)
        _exact_keys(
            resource,
            {"kind", "name", "source_ref", "precedence_tier", "enabled", "condition", "evidence"},
            label,
        )
        normalized = {
            "kind": _choice(resource.get("kind"), RESOURCE_KINDS, f"{label}.kind"),
            "name": _choice(resource.get("name"), RESOURCE_NAMES, f"{label}.name"),
            "source_ref": _choice(resource.get("source_ref"), SOURCE_REFS, f"{label}.source_ref"),
            "precedence_tier": _choice(resource.get("precedence_tier"), PRECEDENCE, f"{label}.precedence_tier"),
            "enabled": _boolean(resource.get("enabled"), f"{label}.enabled"),
            "condition": _choice(resource.get("condition"), CONDITIONS, f"{label}.condition"),
            "evidence": _choice(resource.get("evidence"), EVIDENCE_CLASSES, f"{label}.evidence"),
        }
        identity = (normalized["kind"], normalized["name"], normalized["source_ref"])
        if identity in seen_resources:
            raise ObservationError(f"{label} duplicates an earlier resource candidate")
        seen_resources.add(identity)
        resources.append(normalized)

    projections: list[dict[str, Any]] = []
    seen_projections: set[tuple[str, str, str]] = set()
    for index, item in enumerate(_array(root.get("projections"), "projections")):
        label = f"projections[{index}]"
        projection = _object(item, label)
        _exact_keys(projection, {"kind", "name", "surface", "status", "source_ref", "evidence"}, label)
        normalized = {
            "kind": _choice(projection.get("kind"), RESOURCE_KINDS, f"{label}.kind"),
            "name": _choice(projection.get("name"), RESOURCE_NAMES, f"{label}.name"),
            "surface": _choice(projection.get("surface"), PROJECTION_SURFACES, f"{label}.surface"),
            "status": _choice(projection.get("status"), PROJECTION_STATUSES, f"{label}.status"),
            "source_ref": _choice(projection.get("source_ref"), SOURCE_REFS, f"{label}.source_ref"),
            "evidence": _choice(projection.get("evidence"), EVIDENCE_CLASSES, f"{label}.evidence"),
        }
        identity = (normalized["kind"], normalized["name"], normalized["surface"])
        if identity in seen_projections:
            raise ObservationError(f"{label} duplicates an earlier projection")
        seen_projections.add(identity)
        projections.append(normalized)

    policies: list[dict[str, Any]] = []
    seen_capabilities: set[str] = set()
    for index, item in enumerate(_array(root.get("policies"), "policies")):
        label = f"policies[{index}]"
        policy = _object(item, label)
        _exact_keys(policy, {"capability", "decision", "mode", "enforcement", "source_ref", "evidence"}, label)
        capability = _choice(
            policy.get("capability"),
            {"local:mutation-probe", "local:observation-probe", "local:response"},
            f"{label}.capability",
        )
        if capability in seen_capabilities:
            raise ObservationError(f"{label} duplicates an earlier capability")
        seen_capabilities.add(capability)
        policies.append(
            {
                "capability": capability,
                "decision": _choice(policy.get("decision"), POLICY_DECISIONS, f"{label}.decision"),
                "mode": _choice(policy.get("mode"), POLICY_MODES, f"{label}.mode"),
                "enforcement": _choice(policy.get("enforcement"), ENFORCEMENT_POINTS, f"{label}.enforcement"),
                "source_ref": _choice(policy.get("source_ref"), SOURCE_REFS, f"{label}.source_ref"),
                "evidence": _choice(policy.get("evidence"), EVIDENCE_CLASSES, f"{label}.evidence"),
            }
        )

    unknowns: list[dict[str, str]] = []
    seen_unknowns: set[str] = set()
    for index, item in enumerate(_array(root.get("unknowns"), "unknowns", limit=100)):
        label = f"unknowns[{index}]"
        unknown = _object(item, label)
        _exact_keys(unknown, {"code"}, label)
        code = _choice(unknown.get("code"), set(UNKNOWN_CATALOG), f"{label}.code")
        if code in seen_unknowns:
            raise ObservationError(f"{label} duplicates an earlier unknown")
        seen_unknowns.add(code)
        class_, statement = UNKNOWN_CATALOG[code]
        unknowns.append({"code": code, "class": class_, "statement": statement})

    return {
        "schema": INPUT_SCHEMA,
        "observation": normalized_observation,
        "resources": resources,
        "projections": projections,
        "policies": policies,
        "unknowns": unknowns,
    }


def _candidate_state(candidate: dict[str, Any]) -> str:
    if not candidate["enabled"]:
        return "disabled"
    if candidate["condition"] == "unsatisfied":
        return "condition_unsatisfied"
    if candidate["condition"] == "unresolved":
        return "conditional_unresolved"
    if candidate["evidence"] in {"unknown", "inaccessible"}:
        return "evidence_unresolved"
    return "eligible"


def _composition(resources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for resource in resources:
        groups[(resource["kind"], resource["name"])].append(resource)

    output: list[dict[str, Any]] = []
    for (kind, name), candidates in sorted(groups.items()):
        ordered = sorted(candidates, key=lambda item: (PRECEDENCE[item["precedence_tier"]], item["source_ref"]))
        eligible = [item for item in ordered if _candidate_state(item) == "eligible"]
        if eligible:
            winning_rank = PRECEDENCE[eligible[0]["precedence_tier"]]
            winning = [item for item in eligible if PRECEDENCE[item["precedence_tier"]] == winning_rank]
        else:
            winning = []
        unresolved_candidates = [
            item
            for item in ordered
            if _candidate_state(item) in {"conditional_unresolved", "evidence_unresolved"}
        ]
        unresolved_preempts = bool(
            unresolved_candidates
            and (
                not winning
                or PRECEDENCE[unresolved_candidates[0]["precedence_tier"]]
                <= PRECEDENCE[winning[0]["precedence_tier"]]
            )
        )
        if unresolved_preempts:
            status, winner = "unknown", None
        elif len(winning) > 1:
            status, winner = "ambiguous", None
        elif len(winning) == 1:
            status, winner = "selected", winning[0]["source_ref"]
        elif unresolved_candidates:
            status, winner = "unknown", None
        else:
            status, winner = "unavailable", None

        rendered = []
        for candidate in ordered:
            state = _candidate_state(candidate)
            if status == "ambiguous" and candidate in winning:
                disposition = "ambiguous_winner"
            elif winner == candidate["source_ref"]:
                disposition = "winner"
            elif status == "unknown" and state == "eligible":
                disposition = "provisional_candidate"
            elif state == "eligible":
                disposition = "shadowed"
            else:
                disposition = state
            rendered.append({**candidate, "disposition": disposition})

        output.append(
            {
                "kind": kind,
                "name": name,
                "selection_status": status,
                "winner": winner,
                "relation": "selection_not_authority",
                "candidates": rendered,
            }
        )
    return output


def observe(raw: Any) -> dict[str, Any]:
    """Return a deterministic public-safe report for one validated fixture."""

    data = validate_input(raw)
    observation = data["observation"]
    capabilities = []
    for policy in sorted(data["policies"], key=lambda item: item["capability"]):
        capabilities.append(
            {
                **policy,
                "structurally_enforced_at_reported_boundary": policy["enforcement"]
                in {"pre_execution", "mcp_execution"},
                "authority": "not_established",
                "consequence_evidence": "not_observed",
            }
        )

    return {
        "schema": REPORT_SCHEMA,
        "boundary": {
            "mode": "allowlisted_sanitized_fixture",
            "read_only": True,
            "content_free_by_enumeration": True,
            "non_authoritative": True,
            "canonical": False,
            "mutation_performed": False,
            "runtime_observed": False,
        },
        "provenance": {
            "agent_zero_source_revision": observation["source_revision"],
            "agent_zero_revision_verification": "external_to_observer",
            "fixture_fingerprint": "sha256:" + hashlib.sha256(_canonical(data)).hexdigest(),
            "observer_implementation_version": IMPLEMENTATION_VERSION,
            "observer_implementation_fingerprint": _implementation_fingerprint(),
            "hash_limit": "sameness_or_change_not_trust_meaning_authority_or_truth",
        },
        "observation": {
            "observed_at": observation["observed_at"],
            "vantage": observation["vantage"],
            "evidence_class": "sanitized_fixture",
        },
        "coordinates": {
            "context": {"reference": observation["context_ref"], "meaning": "mutable_selector_not_identity"},
            "project": {"reference": observation["project_ref"], "meaning": "mutable_selector_not_identity"},
            "profile": {"reference": observation["profile_ref"], "meaning": "mutable_selector_not_identity"},
        },
        "selection": _composition(data["resources"]),
        "projection": sorted(data["projections"], key=lambda item: (item["kind"], item["name"], item["surface"])),
        "enforcement": capabilities,
        "authority": {"status": "not_established"},
        "consequence_verification": {"status": "not_observed"},
        "unknowns": sorted(data["unknowns"], key=lambda item: (item["class"], item["code"])),
        "claims_not_made": [
            "authority",
            "continuity",
            "identity",
            "permission",
            "readiness",
            "recovery",
            "trust",
        ],
    }


def _fixture_path(name: str) -> Path:
    if name != Path(name).name or not name.endswith(".json"):
        raise ObservationError("fixture must be a JSON filename beneath the allowlisted fixture root")
    path = (FIXTURE_ROOT / name).resolve(strict=True)
    if path.parent != FIXTURE_ROOT.resolve() or path.is_symlink():
        raise ObservationError("fixture escapes the allowlisted fixture root")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", help="allowlisted fixture filename")
    args = parser.parse_args(argv)
    try:
        path = _fixture_path(args.fixture)
        raw = json.loads(path.read_text(encoding="utf-8"))
        report = observe(raw)
    except (OSError, UnicodeError, json.JSONDecodeError, ObservationError) as exc:
        print(f"observer error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
