"""Fail-closed runtime boundary for continuation reflex handoffs.

Current Agent Zero exposes ``AgentContext.communicate(UserMessage(...))`` as the
supported way to start work.  Even an empty ``UserMessage`` with
``system_message`` is persisted through ``hist_add_user_message`` as a user-side
history record, and ``Agent.monologue`` is not natively bounded to one model
turn.  The requested adapter must do neither, so this plugin deliberately stops
before claim or dispatch until Agent Zero provides a trusted typed-protocol,
one-turn entrypoint.
"""

from __future__ import annotations

import hashlib
import json
import stat
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

PLUGIN_NAME = "continuation_reflex"
REQUEST_RELATIVE = Path("state/continuations/reflex/requests")
INTENT_RELATIVE = Path("state/continuations/intents")
CHECKPOINT_RELATIVE = Path("state/continuations/checkpoints")
RECEIPT_RELATIVE = Path("state/continuations/reflex/receipts")
CLAIM_RELATIVE = Path("state/continuations/reflex/claims")
TERMINAL_STATES = frozenset({"completed", "cancelled", "blocked", "failed"})
RUNTIME_TRIGGER_SUPPORTED = False
RUNTIME_TRIGGER_BLOCK = "runtime_typed_protocol_one_turn_unsupported"

_SCAN_LOCK = threading.Lock()
_LAST_SCAN_AT = 0.0
_LAST_RESULTS: tuple["Inspection", ...] = ()


class ReflexValidationError(ValueError):
    """A continuation artifact is malformed, unsafe, or inconsistent."""


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
        if not RUNTIME_TRIGGER_SUPPORTED:
            return Inspection(request_id, intent_id, context_id, "blocked", (RUNTIME_TRIGGER_BLOCK,))
        raise ReflexValidationError("runtime support flag set without an adapter implementation")
    except (OSError, ReflexValidationError) as exc:
        return Inspection(request_id, intent_id, context_id, "invalid", (str(exc),))


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
