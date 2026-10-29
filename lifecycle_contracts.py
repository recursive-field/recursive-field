#!/usr/bin/env python3
"""Pure durable lifecycle contracts for obligations and deterministic execution.

This module defines exactly three top-level durable record types:
``turn_obligation``, ``execution_authorization``, and ``execution_result``.
It evaluates no live state and performs no I/O.  Callers must supply already
resolved formation observations to the validators.
"""

from __future__ import annotations

import copy
import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any, Mapping, Sequence

from continuation_schema import canonical_json_bytes, parse_timestamp

SCHEMA_VERSION = "1.0.0"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
OPAQUE_MAX = 256

TURN_TRANSITIONS: dict[str, frozenset[str]] = {
    "open": frozenset({"active", "waiting", "awaiting_human", "handed_off", "reconciling", "closed"}),
    "active": frozenset({"waiting", "awaiting_human", "handed_off", "reconciling", "closed"}),
    "waiting": frozenset({"active"}),
    "awaiting_human": frozenset(),
    "handed_off": frozenset(),
    "reconciling": frozenset(),
    "closed": frozenset(),
}
RESULT_TRANSITIONS: dict[str, frozenset[str]] = {
    "ready": frozenset({"claimed", "expired"}),
    "claimed": frozenset({"dispatched", "failed", "ambiguous", "expired"}),
    "dispatched": frozenset({"completed", "failed", "ambiguous"}),
    "completed": frozenset(),
    "failed": frozenset(),
    "ambiguous": frozenset(),
    "expired": frozenset(),
}
TERMINAL_RESULT_STATES = frozenset({"completed", "failed", "ambiguous", "expired"})


class LifecycleContractError(ValueError):
    """A lifecycle document or transition violates its closed contract."""


class LifecycleConflictError(LifecycleContractError):
    """A compare-and-swap, generation, or immutable binding conflicts."""


def domain_sha256(domain: str, value: Any) -> str:
    """Hash canonical JSON with an explicit Recursive Field domain prefix."""
    if not isinstance(domain, str) or not domain or len(domain) > 128:
        raise LifecycleContractError("hash domain must be a non-empty bounded string")
    prefix = f"recursive-field:{domain}:v1\0".encode("utf-8")
    return hashlib.sha256(prefix + canonical_json_bytes(value)).hexdigest()


def _sealed(document: Mapping[str, Any], hash_field: str, domain: str) -> dict[str, Any]:
    result = copy.deepcopy(dict(document))
    result.pop(hash_field, None)
    result[hash_field] = domain_sha256(domain, result)
    return result


def _exact_keys(value: Mapping[str, Any], required: set[str], label: str) -> None:
    if not isinstance(value, Mapping):
        raise LifecycleContractError(f"{label} must be an object")
    missing = sorted(required - set(value))
    extras = sorted(set(value) - required)
    if missing:
        raise LifecycleContractError(f"{label} missing fields: {', '.join(missing)}")
    if extras:
        raise LifecycleContractError(f"{label} has unexpected fields: {', '.join(extras)}")


def _bounded_string(value: Any, label: str, *, maximum: int = OPAQUE_MAX) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum or "\x00" in value:
        raise LifecycleContractError(f"{label} must be a non-empty bounded string")
    return value


def _uuid(value: Any, label: str) -> str:
    value = _bounded_string(value, label, maximum=36)
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise LifecycleContractError(f"{label} must be a UUID") from exc
    if str(parsed) != value:
        raise LifecycleContractError(f"{label} must be a canonical UUID")
    return value


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise LifecycleContractError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _positive_int(value: Any, label: str, *, allow_zero: bool = False) -> int:
    minimum = 0 if allow_zero else 1
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise LifecycleContractError(f"{label} must be an integer >= {minimum}")
    return value


def _timestamp(value: Any, label: str) -> datetime:
    try:
        return parse_timestamp(value, label)
    except ValueError as exc:
        raise LifecycleContractError(str(exc)) from exc


def _relative_path(value: Any, label: str) -> str:
    value = _bounded_string(value, label, maximum=1024)
    path = PurePosixPath(value)
    if path.is_absolute() or value in {".", ".."} or ".." in path.parts:
        raise LifecycleContractError(f"{label} must be relative to the discovered field root")
    return value


def _json_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise LifecycleContractError(f"{label} must be a JSON object")
    copied = copy.deepcopy(dict(value))
    canonical_json_bytes(copied)
    return copied


def _validate_evidence_descriptor(evidence: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(evidence, Mapping):
        raise LifecycleContractError("evidence descriptor must be an object")
    evidence_type = evidence.get("evidence_type")
    if evidence_type == "file_exists":
        _exact_keys(evidence, {"evidence_type", "path", "expected_exists"}, "file_exists evidence")
        _relative_path(evidence["path"], "evidence.path")
        if evidence["expected_exists"] is not True:
            raise LifecycleContractError("file_exists evidence requires expected_exists=true")
    elif evidence_type == "sha256_match":
        _exact_keys(evidence, {"evidence_type", "path", "expected_sha256"}, "sha256_match evidence")
        _relative_path(evidence["path"], "evidence.path")
        _sha256(evidence["expected_sha256"], "evidence.expected_sha256")
    elif evidence_type == "ledger_entry_present":
        _exact_keys(
            evidence,
            {"evidence_type", "ledger_path", "entry_id", "entry_sha256"},
            "ledger_entry_present evidence",
        )
        _relative_path(evidence["ledger_path"], "evidence.ledger_path")
        _bounded_string(evidence["entry_id"], "evidence.entry_id")
        _sha256(evidence["entry_sha256"], "evidence.entry_sha256")
    else:
        raise LifecycleContractError(f"unsupported evidence_type: {evidence_type!r}")
    return copy.deepcopy(dict(evidence))


def validate_evidence_descriptors(values: Any, *, require_nonempty: bool) -> tuple[dict[str, Any], ...]:
    if not isinstance(values, (list, tuple)):
        raise LifecycleContractError("evidence descriptors must be an array")
    if require_nonempty and not values:
        raise LifecycleContractError("at least one evidence descriptor is required")
    validated = tuple(_validate_evidence_descriptor(item) for item in values)
    encodings = [canonical_json_bytes(item) for item in validated]
    if encodings != sorted(encodings):
        raise LifecycleContractError("evidence descriptors must use canonical sorted order")
    if len(set(encodings)) != len(encodings):
        raise LifecycleContractError("evidence descriptors must be unique")
    return validated


def _closure_evidence(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise LifecycleContractError("closure_evidence must be an object or null")
    kind = value.get("evidence_type")
    variants = {
        "terminal_response_emitted": {"evidence_type", "message_ref", "persisted_at", "delivery_claimed", "human_observation_claimed"},
        "checkpoint_planted": {"evidence_type", "checkpoint_id", "checkpoint_sha256", "planted_at"},
        "human_gate_reached": {"evidence_type", "gate_id", "reason_code", "reached_at", "human_observation_claimed"},
        "handed_off_to_intent": {"evidence_type", "intent_id", "checkpoint_id", "checkpoint_sha256", "handed_off_at"},
        "reconciliation_claimed": {"evidence_type", "claim_id", "execution_result_id", "claimed_at"},
    }
    if kind not in variants:
        raise LifecycleContractError(f"unsupported closure evidence type: {kind!r}")
    _exact_keys(value, variants[kind], f"{kind} closure evidence")
    time_fields = {
        "terminal_response_emitted": "persisted_at",
        "checkpoint_planted": "planted_at",
        "human_gate_reached": "reached_at",
        "handed_off_to_intent": "handed_off_at",
        "reconciliation_claimed": "claimed_at",
    }
    _timestamp(value[time_fields[kind]], f"closure_evidence.{time_fields[kind]}")
    if kind == "terminal_response_emitted":
        _bounded_string(value["message_ref"], "closure_evidence.message_ref")
        if value["delivery_claimed"] is not False or value["human_observation_claimed"] is not False:
            raise LifecycleContractError("message persistence cannot claim delivery or human observation")
    elif kind == "checkpoint_planted":
        _uuid(value["checkpoint_id"], "closure_evidence.checkpoint_id")
        _sha256(value["checkpoint_sha256"], "closure_evidence.checkpoint_sha256")
    elif kind == "human_gate_reached":
        _uuid(value["gate_id"], "closure_evidence.gate_id")
        _bounded_string(value["reason_code"], "closure_evidence.reason_code", maximum=128)
        if value["human_observation_claimed"] is not False:
            raise LifecycleContractError("human gate persistence cannot claim human observation")
    elif kind == "handed_off_to_intent":
        _uuid(value["intent_id"], "closure_evidence.intent_id")
        _uuid(value["checkpoint_id"], "closure_evidence.checkpoint_id")
        _sha256(value["checkpoint_sha256"], "closure_evidence.checkpoint_sha256")
    else:
        _uuid(value["claim_id"], "closure_evidence.claim_id")
        _uuid(value["execution_result_id"], "closure_evidence.execution_result_id")
    return copy.deepcopy(dict(value))


@dataclass(frozen=True)
class TurnObligation:
    obligation_id: str
    field_genesis_uuid: str
    context_id: str
    intent_id: str
    checkpoint_id: str
    checkpoint_sha256: str
    generation: int
    phase_generation: int
    advance_source: str
    state: str
    turn_closed: bool
    responsibility_state: str
    objective_status: str
    closure_evidence: Mapping[str, Any] | None
    recorded_at: str
    previous_record_sha256: str | None
    turn_obligation_sha256: str

    def to_document(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_type": "turn_obligation",
            "obligation_id": self.obligation_id,
            "field_genesis_uuid": self.field_genesis_uuid,
            "context_id": self.context_id,
            "intent_id": self.intent_id,
            "checkpoint_id": self.checkpoint_id,
            "checkpoint_sha256": self.checkpoint_sha256,
            "generation": self.generation,
            "phase_generation": self.phase_generation,
            "advance_source": self.advance_source,
            "state": self.state,
            "turn_closed": self.turn_closed,
            "responsibility_state": self.responsibility_state,
            "objective_status": self.objective_status,
            "closure_evidence": copy.deepcopy(dict(self.closure_evidence)) if self.closure_evidence is not None else None,
            "recorded_at": self.recorded_at,
            "previous_record_sha256": self.previous_record_sha256,
            "turn_obligation_sha256": self.turn_obligation_sha256,
        }

    @classmethod
    def from_document(cls, document: Mapping[str, Any]) -> "TurnObligation":
        validated = validate_turn_obligation(document)
        return cls(**{key: validated[key] for key in cls.__dataclass_fields__})


def build_turn_obligation(
    *,
    obligation_id: str,
    field_genesis_uuid: str,
    context_id: str,
    intent_id: str,
    checkpoint_id: str,
    checkpoint_sha256: str,
    recorded_at: str,
) -> TurnObligation:
    document = _sealed(
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "turn_obligation",
            "obligation_id": obligation_id,
            "field_genesis_uuid": field_genesis_uuid,
            "context_id": context_id,
            "intent_id": intent_id,
            "checkpoint_id": checkpoint_id,
            "checkpoint_sha256": checkpoint_sha256,
            "generation": 1,
            "phase_generation": 0,
            "advance_source": "user_ingress",
            "state": "open",
            "turn_closed": False,
            "responsibility_state": "retained",
            "objective_status": "incomplete",
            "closure_evidence": None,
            "recorded_at": recorded_at,
            "previous_record_sha256": None,
        },
        "turn_obligation_sha256",
        "turn-obligation",
    )
    return TurnObligation.from_document(document)


def advance_turn_obligation(
    previous: TurnObligation | Mapping[str, Any],
    *,
    state: str,
    recorded_at: str,
    advance_source: str,
    closure_evidence: Mapping[str, Any] | None = None,
    objective_status: str = "incomplete",
) -> TurnObligation:
    old = previous.to_document() if isinstance(previous, TurnObligation) else validate_turn_obligation(previous)
    semantics = {
        "open": (False, "retained"),
        "active": (False, "retained"),
        "waiting": (True, "retained"),
        "awaiting_human": (True, "awaiting_human"),
        "handed_off": (True, "handed_off"),
        "reconciling": (True, "reconciliation"),
        "closed": (True, "none"),
    }
    if state not in semantics:
        raise LifecycleContractError(f"unsupported turn state: {state!r}")
    turn_closed, responsibility = semantics[state]
    phase_generation = old["phase_generation"] + (1 if advance_source == "protocol_reflex" else 0)
    document = _sealed(
        {
            **{key: old[key] for key in ("schema_version", "record_type", "obligation_id", "field_genesis_uuid", "context_id", "intent_id", "checkpoint_id", "checkpoint_sha256")},
            "generation": old["generation"] + 1,
            "phase_generation": phase_generation,
            "advance_source": advance_source,
            "state": state,
            "turn_closed": turn_closed,
            "responsibility_state": responsibility,
            "objective_status": objective_status,
            "closure_evidence": copy.deepcopy(dict(closure_evidence)) if closure_evidence is not None else None,
            "recorded_at": recorded_at,
            "previous_record_sha256": old["turn_obligation_sha256"],
        },
        "turn_obligation_sha256",
        "turn-obligation",
    )
    validate_turn_transition(old, document)
    return TurnObligation.from_document(document)


def validate_turn_obligation(document: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version", "record_type", "obligation_id", "field_genesis_uuid", "context_id", "intent_id",
        "checkpoint_id", "checkpoint_sha256", "generation", "phase_generation", "advance_source", "state",
        "turn_closed", "responsibility_state", "objective_status", "closure_evidence", "recorded_at",
        "previous_record_sha256", "turn_obligation_sha256",
    }
    _exact_keys(document, required, "turn_obligation")
    if document["schema_version"] != SCHEMA_VERSION or document["record_type"] != "turn_obligation":
        raise LifecycleContractError("turn obligation tag/version mismatch")
    for field in ("obligation_id", "field_genesis_uuid", "intent_id", "checkpoint_id"):
        _uuid(document[field], field)
    _bounded_string(document["context_id"], "context_id")
    _sha256(document["checkpoint_sha256"], "checkpoint_sha256")
    generation = _positive_int(document["generation"], "generation")
    _positive_int(document["phase_generation"], "phase_generation", allow_zero=True)
    if document["advance_source"] not in {"user_ingress", "protocol_reflex", "deterministic_policy", "human"}:
        raise LifecycleContractError("unsupported advance_source")
    state = document["state"]
    if state not in TURN_TRANSITIONS:
        raise LifecycleContractError("unsupported turn state")
    if document["objective_status"] not in {"incomplete", "completed", "cancelled"}:
        raise LifecycleContractError("unsupported objective_status")
    if document["responsibility_state"] not in {"retained", "awaiting_human", "handed_off", "reconciliation", "none"}:
        raise LifecycleContractError("unsupported responsibility_state")
    if not isinstance(document["turn_closed"], bool):
        raise LifecycleContractError("turn_closed must be boolean")
    evidence = _closure_evidence(document["closure_evidence"])
    recorded_at = _timestamp(document["recorded_at"], "recorded_at")
    if generation == 1:
        if document["previous_record_sha256"] is not None:
            raise LifecycleContractError("initial obligation cannot name a predecessor")
        if document["phase_generation"] != 0 or document["advance_source"] != "user_ingress" or state != "open":
            raise LifecycleContractError("initial obligation must be open user ingress at phase_generation 0")
    else:
        _sha256(document["previous_record_sha256"], "previous_record_sha256")
    expected = {
        "open": (False, "retained", None),
        "active": (False, "retained", None),
        "waiting": (True, "retained", "checkpoint_planted"),
        "awaiting_human": (True, "awaiting_human", "human_gate_reached"),
        "handed_off": (True, "handed_off", "handed_off_to_intent"),
        "reconciling": (True, "reconciliation", "reconciliation_claimed"),
        "closed": (True, "none", "terminal_response_emitted"),
    }[state]
    evidence_type = evidence["evidence_type"] if evidence is not None else None
    if (document["turn_closed"], document["responsibility_state"], evidence_type) != expected:
        raise LifecycleContractError("turn state, closure, responsibility, and evidence are inconsistent")
    if evidence is not None:
        evidence_time_field = {
            "terminal_response_emitted": "persisted_at",
            "checkpoint_planted": "planted_at",
            "human_gate_reached": "reached_at",
            "handed_off_to_intent": "handed_off_at",
            "reconciliation_claimed": "claimed_at",
        }[evidence_type]
        if _timestamp(evidence[evidence_time_field], f"closure_evidence.{evidence_time_field}") > recorded_at:
            raise LifecycleContractError("closure evidence cannot postdate its obligation record")
        if evidence_type == "checkpoint_planted" and (
            evidence["checkpoint_id"] != document["checkpoint_id"]
            or evidence["checkpoint_sha256"] != document["checkpoint_sha256"]
        ):
            raise LifecycleContractError("checkpoint closure evidence must bind the obligation checkpoint")
        if evidence_type == "handed_off_to_intent" and (
            evidence["intent_id"] != document["intent_id"]
            or evidence["checkpoint_id"] != document["checkpoint_id"]
            or evidence["checkpoint_sha256"] != document["checkpoint_sha256"]
        ):
            raise LifecycleContractError("handoff evidence must bind the obligation intent and checkpoint")
    if state != "closed" and document["objective_status"] != "incomplete":
        raise LifecycleContractError("only a closed turn may declare objective completion or cancellation")
    expected_hash = domain_sha256("turn-obligation", {key: copy.deepcopy(value) for key, value in document.items() if key != "turn_obligation_sha256"})
    if document["turn_obligation_sha256"] != expected_hash:
        raise LifecycleContractError("turn obligation hash mismatch")
    return copy.deepcopy(dict(document))


def validate_turn_transition(previous: Mapping[str, Any], current: Mapping[str, Any]) -> None:
    old = validate_turn_obligation(previous)
    new = validate_turn_obligation(current)
    immutable = ("obligation_id", "field_genesis_uuid", "context_id", "intent_id", "checkpoint_id", "checkpoint_sha256")
    if any(old[field] != new[field] for field in immutable):
        raise LifecycleConflictError("turn transition changed immutable identity")
    if new["generation"] != old["generation"] + 1 or new["previous_record_sha256"] != old["turn_obligation_sha256"]:
        raise LifecycleConflictError("turn transition violates strict CAS generation")
    if _timestamp(new["recorded_at"], "recorded_at") <= _timestamp(old["recorded_at"], "previous.recorded_at"):
        raise LifecycleContractError("turn transition time must strictly increase")
    if new["state"] not in TURN_TRANSITIONS[old["state"]]:
        raise LifecycleContractError(f"turn transition {old['state']} -> {new['state']} is not allowed")
    if new["advance_source"] == "protocol_reflex":
        if old["state"] != "waiting" or new["state"] != "active":
            raise LifecycleContractError("protocol_reflex may only advance a waiting obligation")
        if new["phase_generation"] != old["phase_generation"] + 1:
            raise LifecycleConflictError("protocol_reflex must increment phase_generation exactly once")
    elif new["phase_generation"] != old["phase_generation"]:
        raise LifecycleConflictError("non-reflex transition cannot change phase_generation")


@dataclass(frozen=True)
class DeterministicAdapterSpec:
    adapter_id: str
    adapter_version: str
    effect_classes: tuple[str, ...]
    deterministic: bool = True

    @property
    def registry_entry_sha256(self) -> str:
        return domain_sha256(
            "deterministic-adapter-registry-entry",
            {
                "adapter_id": self.adapter_id,
                "adapter_version": self.adapter_version,
                "effect_classes": list(self.effect_classes),
                "deterministic": self.deterministic,
            },
        )


MVP_ADAPTER_REGISTRY_VERSION = "1.0.0"
MVP_ADAPTER_REGISTRY: dict[tuple[str, str], DeterministicAdapterSpec] = {
    ("inspect_unit_cell", "1.0.0"): DeterministicAdapterSpec(
        adapter_id="inspect_unit_cell",
        adapter_version="1.0.0",
        effect_classes=("observation",),
    )
}


def _validate_adapter_payload(spec: DeterministicAdapterSpec, payload: Mapping[str, Any]) -> None:
    """Validate the closed payload contract for one deterministic adapter."""
    if (spec.adapter_id, spec.adapter_version) == ("inspect_unit_cell", "1.0.0"):
        _exact_keys(payload, set(), "inspect_unit_cell payload")
        return
    raise LifecycleContractError("deterministic adapter has no registered payload contract")


@dataclass(frozen=True)
class AuthorizationFreshness:
    observed_at: str
    boot_id: str
    security_profile: str
    security_config_path: str
    security_config_sha256: str
    lease_generation: int
    intent_generation: int
    phase_generation: int


@dataclass(frozen=True)
class ExecutionAuthorization:
    authorization_id: str
    adapter: Mapping[str, Any]
    payload: Mapping[str, Any]
    payload_sha256: str
    target: Mapping[str, Any]
    acting_identity: Mapping[str, Any]
    security_posture: Mapping[str, Any]
    field_identity: Mapping[str, Any]
    lineage: Mapping[str, Any]
    effect_class: str
    expected_evidence: tuple[Mapping[str, Any], ...]
    evidence_attestation_sha256: str
    validity: Mapping[str, Any]
    issuer: Mapping[str, Any]
    operational_digest_sha256: str
    authorization_sha256: str

    def to_document(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_type": "execution_authorization",
            "authorization_id": self.authorization_id,
            "adapter": copy.deepcopy(dict(self.adapter)),
            "payload": copy.deepcopy(dict(self.payload)),
            "payload_sha256": self.payload_sha256,
            "target": copy.deepcopy(dict(self.target)),
            "acting_identity": copy.deepcopy(dict(self.acting_identity)),
            "security_posture": copy.deepcopy(dict(self.security_posture)),
            "field_identity": copy.deepcopy(dict(self.field_identity)),
            "lineage": copy.deepcopy(dict(self.lineage)),
            "effect_class": self.effect_class,
            "expected_evidence": [copy.deepcopy(dict(item)) for item in self.expected_evidence],
            "evidence_attestation_sha256": self.evidence_attestation_sha256,
            "validity": copy.deepcopy(dict(self.validity)),
            "issuer": copy.deepcopy(dict(self.issuer)),
            "operational_digest_sha256": self.operational_digest_sha256,
            "authorization_sha256": self.authorization_sha256,
        }

    @classmethod
    def from_document(cls, document: Mapping[str, Any]) -> "ExecutionAuthorization":
        validated = validate_execution_authorization(document)
        fields = {key: validated[key] for key in cls.__dataclass_fields__}
        fields["expected_evidence"] = tuple(validated["expected_evidence"])
        return cls(**fields)


def _operational_binding(document: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(document[key])
        for key in (
            "adapter", "payload", "payload_sha256", "target", "acting_identity", "security_posture",
            "field_identity", "lineage", "effect_class", "expected_evidence", "evidence_attestation_sha256",
            "validity", "issuer",
        )
    }


def mint_execution_authorization(
    *,
    authorization_id: str,
    adapter_id: str,
    adapter_version: str,
    payload: Mapping[str, Any],
    target_identity: str,
    target_namespace: str,
    acting_identity: str,
    acting_namespace: str,
    security_profile: str,
    security_config_path: str,
    security_config_sha256: str,
    field_id: str,
    field_genesis_uuid: str,
    obligation_id: str,
    phase_generation: int,
    context_id: str,
    intent_id: str,
    intent_generation: int,
    checkpoint_id: str,
    checkpoint_sha256: str,
    checkpoint_sequence: int,
    lease: Mapping[str, Any],
    effect_class: str,
    expected_evidence: Sequence[Mapping[str, Any]],
    issued_at: str,
    not_before: str,
    expires_at: str,
    issuer_id: str,
    policy_id: str,
    policy_version: str,
    policy_sha256: str,
    registry: Mapping[tuple[str, str], DeterministicAdapterSpec] = MVP_ADAPTER_REGISTRY,
) -> ExecutionAuthorization:
    spec = registry.get((adapter_id, adapter_version))
    if spec is None or not spec.deterministic:
        raise LifecycleContractError("authorization may be minted only for a deterministic registered adapter")
    if effect_class not in spec.effect_classes:
        raise LifecycleContractError("adapter registry does not allow the requested effect_class")
    evidence = validate_evidence_descriptors(list(expected_evidence), require_nonempty=True)
    payload_copy = _json_object(payload, "payload")
    _validate_adapter_payload(spec, payload_copy)
    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "execution_authorization",
        "authorization_id": authorization_id,
        "adapter": {
            "adapter_id": adapter_id,
            "adapter_version": adapter_version,
            "registry_version": MVP_ADAPTER_REGISTRY_VERSION,
            "registry_entry_sha256": spec.registry_entry_sha256,
            "deterministic": True,
        },
        "payload": payload_copy,
        "payload_sha256": domain_sha256("execution-payload", payload_copy),
        "target": {"identity": target_identity, "namespace": target_namespace},
        "acting_identity": {"identity": acting_identity, "namespace": acting_namespace},
        "security_posture": {
            "profile": security_profile,
            "config_path": security_config_path,
            "config_sha256": security_config_sha256,
        },
        "field_identity": {"field_id": field_id, "field_genesis_uuid": field_genesis_uuid},
        "lineage": {
            "obligation_id": obligation_id,
            "phase_generation": phase_generation,
            "context_id": context_id,
            "intent_id": intent_id,
            "intent_generation": intent_generation,
            "checkpoint_id": checkpoint_id,
            "checkpoint_sha256": checkpoint_sha256,
            "checkpoint_sequence": checkpoint_sequence,
            "lease": copy.deepcopy(dict(lease)),
        },
        "effect_class": effect_class,
        "expected_evidence": [copy.deepcopy(dict(item)) for item in evidence],
        "evidence_attestation_sha256": domain_sha256("expected-evidence-attestation", list(evidence)),
        "validity": {"issued_at": issued_at, "not_before": not_before, "expires_at": expires_at},
        "issuer": {
            "issuer_id": issuer_id,
            "authority": "deterministic_policy",
            "policy_id": policy_id,
            "policy_version": policy_version,
            "policy_sha256": policy_sha256,
            "model_orientation_authority": False,
        },
    }
    document["operational_digest_sha256"] = domain_sha256("execution-operational-binding", _operational_binding(document))
    document = _sealed(document, "authorization_sha256", "execution-authorization")
    return ExecutionAuthorization.from_document(document)


def _validate_identity(value: Mapping[str, Any], label: str) -> None:
    _exact_keys(value, {"identity", "namespace"}, label)
    _bounded_string(value["identity"], f"{label}.identity")
    _bounded_string(value["namespace"], f"{label}.namespace")


def _validate_lease(value: Mapping[str, Any], label: str = "lease") -> None:
    _exact_keys(value, {"holder", "attempt_id", "generation", "boot_id", "acquired_at", "expires_at"}, label)
    _bounded_string(value["holder"], f"{label}.holder")
    _uuid(value["attempt_id"], f"{label}.attempt_id")
    _positive_int(value["generation"], f"{label}.generation")
    _uuid(value["boot_id"], f"{label}.boot_id")
    acquired = _timestamp(value["acquired_at"], f"{label}.acquired_at")
    expires = _timestamp(value["expires_at"], f"{label}.expires_at")
    if expires <= acquired:
        raise LifecycleContractError(f"{label} expiry must follow acquisition")


def validate_execution_authorization(document: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version", "record_type", "authorization_id", "adapter", "payload", "payload_sha256", "target",
        "acting_identity", "security_posture", "field_identity", "lineage", "effect_class", "expected_evidence",
        "evidence_attestation_sha256", "validity", "issuer", "operational_digest_sha256", "authorization_sha256",
    }
    _exact_keys(document, required, "execution_authorization")
    if document["schema_version"] != SCHEMA_VERSION or document["record_type"] != "execution_authorization":
        raise LifecycleContractError("execution authorization tag/version mismatch")
    _uuid(document["authorization_id"], "authorization_id")
    adapter = document["adapter"]
    _exact_keys(adapter, {"adapter_id", "adapter_version", "registry_version", "registry_entry_sha256", "deterministic"}, "adapter")
    adapter_id = _bounded_string(adapter["adapter_id"], "adapter.adapter_id", maximum=128)
    adapter_version = _bounded_string(adapter["adapter_version"], "adapter.adapter_version", maximum=64)
    if adapter["registry_version"] != MVP_ADAPTER_REGISTRY_VERSION or adapter["deterministic"] is not True:
        raise LifecycleContractError("authorization adapter must use the deterministic MVP registry")
    spec = MVP_ADAPTER_REGISTRY.get((adapter_id, adapter_version))
    if spec is None or adapter["registry_entry_sha256"] != spec.registry_entry_sha256:
        raise LifecycleContractError("authorization adapter registry binding mismatch")
    payload = _json_object(document["payload"], "payload")
    _validate_adapter_payload(spec, payload)
    if document["payload_sha256"] != domain_sha256("execution-payload", payload):
        raise LifecycleContractError("authorization payload hash mismatch")
    _validate_identity(document["target"], "target")
    _validate_identity(document["acting_identity"], "acting_identity")
    security = document["security_posture"]
    _exact_keys(security, {"profile", "config_path", "config_sha256"}, "security_posture")
    _bounded_string(security["profile"], "security_posture.profile", maximum=128)
    _relative_path(security["config_path"], "security_posture.config_path")
    _sha256(security["config_sha256"], "security_posture.config_sha256")
    field = document["field_identity"]
    _exact_keys(field, {"field_id", "field_genesis_uuid"}, "field_identity")
    _bounded_string(field["field_id"], "field_identity.field_id")
    _uuid(field["field_genesis_uuid"], "field_identity.field_genesis_uuid")
    lineage = document["lineage"]
    _exact_keys(
        lineage,
        {
            "obligation_id", "phase_generation", "context_id", "intent_id", "intent_generation",
            "checkpoint_id", "checkpoint_sha256", "checkpoint_sequence", "lease",
        },
        "lineage",
    )
    for name in ("obligation_id", "intent_id", "checkpoint_id"):
        _uuid(lineage[name], f"lineage.{name}")
    _positive_int(lineage["phase_generation"], "lineage.phase_generation", allow_zero=True)
    _bounded_string(lineage["context_id"], "lineage.context_id")
    _positive_int(lineage["intent_generation"], "lineage.intent_generation")
    _sha256(lineage["checkpoint_sha256"], "lineage.checkpoint_sha256")
    _positive_int(lineage["checkpoint_sequence"], "lineage.checkpoint_sequence")
    _validate_lease(lineage["lease"], "lineage.lease")
    effect_class = document["effect_class"]
    if effect_class not in spec.effect_classes:
        raise LifecycleContractError("authorization effect_class is not allowed by adapter registry")
    evidence = validate_evidence_descriptors(document["expected_evidence"], require_nonempty=True)
    if document["evidence_attestation_sha256"] != domain_sha256("expected-evidence-attestation", list(evidence)):
        raise LifecycleContractError("authorization evidence attestation hash mismatch")
    validity = document["validity"]
    _exact_keys(validity, {"issued_at", "not_before", "expires_at"}, "validity")
    issued = _timestamp(validity["issued_at"], "validity.issued_at")
    not_before = _timestamp(validity["not_before"], "validity.not_before")
    expires = _timestamp(validity["expires_at"], "validity.expires_at")
    lease_acquired = _timestamp(lineage["lease"]["acquired_at"], "lineage.lease.acquired_at")
    lease_expires = _timestamp(lineage["lease"]["expires_at"], "lineage.lease.expires_at")
    if not (lease_acquired <= issued <= not_before < expires <= lease_expires):
        raise LifecycleContractError("authorization validity must be contained by its lease")
    issuer = document["issuer"]
    _exact_keys(issuer, {"issuer_id", "authority", "policy_id", "policy_version", "policy_sha256", "model_orientation_authority"}, "issuer")
    for name in ("issuer_id", "policy_id", "policy_version"):
        _bounded_string(issuer[name], f"issuer.{name}", maximum=128)
    _sha256(issuer["policy_sha256"], "issuer.policy_sha256")
    if issuer["authority"] != "deterministic_policy" or issuer["model_orientation_authority"] is not False:
        raise LifecycleContractError("only deterministic policy may mint authority; model orientation is never authority")
    if document["operational_digest_sha256"] != domain_sha256("execution-operational-binding", _operational_binding(document)):
        raise LifecycleContractError("authorization operational digest mismatch")
    expected_hash = domain_sha256("execution-authorization", {key: copy.deepcopy(value) for key, value in document.items() if key != "authorization_sha256"})
    if document["authorization_sha256"] != expected_hash:
        raise LifecycleContractError("execution authorization hash mismatch")
    return copy.deepcopy(dict(document))


def validate_authorization_freshness(
    authorization: ExecutionAuthorization | Mapping[str, Any],
    snapshot: AuthorizationFreshness,
    *,
    require_current_validity: bool = True,
) -> None:
    document = authorization.to_document() if isinstance(authorization, ExecutionAuthorization) else validate_execution_authorization(authorization)
    observed = _timestamp(snapshot.observed_at, "freshness.observed_at")
    validity = document["validity"]
    not_before = _timestamp(validity["not_before"], "validity.not_before")
    expires = _timestamp(validity["expires_at"], "validity.expires_at")
    if observed < not_before or (require_current_validity and observed >= expires):
        raise LifecycleConflictError("execution authorization is not currently valid")
    security = document["security_posture"]
    _relative_path(snapshot.security_config_path, "freshness.security_config_path")
    if (snapshot.security_profile, snapshot.security_config_path, snapshot.security_config_sha256) != (
        security["profile"], security["config_path"], security["config_sha256"]
    ):
        raise LifecycleConflictError("security posture or durable configuration drift invalidates authorization")
    lease = document["lineage"]["lease"]
    _uuid(snapshot.boot_id, "freshness.boot_id")
    if snapshot.boot_id != lease["boot_id"] or snapshot.lease_generation != lease["generation"]:
        raise LifecycleConflictError("boot or lease generation drift invalidates authorization")
    if snapshot.intent_generation != document["lineage"]["intent_generation"]:
        raise LifecycleConflictError("intent generation drift invalidates authorization")
    if snapshot.phase_generation != document["lineage"]["phase_generation"]:
        raise LifecycleConflictError("phase generation drift invalidates authorization")


@dataclass(frozen=True)
class ExecutionResult:
    result_id: str
    authorization_id: str
    authorization_sha256: str
    obligation_id: str
    phase_generation: int
    payload_sha256: str
    generation: int
    previous_result_sha256: str | None
    state: str
    run_id: str | None
    claim: Mapping[str, Any] | None
    timestamps: Mapping[str, Any]
    observed_evidence: tuple[Mapping[str, Any], ...]
    ambiguity_boundary: Mapping[str, Any] | None
    terminal_result: Mapping[str, Any] | None
    physical_effect_exactly_once_claimed: bool
    execution_result_sha256: str

    def to_document(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_type": "execution_result",
            "result_id": self.result_id,
            "authorization_id": self.authorization_id,
            "authorization_sha256": self.authorization_sha256,
            "obligation_id": self.obligation_id,
            "phase_generation": self.phase_generation,
            "payload_sha256": self.payload_sha256,
            "generation": self.generation,
            "previous_result_sha256": self.previous_result_sha256,
            "state": self.state,
            "run_id": self.run_id,
            "claim": copy.deepcopy(dict(self.claim)) if self.claim is not None else None,
            "timestamps": copy.deepcopy(dict(self.timestamps)),
            "observed_evidence": [copy.deepcopy(dict(item)) for item in self.observed_evidence],
            "ambiguity_boundary": copy.deepcopy(dict(self.ambiguity_boundary)) if self.ambiguity_boundary is not None else None,
            "terminal_result": copy.deepcopy(dict(self.terminal_result)) if self.terminal_result is not None else None,
            "physical_effect_exactly_once_claimed": self.physical_effect_exactly_once_claimed,
            "execution_result_sha256": self.execution_result_sha256,
        }

    @classmethod
    def from_document(cls, document: Mapping[str, Any]) -> "ExecutionResult":
        validated = validate_execution_result(document)
        fields = {key: validated[key] for key in cls.__dataclass_fields__}
        fields["observed_evidence"] = tuple(validated["observed_evidence"])
        return cls(**fields)


def build_execution_result(
    *, result_id: str, authorization: ExecutionAuthorization | Mapping[str, Any], ready_at: str
) -> ExecutionResult:
    auth = authorization.to_document() if isinstance(authorization, ExecutionAuthorization) else validate_execution_authorization(authorization)
    document = _sealed(
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "execution_result",
            "result_id": result_id,
            "authorization_id": auth["authorization_id"],
            "authorization_sha256": auth["authorization_sha256"],
            "obligation_id": auth["lineage"]["obligation_id"],
            "phase_generation": auth["lineage"]["phase_generation"],
            "payload_sha256": auth["payload_sha256"],
            "generation": 1,
            "previous_result_sha256": None,
            "state": "ready",
            "run_id": None,
            "claim": None,
            "timestamps": {"ready_at": ready_at, "claimed_at": None, "dispatched_at": None, "terminal_at": None},
            "observed_evidence": [],
            "ambiguity_boundary": None,
            "terminal_result": None,
            "physical_effect_exactly_once_claimed": False,
        },
        "execution_result_sha256",
        "execution-result",
    )
    return ExecutionResult.from_document(document)


def advance_execution_result(
    previous: ExecutionResult | Mapping[str, Any],
    *,
    state: str,
    at: str,
    authorization: ExecutionAuthorization | Mapping[str, Any],
    freshness: AuthorizationFreshness | None = None,
    run_id: str | None = None,
    claim: Mapping[str, Any] | None = None,
    observed_evidence: Sequence[Mapping[str, Any]] = (),
    ambiguity_boundary: Mapping[str, Any] | None = None,
    terminal_result: Mapping[str, Any] | None = None,
) -> ExecutionResult:
    old = previous.to_document() if isinstance(previous, ExecutionResult) else validate_execution_result(previous)
    auth = authorization.to_document() if isinstance(authorization, ExecutionAuthorization) else validate_execution_authorization(authorization)
    freshness_required = state in {"claimed", "dispatched", "completed", "failed", "ambiguous"}
    if freshness_required and freshness is None:
        raise LifecycleContractError("current freshness evidence is required before execution progress")
    if freshness is not None and freshness_required:
        validate_authorization_freshness(
            auth,
            freshness,
            require_current_validity=state != "ambiguous",
        )
        if _timestamp(freshness.observed_at, "freshness.observed_at") != _timestamp(at, "transition.at"):
            raise LifecycleConflictError("freshness evidence must be observed at the transition time")
    timestamps = copy.deepcopy(old["timestamps"])
    if state == "claimed":
        timestamps["claimed_at"] = at
    elif state == "dispatched":
        timestamps["dispatched_at"] = at
    elif state in TERMINAL_RESULT_STATES:
        timestamps["terminal_at"] = at
    document = _sealed(
        {
            **{key: old[key] for key in ("schema_version", "record_type", "result_id", "authorization_id", "authorization_sha256", "obligation_id", "phase_generation", "payload_sha256")},
            "generation": old["generation"] + 1,
            "previous_result_sha256": old["execution_result_sha256"],
            "state": state,
            "run_id": run_id if run_id is not None else old["run_id"],
            "claim": copy.deepcopy(dict(claim)) if claim is not None else copy.deepcopy(old["claim"]),
            "timestamps": timestamps,
            "observed_evidence": [copy.deepcopy(dict(item)) for item in observed_evidence],
            "ambiguity_boundary": copy.deepcopy(dict(ambiguity_boundary)) if ambiguity_boundary is not None else None,
            "terminal_result": copy.deepcopy(dict(terminal_result)) if terminal_result is not None else None,
            "physical_effect_exactly_once_claimed": False,
        },
        "execution_result_sha256",
        "execution-result",
    )
    validate_result_transition(old, document, auth)
    return ExecutionResult.from_document(document)


def _validate_claim(value: Mapping[str, Any]) -> None:
    _exact_keys(value, {"claim_id", "holder", "lease_generation", "boot_id", "claimed_at", "expires_at"}, "claim")
    _uuid(value["claim_id"], "claim.claim_id")
    _bounded_string(value["holder"], "claim.holder")
    _positive_int(value["lease_generation"], "claim.lease_generation")
    _uuid(value["boot_id"], "claim.boot_id")
    if _timestamp(value["expires_at"], "claim.expires_at") <= _timestamp(value["claimed_at"], "claim.claimed_at"):
        raise LifecycleContractError("claim expiry must follow claim time")


def _validate_terminal_result(value: Any, state: str) -> dict[str, Any] | None:
    if state not in TERMINAL_RESULT_STATES:
        if value is not None:
            raise LifecycleContractError("nonterminal execution result cannot contain terminal_result")
        return None
    if not isinstance(value, Mapping) or value.get("result_type") != state:
        raise LifecycleContractError("terminal_result must be tagged with the execution state")
    variants = {
        "completed": {"result_type", "outcome_sha256", "summary_code"},
        "failed": {"result_type", "error_code", "retryable"},
        "ambiguous": {"result_type", "reason_code", "reconciliation_required"},
        "expired": {"result_type", "reason_code"},
    }
    _exact_keys(value, variants[state], f"{state} terminal_result")
    if state == "completed":
        _sha256(value["outcome_sha256"], "terminal_result.outcome_sha256")
        _bounded_string(value["summary_code"], "terminal_result.summary_code", maximum=128)
    elif state == "failed":
        _bounded_string(value["error_code"], "terminal_result.error_code", maximum=128)
        if not isinstance(value["retryable"], bool):
            raise LifecycleContractError("terminal_result.retryable must be boolean")
    elif state == "ambiguous":
        _bounded_string(value["reason_code"], "terminal_result.reason_code", maximum=128)
        if value["reconciliation_required"] is not True:
            raise LifecycleContractError("ambiguous result requires reconciliation")
    else:
        _bounded_string(value["reason_code"], "terminal_result.reason_code", maximum=128)
    return copy.deepcopy(dict(value))


def validate_execution_result(document: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version", "record_type", "result_id", "authorization_id", "authorization_sha256", "obligation_id",
        "phase_generation", "payload_sha256", "generation", "previous_result_sha256", "state", "run_id", "claim",
        "timestamps", "observed_evidence", "ambiguity_boundary", "terminal_result",
        "physical_effect_exactly_once_claimed", "execution_result_sha256",
    }
    _exact_keys(document, required, "execution_result")
    if document["schema_version"] != SCHEMA_VERSION or document["record_type"] != "execution_result":
        raise LifecycleContractError("execution result tag/version mismatch")
    for name in ("result_id", "authorization_id", "obligation_id"):
        _uuid(document[name], name)
    for name in ("authorization_sha256", "payload_sha256"):
        _sha256(document[name], name)
    _positive_int(document["phase_generation"], "phase_generation", allow_zero=True)
    generation = _positive_int(document["generation"], "generation")
    state = document["state"]
    if state not in RESULT_TRANSITIONS:
        raise LifecycleContractError("unsupported execution result state")
    if generation == 1:
        if document["previous_result_sha256"] is not None or state != "ready":
            raise LifecycleContractError("initial execution result must be ready without predecessor")
    else:
        _sha256(document["previous_result_sha256"], "previous_result_sha256")
    if document["physical_effect_exactly_once_claimed"] is not False:
        raise LifecycleContractError("execution results cannot claim exactly-once physical effects")
    claim = document["claim"]
    if claim is not None:
        _validate_claim(claim)
    run_id = document["run_id"]
    if run_id is not None:
        _uuid(run_id, "run_id")
    timestamps = document["timestamps"]
    _exact_keys(timestamps, {"ready_at", "claimed_at", "dispatched_at", "terminal_at"}, "timestamps")
    ready = _timestamp(timestamps["ready_at"], "timestamps.ready_at")
    for name in ("claimed_at", "dispatched_at", "terminal_at"):
        if timestamps[name] is not None:
            _timestamp(timestamps[name], f"timestamps.{name}")
    needs_claim = state in {"claimed", "dispatched", "completed", "failed", "ambiguous"}
    if needs_claim and (claim is None or run_id is None or timestamps["claimed_at"] is None):
        raise LifecycleContractError("claimed or later execution state requires run and claim coordinates")
    if state in {"ready", "expired"} and state == "ready" and (claim is not None or run_id is not None):
        raise LifecycleContractError("ready result cannot contain claim coordinates")
    if claim is not None and timestamps["claimed_at"] != claim["claimed_at"]:
        raise LifecycleContractError("claim timestamp must match lifecycle timestamps")
    if state in {"dispatched", "completed", "failed", "ambiguous"} and timestamps["dispatched_at"] is None:
        terminal = document["terminal_result"]
        pre_dispatch_failure = (
            state == "failed"
            and isinstance(terminal, Mapping)
            and terminal.get("error_code") == "pre_dispatch_failure"
        )
        claimed_ambiguity = (
            state == "ambiguous"
            and isinstance(document["ambiguity_boundary"], Mapping)
            and document["ambiguity_boundary"].get("last_certain_state") == "claimed"
        )
        if not pre_dispatch_failure and not claimed_ambiguity:
            raise LifecycleContractError("dispatched or post-dispatch state requires dispatched_at")
    if state in TERMINAL_RESULT_STATES and timestamps["terminal_at"] is None:
        raise LifecycleContractError("terminal state requires terminal_at")
    if state not in TERMINAL_RESULT_STATES and timestamps["terminal_at"] is not None:
        raise LifecycleContractError("nonterminal state cannot have terminal_at")
    ordered = [ready] + [
        _timestamp(timestamps[name], f"timestamps.{name}")
        for name in ("claimed_at", "dispatched_at", "terminal_at")
        if timestamps[name] is not None
    ]
    if ordered != sorted(ordered) or len(set(ordered)) != len(ordered):
        raise LifecycleContractError("execution timestamps must strictly increase")
    evidence = validate_evidence_descriptors(document["observed_evidence"], require_nonempty=state == "completed")
    if state not in TERMINAL_RESULT_STATES and evidence:
        raise LifecycleContractError("observed postcondition evidence is terminal-only")
    boundary = document["ambiguity_boundary"]
    if state == "ambiguous":
        if not isinstance(boundary, Mapping):
            raise LifecycleContractError("ambiguous result requires ambiguity_boundary")
        _exact_keys(boundary, {"last_certain_state", "reason_code", "observed_at"}, "ambiguity_boundary")
        if boundary["last_certain_state"] not in {"claimed", "dispatched"}:
            raise LifecycleContractError("invalid ambiguity last_certain_state")
        _bounded_string(boundary["reason_code"], "ambiguity_boundary.reason_code", maximum=128)
        boundary_at = _timestamp(boundary["observed_at"], "ambiguity_boundary.observed_at")
        if timestamps["terminal_at"] is None or boundary_at != _timestamp(timestamps["terminal_at"], "timestamps.terminal_at"):
            raise LifecycleContractError("ambiguity observation must equal the terminal timestamp")
        if boundary["last_certain_state"] == "claimed" and timestamps["dispatched_at"] is not None:
            raise LifecycleContractError("claimed ambiguity cannot include a dispatch timestamp")
        if boundary["last_certain_state"] == "dispatched" and timestamps["dispatched_at"] is None:
            raise LifecycleContractError("dispatched ambiguity requires a dispatch timestamp")
    elif boundary is not None:
        raise LifecycleContractError("only ambiguous results may contain ambiguity_boundary")
    _validate_terminal_result(document["terminal_result"], state)
    expected_hash = domain_sha256("execution-result", {key: copy.deepcopy(value) for key, value in document.items() if key != "execution_result_sha256"})
    if document["execution_result_sha256"] != expected_hash:
        raise LifecycleContractError("execution result hash mismatch")
    return copy.deepcopy(dict(document))


def validate_result_transition(
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
    authorization: ExecutionAuthorization | Mapping[str, Any],
) -> None:
    old = validate_execution_result(previous)
    new = validate_execution_result(current)
    auth = authorization.to_document() if isinstance(authorization, ExecutionAuthorization) else validate_execution_authorization(authorization)
    immutable = ("result_id", "authorization_id", "authorization_sha256", "obligation_id", "phase_generation", "payload_sha256")
    if any(old[field] != new[field] for field in immutable):
        raise LifecycleConflictError("execution result transition changed immutable linkage")
    if (
        new["authorization_id"] != auth["authorization_id"]
        or new["authorization_sha256"] != auth["authorization_sha256"]
        or new["payload_sha256"] != auth["payload_sha256"]
        or new["obligation_id"] != auth["lineage"]["obligation_id"]
        or new["phase_generation"] != auth["lineage"]["phase_generation"]
    ):
        raise LifecycleConflictError("execution result does not bind its authorization")
    if new["generation"] != old["generation"] + 1 or new["previous_result_sha256"] != old["execution_result_sha256"]:
        raise LifecycleConflictError("execution result violates strict CAS generation")
    if new["state"] not in RESULT_TRANSITIONS[old["state"]]:
        raise LifecycleContractError(f"execution result transition {old['state']} -> {new['state']} is not allowed")
    if old["claim"] is not None and (new["claim"] != old["claim"] or new["run_id"] != old["run_id"]):
        raise LifecycleConflictError("claim and run coordinates are immutable after claim")
    if new["claim"] is not None:
        authorization_lease = auth["lineage"]["lease"]
        if (
            new["claim"]["holder"] != authorization_lease["holder"]
            or new["claim"]["boot_id"] != authorization_lease["boot_id"]
            or new["claim"]["lease_generation"] != authorization_lease["generation"]
        ):
            raise LifecycleConflictError("execution claim does not bind the authorized holder, boot, and lease generation")
        claimed_at = _timestamp(new["claim"]["claimed_at"], "claim.claimed_at")
        if not (
            _timestamp(auth["validity"]["not_before"], "validity.not_before")
            <= claimed_at
            < _timestamp(auth["validity"]["expires_at"], "validity.expires_at")
        ):
            raise LifecycleConflictError("execution claim falls outside authorization validity")
        claim_expiry = _timestamp(new["claim"]["expires_at"], "claim.expires_at")
        if claim_expiry > _timestamp(auth["validity"]["expires_at"], "validity.expires_at"):
            raise LifecycleConflictError("execution claim cannot outlive its authorization")
        if claim_expiry > _timestamp(authorization_lease["expires_at"], "lineage.lease.expires_at"):
            raise LifecycleConflictError("execution claim cannot outlive its authorized lease")
        terminal_at = new["timestamps"]["terminal_at"]
        dispatched_at = new["timestamps"]["dispatched_at"]
        if dispatched_at is not None and _timestamp(dispatched_at, "timestamps.dispatched_at") >= claim_expiry:
            raise LifecycleConflictError("dispatch cannot occur at or after claim expiry")
        if new["state"] in {"completed", "failed"} and terminal_at is not None and _timestamp(terminal_at, "timestamps.terminal_at") >= claim_expiry:
            raise LifecycleConflictError("late terminal certainty must be represented as ambiguous")
    if new["state"] == "expired":
        if new["timestamps"]["dispatched_at"] is not None:
            raise LifecycleContractError("a dispatched result cannot become expired; it must reconcile ambiguity")
        expiry_boundary = (
            _timestamp(old["claim"]["expires_at"], "claim.expires_at")
            if old["claim"] is not None
            else _timestamp(auth["validity"]["expires_at"], "validity.expires_at")
        )
        if _timestamp(new["timestamps"]["terminal_at"], "timestamps.terminal_at") < expiry_boundary:
            raise LifecycleContractError("execution cannot expire before its active validity or claim boundary")
