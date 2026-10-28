# Continuation Reflex

An installable Agent Zero user plugin that bridges immutable Recursive Field continuation handoffs to Agent Zero's native typed continuation primitive. This directory is the tracked source boundary; an installed runtime copy belongs under `/a0/usr/plugins/continuation_reflex`.

## Safety boundary

The plugin never accepts or sends a user message. The authenticated endpoint accepts only a canonical immutable `request_id`; protocol text is resolved from the configured Recursive Field root and independently validated against the request, intent head, checkpoint, hashes, authority state, retry budget, token snapshot, and lease evidence.

The bridge calls `AgentContext.continuation_turn()` in process. The engine primitive:

- resolves an existing live context and existing durable chat coordinate only;
- requires an idle context for initial dispatch;
- reserves an engine-owned receipt before inference;
- projects hash-bound protocol as `SystemMessage` material without `UserMessage`, `hist_add_user_message`, `communicate()`, or `monologue()`;
- makes exactly one model invocation with tools disabled and transport retries set to zero;
- persists only the assistant result on unambiguous completion;
- records immutable `completed`, `failed`, `cancelled`, or `ambiguous` engine evidence.

Formation claims and `continuation_reflex_fired` receipts remain separate from engine receipts. A matching retry replays durable evidence; a retry during the same claimed native turn may return in-progress, while payload conflicts, unrelated running work, stale generations, expired or old-boot claims, and ambiguous outcomes fail closed.

The periodic extension is inspection-only. It does not claim requests or dispatch continuation turns.

## API

`POST /api/plugins/continuation_reflex/continuation_turn`

The route inherits Agent Zero's authenticated, CSRF-protected POST defaults. Its JSON body must contain exactly:

```json
{"request_id":"00000000-0000-4000-8000-000000000000"}
```

Responses:

- `202`: the identical engine reservation is still in progress;
- `200`: the turn completed and the separate formation receipt was created/replayed, or an existing formation receipt was replayed;
- `404`: the immutable request, field root, or exact existing context was not found;
- `409`: concurrency, idempotency, generation, claim, authority, or terminal engine-state conflict;
- `422`: malformed input or invalid/hash-inconsistent formation or engine evidence.

No HTTP-provided field can supply model-facing protocol text.

## Configuration

The checked-in default is inert:

```yaml
enabled: false
field_root: ""
current_token_source: ""
current_token_model: ""
scan_interval_seconds: 60
```

Enablement and runtime installation are separate operational actions and are not performed by this source package. The configured `field_root` must already exist and contain the Recursive Field marker and continuation artifacts expected by the formation validator.

## Source verification

From the Recursive Field checkout, these checks exercise tracked source directly without installing, reloading, or activating the plugin:

```bash
cd /a0/usr/projects/recursive-field
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/a0:/a0/usr/projects/recursive-field \
  /opt/venv-a0/bin/python -m py_compile \
  agent_zero_plugins/continuation_reflex/api/continuation_turn.py \
  agent_zero_plugins/continuation_reflex/helpers/runtime.py \
  agent_zero_plugins/continuation_reflex/extensions/python/job_loop/_50_continuation_reflex.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/a0:/a0/usr/projects/recursive-field \
  /opt/venv-a0/bin/python -m unittest -v \
  agent_zero_plugins.continuation_reflex.tests.test_runtime \
  agent_zero_plugins.continuation_reflex.tests.test_api
```

The tests use temporary formation roots and mocks/fakes only. They do not call the API, create chats, invoke a model, or install/activate the plugin.
