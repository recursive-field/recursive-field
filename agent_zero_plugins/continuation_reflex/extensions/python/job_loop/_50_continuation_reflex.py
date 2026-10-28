"""Periodic fail-closed inspection of explicit continuation handoffs."""

from __future__ import annotations

from typing import Any

from helpers.extension import Extension
from helpers.plugins import get_plugin_config
from helpers.print_style import PrintStyle
from usr.plugins.continuation_reflex.helpers.runtime import scan_once


class ContinuationReflexJob(Extension):
    async def execute(self, data: dict[str, Any] | None = None, **kwargs: Any) -> None:
        config = get_plugin_config("continuation_reflex", caller="agent") or {}
        results = scan_once(config)
        for result in results:
            if result.disposition in {"invalid", "blocked"}:
                PrintStyle.warning(
                    "Continuation reflex did not fire: "
                    f"{result.request_id or '<unknown>'}: {', '.join(result.reasons)}"
                )
