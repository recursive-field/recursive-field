from __future__ import annotations

import importlib.util
import json
import os
import sys
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from flask import Flask

PROJECT_ROOT = Path(
    os.environ.get("RECURSIVE_FIELD_PROJECT_ROOT", "/a0/usr/projects/recursive-field")
).resolve()
FRAMEWORK_ROOT = Path(os.environ.get("AGENT_ZERO_ROOT", "/a0")).resolve()
PLUGIN_ROOT = Path(__file__).resolve().parents[1]
for root in (PROJECT_ROOT, FRAMEWORK_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from agent_zero_plugins.continuation_reflex.helpers import runtime
from helpers.continuation_turn import (
    ContinuationTurnConflictError,
    ContinuationTurnNotFoundError,
    ContinuationTurnValidationError,
)

# Runtime installation uses the required usr.plugins import. Bind that exact
# name to tracked source for static package tests without installing/activating
# the plugin.
sys.modules["usr.plugins.continuation_reflex.helpers.runtime"] = runtime
_API_SPEC = importlib.util.spec_from_file_location(
    "continuation_reflex_api_under_test",
    PLUGIN_ROOT / "api" / "continuation_turn.py",
)
if _API_SPEC is None or _API_SPEC.loader is None:
    raise RuntimeError("cannot load continuation reflex API under test")
api = importlib.util.module_from_spec(_API_SPEC)
_API_SPEC.loader.exec_module(api)

REQUEST_ID = "11111111-1111-4111-8111-111111111111"
CONTEXT_ID = "opaque-existing-context"


class FakeContext:
    def __init__(self, result: dict | None = None) -> None:
        self.continuation_turn = AsyncMock(
            return_value=result
            or {
                "disposition": "completed",
                "request_id": REQUEST_ID,
                "context_id": CONTEXT_ID,
                "generation": 1,
                "state": "completed",
                "terminal": True,
                "receipt": {
                    "request_id": REQUEST_ID,
                    "context_id": CONTEXT_ID,
                    "generation": 1,
                    "state": "completed",
                    "terminal": True,
                    "formation_reflex_sha256": "a" * 64,
                    "protocol_text_sha256": "b" * 64,
                },
            }
        )


def plan_for(
    context: FakeContext | None = None,
    *,
    existing_fired: dict | None = None,
) -> runtime.DispatchPlan:
    return runtime.DispatchPlan(
        root=Path("/isolated-test-root"),
        request={"request_id": REQUEST_ID, "context_id": CONTEXT_ID},
        context=context or FakeContext(),
        engine_request={
            "schema_version": "1.0.0",
            "request_id": REQUEST_ID,
            "context_id": CONTEXT_ID,
            "generation": 1,
            "formation_reflex_sha256": "a" * 64,
            "system_protocol": {
                "role": "system",
                "maximum_new_turns": 1,
                "user_message_sent": False,
                "require_existing_context": True,
                "require_idle_context": True,
                "text": "trusted immutable protocol",
                "text_sha256": "b" * 64,
            },
        },
        claim={"claim": {"claim_id": "claim"}},
        claim_disposition="created",
        existing_fired=existing_fired,
    )


class ContinuationReflexApiTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.app = Flask("continuation_reflex_api_test")
        self.handler = api.ContinuationTurn(self.app, threading.RLock())

    @staticmethod
    def payload(response) -> dict:
        return json.loads(response.get_data(as_text=True))

    def test_route_keeps_authenticated_csrf_protected_post_defaults(self) -> None:
        self.assertEqual(api.ContinuationTurn.get_methods(), ["POST"])
        self.assertIs(api.ContinuationTurn.requires_auth(), True)
        self.assertIs(api.ContinuationTurn.requires_csrf(), True)
        self.assertIs(api.ContinuationTurn.requires_api_key(), False)
        self.assertIs(api.ContinuationTurn.requires_loopback(), False)

    async def test_http_body_can_select_only_request_id(self) -> None:
        response = await self.handler.process(
            {"request_id": REQUEST_ID, "system_protocol": "attacker text"},
            SimpleNamespace(),
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.payload(response)["error"], "request_id_only")

    async def test_not_found_conflict_and_validation_map_to_contract_statuses(self) -> None:
        cases = (
            (runtime.ReflexNotFoundError("missing"), 404),
            (ContinuationTurnNotFoundError("missing context"), 404),
            (runtime.ReflexConflictError("busy"), 409),
            (ContinuationTurnConflictError("engine conflict"), 409),
            (runtime.ReflexValidationError("bad artifact"), 422),
            (ContinuationTurnValidationError("bad engine request"), 422),
        )
        for exception, expected in cases:
            with self.subTest(exception=type(exception).__name__), patch.object(
                api, "get_plugin_config", return_value={"enabled": True}
            ), patch.object(runtime, "prepare_dispatch", side_effect=exception):
                response = await self.handler.process(
                    {"request_id": REQUEST_ID}, SimpleNamespace()
                )
                self.assertEqual(response.status_code, expected)

    async def test_in_progress_engine_reservation_returns_202_without_fired_receipt(self) -> None:
        context = FakeContext(
            {
                "disposition": "in_progress",
                "request_id": REQUEST_ID,
                "context_id": CONTEXT_ID,
                "generation": 1,
                "state": "reserved",
                "terminal": False,
            }
        )
        plan = plan_for(context)
        with patch.object(api, "get_plugin_config", return_value={}), patch.object(
            runtime, "prepare_dispatch", return_value=plan
        ), patch.object(runtime, "record_fired") as record_fired:
            response = await self.handler.process(
                {"request_id": REQUEST_ID}, SimpleNamespace()
            )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(self.payload(response)["status"], "in_progress")
        context.continuation_turn.assert_awaited_once_with(plan.engine_request)
        record_fired.assert_not_called()

    async def test_completed_engine_turn_records_separate_formation_receipt(self) -> None:
        plan = plan_for()
        with patch.object(api, "get_plugin_config", return_value={}), patch.object(
            runtime, "prepare_dispatch", return_value=plan
        ), patch.object(
            runtime,
            "record_fired",
            return_value=({"event_type": "continuation_reflex_fired"}, "created"),
        ) as record_fired:
            response = await self.handler.process(
                {"request_id": REQUEST_ID}, SimpleNamespace()
            )
        body = self.payload(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "fired")
        self.assertEqual(body["formation_disposition"], "created")
        record_fired.assert_called_once()

    async def test_existing_formation_receipt_replays_200_without_engine_call(self) -> None:
        context = FakeContext()
        plan = plan_for(context, existing_fired={"event_type": "continuation_reflex_fired"})
        with patch.object(api, "get_plugin_config", return_value={}), patch.object(
            runtime, "prepare_dispatch", return_value=plan
        ), patch.object(runtime, "record_fired") as record_fired:
            response = await self.handler.process(
                {"request_id": REQUEST_ID}, SimpleNamespace()
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.payload(response)["status"], "already_fired")
        context.continuation_turn.assert_not_awaited()
        record_fired.assert_not_called()

    async def test_terminal_noncompletion_returns_409_without_fired_receipt(self) -> None:
        context = FakeContext(
            {
                "disposition": "replayed",
                "request_id": REQUEST_ID,
                "context_id": CONTEXT_ID,
                "generation": 1,
                "state": "ambiguous",
                "terminal": True,
            }
        )
        plan = plan_for(context)
        with patch.object(api, "get_plugin_config", return_value={}), patch.object(
            runtime, "prepare_dispatch", return_value=plan
        ), patch.object(runtime, "record_fired") as record_fired:
            response = await self.handler.process(
                {"request_id": REQUEST_ID}, SimpleNamespace()
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.payload(response)["engine_state"], "ambiguous")
        record_fired.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
