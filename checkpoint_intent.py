#!/usr/bin/env python3
"""Explicit formation-side continuation arming and checkpoint recording.

The tool only writes formation artifacts below ``state/continuations``.  It does
not inspect chats, call Agent Zero, execute model turns, dispatch work, replay
external effects, change services, or deploy anything.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import stat
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping

sys.dont_write_bytecode = True
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from continuation_schema import (  # noqa: E402
    ContinuationConflictError,
    ContinuationValidationError,
    advance_intent,
    build_checkpoint,
    build_context_evidence,
    build_dispatch,
    build_intent,
    build_lease,
    build_retry_budget,
    build_token_snapshot,
    build_work_snapshot,
    canonical_json_bytes,
    checkpoint_pointer,
    compare_and_swap_intent,
    create_immutable_document,
    parse_timestamp,
    read_json_document,
    validate_transition,
)
from find_root import find_root  # noqa: E402
from resume_thread import (  # noqa: E402
    CONTINUATIONS_PATH,
    CONTROL_PROFILE_PATH,
    MARKER_FILENAME,
    _canonical_uuid,
    _read_plain_object,
    _safe_formation_path,
    _security_reasons,
    _validate_marker,
)

EXIT_OK = 0
EXIT_INVALID = 3
EXIT_CONFLICT = 4
EXIT_UNAVAILABLE = 5


def _resolve_root(start: str | os.PathLike[str] | None) -> Path:
    root = find_root(start)
    if root is None:
        raise FileNotFoundError("field root not found")
    return root


def _formation_inputs(root: Path) -> tuple[str, dict[str, Any]]:
    marker_path = _safe_formation_path(root, root / MARKER_FILENAME, "genesis marker")
    control_path = _safe_formation_path(root, root / CONTROL_PROFILE_PATH, "control profile")
    marker = _read_plain_object(marker_path, "genesis marker")
    control = _read_plain_object(control_path, "control profile")
    genesis_uuid = _validate_marker(marker)
    active = control.get("active_security_profile")
    profiles = control.get("security_profiles")
    if not isinstance(active, str) or not isinstance(profiles, dict):
        raise ContinuationValidationError("control profile has invalid security structure")
    record = profiles.get(active)
    if not isinstance(record, dict) or not isinstance(record.get("capabilities"), list):
        raise ContinuationValidationError("active security profile is not defined")
    return genesis_uuid, control


def _intent_path(root: Path, intent_id: str) -> Path:
    return _safe_formation_path(
        root,
        root / CONTINUATIONS_PATH / "intents" / f"{intent_id}.json",
        "intent artifact",
    )


def _checkpoint_path(root: Path, checkpoint_id: str) -> Path:
    return _safe_formation_path(
        root,
        root / CONTINUATIONS_PATH / "checkpoints" / f"{checkpoint_id}.json",
        "checkpoint artifact",
    )


@contextmanager
def _intent_lock(root: Path, intent_id: str) -> Iterator[None]:
    lock_path = _safe_formation_path(
        root,
        root / CONTINUATIONS_PATH / "locks" / f"{intent_id}.lock",
        "intent lock",
    )
    lock_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if lock_path.is_symlink():
        raise ContinuationValidationError("intent lock must not be a symlink")
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(lock_path, flags, 0o600)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ContinuationValidationError("intent lock is not a regular file")
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def arm_intent(
    *,
    start: str | os.PathLike[str] | None,
    intent_id: str,
    context_id: str,
    history_sha256: str,
    observed_at: str,
    created_at: str,
    required_capabilities: list[str],
    attest_context_exists: bool,
    interruption_class: str,
    token_source: str,
    token_model: str,
    maximum_retry_attempts: int,
    work_vector: str,
    git_commit: str,
    file_state: list[Mapping[str, Any]],
    subordinate_context_ids: list[str],
    parallel_references: list[Mapping[str, Any]],
) -> tuple[dict[str, Any], str, Path]:
    """Construct and immutably publish one explicitly armed intent."""
    if not attest_context_exists:
        raise ContinuationValidationError("positive context attestation is required")
    if not _canonical_uuid(intent_id):
        raise ContinuationValidationError("intent_id must be a canonical UUID")
    if parse_timestamp(observed_at, "observed_at") > parse_timestamp(created_at, "created_at"):
        raise ContinuationValidationError("context observation cannot postdate arming")
    root = _resolve_root(start)
    genesis_uuid, control = _formation_inputs(root)
    active = control["active_security_profile"]
    security = {"profile": active, "required_capabilities": sorted(set(required_capabilities))}
    if not security["required_capabilities"]:
        raise ContinuationValidationError("at least one required capability is required")
    reasons = _security_reasons(security, control)
    if reasons:
        raise ContinuationValidationError(
            "cannot arm under unavailable capabilities: " + ", ".join(reasons)
        )
    evidence = build_context_evidence(
        context_id=context_id,
        observed_at=observed_at,
        history_sha256=history_sha256,
        exists=True,
    )
    intent = build_intent(
        intent_id=intent_id,
        field_genesis_uuid=genesis_uuid,
        context_id=context_id,
        created_at=created_at,
        security_profile=active,
        required_capabilities=security["required_capabilities"],
        context_evidence=evidence,
        interruption_class=interruption_class,
        token_snapshot=build_token_snapshot(
            token_source=token_source,
            token_model=token_model,
        ),
        retry_budget=build_retry_budget(maximum_attempts=maximum_retry_attempts),
        work_snapshot=build_work_snapshot(
            work_vector=work_vector,
            git_commit=git_commit,
            file_state=file_state,
            subordinate_context_ids=subordinate_context_ids,
            parallel_references=parallel_references,
        ),
    )
    path = _intent_path(root, intent_id)
    disposition = create_immutable_document(path, intent, "intent")
    return intent, disposition, path


def _load_predecessor(root: Path, intent: Mapping[str, Any]) -> dict[str, Any] | None:
    pointer = intent["latest_checkpoint"]
    if pointer is None:
        return None
    previous = read_json_document(_checkpoint_path(root, pointer["checkpoint_id"]), "checkpoint")
    if checkpoint_pointer(previous) != pointer:
        raise ContinuationValidationError("intent head does not match predecessor artifact")
    return previous


def record_checkpoint(
    *,
    start: str | os.PathLike[str] | None,
    intent_id: str,
    expected_intent_sha256: str,
    checkpoint_id: str,
    recorded_at: str,
    state: str,
    lease: Mapping[str, Any],
    dispatch: Mapping[str, Any] | None = None,
    attempts_used: int | None = None,
) -> tuple[dict[str, Any], str, str, Path]:
    """Publish an immutable checkpoint and CAS-advance its intent head."""
    if not _canonical_uuid(intent_id) or not _canonical_uuid(checkpoint_id):
        raise ContinuationValidationError("intent_id and checkpoint_id must be canonical UUIDs")
    root = _resolve_root(start)
    genesis_uuid, control = _formation_inputs(root)
    intent_path = _intent_path(root, intent_id)
    checkpoint_path = _checkpoint_path(root, checkpoint_id)
    with _intent_lock(root, intent_id):
        intent = read_json_document(intent_path, "intent")
        if intent["intent_id"] != intent_id:
            raise ContinuationValidationError("intent artifact ID does not match its path")
        if intent["field_genesis_uuid"] != genesis_uuid:
            raise ContinuationValidationError("intent genesis does not match field genesis")
        if not intent["context_evidence"]["exists"]:
            raise ContinuationValidationError("intent has no positive context attestation")
        drift = _security_reasons(intent["security"], control)
        if drift:
            raise ContinuationValidationError("security posture requires reconciliation: " + ", ".join(drift))

        # Exact retry after a completed CAS: the immutable artifact and head are
        # already authoritative even though the caller still holds the old CAS token.
        if intent["latest_checkpoint"] is not None and intent["latest_checkpoint"]["checkpoint_id"] == checkpoint_id:
            existing = read_json_document(checkpoint_path, "checkpoint")
            if checkpoint_pointer(existing) != intent["latest_checkpoint"]:
                raise ContinuationConflictError("checkpoint head and immutable artifact conflict")
            requested_dispatch = dict(dispatch) if dispatch is not None else build_dispatch()
            if (
                existing["recorded_at"] != recorded_at
                or existing["state"] != state
                or existing["lease"] != dict(lease)
                or existing["dispatch"] != requested_dispatch
                or (
                    attempts_used is not None
                    and existing["retry_budget"]["attempts_used"] != attempts_used
                )
            ):
                raise ContinuationConflictError("checkpoint UUID retry has different content")
            return existing, "identical", "identical", checkpoint_path

        if intent["intent_sha256"] != expected_intent_sha256:
            raise ContinuationConflictError("intent head changed before checkpoint construction")
        previous = _load_predecessor(root, intent)
        checkpoint = build_checkpoint(
            checkpoint_id=checkpoint_id,
            intent=intent,
            recorded_at=recorded_at,
            state=state,
            lease=lease,
            previous_checkpoint=(checkpoint_pointer(previous) if previous is not None else None),
            dispatch=dispatch,
            attempts_used=attempts_used,
        )
        validate_transition(intent, checkpoint, previous)
        checkpoint_disposition = create_immutable_document(
            checkpoint_path, checkpoint, "checkpoint"
        )
        advanced = advance_intent(intent, checkpoint)
        intent_disposition = compare_and_swap_intent(
            intent_path,
            advanced,
            expected_intent_sha256=expected_intent_sha256,
        )
        return checkpoint, checkpoint_disposition, intent_disposition, checkpoint_path


def _print(value: Mapping[str, Any]) -> None:
    sys.stdout.buffer.write(canonical_json_bytes(value) + b"\n")


def _lease_from_args(args: argparse.Namespace) -> dict[str, Any]:
    if args.lease_state == "held":
        return build_lease(
            state="held",
            holder=args.lease_holder,
            attempt_id=args.attempt_id,
            generation=args.lease_generation,
            boot_id=args.boot_id,
            acquired_at=args.lease_acquired_at,
            expires_at=args.lease_expires_at,
        )
    return build_lease(state=args.lease_state)


def _dispatch_from_args(args: argparse.Namespace) -> dict[str, Any]:
    return build_dispatch(
        state=args.dispatch_state,
        dispatch_id=args.dispatch_id,
        effect_sha256=args.effect_sha256,
        observed_at=args.dispatch_observed_at,
    )


def _json_array(value: str, label: str) -> list[Any]:
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"{label} must be valid JSON: {exc}") from exc
    if not isinstance(decoded, list):
        raise argparse.ArgumentTypeError(f"{label} must be a JSON array")
    return decoded


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create formation-owned continuation artifacts")
    subparsers = parser.add_subparsers(dest="command", required=True)
    arm = subparsers.add_parser("arm", help="explicitly create one immutable armed intent")
    arm.add_argument("--intent-id", required=True)
    arm.add_argument("--context-id", required=True)
    arm.add_argument("--history-sha256", required=True)
    arm.add_argument("--observed-at", required=True)
    arm.add_argument("--created-at", required=True)
    arm.add_argument("--required-capability", action="append", required=True)
    arm.add_argument("--attest-context-exists", action="store_true", required=True)
    arm.add_argument("--interruption-class", choices=("self_initiated", "external"), required=True)
    arm.add_argument("--token-source", required=True)
    arm.add_argument("--token-model", choices=("capped", "metered"), required=True)
    arm.add_argument("--maximum-retry-attempts", type=int, default=3)
    arm.add_argument("--work-vector", required=True)
    arm.add_argument("--git-commit", required=True)
    arm.add_argument("--file-state-json", default="[]")
    arm.add_argument("--subordinate-context-id", action="append", default=[])
    arm.add_argument("--parallel-references-json", default="[]")
    arm.add_argument("--start")

    checkpoint = subparsers.add_parser("checkpoint", help="immutably record and CAS-link a checkpoint")
    checkpoint.add_argument("intent_id")
    checkpoint.add_argument("--expected-intent-sha256", required=True)
    checkpoint.add_argument("--checkpoint-id", required=True)
    checkpoint.add_argument("--recorded-at", required=True)
    checkpoint.add_argument("--state", required=True)
    checkpoint.add_argument("--lease-state", choices=("unclaimed", "held", "released"), default="unclaimed")
    checkpoint.add_argument("--lease-holder")
    checkpoint.add_argument("--attempt-id")
    checkpoint.add_argument("--lease-generation", type=int)
    checkpoint.add_argument("--boot-id")
    checkpoint.add_argument("--lease-acquired-at")
    checkpoint.add_argument("--lease-expires-at")
    checkpoint.add_argument("--dispatch-state", choices=("none", "unreconciled", "reconciled"), default="none")
    checkpoint.add_argument("--dispatch-id")
    checkpoint.add_argument("--effect-sha256")
    checkpoint.add_argument("--dispatch-observed-at")
    checkpoint.add_argument("--attempts-used", type=int)
    checkpoint.add_argument("--start")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    start = args.start or os.environ.get("FIELD_ROOT") or None
    try:
        if args.command == "arm":
            intent, disposition, path = arm_intent(
                start=start,
                intent_id=args.intent_id,
                context_id=args.context_id,
                history_sha256=args.history_sha256,
                observed_at=args.observed_at,
                created_at=args.created_at,
                required_capabilities=args.required_capability,
                attest_context_exists=args.attest_context_exists,
                interruption_class=args.interruption_class,
                token_source=args.token_source,
                token_model=args.token_model,
                maximum_retry_attempts=args.maximum_retry_attempts,
                work_vector=args.work_vector,
                git_commit=args.git_commit,
                file_state=_json_array(args.file_state_json, "--file-state-json"),
                subordinate_context_ids=args.subordinate_context_id,
                parallel_references=_json_array(
                    args.parallel_references_json,
                    "--parallel-references-json",
                ),
            )
            _print({
                "action": "arm",
                "disposition": disposition,
                "intent_id": intent["intent_id"],
                "intent_sha256": intent["intent_sha256"],
                "path": str(path),
                "schema_version": intent["schema_version"],
            })
        else:
            checkpoint, checkpoint_disposition, intent_disposition, path = record_checkpoint(
                start=start,
                intent_id=args.intent_id,
                expected_intent_sha256=args.expected_intent_sha256,
                checkpoint_id=args.checkpoint_id,
                recorded_at=args.recorded_at,
                state=args.state,
                lease=_lease_from_args(args),
                dispatch=_dispatch_from_args(args),
                attempts_used=args.attempts_used,
            )
            _print({
                "action": "checkpoint",
                "checkpoint_disposition": checkpoint_disposition,
                "checkpoint_id": checkpoint["checkpoint_id"],
                "checkpoint_sha256": checkpoint["checkpoint_sha256"],
                "intent_disposition": intent_disposition,
                "intent_id": checkpoint["intent_id"],
                "path": str(path),
                "schema_version": checkpoint["schema_version"],
                "sequence": checkpoint["sequence"],
                "state": checkpoint["state"],
            })
        return EXIT_OK
    except FileNotFoundError as exc:
        _print({"error": "unavailable", "message": str(exc)})
        return EXIT_UNAVAILABLE
    except ContinuationConflictError as exc:
        _print({"error": "conflict", "message": str(exc)})
        return EXIT_CONFLICT
    except (ContinuationValidationError, OSError) as exc:
        _print({"error": "invalid", "message": str(exc)})
        return EXIT_INVALID


if __name__ == "__main__":
    raise SystemExit(main())
