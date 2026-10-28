#!/usr/bin/env python3
"""Fail-closed formation handoff for a trusted continuation reflex adapter.

This module never imports Agent Zero and never starts a turn.  It creates an
immutable request that an in-process adapter may claim only after independently
verifying that the referenced context exists and is idle.  A successful adapter
records a ``continuation_reflex_fired`` receipt after injecting the request as a
trusted system protocol for at most one new turn and without a user message.
"""

from __future__ import annotations

import copy
import uuid
from pathlib import Path
from typing import Any, Mapping

from continuation_schema import (
    ContinuationConflictError,
    ContinuationValidationError,
    canonical_json_bytes,
    canonical_sha256,
    checkpoint_pointer,
    create_immutable_document,
    parse_timestamp,
    read_json_document,
    seal_document,
)
from resume_thread import CONTINUATIONS_PATH, classify_intent


class ContinuationReflexBlocked(ContinuationValidationError):
    """The formation cannot safely prepare or advance a reflex handoff."""

    def __init__(self, classification: str, exit_code: int, reasons: tuple[str, ...]):
        self.classification = classification
        self.exit_code = exit_code
        self.reasons = reasons
        super().__init__(f"continuation reflex blocked: {classification}: {', '.join(reasons)}")


def _intent_path(root: Path, intent_id: str) -> Path:
    return root / CONTINUATIONS_PATH / "intents" / f"{intent_id}.json"


def _request_path(root: Path, request_id: str) -> Path:
    return root / CONTINUATIONS_PATH / "reflex" / "requests" / f"{request_id}.json"


def _claim_path(root: Path, request_id: str, attempt: int) -> Path:
    return root / CONTINUATIONS_PATH / "reflex" / "claims" / request_id / f"{attempt}.json"


def _receipt_path(root: Path, request_id: str) -> Path:
    return root / CONTINUATIONS_PATH / "reflex" / "receipts" / f"{request_id}.json"


def _stable_request_id(intent: Mapping[str, Any]) -> str:
    pointer = intent["latest_checkpoint"]
    head = pointer["checkpoint_sha256"] if pointer is not None else intent["intent_sha256"]
    return str(uuid.uuid5(uuid.UUID(intent["intent_id"]), f"continuation-reflex:{head}"))


def _protocol_text(intent: Mapping[str, Any]) -> str:
    payload = {
        "protocol": "continuation_reflex",
        "intent_id": intent["intent_id"],
        "checkpoint": intent["latest_checkpoint"],
        "interruption_class": intent["interruption_class"],
        "retry_budget": intent["retry_budget"],
        "token_snapshot": intent["token_snapshot"],
        "work_snapshot": intent["work_snapshot"],
        "instructions": [
            "Continue from this durable work vector without reconstructing completed investigation.",
            "Reuse completed subordinate results and continue incomplete subordinate contexts by their opaque context IDs.",
            "Do not exceed one new model turn for this reflex.",
        ],
    }
    return "[PROTOCOL — CONTINUATION REFLEX]\n" + canonical_json_bytes(payload).decode("utf-8")


def build_reflex_request(intent: Mapping[str, Any]) -> dict[str, Any]:
    """Build a deterministic request for the current immutable intent head."""
    request_id = _stable_request_id(intent)
    text = _protocol_text(intent)
    recorded_at = intent["created_at"]
    if intent["latest_checkpoint"] is not None:
        # The pointer is hash-bound but has no timestamp.  The intent head hash is
        # sufficient for request identity; creation time remains deterministic.
        recorded_at = intent["created_at"]
    return seal_document(
        {
            "schema_version": intent["schema_version"],
            "artifact_type": "continuation_reflex",
            "stage": "request",
            "event_type": None,
            "request_id": request_id,
            "intent_id": intent["intent_id"],
            "intent_sha256": intent["intent_sha256"],
            "checkpoint": copy.deepcopy(intent["latest_checkpoint"]),
            "context_id": intent["context_id"],
            "recorded_at": recorded_at,
            "interruption_class": intent["interruption_class"],
            "token_snapshot": copy.deepcopy(intent["token_snapshot"]),
            "retry_budget": copy.deepcopy(intent["retry_budget"]),
            "work_snapshot": copy.deepcopy(intent["work_snapshot"]),
            "system_protocol": {
                "role": "system",
                "maximum_new_turns": 1,
                "user_message_sent": False,
                "require_existing_context": True,
                "require_idle_context": True,
                "text": text,
                "text_sha256": canonical_sha256(text),
            },
            "claim": None,
            "fired": None,
        },
        "reflex",
    )


def prepare_reflex_request(
    *,
    root: Path,
    intent_id: str,
    at,
    boot_id: str | None,
    current_token_source: str | None,
    current_token_model: str | None,
    persist: bool,
) -> tuple[dict[str, Any], str, Path]:
    """Classify and prepare an idempotent handoff without entering Agent Zero."""
    result = classify_intent(
        intent_id,
        start=root,
        at=at,
        boot_id=boot_id,
        current_token_source=current_token_source,
        current_token_model=current_token_model,
    )
    if result.classification != "resumable":
        raise ContinuationReflexBlocked(
            result.classification,
            result.exit_code,
            result.reasons,
        )
    intent = read_json_document(_intent_path(root, intent_id), "intent")
    if not intent["context_evidence"]["exists"]:
        raise ContinuationReflexBlocked("unavailable", 40, ("context_not_attested",))
    request = build_reflex_request(intent)
    path = _request_path(root, request["request_id"])
    disposition = (
        create_immutable_document(path, request, "reflex") if persist else "dry_run"
    )
    return request, disposition, path


def claim_reflex_request(
    *,
    root: Path,
    request_id: str,
    attempt: int,
    claim_id: str,
    adapter_instance: str,
    boot_id: str,
    claimed_at: str,
    expires_at: str,
    context_id: str,
    context_exists: bool,
    context_running: bool,
) -> tuple[dict[str, Any], str, Path]:
    """Create one immutable claim after adapter-side context checks."""
    request = read_json_document(_request_path(root, request_id), "reflex")
    if request["stage"] != "request" or request["request_id"] != request_id:
        raise ContinuationValidationError("reflex claim does not bind a request artifact")
    if context_id != request["context_id"] or not context_exists:
        raise ContinuationReflexBlocked("unavailable", 40, ("context_missing",))
    if context_running:
        raise ContinuationReflexBlocked("active", 10, ("context_already_running",))
    if parse_timestamp(expires_at, "expires_at") <= parse_timestamp(claimed_at, "claimed_at"):
        raise ContinuationValidationError("reflex claim expiry must follow claim time")
    claim = copy.deepcopy(request)
    claim.update(
        stage="claim",
        recorded_at=claimed_at,
        claim={
            "claim_id": claim_id,
            "attempt": attempt,
            "adapter_instance": adapter_instance,
            "boot_id": boot_id,
            "claimed_at": claimed_at,
            "expires_at": expires_at,
            "context_exists": True,
            "context_was_running": False,
        },
    )
    claim = seal_document(claim, "reflex")
    path = _claim_path(root, request_id, attempt)
    disposition = create_immutable_document(path, claim, "reflex")
    return claim, disposition, path


def record_reflex_fired(
    *,
    root: Path,
    request_id: str,
    attempt: int,
    receipt_id: str,
    turn_id: str,
    fired_at: str,
    context_id: str,
    context_exists: bool,
    context_was_running: bool,
    injection_role: str,
    maximum_new_turns: int,
    user_message_sent: bool,
) -> tuple[dict[str, Any], str, Path]:
    """Record the post-success audit receipt; never performs the injection."""
    claim = read_json_document(_claim_path(root, request_id, attempt), "reflex")
    if claim["stage"] != "claim" or claim["request_id"] != request_id:
        raise ContinuationValidationError("reflex receipt does not bind a claim artifact")
    if context_id != claim["context_id"] or not context_exists:
        raise ContinuationReflexBlocked("unavailable", 40, ("context_missing",))
    if context_was_running:
        raise ContinuationReflexBlocked("active", 10, ("context_already_running",))
    if injection_role != "system" or maximum_new_turns != 1 or user_message_sent:
        raise ContinuationValidationError(
            "reflex receipt requires system protocol, maximum_new_turns=1, and no user message"
        )
    fired = copy.deepcopy(claim)
    fired.update(
        stage="fired",
        event_type="continuation_reflex_fired",
        recorded_at=fired_at,
        fired={
            "receipt_id": receipt_id,
            "claim_id": claim["claim"]["claim_id"],
            "turn_id": turn_id,
            "fired_at": fired_at,
            "injection_role": "system",
            "maximum_new_turns": 1,
            "user_message_sent": False,
            "context_exists": True,
            "context_was_running": False,
        },
    )
    fired = seal_document(fired, "reflex")
    path = _receipt_path(root, request_id)
    disposition = create_immutable_document(path, fired, "reflex")
    return fired, disposition, path
