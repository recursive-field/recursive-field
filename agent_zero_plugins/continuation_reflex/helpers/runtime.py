"""Formation validation and audit boundary for native continuation turns.

The API adapter accepts only an immutable request identifier. This module
resolves and validates the hash-bound formation artifacts, claims the request,
and builds the narrow engine request consumed by
``AgentContext.continuation_turn``. It never creates a ``UserMessage`` or enters
the normal monologue loop.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

PLUGIN_NAME = "continuation_reflex"
REQUEST_RELATIVE = Path("state/continuations/reflex/requests")
INTENT_RELATIVE = Path("state/continuations/intents")
CHECKPOINT_RELATIVE = Path("state/continuations/checkpoints")
RECEIPT_RELATIVE = Path("state/continuations/reflex/receipts")
CLAIM_RELATIVE = Path("state/continuations/reflex/claims")
TERMINAL_STATES = frozenset({"completed", "cancelled", "blocked", "failed"})

_SCAN_LOCK = threading.Lock()
_LAST_SCAN_AT = 0.0
_LAST_RESULTS: tuple["Inspection", ...] = ()


class ReflexValidationError(ValueError):
    """A continuation artifact is malformed, unsafe, or inconsistent."""


class ReflexNotFoundError(ReflexValidationError):
    """A configured field artifact or existing Agent Zero context is absent."""


class ReflexConflictError(ReflexValidationError):
    """Validated evidence currently forbids or conflicts with dispatch."""


@dataclass(frozen=True)
class Inspection:
    request_id: str
    intent_id: str
    context_id: str
    disposition: str
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "intent_id": self.intent_id,
            "context_id": self.context_id,
            "disposition": self.disposition,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class DispatchPlan:
    root: Path
    request: dict[str, Any]
    context: Any
    engine_request: dict[str, Any]
    claim: dict[str, Any] | None
    claim_disposition: str
    existing_fired: dict[str, Any] | None = None


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def embedded_hash(document: Mapping[str, Any], field: str) -> str:
    payload = dict(document)
    payload.pop(field, None)
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def _canonical_uuid(value: Any) -> bool:
    import uuid

    if not isinstance(value, str):
        return False
    try:
        return str(uuid.UUID(value)) == value
    except ValueError:
        return False


def _confined_regular_file(root: Path, path: Path) -> Path:
    root = root.resolve(strict=True)
    candidate = path.resolve(strict=True)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ReflexValidationError(f"path escapes field root: {path}") from exc
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ReflexValidationError(f"artifact is not a regular non-symlink file: {path}")
    return candidate


def _read_json(root: Path, path: Path) -> dict[str, Any]:
    candidate = _confined_regular_file(root, path)
    try:
        value = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReflexValidationError(f"cannot read JSON artifact: {path}") from exc
    if not isinstance(value, dict):
        raise ReflexValidationError(f"artifact must be a JSON object: {path}")
    return value


def _read_boot_id() -> str | None:
    try:
        value = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
    except OSError:
        return None
    return value if _canonical_uuid(value) else None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ReflexValidationError(f"{field} is invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReflexValidationError(f"{field} is invalid") from exc
    if parsed.tzinfo is None:
        raise ReflexValidationError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _seal_reflex(document: Mapping[str, Any]) -> dict[str, Any]:
    sealed = dict(document)
    sealed.pop("reflex_sha256", None)
    sealed["reflex_sha256"] = hashlib.sha256(canonical_bytes(sealed)).hexdigest()
    return sealed


def _write_atomic(path: Path, document: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(document) + b"\n"
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _create_immutable(path: Path, document: Mapping[str, Any]) -> str:
    payload = canonical_bytes(document) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        try:
            existing = path.read_bytes()
        except OSError as exc:
            raise ReflexConflictError(f"cannot read existing artifact: {path}") from exc
        if existing == payload:
            return "exists_identical"
        raise ReflexConflictError(f"immutable artifact conflict: {path}")
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise
    return "created"


def _validate_derived_binding(
    request: Mapping[str, Any], document: Mapping[str, Any], stage: str
) -> None:
    if embedded_hash(document, "reflex_sha256") != document.get("reflex_sha256"):
        raise ReflexConflictError(f"existing {stage} reflex_sha256 mismatch")
    mutable = {
        "stage",
        "event_type",
        "recorded_at",
        "claim",
        "fired",
        "reflex_sha256",
    }
    for field, expected in request.items():
        if field not in mutable and document.get(field) != expected:
            raise ReflexConflictError(f"existing {stage} request binding mismatch")
    if document.get("request_id") != request.get("request_id"):
        raise ReflexConflictError(f"existing {stage} request_id mismatch")


def _validate_claim(
    request: Mapping[str, Any], document: Mapping[str, Any], *, current_boot_id: str
) -> dict[str, Any]:
    _validate_derived_binding(request, document, "claim")
    if (
        document.get("stage") != "claim"
        or document.get("event_type") is not None
        or document.get("fired") is not None
    ):
        raise ReflexConflictError("existing claim stage is invalid")
    claim = document.get("claim")
    required = {
        "claim_id",
        "attempt",
        "adapter_instance",
        "boot_id",
        "claimed_at",
        "expires_at",
        "context_exists",
        "context_was_running",
    }
    if not isinstance(claim, dict) or set(claim) != required:
        raise ReflexConflictError("existing claim payload is invalid")
    _maximum, used = _validate_retry(request.get("retry_budget"))
    if (
        not _canonical_uuid(claim.get("claim_id"))
        or claim.get("attempt") != used + 1
        or claim.get("context_exists") is not True
        or claim.get("context_was_running") is not False
    ):
        raise ReflexConflictError("existing claim authority binding is invalid")
    if claim.get("boot_id") != current_boot_id:
        raise ReflexConflictError("existing_claim_from_old_boot")
    claimed_at = _parse_timestamp(claim.get("claimed_at"), "claimed_at")
    expires_at = _parse_timestamp(claim.get("expires_at"), "expires_at")
    if expires_at <= claimed_at:
        raise ReflexConflictError("existing claim expiry is invalid")
    if expires_at <= _utc_now():
        raise ReflexConflictError("existing_claim_expired")
    return dict(document)


def _validate_fired(
    request: Mapping[str, Any], document: Mapping[str, Any]
) -> dict[str, Any]:
    _validate_derived_binding(request, document, "fired receipt")
    if (
        document.get("stage") != "fired"
        or document.get("event_type") != "continuation_reflex_fired"
    ):
        raise ReflexConflictError("existing fired receipt stage is invalid")
    claim = document.get("claim")
    fired = document.get("fired")
    required = {
        "receipt_id",
        "claim_id",
        "turn_id",
        "fired_at",
        "injection_role",
        "maximum_new_turns",
        "user_message_sent",
        "context_exists",
        "context_was_running",
    }
    if (
        not isinstance(claim, dict)
        or not isinstance(fired, dict)
        or set(fired) != required
    ):
        raise ReflexConflictError("existing fired receipt payload is invalid")
    if (
        not _canonical_uuid(fired.get("receipt_id"))
        or fired.get("claim_id") != claim.get("claim_id")
        or fired.get("injection_role") != "system"
        or fired.get("maximum_new_turns") != 1
        or fired.get("user_message_sent") is not False
        or fired.get("context_exists") is not True
        or fired.get("context_was_running") is not False
    ):
        raise ReflexConflictError(
            "existing fired receipt authority binding is invalid"
        )
    _parse_timestamp(fired.get("fired_at"), "fired_at")
    return dict(document)


def _validate_retry(value: Any) -> tuple[int, int]:
    if not isinstance(value, dict):
        raise ReflexValidationError("retry_budget must be an object")
    maximum = value.get("maximum_attempts")
    used = value.get("attempts_used")
    if type(maximum) is not int or maximum < 1 or type(used) is not int or used < 0:
        raise ReflexValidationError("retry_budget is invalid")
    if used >= maximum:
        raise ReflexValidationError("retry_budget_exhausted")
    return maximum, used


def validate_request(document: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "artifact_type",
        "stage",
        "event_type",
        "request_id",
        "intent_id",
        "intent_sha256",
        "checkpoint",
        "context_id",
        "recorded_at",
        "interruption_class",
        "token_snapshot",
        "retry_budget",
        "work_snapshot",
        "system_protocol",
        "claim",
        "fired",
        "reflex_sha256",
    }
    if set(document) != required:
        raise ReflexValidationError("request properties do not match the reflex contract")
    if document.get("schema_version") != "1.0.0":
        raise ReflexValidationError("unsupported reflex schema_version")
    if document.get("artifact_type") != "continuation_reflex":
        raise ReflexValidationError("artifact_type is not continuation_reflex")
    if document.get("stage") != "request" or document.get("event_type") is not None:
        raise ReflexValidationError("only request-stage reflex artifacts are dispatchable")
    if document.get("claim") is not None or document.get("fired") is not None:
        raise ReflexValidationError("request already contains claim/fired evidence")
    for field in ("request_id", "intent_id"):
        if not _canonical_uuid(document.get(field)):
            raise ReflexValidationError(f"{field} is not a canonical UUID")
    for field in ("intent_sha256", "reflex_sha256"):
        value = document.get(field)
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ReflexValidationError(f"{field} is not lowercase SHA-256")
    if embedded_hash(document, "reflex_sha256") != document["reflex_sha256"]:
        raise ReflexValidationError("reflex_sha256 mismatch")
    context_id = document.get("context_id")
    if not isinstance(context_id, str) or not context_id or len(context_id) > 256:
        raise ReflexValidationError("context_id is invalid")
    if document.get("interruption_class") not in {"self_initiated", "external"}:
        raise ReflexValidationError("interruption_class is invalid")
    _validate_retry(document.get("retry_budget"))
    protocol = document.get("system_protocol")
    if not isinstance(protocol, dict):
        raise ReflexValidationError("system_protocol must be an object")
    if protocol.get("role") != "system":
        raise ReflexValidationError("system_protocol role must be system")
    if protocol.get("maximum_new_turns") != 1:
        raise ReflexValidationError("maximum_new_turns must equal one")
    if protocol.get("user_message_sent") is not False:
        raise ReflexValidationError("user_message_sent must be false")
    if protocol.get("require_existing_context") is not True:
        raise ReflexValidationError("existing context must be required")
    if protocol.get("require_idle_context") is not True:
        raise ReflexValidationError("idle context must be required")
    text = protocol.get("text")
    if not isinstance(text, str) or not text:
        raise ReflexValidationError("system_protocol text is empty")
    if hashlib.sha256(canonical_bytes(text)).hexdigest() != protocol.get("text_sha256"):
        raise ReflexValidationError("system_protocol text hash mismatch")
    return dict(document)


def _validate_intent_binding(
    root: Path,
    request: Mapping[str, Any],
    *,
    current_token_source: str,
    current_token_model: str,
) -> dict[str, Any]:
    intent_id = request["intent_id"]
    intent = _read_json(root, root / INTENT_RELATIVE / f"{intent_id}.json")
    if intent.get("artifact_type") != "continuation_intent":
        raise ReflexValidationError("bound intent artifact_type is invalid")
    if intent.get("intent_id") != intent_id:
        raise ReflexValidationError("intent_id binding mismatch")
    if embedded_hash(intent, "intent_sha256") != intent.get("intent_sha256"):
        raise ReflexValidationError("intent_sha256 mismatch")
    if intent.get("intent_sha256") != request.get("intent_sha256"):
        raise ReflexValidationError("request does not bind current intent head")
    if intent.get("context_id") != request.get("context_id"):
        raise ReflexValidationError("request context_id does not match intent")
    if intent.get("latest_checkpoint") != request.get("checkpoint"):
        raise ReflexValidationError("request checkpoint pointer does not match intent")
    if intent.get("interruption_class") != request.get("interruption_class"):
        raise ReflexValidationError("request interruption_class does not match intent")
    if intent.get("token_snapshot") != request.get("token_snapshot"):
        raise ReflexValidationError("request token_snapshot does not match intent")
    if intent.get("retry_budget") != request.get("retry_budget"):
        raise ReflexValidationError("request retry_budget does not match intent")
    if intent.get("work_snapshot") != request.get("work_snapshot"):
        raise ReflexValidationError("request work_snapshot does not match intent")
    _validate_retry(intent.get("retry_budget"))
    token = intent.get("token_snapshot")
    if not isinstance(token, dict):
        raise ReflexValidationError("intent token_snapshot is invalid")
    if intent.get("interruption_class") == "external":
        if not current_token_source or current_token_model not in {"capped", "metered"}:
            raise ReflexValidationError("current_token_snapshot_unavailable")
        if token.get("token_model") == "capped" and current_token_model == "metered":
            raise ReflexValidationError("external_capped_to_metered_drift")
    pointer = intent.get("latest_checkpoint")
    if pointer is not None:
        if not isinstance(pointer, dict) or not _canonical_uuid(pointer.get("checkpoint_id")):
            raise ReflexValidationError("checkpoint pointer is invalid")
        checkpoint = _read_json(
            root,
            root / CHECKPOINT_RELATIVE / f"{pointer['checkpoint_id']}.json",
        )
        if embedded_hash(checkpoint, "checkpoint_sha256") != checkpoint.get("checkpoint_sha256"):
            raise ReflexValidationError("checkpoint_sha256 mismatch")
        if checkpoint.get("checkpoint_sha256") != pointer.get("checkpoint_sha256"):
            raise ReflexValidationError("checkpoint pointer hash mismatch")
        lease = checkpoint.get("lease")
        if not isinstance(lease, dict):
            raise ReflexValidationError("checkpoint lease is invalid")
        if lease.get("state") == "held":
            current_boot = _read_boot_id()
            if current_boot is None or lease.get("boot_id") != current_boot:
                raise ReflexValidationError("old_boot_lease_requires_reconciliation")
            raise ReflexValidationError("held_lease_excluded")
    status = intent.get("status")
    if status == "awaiting_human":
        raise ReflexValidationError("awaiting_human_excluded")
    if status in TERMINAL_STATES:
        raise ReflexValidationError("terminal_intent_excluded")
    if status != "armed":
        raise ReflexValidationError("intent_is_not_resumable")
    return intent


def inspect_request(
    root: Path,
    request_path: Path,
    *,
    current_token_source: str = "",
    current_token_model: str = "",
    context_lookup=None,
) -> Inspection:
    """Validate one handoff and stop before claim if no safe runtime trigger exists."""
    request_id = request_path.stem
    intent_id = ""
    context_id = ""
    try:
        request = validate_request(_read_json(root, request_path))
        request_id = request["request_id"]
        intent_id = request["intent_id"]
        context_id = request["context_id"]
        _validate_intent_binding(
            root,
            request,
            current_token_source=current_token_source,
            current_token_model=current_token_model,
        )
        receipt = root / RECEIPT_RELATIVE / f"{request_id}.json"
        if receipt.exists():
            return Inspection(request_id, intent_id, context_id, "already_fired", ("receipt_exists",))
        claims = root / CLAIM_RELATIVE / request_id
        if claims.exists() and any(claims.glob("*.json")):
            return Inspection(request_id, intent_id, context_id, "claimed", ("claim_exists",))
        if context_lookup is None:
            from agent import AgentContext

            context_lookup = AgentContext.get
        context = context_lookup(context_id)
        if context is None:
            return Inspection(request_id, intent_id, context_id, "blocked", ("existing_context_not_found",))
        if context.is_running():
            return Inspection(request_id, intent_id, context_id, "blocked", ("context_already_running",))
        return Inspection(request_id, intent_id, context_id, "ready", ())
    except (OSError, ReflexValidationError) as exc:
        return Inspection(request_id, intent_id, context_id, "invalid", (str(exc),))


def _resolve_field_root(config: Mapping[str, Any]) -> Path:
    if config.get("enabled") is not True:
        raise ReflexConflictError("plugin_disabled")
    configured = str(config.get("field_root") or "").strip()
    if not configured:
        raise ReflexValidationError("field_root_not_configured")
    try:
        return Path(configured).resolve(strict=True)
    except OSError as exc:
        raise ReflexNotFoundError("field_root_unavailable") from exc


def _engine_generation(request: Mapping[str, Any]) -> int:
    pointer = request.get("checkpoint")
    if pointer is None:
        return 1
    sequence = pointer.get("sequence") if isinstance(pointer, dict) else None
    if type(sequence) is not int or sequence < 1:
        raise ReflexValidationError("checkpoint sequence is invalid")
    return sequence


def _engine_request(request: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "request_id": request["request_id"],
        "context_id": request["context_id"],
        "generation": _engine_generation(request),
        "formation_reflex_sha256": request["reflex_sha256"],
        "system_protocol": dict(request["system_protocol"]),
    }


def _claim_document(request: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
    maximum, used = _validate_retry(request["retry_budget"])
    attempt = used + 1
    if attempt > maximum:
        raise ReflexConflictError("retry_budget_exhausted")
    boot_id = _read_boot_id()
    if boot_id is None:
        raise ReflexConflictError("current_boot_id_unavailable")
    now = _utc_now()
    claim = dict(request)
    claim.update(
        stage="claim",
        recorded_at=_timestamp(now),
        claim={
            "claim_id": str(
                uuid.uuid5(
                    uuid.UUID(request["request_id"]),
                    f"continuation-reflex-claim:{attempt}",
                )
            ),
            "attempt": attempt,
            "adapter_instance": str(
                config.get("adapter_instance") or "continuation_reflex_api"
            )[:256],
            "boot_id": boot_id,
            "claimed_at": _timestamp(now),
            "expires_at": _timestamp(now + timedelta(minutes=5)),
            "context_exists": True,
            "context_was_running": False,
        },
    )
    return _seal_reflex(claim)


def _fired_document(
    claim: Mapping[str, Any], engine_result: Mapping[str, Any]
) -> dict[str, Any]:
    now = _utc_now()
    fired = dict(claim)
    fired.update(
        stage="fired",
        event_type="continuation_reflex_fired",
        recorded_at=_timestamp(now),
        fired={
            "receipt_id": str(
                uuid.uuid5(
                    uuid.UUID(claim["request_id"]),
                    "continuation-reflex-fired",
                )
            ),
            "claim_id": claim["claim"]["claim_id"],
            "turn_id": f"{engine_result['request_id']}:{engine_result['generation']}",
            "fired_at": _timestamp(now),
            "injection_role": "system",
            "maximum_new_turns": 1,
            "user_message_sent": False,
            "context_exists": True,
            "context_was_running": False,
        },
    )
    return _seal_reflex(fired)


def prepare_dispatch(
    config: Mapping[str, Any],
    request_id: str,
    *,
    context_lookup=None,
) -> DispatchPlan:
    """Formation-prevalidate and immutably claim one API dispatch."""
    if not _canonical_uuid(request_id):
        raise ReflexValidationError("request_id is not a canonical UUID")
    root = _resolve_field_root(config)
    request_path = root / REQUEST_RELATIVE / f"{request_id}.json"
    if not request_path.is_file():
        raise ReflexNotFoundError("continuation_request_not_found")
    request = validate_request(_read_json(root, request_path))
    if request["request_id"] != request_id or request_path.stem != request_id:
        raise ReflexValidationError("request filename binding mismatch")
    _validate_intent_binding(
        root,
        request,
        current_token_source=str(config.get("current_token_source") or ""),
        current_token_model=str(config.get("current_token_model") or ""),
    )
    if context_lookup is None:
        from agent import AgentContext

        context_lookup = AgentContext.get
    context = context_lookup(request["context_id"])
    if context is None:
        raise ReflexNotFoundError("existing_context_not_found")

    # Durable terminal evidence is replayable regardless of later context
    # activity; no new engine work occurs on this path.
    receipt_path = root / RECEIPT_RELATIVE / f"{request_id}.json"
    if receipt_path.exists():
        existing_fired = _validate_fired(
            request,
            _read_json(root, receipt_path),
        )
        return DispatchPlan(
            root=root,
            request=request,
            context=context,
            engine_request=_engine_request(request),
            claim=None,
            claim_disposition="not_required_already_fired",
            existing_fired=existing_fired,
        )

    boot_id = _read_boot_id()
    if boot_id is None:
        raise ReflexConflictError("current_boot_id_unavailable")
    _maximum, used = _validate_retry(request["retry_budget"])
    attempt = used + 1
    claim_path = root / CLAIM_RELATIVE / request_id / f"{attempt}.json"
    if claim_path.exists():
        # An identical claim may be retried while its own native turn is active.
        # Let the engine distinguish same-request in-progress replay from an
        # unrelated running task or a conflicting continuation.
        claim = _validate_claim(
            request,
            _read_json(root, claim_path),
            current_boot_id=boot_id,
        )
        claim_disposition = "exists_identical"
    else:
        # Initial dispatch is formation-gated on an idle context. The engine
        # repeats this check under its activity lock after the durable claim.
        if context.is_running():
            raise ReflexConflictError("context_already_running")
        claim = _claim_document(request, config)
        try:
            claim_disposition = _create_immutable(claim_path, claim)
        except ReflexConflictError:
            # A concurrent authenticated request may have won O_EXCL. Re-read
            # and accept only the exact authority binding for this request.
            claim = _validate_claim(
                request,
                _read_json(root, claim_path),
                current_boot_id=boot_id,
            )
            claim_disposition = "exists_identical"
    return DispatchPlan(
        root=root,
        request=request,
        context=context,
        engine_request=_engine_request(request),
        claim=claim,
        claim_disposition=claim_disposition,
        existing_fired=None,
    )


def record_fired(
    plan: DispatchPlan, engine_result: Mapping[str, Any]
) -> tuple[dict[str, Any], str]:
    """Write the formation-owned fired audit only for bound engine completion."""
    if (
        engine_result.get("state") != "completed"
        or engine_result.get("terminal") is not True
    ):
        raise ReflexConflictError("engine_turn_not_completed")
    expected = plan.engine_request
    if (
        engine_result.get("request_id") != expected["request_id"]
        or engine_result.get("context_id") != expected["context_id"]
        or engine_result.get("generation") != expected["generation"]
    ):
        raise ReflexConflictError("engine_receipt_request_binding_mismatch")
    engine_receipt = engine_result.get("receipt")
    if not isinstance(engine_receipt, Mapping) or (
        engine_receipt.get("request_id") != expected["request_id"]
        or engine_receipt.get("context_id") != expected["context_id"]
        or engine_receipt.get("generation") != expected["generation"]
        or engine_receipt.get("state") != "completed"
        or engine_receipt.get("terminal") is not True
        or engine_receipt.get("formation_reflex_sha256")
        != expected["formation_reflex_sha256"]
        or engine_receipt.get("protocol_text_sha256")
        != expected["system_protocol"]["text_sha256"]
    ):
        raise ReflexConflictError("engine_receipt_evidence_mismatch")
    if plan.claim is None:
        raise ReflexConflictError("formation_claim_missing")
    path = plan.root / RECEIPT_RELATIVE / f"{plan.request['request_id']}.json"
    if path.exists():
        existing = _validate_fired(plan.request, _read_json(plan.root, path))
        return existing, "exists_identical"
    fired = _fired_document(plan.claim, engine_result)
    try:
        return fired, _create_immutable(path, fired)
    except ReflexConflictError:
        existing = _validate_fired(plan.request, _read_json(plan.root, path))
        return existing, "exists_identical"


def scan_once(config: Mapping[str, Any], *, force: bool = False) -> tuple[Inspection, ...]:
    """Inspect configured requests without claiming, writing, or starting work."""
    global _LAST_SCAN_AT, _LAST_RESULTS
    if config.get("enabled") is not True:
        return ()
    field_root = str(config.get("field_root") or "").strip()
    if not field_root:
        return (Inspection("", "", "", "blocked", ("field_root_not_configured",)),)
    root = Path(field_root)
    try:
        root = root.resolve(strict=True)
    except OSError:
        return (Inspection("", "", "", "blocked", ("field_root_unavailable",)),)
    try:
        interval = max(1.0, float(config.get("scan_interval_seconds", 60)))
    except (TypeError, ValueError):
        interval = 60.0
    now = time.monotonic()
    with _SCAN_LOCK:
        if not force and now - _LAST_SCAN_AT < interval:
            return _LAST_RESULTS
        _LAST_SCAN_AT = now
        request_dir = root / REQUEST_RELATIVE
        if not request_dir.is_dir():
            _LAST_RESULTS = ()
            return ()
        results = tuple(
            inspect_request(
                root,
                path,
                current_token_source=str(config.get("current_token_source") or ""),
                current_token_model=str(config.get("current_token_model") or ""),
            )
            for path in sorted(request_dir.glob("*.json"))
        )
        _LAST_RESULTS = results
        return results
