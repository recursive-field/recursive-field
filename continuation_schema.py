#!/usr/bin/env python3
"""Canonical continuation-artifact validation and durable JSON writes.

This module is formation-owned.  It validates the checked-in JSON Schema
contracts plus cross-field hash, lease, context-evidence, and effect-boundary
invariants.  It does not inspect or mutate Agent Zero state.
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
}
HASH_FIELDS = {
    "intent": "intent_sha256",
    "checkpoint": "checkpoint_sha256",
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
RFC3339_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


class ContinuationValidationError(ValueError):
    """Raised when a continuation artifact violates its durable contract."""


def canonical_json_bytes(value: Any) -> bytes:
    """Return RFC-8259-compatible, deterministic UTF-8 JSON bytes."""
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
    """Hash an object after removing exactly its embedded hash field."""
    payload = copy.deepcopy(dict(value))
    payload.pop(hash_field, None)
    return canonical_sha256(payload)


def seal_context_evidence(evidence: Mapping[str, Any]) -> dict[str, Any]:
    sealed = copy.deepcopy(dict(evidence))
    sealed["evidence_sha256"] = embedded_hash(sealed, "evidence_sha256")
    return sealed


def seal_document(document: Mapping[str, Any], kind: str) -> dict[str, Any]:
    """Return a copy with canonical nested evidence and document hashes."""
    if kind not in HASH_FIELDS:
        raise ContinuationValidationError(f"unknown continuation artifact kind: {kind!r}")
    sealed = copy.deepcopy(dict(document))
    evidence = sealed.get("context_evidence")
    if isinstance(evidence, Mapping):
        sealed["context_evidence"] = seal_context_evidence(evidence)
    hash_field = HASH_FIELDS[kind]
    sealed[hash_field] = embedded_hash(sealed, hash_field)
    return sealed


def _schema(kind: str) -> dict[str, Any]:
    if kind not in SCHEMA_PATHS:
        raise ContinuationValidationError(f"unknown continuation artifact kind: {kind!r}")
    try:
        loaded = json.loads(SCHEMA_PATHS[kind].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContinuationValidationError(
            f"cannot load {kind} schema: {exc}"
        ) from exc
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
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "null":
        return value is None
    raise ContinuationValidationError(f"unsupported schema type: {expected!r}")


def parse_timestamp(value: str, label: str = "timestamp") -> datetime:
    """Parse the RFC 3339 profile used by JSON Schema ``date-time``."""
    if not isinstance(value, str) or RFC3339_PATTERN.fullmatch(value) is None:
        raise ContinuationValidationError(f"{label} is not valid RFC 3339 date-time")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContinuationValidationError(
            f"{label} is not valid RFC 3339 date-time"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ContinuationValidationError(f"{label} must include a UTC offset")
    return parsed


def _json_equal(left: Any, right: Any) -> bool:
    """Compare JSON values without Python's ``False == 0`` coercion."""
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if left is None or right is None:
        return left is None and right is None
    return left == right


def _validate_format(value: str, format_name: str, path: str) -> None:
    if format_name == "uuid":
        try:
            if str(uuid.UUID(value)) != value:
                raise ValueError
        except (AttributeError, ValueError) as exc:
            raise ContinuationValidationError(f"{path} must be a canonical UUID") from exc
    elif format_name == "date-time":
        parse_timestamp(value, path)
    else:
        raise ContinuationValidationError(f"unsupported schema format: {format_name!r}")


def _validate_schema_value(
    value: Any,
    schema: Mapping[str, Any],
    root_schema: Mapping[str, Any],
    path: str,
) -> None:
    if "$ref" in schema:
        _validate_schema_value(value, _resolve_ref(root_schema, schema["$ref"]), root_schema, path)
        return

    if "const" in schema and not _json_equal(value, schema["const"]):
        raise ContinuationValidationError(f"{path} must equal {schema['const']!r}")
    if "enum" in schema and not any(
        _json_equal(value, candidate) for candidate in schema["enum"]
    ):
        raise ContinuationValidationError(f"{path} has unsupported value {value!r}")

    expected = schema.get("type")
    if expected is not None:
        expected_types = [expected] if isinstance(expected, str) else expected
        if not isinstance(expected_types, list) or not all(
            isinstance(item, str) for item in expected_types
        ):
            raise ContinuationValidationError(f"invalid type declaration in schema at {path}")
        if not any(_matches_type(value, item) for item in expected_types):
            raise ContinuationValidationError(
                f"{path} must have type {' or '.join(expected_types)}"
            )
        if value is None:
            return

    if isinstance(value, dict):
        required = schema.get("required", [])
        missing = sorted(set(required) - set(value))
        if missing:
            raise ContinuationValidationError(
                f"{path} missing required properties: {', '.join(missing)}"
            )
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extras = sorted(set(value) - set(properties))
            if extras:
                raise ContinuationValidationError(
                    f"{path} has unexpected properties: {', '.join(extras)}"
                )
        for key, child in value.items():
            child_schema = properties.get(key)
            if child_schema is not None:
                _validate_schema_value(child, child_schema, root_schema, f"{path}.{key}")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise ContinuationValidationError(f"{path} has too few items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise ContinuationValidationError(f"{path} has too many items")
        if schema.get("uniqueItems"):
            encoded = [canonical_json_bytes(item) for item in value]
            if len(set(encoded)) != len(encoded):
                raise ContinuationValidationError(f"{path} must contain unique items")
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(value):
                _validate_schema_value(item, item_schema, root_schema, f"{path}[{index}]")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise ContinuationValidationError(f"{path} is too short")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise ContinuationValidationError(f"{path} is too long")
        pattern = schema.get("pattern")
        if pattern is not None and re.fullmatch(pattern, value) is None:
            raise ContinuationValidationError(f"{path} does not match its required pattern")
        format_name = schema.get("format")
        if format_name is not None:
            _validate_format(value, format_name, path)


def _validate_hash(value: Mapping[str, Any], field: str, label: str) -> None:
    expected = embedded_hash(value, field)
    if value.get(field) != expected:
        raise ContinuationValidationError(f"{label} embedded hash mismatch")


def _validate_evidence(document: Mapping[str, Any], artifact_time_field: str) -> None:
    evidence = document["context_evidence"]
    _validate_hash(evidence, "evidence_sha256", "context evidence")
    if evidence["context_id"] != document["context_id"]:
        raise ContinuationValidationError("context evidence does not bind the artifact context_id")
    artifact_time = parse_timestamp(document[artifact_time_field], artifact_time_field)
    observed_at = parse_timestamp(evidence["observed_at"], "context_evidence.observed_at")
    if observed_at > artifact_time:
        raise ContinuationValidationError("context evidence cannot postdate its artifact")


def _validate_common(document: Mapping[str, Any], artifact_time_field: str) -> None:
    capabilities = document["security"]["required_capabilities"]
    if capabilities != sorted(capabilities):
        raise ContinuationValidationError("required_capabilities must use stable sorted order")
    boundary = document["effect_boundary"]
    if tuple(boundary["prohibited_effects"]) != PROHIBITED_EFFECTS:
        raise ContinuationValidationError(
            "effect boundary must preserve the complete stable prohibited-effect set"
        )
    _validate_evidence(document, artifact_time_field)


def _validate_checkpoint_semantics(document: Mapping[str, Any]) -> None:
    lease = document["lease"]
    state = lease["state"]
    coordinates = ("holder", "attempt_id", "acquired_at", "expires_at")
    if state in {"unclaimed", "released"}:
        if any(lease[name] is not None for name in coordinates):
            raise ContinuationValidationError(
                f"{state} lease coordinates must all be null"
            )
    else:
        if any(lease[name] is None for name in coordinates):
            raise ContinuationValidationError("held lease coordinates must all be populated")
        acquired = parse_timestamp(lease["acquired_at"], "lease.acquired_at")
        expires = parse_timestamp(lease["expires_at"], "lease.expires_at")
        if expires <= acquired:
            raise ContinuationValidationError("lease expiry must follow acquisition")
        recorded = parse_timestamp(document["recorded_at"], "recorded_at")
        if acquired > recorded:
            raise ContinuationValidationError("lease acquisition cannot postdate checkpoint")
    previous = document["previous_checkpoint"]
    if previous is not None and previous["checkpoint_id"] == document["checkpoint_id"]:
        raise ContinuationValidationError("checkpoint cannot name itself as predecessor")


def validate_document(document: Any, kind: str) -> dict[str, Any]:
    """Validate schema, hashes, and semantic invariants; return a deep copy."""
    if not isinstance(document, dict):
        raise ContinuationValidationError(f"{kind} artifact must be a JSON object")
    schema = _schema(kind)
    _validate_schema_value(document, schema, schema, kind)
    _validate_hash(document, HASH_FIELDS[kind], kind)
    if kind == "intent":
        _validate_common(document, "created_at")
    else:
        _validate_common(document, "recorded_at")
        _validate_checkpoint_semantics(document)
    return copy.deepcopy(document)


def read_json_document(path: Path, kind: str) -> dict[str, Any]:
    """Read one regular, non-symlink JSON file and validate it."""
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
    except UnicodeDecodeError as exc:
        raise ContinuationValidationError(f"artifact is not UTF-8: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ContinuationValidationError(f"invalid JSON in {path}: {exc.msg}") from exc
    return validate_document(document, kind)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _ensure_directory_durable(path: Path) -> None:
    """Create missing ancestors and fsync each new parent directory entry."""
    missing: list[Path] = []
    current = path
    while True:
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            missing.append(current)
            parent = current.parent
            if parent == current:
                raise ContinuationValidationError(
                    f"cannot establish artifact directory: {path}"
                )
            current = parent
            continue
        except OSError as exc:
            raise ContinuationValidationError(
                f"cannot inspect artifact directory {current}: {exc}"
            ) from exc
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise ContinuationValidationError(
                f"artifact directory is not a real directory: {current}"
            )
        break

    for directory in reversed(missing):
        try:
            os.mkdir(directory, 0o700)
        except FileExistsError:
            metadata = directory.lstat()
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
                raise ContinuationValidationError(
                    f"artifact directory is not a real directory: {directory}"
                )
        except OSError as exc:
            raise ContinuationValidationError(
                f"cannot create artifact directory {directory}: {exc}"
            ) from exc
        _fsync_directory(directory.parent)


def atomic_write_document(path: Path, document: Mapping[str, Any], kind: str) -> None:
    """Validate and atomically replace an artifact with canonical JSON bytes."""
    validated = validate_document(dict(document), kind)
    if path.is_symlink():
        raise ContinuationValidationError(f"refusing to replace symlink: {path}")
    _ensure_directory_durable(path.parent)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    payload = canonical_json_bytes(validated) + b"\n"
    try:
        descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException:
            if temporary.exists():
                temporary.unlink()
            raise
        os.replace(temporary, path)
        os.chmod(path, 0o600)
        _fsync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()
