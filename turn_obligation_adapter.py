#!/usr/bin/env python3
"""Recursive Field adapter for Agent Zero's generic turn-obligation owner.

The adapter supplies schema 1.1.0 semantics only.  Agent Zero owns chat-local
locking and persistence; this module performs no I/O except reading the field's
immutable genesis marker during adapter construction.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping


class TurnObligationAdapterError(ValueError):
    """The field marker, event, selection, or transition is invalid."""


def _load_contracts(root: Path) -> ModuleType:
    name = "recursive_field_lifecycle_contracts"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    path = root / "lifecycle_contracts.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise TurnObligationAdapterError("lifecycle_contracts.py cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise TurnObligationAdapterError(f"{label} fields do not match the contract")


class RecursiveFieldTurnObligationAdapter:
    """Project-scoped semantic adapter for locked turn-obligation v1.1.0."""

    hash_field = "turn_obligation_sha256"

    def __init__(self, field_root: Path, *, contracts: ModuleType | None = None) -> None:
        self.field_root = field_root.resolve(strict=True)
        self.contracts = contracts or _load_contracts(self.field_root)
        marker_path = self.field_root / ".recursive-field-root"
        try:
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise TurnObligationAdapterError("field genesis marker is unreadable") from exc
        if not isinstance(marker, dict) or set(marker) != {
            "genesis_uuid",
            "inception_timestamp",
            "schema_version",
        }:
            raise TurnObligationAdapterError("field genesis marker fields are invalid")
        # Reuse the locked validator by constructing a harmless ingress record.
        self.field_genesis_uuid = str(marker["genesis_uuid"])

    def build_ordinary_ingress(self, event: Mapping[str, Any]) -> Mapping[str, Any]:
        _exact_keys(
            event,
            {
                "obligation_id",
                "context_id",
                "ingress_id",
                "ingress_sha256",
                "projection_sha256",
                "ingressed_at",
                "ingress_identity",
                "recorded_at",
            },
            "ordinary ingress event",
        )
        return self.contracts.build_turn_obligation(
            obligation_id=event["obligation_id"],
            field_genesis_uuid=self.field_genesis_uuid,
            context_id=event["context_id"],
            ingress_id=event["ingress_id"],
            ingress_sha256=event["ingress_sha256"],
            projection_sha256=event["projection_sha256"],
            ingressed_at=event["ingressed_at"],
            ingress_identity=event["ingress_identity"],
            recorded_at=event["recorded_at"],
        ).to_document()

    def validate_record(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        validated = self.contracts.validate_turn_obligation(record)
        if validated["lineage"]["field_genesis_uuid"] != self.field_genesis_uuid:
            raise TurnObligationAdapterError("turn obligation belongs to another field genesis")
        return validated

    def validate_transition(
        self,
        previous: Mapping[str, Any],
        current: Mapping[str, Any],
    ) -> None:
        self.contracts.validate_turn_transition(previous, current)

    def advance_processing(
        self,
        previous: Mapping[str, Any],
        *,
        recorded_at: str,
    ) -> Mapping[str, Any]:
        if previous.get("state") != "open":
            raise TurnObligationAdapterError("ordinary processing requires an open obligation")
        return self.contracts.advance_turn_obligation(
            previous,
            state="active",
            recorded_at=recorded_at,
            advance_source="engine",
        ).to_document()

    def close_terminal(
        self,
        previous: Mapping[str, Any],
        *,
        message_ref: str,
        persisted_at: str,
    ) -> Mapping[str, Any]:
        if previous.get("state") not in {"open", "active"}:
            raise TurnObligationAdapterError("terminal persistence cannot close this obligation state")
        return self.contracts.advance_turn_obligation(
            previous,
            state="closed",
            recorded_at=persisted_at,
            advance_source="engine",
            closure_evidence={
                "evidence_type": "terminal_response_emitted",
                "message_ref": message_ref,
                "persisted_at": persisted_at,
                "delivery_claimed": False,
                "human_observation_claimed": False,
            },
            # Persistence closes this turn; it does not prove the objective complete.
            objective_status="incomplete",
        ).to_document()

    def apply_handoff(
        self,
        previous: Mapping[str, Any],
        *,
        evidence: Mapping[str, Any],
        recorded_at: str,
    ) -> Mapping[str, Any]:
        evidence_type = evidence.get("evidence_type")
        if evidence_type in {"checkpoint_planted", "handed_off_to_intent"} and (
            previous.get("lineage", {}).get("lineage_mode") == "ordinary_ingress"
        ):
            return self.contracts.bind_turn_obligation(
                previous,
                recorded_at=recorded_at,
                closure_evidence=evidence,
            ).to_document()
        states = {
            "human_gate_reached": "awaiting_human",
            "reconciliation_claimed": "reconciling",
            "checkpoint_planted": "waiting",
            "handed_off_to_intent": "handed_off",
        }
        state = states.get(evidence_type)
        if state is None:
            raise TurnObligationAdapterError("unsupported typed handoff evidence")
        return self.contracts.advance_turn_obligation(
            previous,
            state=state,
            recorded_at=recorded_at,
            advance_source="formation",
            closure_evidence=evidence,
            objective_status="incomplete",
        ).to_document()

    def select_protocol_reflex(
        self,
        records: tuple[Mapping[str, Any], ...],
        *,
        formation_binding: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        _exact_keys(
            formation_binding,
            {"intent_id", "checkpoint"},
            "protocol-reflex formation binding",
        )
        pointer = formation_binding["checkpoint"]
        if not isinstance(pointer, Mapping):
            raise TurnObligationAdapterError("protocol reflex requires a checkpoint pointer")
        required_pointer = {"checkpoint_id", "checkpoint_sha256", "sequence"}
        if set(pointer) != required_pointer:
            raise TurnObligationAdapterError("checkpoint pointer fields are invalid")
        matches: list[Mapping[str, Any]] = []
        for candidate in records:
            record = self.validate_record(candidate)
            lineage = record["lineage"]
            if (
                record["state"] == "waiting"
                and record["turn_closed"] is True
                and lineage["lineage_mode"] == "bound"
                and lineage["intent_id"] == formation_binding["intent_id"]
                and lineage["checkpoint_id"] == pointer["checkpoint_id"]
                and lineage["checkpoint_sha256"] == pointer["checkpoint_sha256"]
            ):
                matches.append(record)
        if not matches:
            raise TurnObligationAdapterError("no bound waiting obligation matches the reflex")
        if len(matches) != 1:
            raise TurnObligationAdapterError("multiple bound waiting obligations match the reflex")
        return copy.deepcopy(dict(matches[0]))

    def advance_protocol_reflex(
        self,
        previous: Mapping[str, Any],
        *,
        recorded_at: str,
    ) -> Mapping[str, Any]:
        # The locked transition validator enforces bound lineage, waiting->active,
        # same obligation identity, and exactly one phase_generation increment.
        return self.contracts.advance_turn_obligation(
            previous,
            state="active",
            recorded_at=recorded_at,
            advance_source="protocol_reflex",
        ).to_document()
