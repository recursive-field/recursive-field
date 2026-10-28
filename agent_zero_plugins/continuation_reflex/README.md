# Continuation Reflex

A fail-closed, installable Agent Zero user-plugin package for Recursive Field continuation handoffs. This directory is the tracked source boundary; an installed runtime copy belongs under `/a0/usr/plugins/continuation_reflex`.

## Safety boundary

The plugin never sends a user message. Current Agent Zero source provides `AgentContext.communicate(UserMessage(...))` as the supported work-start path; even an empty message carrying `system_message` is persisted through `hist_add_user_message`. `Agent.monologue` also has no native `maximum_new_turns=1` entrypoint. Therefore this version **does not claim a request or start a model turn**.

The periodic extension can inspect explicit handoff requests only when both the plugin and its configuration are enabled. It validates:

- exact immutable request, intent-head, context, checkpoint, and hash bindings;
- `role=system`, `maximum_new_turns=1`, and `user_message_sent=false`;
- retry budget and `awaiting_human`/terminal exclusion;
- external capped-to-metered token drift;
- strict existing-context lookup and idle state;
- held lease boot identity;
- existing claims and `continuation_reflex_fired` receipts.

After validation it stops with `runtime_typed_protocol_one_turn_unsupported`. It does not write a claim or receipt. This prevents a pre-runtime formation process or plugin shim from pretending it safely injected trusted in-memory protocol material.

## Configuration

The checked-in default is inert:

```yaml
enabled: false
field_root: ""
current_token_source: ""
current_token_model: ""
scan_interval_seconds: 60
```

Do not enable the trigger until Agent Zero exposes a native framework-owned operation that can atomically:

1. resolve an existing context without creating one;
2. reject a running context;
3. inject typed trusted protocol/system material without a user-history message;
4. cap execution to exactly one model turn;
5. bind a durable claim before execution and a `continuation_reflex_fired` receipt after success.

## Source verification

From the Recursive Field checkout, static checks exercise the tracked package directly and do not install, reload, or activate it:

```bash
cd /a0/usr/projects/recursive-field
PYTHONDONTWRITEBYTECODE=1 /opt/venv-a0/bin/python -m py_compile \
  agent_zero_plugins/continuation_reflex/helpers/runtime.py \
  agent_zero_plugins/continuation_reflex/extensions/python/job_loop/_50_continuation_reflex.py
PYTHONDONTWRITEBYTECODE=1 /opt/venv-a0/bin/python -m unittest \
  agent_zero_plugins.continuation_reflex.tests.test_runtime
```

The tests resolve their plugin root from the test file itself. Set `RECURSIVE_FIELD_PROJECT_ROOT` only when the checkout is located somewhere other than `/a0/usr/projects/recursive-field`.
