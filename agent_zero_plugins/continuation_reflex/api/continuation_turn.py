"""Authenticated API bridge to Agent Zero's native typed continuation turn."""

from __future__ import annotations

import json
from typing import Any

from flask import Request, Response

from helpers.api import ApiHandler, Input, Output
from helpers.continuation_turn import (
    ContinuationTurnConflictError,
    ContinuationTurnNotFoundError,
    ContinuationTurnValidationError,
)
from helpers.plugins import get_plugin_config
from usr.plugins.continuation_reflex.helpers import runtime


def _response(http_status: int, **payload: Any) -> Response:
    return Response(
        json.dumps(payload, sort_keys=True, separators=(",", ":")),
        status=http_status,
        mimetype="application/json",
    )


class ContinuationTurn(ApiHandler):
    """Validate a formation request and execute/replay one native system turn."""

    async def process(self, input: Input, request: Request) -> Output:
        # The HTTP caller may select only an existing immutable request. It may
        # not supply protocol text or any model-facing message material.
        if not isinstance(input, dict) or set(input) != {"request_id"}:
            return _response(422, error="request_id_only")
        request_id = input.get("request_id")
        if not isinstance(request_id, str):
            return _response(422, error="request_id_is_invalid")

        try:
            config = get_plugin_config(runtime.PLUGIN_NAME, caller="api") or {}
            plan = runtime.prepare_dispatch(config, request_id)
            if plan.existing_fired is not None:
                return _response(
                    200,
                    ok=True,
                    status="already_fired",
                    request_id=request_id,
                    context_id=plan.request["context_id"],
                    formation_disposition="replayed",
                )

            engine_result = await plan.context.continuation_turn(plan.engine_request)
            state = engine_result.get("state")
            disposition = engine_result.get("disposition")
            if not engine_result.get("terminal") or disposition == "in_progress":
                return _response(
                    202,
                    ok=True,
                    status="in_progress",
                    request_id=request_id,
                    context_id=plan.request["context_id"],
                    engine_state=state,
                )
            if state != "completed":
                return _response(
                    409,
                    ok=False,
                    error="engine_turn_not_completed",
                    request_id=request_id,
                    context_id=plan.request["context_id"],
                    engine_state=state,
                )

            _fired, formation_disposition = runtime.record_fired(plan, engine_result)
            return _response(
                200,
                ok=True,
                status="fired",
                request_id=request_id,
                context_id=plan.request["context_id"],
                engine_disposition=disposition,
                formation_disposition=formation_disposition,
            )
        except (runtime.ReflexNotFoundError, ContinuationTurnNotFoundError) as exc:
            return _response(404, error=str(exc))
        except (runtime.ReflexConflictError, ContinuationTurnConflictError) as exc:
            return _response(409, error=str(exc))
        except (runtime.ReflexValidationError, ContinuationTurnValidationError) as exc:
            return _response(422, error=str(exc))
