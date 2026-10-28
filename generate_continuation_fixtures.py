#!/usr/bin/env python3
"""Generate deterministic, test-only fields for all resume classifications.

Generation requires both ``--test-only`` and an explicit new ``--output-root``.
The live project state tree is always refused.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from continuation_schema import (  # noqa: E402
    advance_intent,
    atomic_write_document,
    build_checkpoint,
    build_context_evidence,
    build_intent,
    build_lease,
    build_retry_budget,
    build_token_snapshot,
    build_work_snapshot,
    canonical_json_bytes,
)

GENESIS_ID = "00000000-0000-4000-8000-000000000001"
BOOT_ID = "00000000-0000-4000-8000-000000000002"
OTHER_BOOT_ID = "00000000-0000-4000-8000-000000000003"
AT = "2026-01-01T00:05:00+00:00"
CREATED_AT = "2026-01-01T00:00:00+00:00"
RECORDED_AT = "2026-01-01T00:01:00+00:00"
CONTEXT_ID = "opaque-fixture-context"
HISTORY_SHA256 = "a" * 64
GIT_COMMIT = "c70b317ffeec568ea663e7fc5319b84cf3e69d4e"
TOKEN_SOURCE = "fixture-capped-plan"
TOKEN_MODEL = "capped"
CLASSIFICATIONS = (
    "resumable",
    "active",
    "awaiting_human",
    "terminal",
    "needs_reconciliation",
    "invalid",
    "unavailable",
)


def _uuid(number: int) -> str:
    return f"00000000-0000-4000-8000-{number:012d}"


def _write_plain(path: Path, value: Any) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(canonical_json_bytes(value) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())


def _base_field(root: Path) -> None:
    root.mkdir(mode=0o700)
    _write_plain(
        root / ".recursive-field-root",
        {
            "genesis_uuid": GENESIS_ID,
            "inception_timestamp": CREATED_AT,
            "schema_version": "1.0.0",
        },
    )
    _write_plain(
        root / "state" / "control_profile.json",
        {
            "active_security_profile": "restricted",
            "security_profiles": {
                "restricted": {"capabilities": ["observe", "persist"]}
            },
            "prompt_includes": {},
        },
    )


def _intent(number: int) -> dict[str, Any]:
    context = build_context_evidence(
        context_id=CONTEXT_ID,
        observed_at=CREATED_AT,
        history_sha256=HISTORY_SHA256,
    )
    return build_intent(
        intent_id=_uuid(100 + number),
        field_genesis_uuid=GENESIS_ID,
        context_id=CONTEXT_ID,
        created_at=CREATED_AT,
        security_profile="restricted",
        required_capabilities=["observe"],
        context_evidence=context,
        interruption_class="self_initiated",
        token_snapshot=build_token_snapshot(
            token_source=TOKEN_SOURCE,
            token_model=TOKEN_MODEL,
        ),
        retry_budget=build_retry_budget(maximum_attempts=3),
        work_snapshot=build_work_snapshot(
            work_vector="Continue the deterministic fixture work vector.",
            git_commit=GIT_COMMIT,
            file_state=[
                {"path": "resume_thread.py", "status": "unchanged", "sha256": "b" * 64}
            ],
            subordinate_context_ids=["fixture-subordinate-context"],
            parallel_references=[
                {
                    "job_id": "fixture-job",
                    "context_id": "fixture-subordinate-context",
                    "state": "success",
                    "result_ref": "fixture/result.json",
                }
            ],
        ),
    )


def _write_intent(root: Path, intent: dict[str, Any]) -> None:
    atomic_write_document(
        root / "state" / "continuations" / "intents" / f"{intent['intent_id']}.json",
        intent,
        "intent",
    )


def _with_checkpoint(
    root: Path,
    intent: dict[str, Any],
    *,
    checkpoint_number: int,
    state: str,
    lease: dict[str, Any],
) -> dict[str, Any]:
    checkpoint = build_checkpoint(
        checkpoint_id=_uuid(200 + checkpoint_number),
        intent=intent,
        recorded_at=RECORDED_AT,
        state=state,
        lease=lease,
    )
    atomic_write_document(
        root / "state" / "continuations" / "checkpoints" / f"{checkpoint['checkpoint_id']}.json",
        checkpoint,
        "checkpoint",
    )
    advanced = advance_intent(intent, checkpoint)
    _write_intent(root, advanced)
    return advanced


def generate_fixtures(output_root: Path) -> dict[str, Any]:
    """Create seven complete deterministic field roots below a new output root."""
    output_root = output_root.expanduser().resolve(strict=False)
    source = Path(__file__).resolve().parent
    forbidden = {
        source,
        (source / "state").resolve(strict=False),
        (source / "state" / "continuations").resolve(strict=False),
    }
    if output_root in forbidden or source in output_root.parents:
        raise ValueError("output root must not be the live project or one of its descendants")
    if output_root.exists():
        raise FileExistsError(f"output root already exists: {output_root}")
    output_root.mkdir(mode=0o700, parents=True)

    manifest: dict[str, Any] = {
        "at": AT,
        "boot_id": BOOT_ID,
        "current_token_source": TOKEN_SOURCE,
        "current_token_model": TOKEN_MODEL,
        "fixtures": {},
        "schema_version": "1.0.0",
    }
    for number, classification in enumerate(CLASSIFICATIONS, 1):
        root = output_root / classification
        _base_field(root)
        intent = _intent(number)
        if classification == "resumable":
            _write_intent(root, intent)
        elif classification == "active":
            _with_checkpoint(
                root,
                intent,
                checkpoint_number=number,
                state="active",
                lease=build_lease(
                    state="held",
                    holder="fixture-worker",
                    attempt_id=_uuid(300 + number),
                    generation=1,
                    boot_id=BOOT_ID,
                    acquired_at=RECORDED_AT,
                    expires_at="2026-01-01T00:10:00+00:00",
                ),
            )
        elif classification == "awaiting_human":
            _with_checkpoint(root, intent, checkpoint_number=number, state="awaiting_human", lease=build_lease())
        elif classification == "terminal":
            _with_checkpoint(root, intent, checkpoint_number=number, state="completed", lease=build_lease(state="released"))
        elif classification == "needs_reconciliation":
            _with_checkpoint(
                root,
                intent,
                checkpoint_number=number,
                state="active",
                lease=build_lease(
                    state="held",
                    holder="fixture-worker",
                    attempt_id=_uuid(300 + number),
                    generation=1,
                    boot_id=OTHER_BOOT_ID,
                    acquired_at=RECORDED_AT,
                    expires_at="2026-01-01T00:10:00+00:00",
                ),
            )
        elif classification == "invalid":
            intent["status"] = "active"  # deliberate hash mismatch
            _write_plain(
                root / "state" / "continuations" / "intents" / f"{intent['intent_id']}.json",
                intent,
            )
        elif classification == "unavailable":
            pass  # marker and control profile exist, explicit intent does not
        manifest["fixtures"][classification] = {
            "field_root": str(root),
            "intent_id": intent["intent_id"],
        }
    _write_plain(output_root / "manifest.json", manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate isolated deterministic continuation test fixtures")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--test-only", action="store_true", required=True)
    args = parser.parse_args(argv)
    try:
        manifest = generate_fixtures(Path(args.output_root))
    except (OSError, ValueError) as exc:
        sys.stdout.buffer.write(canonical_json_bytes({"error": str(exc)}) + b"\n")
        return 2
    sys.stdout.buffer.write(canonical_json_bytes(manifest) + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
