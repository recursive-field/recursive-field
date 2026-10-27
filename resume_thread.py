#!/usr/bin/env python3
"""Read-only continuation eligibility classifier for Recursive Field.

The only supported operation is ``--dry-run``.  This script reads explicit,
formation-owned continuation artifacts and reports their state; it never scans
chats, calls Agent Zero, claims an intent, advances a lease, emits lifecycle
events, starts a model turn, or replays an effect.
"""

from __future__ import annotations

import sys

# A dry-run must not create local ``__pycache__`` artifacts while importing the
# formation helpers below.  The main script itself is not cached by Python.
sys.dont_write_bytecode = True

import argparse
import json
import os
import stat
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from continuation_schema import (  # noqa: E402
    SCHEMA_VERSION,
    TERMINAL_STATES,
    ContinuationValidationError,
    canonical_json_bytes,
    parse_timestamp,
    read_json_document,
)
from find_root import find_root  # noqa: E402

MARKER_FILENAME = ".recursive-field-root"
CONTROL_PROFILE_PATH = Path("state") / "control_profile.json"
CONTINUATIONS_PATH = Path("state") / "continuations"

EXIT_CODES = {
    "resumable": 0,
    "active": 10,
    "awaiting_human": 11,
    "terminal": 12,
    "needs_reconciliation": 20,
    "invalid": 30,
    "unavailable": 40,
}


@dataclass(frozen=True)
class Classification:
    classification: str
    intent_id: str
    reasons: tuple[str, ...]
    checkpoint_id: str | None = None

    @property
    def exit_code(self) -> int:
        return EXIT_CODES[self.classification]

    @property
    def eligible(self) -> bool:
        return self.classification == "resumable"

    def with_checkpoint(self, checkpoint_id: str | None) -> "Classification":
        return Classification(
            self.classification,
            self.intent_id,
            self.reasons,
            checkpoint_id,
        )

    def as_dict(self) -> dict[str, Any]:
        blocking_conditions = [] if self.eligible else list(self.reasons)
        return {
            "blocking_conditions": blocking_conditions,
            "checkpoint_id": self.checkpoint_id,
            "classification": self.classification,
            "eligible": self.eligible,
            "exit_code": self.exit_code,
            "intent_id": self.intent_id,
            "reasons": list(self.reasons),
            "schema_version": SCHEMA_VERSION,
            "would_claim": False,
            "would_dispatch": False,
            "would_execute": False,
            "would_write": False,
        }


def _result(classification: str, intent_id: str, *reasons: str) -> Classification:
    return Classification(classification, intent_id, tuple(sorted(set(reasons))))


def _canonical_uuid(value: str) -> bool:
    try:
        return str(uuid.UUID(value)) == value
    except (AttributeError, ValueError):
        return False


def _read_plain_object(path: Path, label: str) -> dict[str, Any]:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise ContinuationValidationError(f"cannot inspect {label}: {exc}") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ContinuationValidationError(f"{label} is not a regular non-symlink file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ContinuationValidationError(f"cannot read {label}: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise ContinuationValidationError(f"{label} is not UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise ContinuationValidationError(f"{label} contains invalid JSON") from exc
    if not isinstance(value, dict):
        raise ContinuationValidationError(f"{label} must be a JSON object")
    return value


def _safe_formation_path(root: Path, path: Path, label: str) -> Path:
    """Reject path escape and symlink traversal below the resolved field root."""
    try:
        resolved_root = root.resolve()
        relative = path.relative_to(root)
    except ValueError as exc:
        raise ContinuationValidationError(f"{label} escapes the field root") from exc
    except OSError as exc:
        raise ContinuationValidationError(f"cannot resolve {label}: {exc}") from exc
    current = resolved_root
    for component in relative.parts:
        current = current / component
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            break
        except OSError as exc:
            raise ContinuationValidationError(f"cannot inspect {label}: {exc}") from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise ContinuationValidationError(f"{label} traverses a symlink")
    try:
        resolved = path.resolve(strict=False)
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ContinuationValidationError(f"{label} resolves outside the field root") from exc
    except OSError as exc:
        raise ContinuationValidationError(f"cannot resolve {label}: {exc}") from exc
    return path


def _validate_marker(marker: Mapping[str, Any]) -> str:
    genesis = marker.get("genesis_uuid")
    if not isinstance(genesis, str) or not _canonical_uuid(genesis):
        raise ContinuationValidationError("genesis marker has no canonical genesis_uuid")
    if marker.get("schema_version") != SCHEMA_VERSION:
        raise ContinuationValidationError("genesis marker schema_version is unsupported")
    return genesis


def _security_reasons(
    expected: Mapping[str, Any], control_profile: Mapping[str, Any]
) -> tuple[str, ...]:
    active = control_profile.get("active_security_profile")
    profiles = control_profile.get("security_profiles")
    if not isinstance(active, str) or not isinstance(profiles, dict):
        raise ContinuationValidationError("control profile has invalid security structure")
    active_record = profiles.get(active)
    if not isinstance(active_record, dict):
        raise ContinuationValidationError("active security profile is not defined")
    capabilities = active_record.get("capabilities")
    if not isinstance(capabilities, list) or not all(
        isinstance(capability, str) for capability in capabilities
    ):
        raise ContinuationValidationError("active security capabilities are invalid")

    reasons: list[str] = []
    if active != expected["profile"]:
        reasons.append("security_profile_drift")
    if "all" not in capabilities:
        missing = sorted(set(expected["required_capabilities"]) - set(capabilities))
        if missing:
            reasons.append("required_capability_unavailable")
    return tuple(reasons)


def _checkpoint_path(root: Path, checkpoint_id: str) -> Path:
    return root / CONTINUATIONS_PATH / "checkpoints" / f"{checkpoint_id}.json"


def _validate_checkpoint_chain(
    root: Path,
    latest: Mapping[str, Any],
    intent: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, Classification | None]:
    pointer: Mapping[str, Any] | None = latest
    newer_recorded_at: datetime | None = None
    visited: set[str] = set()
    newest: dict[str, Any] | None = None

    while pointer is not None:
        checkpoint_id = pointer["checkpoint_id"]
        if checkpoint_id in visited:
            return None, _result("invalid", intent["intent_id"], "checkpoint_cycle")
        visited.add(checkpoint_id)
        try:
            path = _safe_formation_path(
                root, _checkpoint_path(root, checkpoint_id), "checkpoint artifact"
            )
        except ContinuationValidationError:
            return None, _result(
                "invalid", intent["intent_id"], "checkpoint_path_invalid"
            )
        try:
            checkpoint = read_json_document(path, "checkpoint")
        except FileNotFoundError:
            return None, _result(
                "unavailable", intent["intent_id"], "checkpoint_artifact_missing"
            )
        except ContinuationValidationError:
            return None, _result(
                "invalid", intent["intent_id"], "checkpoint_artifact_invalid"
            )

        if checkpoint["checkpoint_sha256"] != pointer["checkpoint_sha256"]:
            return None, _result(
                "invalid", intent["intent_id"], "checkpoint_link_hash_mismatch"
            )
        if checkpoint["checkpoint_id"] != checkpoint_id:
            return None, _result(
                "invalid", intent["intent_id"], "checkpoint_link_id_mismatch"
            )
        if checkpoint["intent_id"] != intent["intent_id"]:
            return None, _result(
                "invalid", intent["intent_id"], "checkpoint_intent_mismatch"
            )
        if checkpoint["field_genesis_uuid"] != intent["field_genesis_uuid"]:
            return None, _result(
                "invalid", intent["intent_id"], "checkpoint_genesis_mismatch"
            )
        if checkpoint["context_id"] != intent["context_id"]:
            return None, _result(
                "invalid", intent["intent_id"], "checkpoint_context_mismatch"
            )

        recorded_at = parse_timestamp(checkpoint["recorded_at"], "recorded_at")
        if newer_recorded_at is not None and recorded_at >= newer_recorded_at:
            return None, _result(
                "invalid", intent["intent_id"], "checkpoint_time_order_invalid"
            )
        if recorded_at < parse_timestamp(intent["created_at"], "created_at"):
            return None, _result(
                "invalid", intent["intent_id"], "checkpoint_predates_intent"
            )
        if newest is not None and checkpoint["state"] in TERMINAL_STATES:
            return None, _result(
                "invalid", intent["intent_id"], "checkpoint_after_terminal_state"
            )
        newer_recorded_at = recorded_at
        if newest is None:
            newest = checkpoint
        pointer = checkpoint["previous_checkpoint"]

    return newest, None


def _classify_state(
    intent: Mapping[str, Any],
    checkpoint: Mapping[str, Any] | None,
    at: datetime,
    drift_reasons: tuple[str, ...],
) -> Classification:
    intent_id = intent["intent_id"]
    if drift_reasons:
        return _result("needs_reconciliation", intent_id, *drift_reasons)

    if checkpoint is None:
        state = intent["status"]
        if state == "armed":
            return _result("resumable", intent_id, "armed_without_checkpoint")
        if state == "active":
            return _result("needs_reconciliation", intent_id, "active_without_checkpoint")
        if state == "awaiting_human":
            return _result("awaiting_human", intent_id, "explicit_human_gate")
        if state in TERMINAL_STATES:
            return _result("terminal", intent_id, f"terminal_{state}")
        return _result("invalid", intent_id, "unsupported_intent_state")

    reconciliation: list[str] = []
    state = checkpoint["state"]
    if intent["status"] != state:
        reconciliation.append("intent_checkpoint_state_drift")
    if intent["security"] != checkpoint["security"]:
        reconciliation.append("intent_checkpoint_security_drift")
    if intent["effect_boundary"] != checkpoint["effect_boundary"]:
        reconciliation.append("intent_checkpoint_effect_boundary_drift")

    lease = checkpoint["lease"]
    lease_state = lease["state"]
    held_and_current = False
    if lease_state == "held":
        acquired_at = parse_timestamp(lease["acquired_at"], "lease.acquired_at")
        expires_at = parse_timestamp(lease["expires_at"], "lease.expires_at")
        if at < acquired_at:
            reconciliation.append("lease_not_started")
        elif expires_at <= at:
            reconciliation.append("lease_expired")
        else:
            held_and_current = True

    if state == "active" and not held_and_current:
        reconciliation.append("active_state_without_current_lease")
    elif state != "active" and held_and_current:
        reconciliation.append("current_lease_conflicts_with_state")

    if reconciliation:
        return _result("needs_reconciliation", intent_id, *reconciliation)
    if state == "armed":
        return _result("resumable", intent_id, "armed_and_unclaimed")
    if state == "active":
        return _result("active", intent_id, "current_lease_held")
    if state == "awaiting_human":
        return _result("awaiting_human", intent_id, "explicit_human_gate")
    if state in TERMINAL_STATES:
        return _result("terminal", intent_id, f"terminal_{state}")
    return _result("invalid", intent_id, "unsupported_checkpoint_state")


def classify_intent(
    intent_id: str,
    *,
    start: str | os.PathLike[str] | None = None,
    at: datetime | None = None,
) -> Classification:
    """Classify one explicit continuation intent without mutating any state."""
    if not _canonical_uuid(intent_id):
        return _result("invalid", intent_id, "intent_id_not_canonical_uuid")
    if at is None:
        at = datetime.now(timezone.utc)
    elif at.tzinfo is None or at.utcoffset() is None:
        return _result("invalid", intent_id, "evaluation_time_missing_offset")

    try:
        root = find_root(start)
    except OSError:
        return _result("unavailable", intent_id, "field_root_unavailable")
    if root is None:
        return _result("unavailable", intent_id, "field_root_not_found")

    try:
        marker_path = _safe_formation_path(
            root, root / MARKER_FILENAME, "genesis marker"
        )
        marker = _read_plain_object(marker_path, "genesis marker")
        genesis_uuid = _validate_marker(marker)
    except FileNotFoundError:
        return _result("unavailable", intent_id, "genesis_marker_missing")
    except ContinuationValidationError:
        return _result("invalid", intent_id, "genesis_marker_invalid")

    try:
        intent_path = _safe_formation_path(
            root,
            root / CONTINUATIONS_PATH / "intents" / f"{intent_id}.json",
            "intent artifact",
        )
    except ContinuationValidationError:
        return _result("invalid", intent_id, "intent_path_invalid")
    try:
        intent = read_json_document(intent_path, "intent")
    except FileNotFoundError:
        return _result("unavailable", intent_id, "intent_artifact_missing")
    except ContinuationValidationError:
        return _result("invalid", intent_id, "intent_artifact_invalid")

    if intent["intent_id"] != intent_id:
        return _result("invalid", intent_id, "intent_id_link_mismatch")
    if intent["field_genesis_uuid"] != genesis_uuid:
        return _result("invalid", intent_id, "intent_genesis_mismatch")
    if not intent["context_evidence"]["exists"]:
        return _result("unavailable", intent_id, "context_not_attested")

    try:
        control_path = _safe_formation_path(
            root, root / CONTROL_PROFILE_PATH, "control profile"
        )
    except ContinuationValidationError:
        return _result("invalid", intent_id, "control_profile_path_invalid")
    try:
        control_profile = _read_plain_object(control_path, "control profile")
        security_reasons = _security_reasons(intent["security"], control_profile)
    except FileNotFoundError:
        return _result("unavailable", intent_id, "control_profile_missing")
    except ContinuationValidationError:
        return _result("invalid", intent_id, "control_profile_invalid")

    latest = intent["latest_checkpoint"]
    checkpoint: dict[str, Any] | None = None
    if latest is not None:
        checkpoint, chain_result = _validate_checkpoint_chain(root, latest, intent)
        if chain_result is not None:
            return chain_result.with_checkpoint(latest["checkpoint_id"])
        assert checkpoint is not None
        if not checkpoint["context_evidence"]["exists"]:
            return _result(
                "unavailable", intent_id, "checkpoint_context_not_attested"
            ).with_checkpoint(checkpoint["checkpoint_id"])

    result = _classify_state(intent, checkpoint, at, security_reasons)
    checkpoint_id = checkpoint["checkpoint_id"] if checkpoint is not None else None
    return result.with_checkpoint(checkpoint_id)


def _parse_at(value: str) -> datetime:
    return parse_timestamp(value, "--at")


def _stable_print(result: Classification) -> None:
    sys.stdout.buffer.write(canonical_json_bytes(result.as_dict()) + b"\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Classify a formation-owned continuation intent without actuation"
    )
    parser.add_argument("intent_id", help="canonical continuation intent UUID")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        required=True,
        help="required; read and classify only",
    )
    parser.add_argument(
        "--start",
        help="field-root discovery start (defaults to FIELD_ROOT, then cwd)",
    )
    parser.add_argument(
        "--at",
        type=_parse_at,
        help="timezone-aware ISO-8601 lease evaluation time",
    )
    args = parser.parse_args(argv)
    start = args.start or os.environ.get("FIELD_ROOT") or None
    result = classify_intent(args.intent_id, start=start, at=args.at)
    _stable_print(result)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
