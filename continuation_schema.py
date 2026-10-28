#!/usr/bin/env python3
"""Canonical continuation artifacts, validation, construction, and durable writes.

This formation-owned module has no Agent Zero dependency.  Constructors are
pure; persistence is explicit and limited to caller-selected paths.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import stat
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION = "1.0.0"
SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"
SCHEMA_PATHS = {
    "intent": SCHEMA_DIR / "continuation-intent.schema.json",
    "checkpoint": SCHEMA_DIR / "continuation-checkpoint.schema.json",
    "reflex": SCHEMA_DIR / "continuation-reflex.schema.json",
}
HASH_FIELDS = {
    "intent": "intent_sha256",
    "checkpoint": "checkpoint_sha256",
    "reflex": "reflex_sha256",
}
PROHIBITED_EFFECTS = (
    "agent_zero_api_call",
    "chat_mutation",
    "deployment",
    "external_effect_replay",
    "intent_claim",
    "lease_advance",
    "model_turn",
    "system_service_change",
)
TERMINAL_STATES = frozenset({"completed", "cancelled", "blocked", "failed"})
NONTERMINAL_STATES = frozenset({"armed", "active", "awaiting_human"})
ALL_STATES = NONTERMINAL_STATES | TERMINAL_STATES
RFC3339_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


class ContinuationValidationError(ValueError):
    """A continuation artifact violates its durable contract."""


class ContinuationConflictError(ContinuationValidationError):
    """An immutable name or compare-and-swap precondition conflicts."""


def canonical_json_bytes(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ContinuationValidationError(f"value is not canonical JSON: {exc}") from exc
    return text.encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def embedded_hash(value: Mapping[str, Any], hash_field: str) -> str:
    payload = copy.deepcopy(dict(value))
    payload.pop(hash_field, None)
    return canonical_sha256(payload)


def seal_context_evidence(evidence: Mapping[str, Any]) -> dict[str, Any]:
    sealed = copy.deepcopy(dict(evidence))
    sealed["evidence_sha256"] = embedded_hash(sealed, "evidence_sha256")
    return sealed


def seal_document(document: Mapping[str, Any], kind: str) -> dict[str, Any]:
    if kind not in HASH_FIELDS:
        raise ContinuationValidationError(f"unknown continuation artifact kind: {kind!r}")
    sealed = copy.deepcopy(dict(document))
    evidence = sealed.get("context_evidence")
    if isinstance(evidence, Mapping):
        sealed["context_evidence"] = seal_context_evidence(evidence)
    hash_field = HASH_FIELDS[kind]
    sealed[hash_field] = embedded_hash(sealed, hash_field)
    return sealed


def build_context_evidence(
    *, context_id: str, observed_at: str, history_sha256: str, exists: bool = True
) -> dict[str, Any]:
    return seal_context_evidence(
        {
            "source": "formation_attestation",
            "context_id": context_id,
            "observed_at": observed_at,
            "exists": exists,
            "history_sha256": history_sha256,
        }
    )


def build_effect_boundary() -> dict[str, Any]:
    return {
        "mode": "classification_only",
        "allows_actuation": False,
        "allowed_effects": [],
        "prohibited_effects": list(PROHIBITED_EFFECTS),
    }


def build_token_snapshot(*, token_source: str, token_model: str) -> dict[str, Any]:
    return {"token_source": token_source, "token_model": token_model}


def build_retry_budget(*, maximum_attempts: int, attempts_used: int = 0) -> dict[str, Any]:
    return {"maximum_attempts": maximum_attempts, "attempts_used": attempts_used}


def build_work_snapshot(
    *,
    work_vector: str,
    git_commit: str,
    file_state: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
    subordinate_context_ids: list[str] | tuple[str, ...] = (),
    parallel_references: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
) -> dict[str, Any]:
    """Build the self-contained state needed to continue without chat recovery."""
    return {
        "work_vector": work_vector,
        "file_state": [copy.deepcopy(dict(item)) for item in file_state],
        "git_commit": git_commit,
        "subordinate_context_ids": sorted(set(subordinate_context_ids)),
        "parallel_references": [
            copy.deepcopy(dict(item))
            for item in sorted(
                parallel_references,
                key=lambda item: (
                    str(item.get("job_id", "")),
                    str(item.get("context_id", "")),
                ),
            )
        ],
    }


def build_lease(
    *,
    state: str = "unclaimed",
    holder: str | None = None,
    attempt_id: str | None = None,
    generation: int | None = None,
    boot_id: str | None = None,
    acquired_at: str | None = None,
    expires_at: str | None = None,
) -> dict[str, Any]:
    return {
        "state": state,
        "holder": holder,
        "attempt_id": attempt_id,
        "generation": generation,
        "boot_id": boot_id,
        "acquired_at": acquired_at,
        "expires_at": expires_at,
    }


def build_dispatch(
    *,
    state: str = "none",
    dispatch_id: str | None = None,
    effect_sha256: str | None = None,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Build dispatch evidence; ``unreconciled`` always blocks resumption."""
    return {
        "state": state,
        "dispatch_id": dispatch_id,
        "effect_sha256": effect_sha256,
        "observed_at": observed_at,
    }


def checkpoint_pointer(checkpoint: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "checkpoint_id": checkpoint["checkpoint_id"],
        "checkpoint_sha256": checkpoint["checkpoint_sha256"],
        "sequence": checkpoint["sequence"],
    }


def build_intent(
    *,
    intent_id: str,
    field_genesis_uuid: str,
    context_id: str,
    created_at: str,
    security_profile: str,
    required_capabilities: list[str] | tuple[str, ...],
    context_evidence: Mapping[str, Any],
    interruption_class: str,
    token_snapshot: Mapping[str, Any],
    retry_budget: Mapping[str, Any],
    work_snapshot: Mapping[str, Any],
    status: str = "armed",
    latest_checkpoint: Mapping[str, Any] | None = None,
    effect_boundary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    document = seal_document(
        {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "continuation_intent",
            "intent_id": intent_id,
            "field_genesis_uuid": field_genesis_uuid,
            "context_id": context_id,
            "created_at": created_at,
            "status": status,
            "interruption_class": interruption_class,
            "token_snapshot": copy.deepcopy(dict(token_snapshot)),
            "retry_budget": copy.deepcopy(dict(retry_budget)),
            "work_snapshot": copy.deepcopy(dict(work_snapshot)),
            "security": {
                "profile": security_profile,
                "required_capabilities": sorted(set(required_capabilities)),
            },
            "context_evidence": copy.deepcopy(dict(context_evidence)),
            "effect_boundary": copy.deepcopy(
                dict(effect_boundary) if effect_boundary is not None else build_effect_boundary()
            ),
            "latest_checkpoint": (
                copy.deepcopy(dict(latest_checkpoint))
                if latest_checkpoint is not None
                else None
            ),
        },
        "intent",
    )
    return validate_document(document, "intent")


def build_checkpoint(
    *,
    checkpoint_id: str,
    intent: Mapping[str, Any],
    recorded_at: str,
    state: str,
    lease: Mapping[str, Any],
    previous_checkpoint: Mapping[str, Any] | None = None,
    sequence: int | None = None,
    context_evidence: Mapping[str, Any] | None = None,
    dispatch: Mapping[str, Any] | None = None,
    attempts_used: int | None = None,
) -> dict[str, Any]:
    previous = (
        copy.deepcopy(dict(previous_checkpoint))
        if previous_checkpoint is not None
        else None
    )
    if sequence is None:
        sequence = 1 if previous is None else int(previous["sequence"]) + 1
    document = seal_document(
        {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "continuation_checkpoint",
            "checkpoint_id": checkpoint_id,
            "intent_id": intent["intent_id"],
            "field_genesis_uuid": intent["field_genesis_uuid"],
            "context_id": intent["context_id"],
            "recorded_at": recorded_at,
            "sequence": sequence,
            "state": state,
            "interruption_class": intent["interruption_class"],
            "token_snapshot": copy.deepcopy(intent["token_snapshot"]),
            "retry_budget": {
                "maximum_attempts": intent["retry_budget"]["maximum_attempts"],
                "attempts_used": (
                    intent["retry_budget"]["attempts_used"]
                    if attempts_used is None
                    else attempts_used
                ),
            },
            "work_snapshot": copy.deepcopy(intent["work_snapshot"]),
            "security": copy.deepcopy(intent["security"]),
            "context_evidence": copy.deepcopy(
                dict(context_evidence)
                if context_evidence is not None
                else intent["context_evidence"]
            ),
            "effect_boundary": copy.deepcopy(intent["effect_boundary"]),
            "lease": copy.deepcopy(dict(lease)),
            "dispatch": copy.deepcopy(
                dict(dispatch) if dispatch is not None else build_dispatch()
            ),
            "previous_checkpoint": previous,
        },
        "checkpoint",
    )
    return validate_document(document, "checkpoint")


def advance_intent(intent: Mapping[str, Any], checkpoint: Mapping[str, Any]) -> dict[str, Any]:
    advanced = copy.deepcopy(dict(intent))
    advanced["status"] = checkpoint["state"]
    advanced["retry_budget"] = copy.deepcopy(checkpoint["retry_budget"])
    advanced["latest_checkpoint"] = checkpoint_pointer(checkpoint)
    return seal_document(advanced, "intent")


def _schema(kind: str) -> dict[str, Any]:
    if kind not in SCHEMA_PATHS:
        raise ContinuationValidationError(f"unknown continuation artifact kind: {kind!r}")
    try:
        loaded = json.loads(SCHEMA_PATHS[kind].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContinuationValidationError(f"cannot load {kind} schema: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ContinuationValidationError(f"{kind} schema root must be an object")
    return loaded


def _resolve_ref(root_schema: Mapping[str, Any], ref: str) -> Mapping[str, Any]:
    if not ref.startswith("#/"):
        raise ContinuationValidationError(f"unsupported external schema reference: {ref}")
    current: Any = root_schema
    for token in ref[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, Mapping) or token not in current:
            raise ContinuationValidationError(f"unresolved schema reference: {ref}")
        current = current[token]
    if not isinstance(current, Mapping):
        raise ContinuationValidationError(f"schema reference is not an object: {ref}")
    return current


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "object": return isinstance(value, dict)
    if expected == "array": return isinstance(value, list)
    if expected == "string": return isinstance(value, str)
    if expected == "boolean": return isinstance(value, bool)
    if expected == "integer": return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number": return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "null": return value is None
    raise ContinuationValidationError(f"unsupported schema type: {expected!r}")


def parse_timestamp(value: str, label: str = "timestamp") -> datetime:
    if not isinstance(value, str) or RFC3339_PATTERN.fullmatch(value) is None:
        raise ContinuationValidationError(f"{label} is not valid RFC 3339 date-time")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContinuationValidationError(f"{label} is not valid RFC 3339 date-time") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ContinuationValidationError(f"{label} must include a UTC offset")
    return parsed


def _json_equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if left is None or right is None:
        return left is None and right is None
    return left == right


def _validate_format(value: str, format_name: str, path: str) -> None:
    if format_name == "uuid":
        try:
            if str(uuid.UUID(value)) != value: raise ValueError
        except (AttributeError, ValueError) as exc:
            raise ContinuationValidationError(f"{path} must be a canonical UUID") from exc
    elif format_name == "date-time":
        parse_timestamp(value, path)
    else:
        raise ContinuationValidationError(f"unsupported schema format: {format_name!r}")


def _validate_schema_value(value: Any, schema: Mapping[str, Any], root: Mapping[str, Any], path: str) -> None:
    if "$ref" in schema:
        _validate_schema_value(value, _resolve_ref(root, schema["$ref"]), root, path)
        return
    if "const" in schema and not _json_equal(value, schema["const"]):
        raise ContinuationValidationError(f"{path} must equal {schema['const']!r}")
    if "enum" in schema and not any(_json_equal(value, item) for item in schema["enum"]):
        raise ContinuationValidationError(f"{path} has unsupported value {value!r}")
    expected = schema.get("type")
    if expected is not None:
        expected_types = [expected] if isinstance(expected, str) else expected
        if not isinstance(expected_types, list) or not all(isinstance(x, str) for x in expected_types):
            raise ContinuationValidationError(f"invalid type declaration in schema at {path}")
        if not any(_matches_type(value, item) for item in expected_types):
            raise ContinuationValidationError(f"{path} must have type {' or '.join(expected_types)}")
        if value is None: return
    if isinstance(value, dict):
        required = schema.get("required", [])
        missing = sorted(set(required) - set(value))
        if missing:
            raise ContinuationValidationError(f"{path} missing required properties: {', '.join(missing)}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extras = sorted(set(value) - set(properties))
            if extras:
                raise ContinuationValidationError(f"{path} has unexpected properties: {', '.join(extras)}")
        for key, child in value.items():
            if key in properties:
                _validate_schema_value(child, properties[key], root, f"{path}.{key}")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise ContinuationValidationError(f"{path} has too few items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise ContinuationValidationError(f"{path} has too many items")
        if schema.get("uniqueItems"):
            encoded = [canonical_json_bytes(item) for item in value]
            if len(set(encoded)) != len(encoded):
                raise ContinuationValidationError(f"{path} must contain unique items")
        if "items" in schema:
            for index, item in enumerate(value):
                _validate_schema_value(item, schema["items"], root, f"{path}[{index}]")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise ContinuationValidationError(f"{path} is below its minimum")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise ContinuationValidationError(f"{path} is too short")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise ContinuationValidationError(f"{path} is too long")
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            raise ContinuationValidationError(f"{path} does not match its required pattern")
        if "format" in schema:
            _validate_format(value, schema["format"], path)


def _validate_hash(value: Mapping[str, Any], field: str, label: str) -> None:
    if value.get(field) != embedded_hash(value, field):
        raise ContinuationValidationError(f"{label} embedded hash mismatch")


def _validate_evidence(document: Mapping[str, Any], time_field: str) -> None:
    evidence = document["context_evidence"]
    _validate_hash(evidence, "evidence_sha256", "context evidence")
    if evidence["context_id"] != document["context_id"]:
        raise ContinuationValidationError("context evidence does not bind the artifact context_id")
    if parse_timestamp(evidence["observed_at"], "context_evidence.observed_at") > parse_timestamp(document[time_field], time_field):
        raise ContinuationValidationError("context evidence cannot postdate its artifact")


def _validate_common(document: Mapping[str, Any], time_field: str) -> None:
    capabilities = document["security"]["required_capabilities"]
    if capabilities != sorted(capabilities):
        raise ContinuationValidationError("required_capabilities must use stable sorted order")
    if tuple(document["effect_boundary"]["prohibited_effects"]) != PROHIBITED_EFFECTS:
        raise ContinuationValidationError("effect boundary must preserve the complete stable prohibited-effect set")
    retry = document["retry_budget"]
    if retry["attempts_used"] > retry["maximum_attempts"]:
        raise ContinuationValidationError("retry attempts cannot exceed maximum_attempts")
    subordinate_ids = document["work_snapshot"]["subordinate_context_ids"]
    if subordinate_ids != sorted(subordinate_ids):
        raise ContinuationValidationError("subordinate_context_ids must use stable sorted order")
    references = document["work_snapshot"]["parallel_references"]
    reference_order = sorted(
        references,
        key=lambda item: (str(item["job_id"]), str(item["context_id"])),
    )
    if references != reference_order:
        raise ContinuationValidationError("parallel_references must use stable job/context order")
    _validate_evidence(document, time_field)


def _validate_checkpoint_semantics(document: Mapping[str, Any]) -> None:
    lease = document["lease"]
    coordinates = ("holder", "attempt_id", "generation", "boot_id", "acquired_at", "expires_at")
    if lease["state"] in {"unclaimed", "released"}:
        if any(lease[name] is not None for name in coordinates):
            raise ContinuationValidationError(f"{lease['state']} lease coordinates must all be null")
    else:
        if any(lease[name] is None for name in coordinates):
            raise ContinuationValidationError("held lease coordinates must all be populated")
        acquired = parse_timestamp(lease["acquired_at"], "lease.acquired_at")
        expires = parse_timestamp(lease["expires_at"], "lease.expires_at")
        recorded = parse_timestamp(document["recorded_at"], "recorded_at")
        if not acquired <= recorded < expires:
            raise ContinuationValidationError("held lease must contain the checkpoint time")
    if document["state"] == "active" and lease["state"] != "held":
        raise ContinuationValidationError("active checkpoint requires a held lease")
    if document["state"] != "active" and lease["state"] == "held":
        raise ContinuationValidationError("held lease requires active checkpoint state")
    retry = document["retry_budget"]
    if retry["attempts_used"] >= retry["maximum_attempts"] and document["state"] != "awaiting_human":
        raise ContinuationValidationError("retry exhaustion requires awaiting_human state")
    previous = document["previous_checkpoint"]
    if previous is None:
        if document["sequence"] != 1:
            raise ContinuationValidationError("first checkpoint sequence must be 1")
    else:
        if previous["checkpoint_id"] == document["checkpoint_id"]:
            raise ContinuationValidationError("checkpoint cannot name itself as predecessor")
        if document["sequence"] != previous["sequence"] + 1:
            raise ContinuationValidationError("checkpoint sequence must follow predecessor sequence")
    dispatch = document["dispatch"]
    fields = ("dispatch_id", "effect_sha256", "observed_at")
    if dispatch["state"] == "none":
        if any(dispatch[name] is not None for name in fields):
            raise ContinuationValidationError("empty dispatch coordinates must all be null")
    else:
        if any(dispatch[name] is None for name in fields):
            raise ContinuationValidationError("dispatch evidence coordinates must all be populated")
        if parse_timestamp(dispatch["observed_at"], "dispatch.observed_at") > parse_timestamp(document["recorded_at"], "recorded_at"):
            raise ContinuationValidationError("dispatch evidence cannot postdate checkpoint")


def _validate_reflex_semantics(document: Mapping[str, Any]) -> None:
    protocol = document["system_protocol"]
    if protocol["text_sha256"] != canonical_sha256(protocol["text"]):
        raise ContinuationValidationError("reflex system protocol hash mismatch")
    retry = document["retry_budget"]
    if retry["attempts_used"] > retry["maximum_attempts"]:
        raise ContinuationValidationError("reflex retry attempts cannot exceed maximum_attempts")
    stage = document["stage"]
    claim = document["claim"]
    fired = document["fired"]
    event_type = document["event_type"]
    recorded = parse_timestamp(document["recorded_at"], "recorded_at")
    if stage == "request":
        if claim is not None or fired is not None or event_type is not None:
            raise ContinuationValidationError("reflex request cannot contain claim or fired evidence")
    elif stage == "claim":
        if claim is None or fired is not None or event_type is not None:
            raise ContinuationValidationError("reflex claim stage has invalid stage evidence")
        claimed = parse_timestamp(claim["claimed_at"], "claim.claimed_at")
        expires = parse_timestamp(claim["expires_at"], "claim.expires_at")
        if recorded != claimed or expires <= claimed:
            raise ContinuationValidationError("reflex claim timestamps are inconsistent")
        remaining = retry["maximum_attempts"] - retry["attempts_used"]
        if claim["attempt"] > remaining:
            raise ContinuationValidationError("reflex claim exceeds remaining retry budget")
    else:
        if claim is None or fired is None or event_type != "continuation_reflex_fired":
            raise ContinuationValidationError("fired reflex requires claim and audit evidence")
        if fired["claim_id"] != claim["claim_id"]:
            raise ContinuationValidationError("reflex fired receipt does not bind its claim")
        fired_at = parse_timestamp(fired["fired_at"], "fired.fired_at")
        claimed = parse_timestamp(claim["claimed_at"], "claim.claimed_at")
        expires = parse_timestamp(claim["expires_at"], "claim.expires_at")
        if recorded != fired_at or not claimed <= fired_at < expires:
            raise ContinuationValidationError("reflex fired time must fall inside its claim lease")


def validate_document(document: Any, kind: str) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise ContinuationValidationError(f"{kind} artifact must be a JSON object")
    schema = _schema(kind)
    _validate_schema_value(document, schema, schema, kind)
    _validate_hash(document, HASH_FIELDS[kind], kind)
    if kind == "reflex":
        _validate_reflex_semantics(document)
        return copy.deepcopy(document)
    _validate_common(document, "created_at" if kind == "intent" else "recorded_at")
    if kind == "intent":
        retry = document["retry_budget"]
        if retry["attempts_used"] >= retry["maximum_attempts"] and document["status"] != "awaiting_human":
            raise ContinuationValidationError("retry exhaustion requires awaiting_human status")
    else:
        _validate_checkpoint_semantics(document)
    return copy.deepcopy(document)


def validate_transition(
    intent: Mapping[str, Any],
    checkpoint: Mapping[str, Any],
    previous: Mapping[str, Any] | None,
) -> None:
    """Validate one checkpoint against its immutable predecessor and intent head."""
    validate_document(dict(intent), "intent")
    validate_document(dict(checkpoint), "checkpoint")
    if intent["status"] in TERMINAL_STATES:
        raise ContinuationValidationError("terminal intent is locked")
    if intent["status"] == "awaiting_human":
        raise ContinuationValidationError("awaiting_human is an authority barrier")
    for field in (
        "intent_id",
        "field_genesis_uuid",
        "context_id",
        "interruption_class",
        "token_snapshot",
        "work_snapshot",
        "security",
        "context_evidence",
        "effect_boundary",
    ):
        expected = intent[field]
        actual = checkpoint[field]
        if actual != expected:
            raise ContinuationValidationError(f"checkpoint does not preserve intent {field}")
    old_retry = intent["retry_budget"]
    new_retry = checkpoint["retry_budget"]
    if new_retry["maximum_attempts"] != old_retry["maximum_attempts"]:
        raise ContinuationValidationError("checkpoint cannot change retry maximum_attempts")
    if not old_retry["attempts_used"] <= new_retry["attempts_used"] <= old_retry["attempts_used"] + 1:
        raise ContinuationValidationError("checkpoint retry attempts must stay stable or increment once")
    latest = intent["latest_checkpoint"]
    if previous is None:
        if latest is not None or checkpoint["previous_checkpoint"] is not None:
            raise ContinuationValidationError("first checkpoint must follow an empty intent head")
        prior_state = intent["status"]
    else:
        validate_document(dict(previous), "checkpoint")
        expected_pointer = checkpoint_pointer(previous)
        if latest != expected_pointer or checkpoint["previous_checkpoint"] != expected_pointer:
            raise ContinuationValidationError("checkpoint predecessor does not match intent head")
        if parse_timestamp(checkpoint["recorded_at"], "recorded_at") <= parse_timestamp(previous["recorded_at"], "previous.recorded_at"):
            raise ContinuationValidationError("checkpoint time must strictly follow predecessor")
        if previous["state"] in TERMINAL_STATES:
            raise ContinuationValidationError("terminal checkpoint cannot have a successor")
        if previous["state"] == "awaiting_human":
            raise ContinuationValidationError("awaiting_human checkpoint is an authority barrier")
        prior_state = previous["state"]
        if prior_state == "active" and checkpoint["state"] == "active":
            old, new = previous["lease"], checkpoint["lease"]
            for field in ("holder", "attempt_id", "boot_id"):
                if new[field] != old[field]:
                    raise ContinuationValidationError(f"active lease renewal must preserve {field}")
            if new["generation"] != old["generation"] + 1:
                raise ContinuationValidationError("active lease renewal must increment generation")
            if parse_timestamp(new["expires_at"], "lease.expires_at") <= parse_timestamp(old["expires_at"], "previous.lease.expires_at"):
                raise ContinuationValidationError("active lease renewal must extend expiry")
        if previous["dispatch"]["state"] == "unreconciled":
            dispatch = checkpoint["dispatch"]
            if dispatch["state"] != "reconciled" or any(
                dispatch[name] != previous["dispatch"][name]
                for name in ("dispatch_id", "effect_sha256")
            ):
                raise ContinuationValidationError("consequential dispatch must be reconciled before progress")
    allowed = {
        "armed": ALL_STATES,
        "active": ALL_STATES,
    }
    if checkpoint["state"] not in allowed.get(prior_state, frozenset()):
        raise ContinuationValidationError(f"transition {prior_state!r} -> {checkpoint['state']!r} is not allowed")


def read_json_document(path: Path, kind: str) -> dict[str, Any]:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise ContinuationValidationError(f"cannot inspect {path}: {exc}") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ContinuationValidationError(f"artifact is not a regular non-symlink file: {path}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ContinuationValidationError(f"cannot read artifact {path}: {exc}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContinuationValidationError(f"invalid UTF-8 JSON in {path}: {exc}") from exc
    return validate_document(document, kind)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try: os.fsync(descriptor)
    finally: os.close(descriptor)


def _ensure_directory_durable(path: Path) -> None:
    missing: list[Path] = []
    current = path
    while True:
        try: metadata = current.lstat()
        except FileNotFoundError:
            missing.append(current)
            if current.parent == current:
                raise ContinuationValidationError(f"cannot establish artifact directory: {path}")
            current = current.parent
            continue
        except OSError as exc:
            raise ContinuationValidationError(f"cannot inspect artifact directory {current}: {exc}") from exc
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise ContinuationValidationError(f"artifact directory is not a real directory: {current}")
        break
    for directory in reversed(missing):
        try: os.mkdir(directory, 0o700)
        except FileExistsError:
            metadata = directory.lstat()
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
                raise ContinuationValidationError(f"artifact directory is not a real directory: {directory}")
        except OSError as exc:
            raise ContinuationValidationError(f"cannot create artifact directory {directory}: {exc}") from exc
        _fsync_directory(directory.parent)


def _canonical_payload(document: Mapping[str, Any], kind: str) -> bytes:
    return canonical_json_bytes(validate_document(dict(document), kind)) + b"\n"


def _write_temporary(path: Path, payload: bytes) -> Path:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return temporary


def atomic_write_document(path: Path, document: Mapping[str, Any], kind: str) -> None:
    payload = _canonical_payload(document, kind)
    if path.is_symlink():
        raise ContinuationValidationError(f"refusing to replace symlink: {path}")
    _ensure_directory_durable(path.parent)
    temporary = _write_temporary(path, payload)
    try:
        os.replace(temporary, path)
        os.chmod(path, 0o600)
        _fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def create_immutable_document(path: Path, document: Mapping[str, Any], kind: str) -> str:
    """Publish create-only; return ``created`` or ``identical`` without overwrite."""
    payload = _canonical_payload(document, kind)
    _ensure_directory_durable(path.parent)
    if path.is_symlink():
        raise ContinuationConflictError(f"immutable target is a symlink: {path}")
    if path.exists():
        existing = read_json_document(path, kind)
        if canonical_json_bytes(existing) + b"\n" == payload:
            return "identical"
        raise ContinuationConflictError(f"immutable target already contains different content: {path}")
    temporary = _write_temporary(path, payload)
    try:
        try:
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError:
            existing = read_json_document(path, kind)
            if canonical_json_bytes(existing) + b"\n" == payload:
                return "identical"
            raise ContinuationConflictError(f"immutable target won a conflicting race: {path}")
        os.chmod(path, 0o600)
        _fsync_directory(path.parent)
        return "created"
    finally:
        temporary.unlink(missing_ok=True)


def compare_and_swap_intent(
    path: Path,
    document: Mapping[str, Any],
    *,
    expected_intent_sha256: str,
) -> str:
    """Replace an intent only when its current embedded hash matches ``expected``."""
    updated = validate_document(dict(document), "intent")
    current = read_json_document(path, "intent")
    if current["intent_sha256"] == updated["intent_sha256"]:
        return "identical"
    if current["intent_sha256"] != expected_intent_sha256:
        raise ContinuationConflictError("intent head changed before compare-and-swap")
    atomic_write_document(path, updated, "intent")
    return "updated"
