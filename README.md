# Recursive Field — Starter Pack

**A brand-neutral, portable scaffold for instantiating bounded, self-organizing agent fields.**

---

## What Is This?

**Recursive Field** is the universal phenomenon of bounded, self-organizing agent spaces. This repository is not *the* Recursive Field; it is an **un-branded starter pack** that *produces* recursive fields.

The scaffold provides pure structural mechanics — identity, connectivity, interface boundaries, governance, state management, and container orchestration — without forcing a fixed brand name or hardcoded identity. Clone it, set your `LIBRARY` name in `.env`, and instantiate a brand-new field formation anywhere.

---

## Quick Start

```bash
# 1. Clone this repository to any path
#    (e.g., /mnt/rootfs/a0/usr/projects/my-field)

# 2. Set your library identity
cp .env.template .env
#    Edit .env: set LIBRARY=<your-name>, PORT_BASE=<your-port>

# 3. Initialize the environment
python3 init_environment.py

# 4. Create your first agent
python3 create_agent.py my-agent "Primary observation node"

# 5. Create a second agent
python3 create_agent.py my-scout "Secondary discovery node"

# 6. Connect them via mesh
python3 create_mesh.py my-mesh my-agent my-scout

# 7. Expose an interface
python3 create_gateway.py my-gw agent my-agent cli

# 8. Hydrate a profile from a seed stone
python3 hydrate_profile.py my-agent sentinel_observer

# 9. Generate Docker Compose harness
python3 generate_compose.py --port-base 44000

# 10. Activate the container entrypoint
python3 entrypoint.py my-agent

# 11. Verify graph integrity
python3 verify_unit_cell.py
```

---

## The `{LIBRARY}` Resolver Switchboard

The entire repository is parameterized around a single placeholder: **`{LIBRARY}`**. Set it in one place (`.env`) and it cascades everywhere:

```env
LIBRARY=tbc
KNOWLEDGE_DIR=state/knowledge/tbc_corpus
FIELD_ROOT=/mnt/rootfs/a0/usr/projects/tbc
PORT_BASE=44000
IMAGE_NAME=agent0ai/agent-zero:latest
```

Changing `LIBRARY` re-interpolates:
- Container service names (`${LIBRARY}-my-agent`)
- Nginx upstream proxies (`${LIBRARY}-my-agent:8000`)
- Volume mounts (`${FIELD_ROOT}/agents/...`)
- Port allocations (`PORT_BASE + idx * 100`)
- Prompt namespaces (governance profiles, include paths)

**No Python logic changes required — the cascade is purely configuration-level.**

---

## Epistemic Separation: Scaffold vs. Knowledge

| Plane | What Lives Here | Examples |
| --- | --- | --- |
| **Scaffold** | Structural scripts, compose templates, resolver | `create_agent.py`, `docker-compose.yml`, `.env` |
| **Knowledge** | Domain intelligence, memory trees | `KNOWLEDGE_DIR=state/knowledge/tbc_corpus` |

Swapping `KNOWLEDGE_DIR` alters what agents know without altering container mounts or scaffold code:

```env
KNOWLEDGE_DIR=state/knowledge/tbc_corpus    # TBC domain intelligence
KNOWLEDGE_DIR=state/knowledge/urban_ops     # Urban Operations intelligence
```

---

## Script Inventory (22 Scripts / Modules)

| Script | Function |
| --- | --- |
| `find_root.py` | Upward marker discovery (`.recursive-field-root` / `.root`) |
| `init_environment.py` | Dynamic runtime coordinate provisioning |
| `create_agent.py` | Primitive 1: Identity & Observation |
| `create_mesh.py` | Primitive 2: Connectivity |
| `create_gateway.py` | Primitive 3: Interface Boundary |
| `verify_unit_cell.py` | Graph integrity validator |
| `inspect_formation.py` | Vantage-point self-inspection (`--agent <slug> --json`) |
| `persist_state.py` | Tiered state snapshots with SHA-256 ledgers |
| `hydrate_profile.py` | Seed stone to profile.json + behaviour.md |
| `generate_compose.py` | Dynamic docker-compose.yml with `${FIELD_ROOT}` interpolation |
| `system_control.py` | Security profile switchboard (open / restricted / lockdown) |
| `build_prompt_pipeline.py` | 5-layer prompt assembly with security-filtered inclusions |
| `spawn_subordinate.py` | Parent-child hierarchy with security posture inheritance |
| `rebalance.py` | Automated topology audit, hierarchy repair, scratch pruning |
| `entrypoint.py` | Container boot: discovery to health to prompt projection to activation; optional fail-closed continuation handoff |
| `delegate_task.py` | Capability-gated task delegation across mesh queues |
| `consume_queue.py` | Bounded async worker with durable cursor, atomic claims, and allowlisted execution |
| `continuation_schema.py` | Canonical JSON, embedded-hash validation, schema checks, and atomic continuation writes |
| `resume_thread.py` | Read-only continuation eligibility classifier; only `--dry-run` is supported |
| `checkpoint_intent.py` | Explicit arming plus immutable, lock-serialized checkpoint creation and CAS intent-head advancement |
| `continuation_reflex.py` | Formation-owned immutable continuation request/claim/receipt handoff; engine actuation occurs only through the authenticated typed-turn plugin bridge |
| `generate_continuation_fixtures.py` | Deterministic test-only fields spanning all seven continuation classifications |

### Bounded Asynchronous Delegation

Legacy delegation remains the default and immediately records an acknowledgement result:

```bash
python3 delegate_task.py sender recipient mesh "payload"
```

Async mode persists a validated task envelope without creating an immediate result. The
recipient then consumes at most one eligible dispatch with the only supported adapter,
`inspect_unit_cell`:

```bash
python3 delegate_task.py sender recipient mesh "inspect the unit cell" --mode async
python3 consume_queue.py recipient mesh --once
```

Async runtime artifacts live beneath the already-ignored formation trees:
`mesh/<mesh>/{tasks,results}/`,
`agents/<agent>/worker_state/claims/<task_id>.json`, and
`agents/<agent>/worker_state/<mesh>.cursor.json`. The worker rechecks the current
`coordinate` capability before claiming work; `lockdown` leaves the task pending.
Task payloads are never interpreted as shell commands.

### Formation-Owned Intent Continuity

Continuation contracts are defined by
`schemas/continuation-intent.schema.json` and
`schemas/continuation-checkpoint.schema.json`, and
`schemas/continuation-reflex.schema.json`. Runtime instances live under the
ignored formation state tree at `state/continuations/`.
Artifacts bind canonical SHA-256 values to field genesis, opaque caller-supplied
context identity, security posture, context evidence, checkpoint ancestry, lease
state, interruption class, token-source economics, retry budget, a self-contained
work/file/Git/subordinate snapshot, and an explicit non-actuating effect boundary.

Step 2 provides classification only:

```bash
python3 resume_thread.py <intent_uuid> --dry-run \
  [--at 2026-01-01T00:05:00+00:00] [--start <field_path>] \
  [--current-token-source <source> --current-token-model capped|metered]
```

The command emits one stable canonical JSON line and classifies the intent as
`resumable`, `active`, `awaiting_human`, `terminal`, `needs_reconciliation`,
`invalid`, or `unavailable`. Output includes the resolved `checkpoint_id`,
`eligible`, sorted `reasons`, `blocking_conditions`, and explicit
`would_claim`, `would_dispatch`, `would_write`, and `would_execute` flags. The
four `would_*` fields are always `false` because Step 2 has no actuating mode;
only `resumable` is eligible, and its blocking list is empty. Exit codes are
respectively `0`, `10`, `11`, `12`, `20`, `30`, and `40`. `--at` makes lease
evaluation reproducible; when omitted, the current UTC time is used but is not
written or included in output.

`resume_thread.py` reads only the explicit formation artifacts, genesis marker,
and current control profile. It does not query Agent Zero, discover chats, claim
work, advance leases, append events, create results, start model turns, replay
effects, or mutate any file. Repeated fixed-input dry-runs therefore preserve
byte-identical runtime state.

Step 3 adds formation-side recording without crossing the Engine boundary.
Arming is explicit and requires caller-supplied opaque context identity, a
history hash, timestamps, positive formation attestation, and required
capabilities. It also snapshots interruption class, token source/model, bounded
retry policy, work vector, file state, Git commit, subordinate context IDs, and
parallel-job references:

```bash
python3 checkpoint_intent.py arm \
  --intent-id <intent_uuid> --context-id <opaque_context_id> \
  --history-sha256 <sha256> --observed-at <RFC3339> \
  --created-at <RFC3339> --required-capability observe \
  --attest-context-exists --interruption-class self_initiated \
  --token-source <source> --token-model capped \
  --maximum-retry-attempts 3 --work-vector <text> \
  --git-commit <40-hex-commit> --start <field_path>
```

`checkpoint_intent.py checkpoint` requires an expected intent hash, explicit
checkpoint UUID/time/state, and complete lease coordinates for `active` state.
Checkpoint files are immutable create-only records; exact retries are
idempotent, conflicting UUID reuse cannot overwrite, and the mutable intent
head advances under a per-intent lock with compare-and-swap. Sequence-bearing
ancestry, terminal locks, the `awaiting_human` authority barrier, current boot
identity, lease attempt/generation/timestamps, exact effect-boundary equality,
and consequential-dispatch reconciliation all fail closed. The recorder itself
performs no dispatch, model turn, chat/API operation, service change, deployment,
or external-effect replay.

For externally interrupted work, a capped-to-metered token-model change—or an
unavailable current token snapshot—classifies as `awaiting_human` (exit `11`).
Retry exhaustion also requires and classifies as `awaiting_human`; this authority
barrier is never auto-cleared.

`entrypoint.py --continuation-intent-id <uuid>` can classify an explicitly armed
intent and prepare one immutable `continuation_reflex` request. This is only a
pre-runtime handoff: it does not import Agent Zero, inspect or mutate chats, send
a user message, inject an in-memory system role, or start a model turn. The
request requires an in-process trusted adapter to verify that the existing
context is present and idle, claim one bounded attempt, inject the supplied
system protocol for `maximum_new_turns=1`, and record an immutable
`continuation_reflex_fired` receipt.

Tracked installable source for the narrow Agent Zero user-plugin boundary lives
at `agent_zero_plugins/continuation_reflex/`; `/a0/usr/plugins/continuation_reflex`
is only an ignored runtime installation. The packaged adapter independently
validates explicit request/intent/checkpoint/hash bindings, current context
existence and idleness, retry and authority barriers, token drift, boot-bound
leases, and prior claim/receipt evidence. Its authenticated, CSRF-protected API
accepts only an immutable request ID, writes a separate formation claim, and
calls Agent Zero's native `AgentContext.continuation_turn()` primitive. The
engine reserves its own durable receipt before exactly one tool-disabled model
invocation, projects only validated system protocol, never creates a user
message or enters `communicate()`/`monologue()`, and fail-closes ambiguous or
stale completion. See `agent_zero_plugins/README.md` for stopped-runtime
installation instructions.

Deterministic classification fixtures are deliberately test-only and require a
new explicit output root outside this live project:

```bash
python3 generate_continuation_fixtures.py \
  --test-only --output-root /tmp/continuation-fixtures
```

The generated manifest fixes IDs, timestamps, hashes, and boot identity while
covering `resumable`, `active`, `awaiting_human`, `terminal`,
`needs_reconciliation`, `invalid`, and `unavailable`.

### Optional systemd scheduling

[`systemd/`](systemd/) contains brand-neutral source templates for a hardened
root-run oneshot worker, a persistent approximately five-second calendar timer,
and a `docker.service` drop-in that requires the exact field-root mount before
Docker starts auto-restarted bind-mounted containers. A missing mount cannot
silently fall back to the root-disk directory. See
[`systemd/README.md`](systemd/README.md) for substitutions, validation,
installation, recovery, and rollback. These unit templates do not change the
22-script/module inventory.

---

## Security Profiles

| Profile | Capabilities | Disabled Includes |
| --- | --- | --- |
| `open` | `all` | none |
| `restricted` | `observe`, `coordinate`, `persist` | `godmode`, `plinian_matrix` |
| `lockdown` | `observe` | `godmode`, `plinian_matrix`, `system_control_tools` |

Switch at runtime without container restarts:
```bash
python3 system_control.py --agent my-agent --set-security restricted
```

---

## Architecture Specification

For the complete, authoritative architectural reference, see:

**[RECURSIVE_FIELD_SPEC.md](RECURSIVE_FIELD_SPEC.md)** — 13 sections covering all architectural invariants, verification proofs, file inventory, and script reference.

---

## Git vs. Generated Separation

**Committed (The Scaffold):**
- All 19 function-literal Python scripts/modules
- Brand-neutral `systemd/` service/timer templates and deployment instructions
- `.recursive-field-root` genesis marker
- `RECURSIVE_FIELD_SPEC.md` specification
- `state/seeds/` seed stone templates
- `state/knowledge/` knowledge backing templates
- `.gitignore` and `README.md`

**Ignored (The Runtime State):**
- `.env` resolver switchboard (instance-specific)
- `agents/`, `mesh/`, `gateways/` (runtime-created by primitives)
- `tmp/` scratch space
- `state/snapshots/`, `state/ledger.jsonl` (generated by `persist_state.py`)
- `state/control_profile.json`, `state/hierarchy.json` (runtime governance)
- `docker-compose.yml` (generated by `generate_compose.py`)
- `keys/` and secrets
- `__pycache__/` and Python caches

---

## License

Unbranded starter pack — use freely. No warranty implied.

---

## Location Agnosticism Grounded in Physical Coordinates

While `find_root.py` guarantees discovery-first location agnosticism (so the repository can be cloned anywhere without path hardcoding), persistent storage still requires deterministic host mount bindings. Anchor points like `/mnt/rootfs` bridge abstract discovery with real block devices, ensuring zero path drift across restarts and directory moves.

The container runtime (`/a0`) is treated as disposable compute. A container can be stopped, deleted, or upgraded (`docker compose down && docker compose up`) without losing the agent's identity or history. Durable identity, memory, knowledge trees, state ledgers, and logs live on persistent host mounts. If a host server dies, attaching those host mount volumes to a fresh machine allows the boot sequence (`entrypoint.py`) to rehydrate the agent's full state instantly.

---

## Structured Impermanence

The scaffold enforces a strict separation between:
- **Disposable compute** (container runtime, ephemeral scratch space)
- **Durable identity** (agent manifests, observation logs, state ledgers, knowledge trees)

This means the formation can survive container destruction, host migration, and hardware failure — as long as the persistent host mount volumes are preserved.


