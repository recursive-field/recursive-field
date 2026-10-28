# Recursive Field Architecture Specification

**Version**: 1.0.0  
**Status**: Empirically Verified (18-step clean-sheet build)  
**Date**: 2026-10-25  
**Genesis UUID**: `c1fcb5fc-4a12-4bd5-af29-ddf52ecdc287`

---

## Table of Contents

1. [Architectural Thesis & Foundational Invariants](#1-architectural-thesis--foundational-invariants)
2. [Three-Layer Architecture](#2-three-layer-architecture)
3. [The Universal Three-Primitive Unit Cell](#3-the-universal-three-primitive-unit-cell)
4. [Tiered State, Hydration & Container Harness](#4-tiered-state-hydration--container-harness)
5. [Active Governance & Prompt Assembly](#5-active-governance--prompt-assembly)
6. [Hierarchical Lineage, Self-Maintenance & Work Dispatch](#6-hierarchical-lineage-self-maintenance--work-dispatch)
7. [Container Runtime Activation & Host-Mount Deployment](#7-container-runtime-activation--host-mount-deployment)
8. [The `{LIBRARY}` Resolver Switchboard](#8-the-library-resolver-switchboard)
9. [Function-Literal Naming Standard](#9-function-literal-naming-standard)
10. [Epistemic Separation: Scaffold vs. Knowledge](#10-epistemic-separation-scaffold-vs-knowledge)
11. [Verification Proofs & Empirical Evidence](#11-verification-proofs--empirical-evidence)
12. [Complete File Inventory](#12-complete-file-inventory)
13. [Script Reference Table](#13-script-reference-table)

---

## 1. Architectural Thesis & Foundational Invariants

### 1.1 Phenomenon vs. Scaffold

**Recursive Field** is the universal phenomenon of bounded, self-organizing agent spaces — like naming "gravity." It is not a single hardcoded project directory.

The codebase produced in Steps 1–18 is a **brand-neutral, portable starter scaffold** that *produces* recursive fields. It provides pure structural mechanics without forcing a fixed brand name or hardcoded identity. The scaffold can be cloned, renamed, and instantiated as any named field instance.

### 1.2 Discovery-First Location Agnosticism

The primary anti-pattern of legacy architectures was hardcoding absolute host paths (e.g., `/mnt/rootfs/...`) directly into scripts and compose definitions. **Field Discovery** eliminates this by placing upward marker discovery first:

- `.recursive-field-root` (or `.root`) marker file at the field root
- `find_root.py` traverses upward from cwd until it locates the marker
- The formation discovers *where* it is before asserting *what* it is
- Zero-drift portability is a foundational property, not a later patch

### 1.3 Engine vs. Formation Separation

The execution engine (Agent Zero) remains an immutable, replaceable substrate. The formation wraps it with governance, observation, and state management — without modifying the engine itself.

| Layer | Role | Mutability |
| --- | --- | --- |
| Engine (Agent Zero) | LLM execution, tool dispatch, model context | Immutable substrate |
| Formation (Recursive Field) | Governance, observation, state, topology | Active, self-adjusting |

### 1.4 Runtime Glass Box & Epistemic Separation

Structural integrity files are **read-only** (kernel-level identity manifests, channel manifests, control profiles). Observation logs and state ledgers are **append-only, writable**. This separation prevents memory corruption from destroying agent identity.

| File Class | Permissions | Examples |
| --- | --- | --- |
| Identity manifests | RO (immutable after creation) | `identity.json`, `channel.json`, `manifest.json` |
| Observation logs | Append-only (W) | `observations/log.jsonl`, `queue.jsonl`, `events.jsonl` |
| State ledgers | Append-only (W) | `state/ledger.jsonl`, `state/snapshots/` |
| Governance profiles | RW (mutable) | `state/control_profile.json`, `state/hierarchy.json` |

---

## 2. Three-Layer Architecture

The formation organizes itself across three distinct structural planes, each with its own configuration scope and resolution mechanism:

### 2.1 The Agent Layer (Local Unit Cell)

The individual agent process — its identity, private memory, and container execution environment.

| Aspect | Detail |
| --- | --- |
| **Scope** | Single agent identity, memory, observation log |
| **Config** | Agent-level `profile.json`, `behaviour.md`, `prompts/` |
| **Container** | Per-agent service definition in `docker-compose.yml` |
| **Scripts** | `create_agent.py`, `hydrate_profile.py`, `build_prompt_pipeline.py` |

### 2.2 The Mesh & Gateway Layer (Connective Tissue)

Meshes connect *multiple* endpoints, so their configuration sits outside any single agent's local boundary. Gateways manage ingress proxies and security boundaries at the host or network level.

| Layer | Scope | Config |
| --- | --- | --- |
| **Mesh** | Communication channels, event queues, peer/parent-child routes | `channel.json`, `queue.jsonl` |
| **Gateway** | Ingress proxies, security boundaries, external API endpoints | `manifest.json`, `events.jsonl`, `nginx.conf` |
| **Scripts** | `create_mesh.py`, `create_gateway.py` |

### 2.3 The Library / Macro-Field Layer (Scaffold & Potential)

The top-level space holding the entire 0-to-1 composition capability — the unbranded franchise template.

| Aspect | Detail |
| --- | --- |
| **Scope** | Root discovery, path resolution, compose harness, macro variables |
| **Config** | `field_env.json` (or `library_env.json`), `.env`, `docker-compose.yml` |
| **Scripts** | `find_root.py`, `init_environment.py`, `generate_compose.py`, `entrypoint.py` |
| **Macro Variables** | `{LIBRARY}`, `{FIELD_ROOT}`, `{PORT_BASE}` |

### 2.4 Cascading Resolution

When the library is instantiated or cloned, slotting a definition into the macro resolver cascades down into individual agent configs, gateway nginx templates, and mesh channel manifests — without touching Python logic.

```
{LIBRARY} (set once in .env / resolver switchboard)
  ├── {FIELD_ROOT} (derived from discovered root path)
  ├── {PORT_BASE} (derived from resolver)
  ├── Container names: ${LIBRARY}_sentinel, ${LIBRARY}_ingress
  ├── Volume mounts: ${FIELD_ROOT}/agents/..., ${LIBRARY}_data
  └── Prompt namespaces: governance profiles, include paths
```

---

## 3. The Universal Three-Primitive Unit Cell

The complete Unit Cell is the composed stack: **Agent** (Identity/Observation) → **Mesh** (Connectivity) → **Gateway** (Interface).

### 3.1 Primitive 1 — Identity & Observation (`create_agent.py`)

Creates an agent identity under `agents/<slug>/` with:

| Artifact | Path | Purpose |
| --- | --- | --- |
| Identity Manifest | `identity.json` | UUID4, slug, genesis UUID, role, timestamp, schema version |
| Observation Log | `observations/log.jsonl` | Append-only, seeded with `genesis_observation` event |
| Memory Namespace | `memory/` | Isolated per-agent memory directory |

**Invocation**: `python3 create_agent.py <slug> [role]`  
**Exit codes**: `0` created · `1` root not found · `2` invalid slug · `3` slug exists

### 3.2 Primitive 2 — Connectivity (`create_mesh.py`)

Binds two or more agents into a communication topology:

| Artifact | Path | Purpose |
| --- | --- | --- |
| Channel Manifest | `channel.json` | mesh_id, endpoints (slug + agent_id), channel_type |
| Event Queue | `queue.jsonl` | Append-only, seeded with `queue_initialized` |
| Bi-directional Events | Both agents' `log.jsonl` | `mesh_connected` event with counterpart details |

**Invocation**: `python3 create_mesh.py <mesh_slug> <agent_1> <agent_2> [channel_type]`  
**Exit codes**: `0` created · `1` root not found · `2` invalid slug · `3` mesh exists · `4` agent not found

### 3.3 Primitive 3 — Interface (`create_gateway.py`)

Binds an interface to an agent or mesh:

| Artifact | Path | Purpose |
| --- | --- | --- |
| Gateway Manifest | `manifest.json` | gateway_id, target_type, target_slug, target_id, gateway_type, status |
| Interface Log | `events.jsonl` | Append-only, seeded with `gateway_initialized` |
| Target Event | Target's log/queue | `gateway_attached` event |

**Invocation**: `python3 create_gateway.py <gw_slug> <target_type> <target_slug> [gw_type]`  
**Exit codes**: `0` created · `1` root not found · `2` invalid args · `3` gateway exists · `4` target not found

### 3.4 Topological Integrity & Self-Inspection

| Script | Function |
| --- | --- |
| `verify_unit_cell.py` | Full graph integrity — UUID linkages, bi-directional events, visual topology tree |
| `inspect_formation.py` | Vantage-point analyzer — live topology, event counts, `--agent <slug> --json` mode |

---

## 4. Tiered State, Hydration & Container Harness

### 4.1 Structured Impermanence & Durable Ledgers (`persist_state.py`)

Separates fast working context from immutable state snapshots:

| Artifact | Path | Purpose |
| --- | --- | --- |
| State Snapshot | `state/snapshots/snap_<timestamp>.json` | Consolidated primitive data with file hashes |
| State Ledger | `state/ledger.jsonl` | Append-only entries with snapshot_id, SHA-256 hashes, event counts |

**Invocation**: `python3 persist_state.py [--agent <slug>] [--flush]`  
**Features**: `--agent` for scoped ingestion · `--flush` for scratch cleanup preserving `field_env.json` · hashes async task envelopes and results plus recursive agent worker state (claims and cursors)

### 4.2 Seed Stone & Profile Hydration (`hydrate_profile.py`)

Expands declarative seeds into active runtime profiles:

| Artifact | Path | Purpose |
| --- | --- | --- |
| Seed Definition | `state/seeds/<seed_name>.json` | reasoning_mode, security_profile, behaviour_directives, active_prompt_includes |
| Agent Profile | `agents/<slug>/profile.json` | Seed hash, reasoning mode, security profile, hydrated timestamp |
| Behavioral Directives | `agents/<slug>/memory/behaviour.md` | Hydrated from seed's behaviour_directives |
| Prompt Files | `agents/<slug>/prompts/*.md` | Generated from active_prompt_includes |

**Invocation**: `python3 hydrate_profile.py <slug> <seed_name> [--force]`  
**Exit codes**: `0` hydrated · `1` root not found · `2` agent not found · `3` profile exists

### 4.3 Dynamic Compose Harness (`generate_compose.py`)

Emits location-agnostic `docker-compose.yml` with `${FIELD_ROOT}` interpolation:

| Feature | Mechanism |
| --- | --- |
| Path interpolation | `${FIELD_ROOT}/agents/<slug>:...` — zero hardcoded absolutes |
| Per-agent ports | `PORT_BASE + idx * 100` — no port collisions across agents |
| Nginx ingress | Auto-generated for HTTP/API gateways with upstream agent configs |
| `.env` provisioning | `FIELD_ROOT`, `PORT_BASE`, `IMAGE_NAME` — single-point definition |

**Invocation**: `python3 generate_compose.py [--out <path>] [--port-base <int>]`  

---

## 5. Active Governance & Prompt Assembly

### 5.1 Dynamic System Control Switchboard (`system_control.py`)

Late-bound security profile transitions without container restarts:

| Profile | Capabilities | Disabled Includes |
| --- | --- | --- |
| `open` | `all` | none |
| `restricted` | `observe`, `coordinate`, `persist` | `godmode`, `plinian_matrix` |
| `lockdown` | `observe` | `godmode`, `plinian_matrix`, `system_control_tools` |

**Invocation**: `python3 system_control.py [--agent <slug>] [--set-security <profile>] [--toggle-include <name>] [--status]`  
**Event**: `control_profile_changed` appended to agent observation logs

### 5.2 5-Layer System Prompt Extension Pipeline (`build_prompt_pipeline.py`)

Laminates prompt layers into a bounded system prompt with security filtering:

| Layer | Purpose | Source |
| --- | --- | --- |
| 1. Substrate Identity | Agent ID, slug, role, genesis UUID | `identity.json` + `prompts/agent_identity.md` |
| 2. Behavioral Directives | Hydrated behavioral rules | `memory/behaviour.md` |
| 3. Active Security Posture | Profile, capabilities, disabled includes | `state/control_profile.json` + `profile.json` |
| 4. Filtered Prompt Includes | Security-filtered prompt files | `prompts/*.md` (filtered by disabled_includes + flags) |
| 5. Vantage Point Anchor | Local field coordinates | `tmp/field_env.json` |

**Output**: `agents/<slug>/assembled_system_prompt.md` with byte length, token estimate, SHA-256 hash  
**Event**: `prompt_pipeline_assembled` appended to observation log  
**Invocation**: `python3 build_prompt_pipeline.py <slug> [--out-file <path>] [--json]`

---

## 6. Hierarchical Lineage, Self-Maintenance & Work Dispatch

### 6.1 Parent-Child Spawn Lineage (`spawn_subordinate.py`)

Spawns subordinate agents with mandatory security posture inheritance:

| Feature | Mechanism |
| --- | --- |
| Parent linkage | `parent_id`, `parent_slug` fields in child's `identity.json` |
| Security capping | Child `security_profile` capped to parent's active level (open > restricted > lockdown) |
| Auto-mesh | `create_mesh.py` creates parent-child channel automatically |
| Hierarchy ledger | `state/hierarchy.json` tracks nodes (parent/children) and edges (parent-child relationships) |
| Seed hydration | Optional `--seed <name` hydrates child profile from seed stone |

**Events**: `subordinate_spawned` (parent log) · `parent_attached` (child log)  
**Invocation**: `python3 spawn_subordinate.py <parent> <child> [role] [--seed <name>]`

### 6.2 Automated Rebalancing Engine (`rebalance.py`)

| Audit | What It Checks |
| --- | --- |
| Mesh topology | All `channel.json` endpoint agents exist in `agents/` |
| Gateway targets | All `manifest.json` targets (agent/mesh) exist |
| Hierarchy consistency | `hierarchy.json` nodes match `identity.json` parent fields |
| Ledger checksums | SHA-256 of identity manifests vs latest `ledger.jsonl` snapshot |

**Flags**: `--dry-run` (audit only) · `--prune-scratch` (clean tmp/) · `--repair-hierarchy` (reconstruct edges)  
**Event**: `field_rebalanced` appended to all agent observation logs  
**Invocation**: `python3 rebalance.py [--dry-run] [--prune-scratch] [--repair-hierarchy]`

### 6.3 Runtime Task Delegation Loop (`delegate_task.py`, `consume_queue.py`)

Capability-gated work dispatch supports two explicit modes:

- `acknowledge` (default): preserves the original immediate acknowledgement flow.
- `async`: atomically persists `mesh/<mesh>/tasks/<task_id>.json`, records only
  `task_dispatched`, `task_delegated`, and `task_received`, and leaves execution to
  the recipient worker.

Async envelopes bind the payload and canonical envelope SHA-256 values to sender,
recipient, mesh, genesis identity, the required `coordinate` capability, optional
active prompt hash, timestamp, task type, and execution policy.

`consume_queue.py <agent> <mesh> --once` scans from the durable
`agents/<agent>/worker_state/<mesh>.cursor.json` cursor, validates the envelope and
current identities, rechecks the current security profile, and creates an exclusive
`agents/<agent>/worker_state/claims/<task_id>.json` claim. Only the
`inspect_unit_cell` adapter under an `allowlisted` execution policy is supported;
task payloads are never executed as shell input. Completion writes a hashed result
artifact under `mesh/<mesh>/results/`, recipient-authored `task_started` plus
`task_completed`/`task_failed` observations, a `task_result` queue event, an
atomically advanced cursor, and a state snapshot. If recovery finds a valid result
artifact before cursor advancement, it reconciles missing lifecycle state without
rewriting or mutating that artifact. Lockdown or loss of `coordinate` leaves the
dispatch pending without a claim.

**Delegation invocation**: `python3 delegate_task.py <sender> <recipient> <mesh> "<payload>" [--payload-file <path>] [--mode acknowledge|async]`

**Worker invocation**: `python3 consume_queue.py <recipient> <mesh> --once`

**Delegation exit codes**: `0` delegated · `1` root not found · `2` agent/mesh not found · `3` mesh doesn't connect · `4` security violation

**Worker exit codes**: `0` completed/idle · `1` runtime failure · `2` missing agent/mesh · `3` validation rejection · `4` security halt · `5` adapter failure

When invoked as a CLI, the worker uses a non-empty `FIELD_ROOT` environment
value as its discovery start. Direct Python callers retain the explicit `start`
argument contract.

### 6.4 Formation-Owned Continuation Intent (`continuation_schema.py`, `resume_thread.py`, `checkpoint_intent.py`, `continuation_reflex.py`)

Intent continuity remains on the Formation side of the Engine/Formation
boundary. Draft 2020-12 contracts in
`schemas/continuation-intent.schema.json` and
`schemas/continuation-checkpoint.schema.json` describe explicit opt-in state;
`schemas/continuation-reflex.schema.json` describes adapter-neutral request,
claim, and fired-receipt artifacts under `state/continuations/`. Context
identifiers are opaque caller-supplied coordinates rather than inferred Engine
grammar.

`continuation_schema.py` supplies dependency-free schema enforcement, pure
constructors, stable UTF-8 canonical JSON, embedded SHA-256 sealing/validation,
timezone-aware lease validation, context-evidence binding, a complete
non-actuating effect boundary, immutable create-only publication, and
same-directory atomic writes with file and directory `fsync`. Sequence-bearing
checkpoint ancestry links every prior checkpoint by canonical UUID and hash.
Intent and checkpoint state also preserve interruption class, token source/model,
bounded retry attempts, work vector, path-and-hash file state, Git commit,
subordinate context IDs, and parallel-job/result references.

`resume_thread.py <intent_uuid> --dry-run` is a strictly read-only eligibility
classifier. It validates regular non-symlink paths confined to the field root,
genesis identity, intent/checkpoint hashes, sequences and linkage, the complete
checkpoint chain, current security profile and required capabilities, attested
context evidence, lease currency and boot identity, consequential-dispatch
reconciliation, and state/effect consistency. Its classifications and exit
codes are:

| Classification | Exit | Meaning |
| --- | ---: | --- |
| `resumable` | 0 | Explicitly armed and unclaimed; classification only |
| `active` | 10 | Active with a current held lease |
| `awaiting_human` | 11 | Explicit human gate; never resumable |
| `terminal` | 12 | Completed, cancelled, blocked, or failed |
| `needs_reconciliation` | 20 | Valid artifacts with lease, state, or security drift |
| `invalid` | 30 | Malformed, tampered, unsafe, or mislinked evidence |
| `unavailable` | 40 | Required formation artifact or current context attestation absent |

For `external` interruptions, classification requires a current token snapshot.
A saved `capped` model observed as `metered`, or an unavailable current snapshot,
returns `awaiting_human` (exit 11). Retry-budget exhaustion likewise requires
`awaiting_human`; no formation path clears that authority barrier automatically.

Output is one canonical JSON line with the resolved `checkpoint_id`,
classification, eligibility, sorted reasons, blocking conditions, and explicit
`would_claim`, `would_dispatch`, `would_write`, and `would_execute` fields. The
four `would_*` fields are invariantly false because Step 2 exposes no actuating
mode; only `resumable` is eligible, and its blocking list is empty. No generated
timestamp is emitted. `--at <ISO-8601>` fixes lease evaluation for reproducible
classification; otherwise current UTC is read but never persisted. The classifier neither scans
Engine chats nor calls an Agent Zero endpoint, and it cannot claim an intent,
advance a lease, mutate a chat, create lifecycle records, start a model turn,
replay an effect, install a service, or deploy. These omissions are the Step 2
effect boundary, not deferred side effects hidden behind dry-run.

Step 3 adds explicit formation-side recording through
`checkpoint_intent.py arm` and `checkpoint_intent.py checkpoint`. Arming requires
a caller-selected canonical intent UUID, opaque context ID, history hash,
observation and creation times, a positive formation attestation, and required
capabilities available in the active security profile, plus interruption class,
token snapshot, retry policy, and a self-contained work/file/Git/subordinate
snapshot. A checkpoint requires an expected intent SHA-256 compare-and-swap
token, a caller-selected checkpoint UUID, timestamp, state, and state-consistent
lease and dispatch evidence.

Intent heads are updated under a per-intent `flock`; checkpoint names are
immutable. Publication is create-only, exact byte-identical retries are
idempotent, and conflicting reuse cannot replace the prior inode. A checkpoint
published before an interrupted intent-head update remains recoverable: an
exact retry reuses the immutable record and completes the locked head update.
Transitions fail closed on sequence or predecessor mismatch, genesis/context/
security/effect-boundary drift, held-lease coordinate omissions, lease attempt
or boot changes during renewal, non-incrementing generation, non-extending
expiry, successors after terminal state, or progress beyond `awaiting_human`.
That human gate is an authority barrier; this recorder cannot clear it.

Held leases bind holder, attempt UUID, positive generation, Linux boot UUID,
acquisition time, and expiry. `resume_thread.py` classifies a current held lease
from a different boot as `needs_reconciliation`. Checkpoint dispatch evidence
can be `none`, `unreconciled`, or `reconciled`; an unreconciled consequential
dispatch also classifies as `needs_reconciliation`, and later ancestry may
advance only through a matching reconciliation record. The recorder never
performs the represented dispatch or any other external effect.

`generate_continuation_fixtures.py --test-only --output-root <new-path>` creates
deterministic isolated test fields and a manifest for all seven classifier
outcomes. It requires an explicit new output root and refuses the live project
and its descendants; it never writes `state/continuations` in the project.

`continuation_reflex.py` defines the narrow formation/Engine handoff without
pretending that a pre-runtime process can mutate an in-memory Agent Zero context.
An eligible explicit intent yields a deterministic immutable request carrying a
trusted system-protocol payload, `maximum_new_turns=1`,
`user_message_sent=false`, and requirements for an existing idle context. Adapter
claims and `continuation_reflex_fired` receipts are immutable and retry-bounded.
The formation module never performs injection or starts a turn.

The repository-owned installable Agent Zero package is
`agent_zero_plugins/continuation_reflex/`; `/a0/usr/plugins/continuation_reflex`
is an ignored runtime copy, not the commit boundary. The plugin validates
requests, immutable intent/checkpoint/hash bindings, strict existing-context
lookup, context idleness, retry and `awaiting_human` barriers, external token
drift, old-boot leases, and existing claim/receipt evidence. Its authenticated,
CSRF-protected POST route accepts only a request ID, creates or replays a
formation-owned claim, and invokes the framework-owned
`AgentContext.continuation_turn()` primitive in process. The engine separately
reserves durable idempotency evidence before one tool-disabled model call,
projects the validated protocol as system material without a `UserMessage` or
normal monologue-loop entry, and records terminal or ambiguous engine evidence.
Only completed engine evidence permits the plugin to publish the separate
`continuation_reflex_fired` receipt. Installation is an explicit stopped-runtime
copy or normal plugin-manager operation, as documented in
`agent_zero_plugins/README.md`.

### 6.5 Optional systemd queue scheduling

`systemd/queue-worker.service.in`, `systemd/queue-worker.timer.in`, and the
`systemd/docker.service.d/field-root.conf.in` drop-in are brand-neutral
rendered-unit sources, not additional scripts. One rendered worker pair binds an
exact agent/mesh pair to an exact deployed field-root mount. The oneshot service
uses `RequiresMountsFor=` plus a `mountpoint` `ExecCondition` so an absent mount
cannot degrade into writes to a fallback directory. The Docker drop-in makes
the same mount a prerequisite for daemon startup, preventing auto-restarted
bind-mounted containers from starting against that fallback. The worker invokes
`consume_queue.py --once` under nonblocking `flock`; lock contention and
lockdown are successful unit outcomes. The persistent calendar timer follows
wall-clock boundaries at seconds `00/5`. After downtime it coalesces missed
boundaries into one catch-up activation rather than replaying every interval;
the next regular boundary may follow in less than five seconds. The oneshot
service and lock prevent overlapping worker execution.

For the first deployment the service explicitly uses `root`: durable runtime
files are currently root-owned and ACL tooling is unavailable. This avoids an
implicit ownership/mode migration while constraining the worker with a private
mount/network namespace, no capabilities or privilege gain, strict system/home
protection, and writes limited to the exact field root and private runtime lock
directory. Rendering, validation, installation, and rollback are specified in
`systemd/README.md`.

---

## 7. Container Runtime Activation & Host-Mount Deployment

### 7.1 Container Entrypoint Activation (`entrypoint.py`)

Bridges governance to live runtime at container boot:

| Step | Action |
| --- | --- |
| 1. Container Field Discovery | `find_root()` from cwd or `/a0/` + `init_environment()` path validation |
| 2. Health Audit | `rebalance.py --dry-run` (unless `--skip-rebalance`) |
| 3. System Prompt Assembly | `build_prompt_pipeline.py <slug>` generates governance-aware prompt |
| 4. Native Prompt Projection | Copies assembled prompt to `prompts/system_prompt.md` for later framework loading; does not enter a context loop |
| 5. Optional Continuation Handoff | Classifies one explicit intent and prepares an immutable adapter request; no chat or model action |
| 6. Activation Event | `container_activated` with hostname, prompt hash, security profile |

**Invocation**: `python3 entrypoint.py <slug> [--dry-run] [--skip-rebalance] [--continuation-intent-id <uuid> --continuation-at <RFC3339> --continuation-boot-id <uuid> --current-token-source <source> --current-token-model capped|metered]`

### 7.2 Host-Mount Verification

Zero-drift portability validated across:

| Relocation | Result |
| --- | --- |
| `/a0/usr/projects/recursive-field` → `/tmp/recursive-field-relocated` | ✅ Zero drift — all paths re-resolved |
| `/a0/usr/projects/recursive-field` → `/tmp/mnt_rootfs_test/recursive-field` | ✅ Zero drift — host mount simulation |

Both relocations confirmed: `.env` and `field_env.json` update seamlessly, UUID linkages intact, SHA-256 checksums match, `verify_unit_cell.py` exits 0.

---

## 8. The `{LIBRARY}` Resolver Switchboard

### 8.1 Single-Point Definition

The entire repository is variableized around a single placeholder slot: **`{LIBRARY}`** (or `${LIBRARY}`).

When a user clones the starter pack, they set their chosen instance name in **one location** — the Resolver Switchboard (`.env` / `field_env.json`):

```env
LIBRARY=tbc
FIELD_ROOT=/mnt/rootfs/a0/usr/projects/tbc
PORT_BASE=44000
IMAGE_NAME=agent0ai/agent-zero:latest
```

### 8.2 Cascading Resolution

Modifying the `{LIBRARY}` entry cascades dynamically across the entire stack:

| Cascade Target | Variable Interpolation |
| --- | --- |
| Container & service names | `${LIBRARY}_sentinel`, `${LIBRARY}_ingress` |
| Volume & VFS mounts | `${FIELD_ROOT}`, `${LIBRARY}_data` |
| Port allocations | `${PORT_BASE}` dynamic offset mapping |
| Prompt & profile namespaces | Governance posture, include paths |

No Python logic changes required — the cascade is purely configuration-level.

### 8.3 Forward/Backward Harmonization

Adjusting any slider in the Resolver Switchboard triggers automatic self-adjustment:
- Security profile shift → prompt pipeline re-laminates, observation logs record the change
- `{LIBRARY}` rename → container names, volume paths, and compose specs re-interpolate
- Port base shift → per-agent host port offsets recalculate
- `rebalance.py` maintains graph equilibrium across all adjustments

---

## 9. Function-Literal Naming Standard

### 9.1 Principle

Every unit cell is itself a bounded field. Naming scripts for their **literal function** (not for a specific field instance) ensures the library remains completely neutral and reusable across cloned or nested instances.

### 9.2 Refactored Names

| Step 18 Name | Refactored Literal Name | Function |
| --- | --- | --- |
| `find_root.py` | `find_root.py` | Upward marker discovery |
| `init_environment.py` | `init_environment.py` | Dynamic runtime coordinate provisioning |
| `entrypoint.py` | `entrypoint.py` | Container boot, health preflight, prompt injection |
| `rebalance.py` | `rebalance.py` | Graph topology audit, hierarchy repair, scratch pruning |

All other scripts (`create_agent.py`, `create_mesh.py`, `create_gateway.py`, `verify_unit_cell.py`, `inspect_formation.py`, `persist_state.py`, `hydrate_profile.py`, `generate_compose.py`, `system_control.py`, `build_prompt_pipeline.py`, `spawn_subordinate.py`, `delegate_task.py`, `consume_queue.py`) are already function-literal — no changes required.

### 9.3 Marker File Compatibility

The root marker file `.recursive-field-root` may be dual-compatible with a generic `.root` marker for full brand-neutrality. The `find_root.py` discovery mechanism checks for both.

---

## 10. Epistemic Separation: Scaffold vs. Knowledge

### 10.1 Two Planes

| Plane | What Lives Here | Examples |
| --- | --- | --- |
| **Scaffold** | Structural scripts, compose templates, resolver config | `create_agent.py`, `docker-compose.yml`, `.env` |
| **Knowledge** | Domain intelligence, manuals, memory trees | `KNOWLEDGE_DIR=tbc_corpus`, `behaviour.md` content |

### 10.2 Swappable Knowledge Backings

Knowledge trees are swapped at the resolver layer using variables like `KNOWLEDGE_DIR=tbc_corpus`. Swapping knowledge files alters domain intelligence instantly without breaking container mounts or modifying scaffold code.

```env
# Same scaffold, different knowledge domain:
KNOWLEDGE_DIR=tbc_corpus    # → loads TBC domain intelligence
KNOWLEDGE_DIR=urban_ops     # → loads Urban Operations intelligence
```

### 10.3 Equality-Sign Promotion

The resolver uses `KEY = VALUE` pairs to promote knowledge bindings above the structural layer. The scaffold never hardcodes knowledge paths — it references `{KNOWLEDGE_DIR}` and the resolver fills in the value.

---

## 11. Verification Proofs & Empirical Evidence

### 11.1 Build Summary

| Metric | Value |
| --- | --- |
| Total scripts/modules | 22 |
| Active agents | 3 (`field-sentinel`, `field-scout`, `sentinel-sub-1`) |
| Active meshes | 2 (`sentinel-scout-mesh`, `field-sentinel-sentinel-sub-1-mesh`) |
| Active gateways | 2 (`sentinel-cli-gw`, `mesh-api-gw`) |
| Total observation events | 27+ (across all agent logs) |
| Relocations tested | 2 (both with zero drift) |

### 11.2 Step-by-Step Verification Results

| Step | Script | Exit Code | Key Verification |
| --- | --- | --- | --- |
| 1 | `find_root.py` | 0 | Nested discovery + external failure (exit 1) |
| 2 | `init_environment.py` | 0 | 5 dirs created, `field_env.json` accurate |
| 3 | `create_agent.py` | 0 | Identity + observation log + duplicate prevention (exit 3) |
| 4 | `create_mesh.py` | 0 | Channel + queue + bi-directional events + duplicate prevention |
| 5 | `create_gateway.py` | 0 | Agent + mesh targets + gateway_attached events + duplicate prevention |
| 6 | `verify_unit_cell.py` | 0 | Full graph integrity — UNIT CELL INTEGRITY OK |
| 7 | `inspect_formation.py` | 0 | Global + agent vantage point with `--json` |
| 8 | `persist_state.py` | 0 | Snapshot + SHA-256 ledger + `--agent` scoping + `--flush` |
| 9 | `hydrate_profile.py` | 0 | Seed → profile.json + behaviour.md + prompt files + observation event |
| 10 | `generate_compose.py` | 0 | `${FIELD_ROOT}` interpolation + per-agent ports + nginx ingress |
| 11 | *(relocation)* | 0 | Zero-drift: copy → re-orient → verify → persist → checksum match |
| 12 | `system_control.py` | 0 | Security profiles + `--status` + `control_profile_changed` event |
| 13 | `build_prompt_pipeline.py` | 0 | 5 layers + token budgeting + SHA-256 hash + lockdown filtering |
| 14 | `spawn_subordinate.py` | 0 | Parent-child + security capping + auto-mesh + hierarchy ledger |
| 15 | `rebalance.py` | 0 | Topology audit + hierarchy repair + multi-agent events |
| 16 | `entrypoint.py` | 0 | Discovery → health → prompt projection → optional fail-closed continuation handoff → activation event |
| 17 | *(host mount)* | 0 | Full lifecycle at `/tmp/mnt_rootfs_test/recursive-field` — zero drift |
| 18 | `delegate_task.py` | 0/4 | Delegation + queue events + bi-directional logs + lockdown gate (exit 4) |
| 19 | `consume_queue.py` | 0/3/4/5 | Once-only execution + replay/tamper/lockdown handling + persisted result |
| 20 | `checkpoint_intent.py` | 0/3/4/5 | Explicit arm/checkpoint recording, immutable checkpoint publish, locked CAS head update |
| 21 | `continuation_reflex.py` | N/A | Formation-owned request/claim/fired-receipt handoff consumed by the authenticated typed-turn plugin bridge |
| 22 | `generate_continuation_fixtures.py` | 0/2 | Test-only deterministic fixtures for all seven classifications |

### 11.3 Portability Proof

| Relocation | `.env` Updated | `field_env.json` Updated | UUID Linkages | SHA-256 Match | `verify_unit_cell` |
| --- | --- | --- | --- | --- | --- |
| `/tmp/recursive-field-relocated` | ✅ | ✅ | ✅ intact | ✅ 9/10 match (1 expected log growth) | ✅ exit 0 |
| `/tmp/mnt_rootfs_test/recursive-field` | ✅ | ✅ | ✅ intact | ✅ all match | ✅ exit 0 |

---

## 12. Complete File Inventory

### 12.1 Core Scripts

```
/a0/usr/projects/recursive-field/
├── find_root.py          # Root discovery (→ find_root.py)
├── init_environment.py   # Environment init (→ init_environment.py)
├── create_agent.py             # Primitive 1: Identity & Observation
├── create_mesh.py              # Primitive 2: Connectivity
├── create_gateway.py           # Primitive 3: Interface
├── verify_unit_cell.py         # Graph integrity validator
├── inspect_formation.py        # Vantage-point self-inspection
├── persist_state.py            # Tiered state & SHA-256 ledger
├── hydrate_profile.py          # Seed stone & profile hydration
├── generate_compose.py         # Dynamic Docker Compose harness
├── system_control.py           # Security profile switchboard
├── build_prompt_pipeline.py    # 5-layer prompt assembly pipeline
├── spawn_subordinate.py        # Parent-child hierarchy spawn
├── rebalance.py          # Self-maintenance (→ rebalance.py)
├── entrypoint.py         # Container entrypoint (→ entrypoint.py)
├── delegate_task.py            # Task delegation primitive
├── consume_queue.py            # Bounded async queue worker
├── continuation_schema.py      # Continuation schema/hash/write contracts
├── resume_thread.py            # Read-only continuation dry-run classifier
├── checkpoint_intent.py        # Explicit formation-side arm/checkpoint recorder
├── continuation_reflex.py      # Adapter-neutral continuation handoff/audit contract
├── generate_continuation_fixtures.py # Deterministic test-only fixture fields
├── schemas/
│   ├── continuation-intent.schema.json
│   ├── continuation-checkpoint.schema.json
│   └── continuation-reflex.schema.json
├── agent_zero_plugins/         # Tracked installable plugin packages (not formation scripts)
│   ├── README.md               # Packaging/install boundary
│   └── continuation_reflex/    # Authenticated typed-turn bridge plugin source
│       ├── plugin.yaml
│       ├── default_config.yaml
│       ├── hooks.py
│       ├── api/continuation_turn.py
│       ├── helpers/runtime.py
│       ├── extensions/python/job_loop/_50_continuation_reflex.py
│       └── tests/{test_runtime.py,test_api.py}
├── systemd/                    # Optional rendered host scheduler (not scripts)
│   ├── docker.service.d/
│   │   └── field-root.conf.in  # Docker exact-mount prerequisite drop-in
│   ├── queue-worker.service.in # Hardened bounded worker template
│   ├── queue-worker.timer.in   # Persistent five-second calendar timer template
│   └── README.md               # Render, install, recovery, and rollback
├── .recursive-field-root       # Genesis marker
├── .env                        # Resolver switchboard
└── docker-compose.yml          # Generated compose spec
```

### 12.2 Agent Structure

```
agents/
├── field-sentinel/
│   ├── identity.json           # Agent ID, slug, genesis, role, parent fields
│   ├── profile.json            # Hydrated from seed (security, reasoning mode)
│   ├── assembled_system_prompt.md  # 5-layer laminated prompt
│   ├── observations/
│   │   └── log.jsonl          # Append-only observation log
│   ├── memory/
│   │   └── behaviour.md       # Behavioral directives from seed
│   └── prompts/
│       ├── system_prompt.md   # Native injection target
│       ├── agent_identity.md  # Identity include
│       └── config_first_orientation.md  # Orientation include
├── field-scout/
│   ├── identity.json
│   ├── observations/log.jsonl
│   └── memory/
└── sentinel-sub-1/
    ├── identity.json           # Includes parent_id, parent_slug
    ├── profile.json
    ├── observations/log.jsonl
    ├── memory/behaviour.md
    └── prompts/
```

### 12.3 Mesh & Gateway Structure

```
mesh/
├── sentinel-scout-mesh/
│   ├── channel.json           # mesh_id, endpoints, channel_type
│   └── queue.jsonl            # Append-only event queue
└── field-sentinel-sentinel-sub-1-mesh/
    ├── channel.json
    └── queue.jsonl

gateways/
├── sentinel-cli-gw/
│   ├── manifest.json          # gateway_id, target (agent), type (cli)
│   └── events.jsonl
└── mesh-api-gw/
    ├── manifest.json          # gateway_id, target (mesh), type (http)
    ├── events.jsonl
    └── nginx.conf             # Auto-generated ingress config
```

### 12.4 State Structure

```
state/
├── control_profile.json       # Active security profile + prompt includes
├── hierarchy.json             # Parent-child node graph + edges
├── ledger.jsonl               # Append-only SHA-256 state ledger
├── continuations/             # Ignored formation-owned runtime instances
│   ├── intents/<intent_uuid>.json
│   ├── checkpoints/<checkpoint_uuid>.json
│   ├── locks/<intent_uuid>.lock
│   └── reflex/{requests,claims,receipts}/
├── seeds/
│   └── sentinel_observer.json  # Default seed stone definition
└── snapshots/
    └── snap_<timestamp>.json  # Atomic state snapshots
```

---

## 13. Script Reference Table

| Script | Invocation | Exit Codes | Dependencies |
| --- | --- | --- | --- |
| `find_root.py` | `python3 find_root.py [start]` | 0 found · 1 not found | None |
| `init_environment.py` | `python3 init_environment.py [start]` | 0 init · 1 no root · 2 bad marker | `find_root` |
| `create_agent.py` | `python3 create_agent.py <slug> [role]` | 0 created · 1 no root · 2 bad slug · 3 exists | `find_root` |
| `create_mesh.py` | `python3 create_mesh.py <mesh> <a1> <a2> [type]` | 0 created · 1 no root · 2 bad · 3 exists · 4 no agent | `find_root` |
| `create_gateway.py` | `python3 create_gateway.py <gw> <type> <target> [gw_type]` | 0 created · 1 no root · 2 bad · 3 exists · 4 no target | `find_root` |
| `verify_unit_cell.py` | `python3 verify_unit_cell.py [start]` | 0 OK · 1 no root · 2 integrity fail | `find_root` |
| `inspect_formation.py` | `python3 inspect_formation.py [--agent <slug>] [--json]` | 0 OK · 1 no root · 2 error | `find_root` |
| `persist_state.py` | `python3 persist_state.py [--agent <slug>] [--flush]` | 0 OK · 1 no root · 2 no env | `find_root` |
| `hydrate_profile.py` | `python3 hydrate_profile.py <slug> <seed> [--force]` | 0 OK · 1 no root · 2 bad · 3 exists | `find_root` |
| `generate_compose.py` | `python3 generate_compose.py [--out <path>] [--port-base <int>]` | 0 OK · 1 no root · 2 no env | `find_root` |
| `system_control.py` | `python3 system_control.py [--agent <s>] [--set-security <p>] [--toggle-include <n>] [--status]` | 0 OK · 1 no root · 2 bad | `find_root` |
| `build_prompt_pipeline.py` | `python3 build_prompt_pipeline.py <slug> [--out-file <path>] [--json]` | 0 OK · 1 no root · 2 no agent | `find_root` |
| `spawn_subordinate.py` | `python3 spawn_subordinate.py <parent> <child> [role] [--seed <name>]` | 0 spawned · 1 no root · 2 bad · 3 exists · 4 security | `find_root`, `create_agent`, `create_mesh`, `hydrate_profile` |
| `rebalance.py` | `python3 rebalance.py [--dry-run] [--prune-scratch] [--repair-hierarchy]` | 0 OK · 1 no root · 2 critical fail | `find_root` |
| `entrypoint.py` | `python3 entrypoint.py <slug> [--dry-run] [--skip-rebalance] [--continuation-intent-id <uuid> ...]` | 0 activated · 1 no root · 2 no agent · 3 health fail | `find_root`, `build_prompt_pipeline`, `rebalance`, `init_environment`, `continuation_reflex` |
| `delegate_task.py` | `python3 delegate_task.py <sender> <recipient> <mesh> "<payload>" [--payload-file <path>] [--mode acknowledge|async]` | 0 delegated · 1 no root · 2 no agent/mesh · 3 no connection · 4 security | `find_root` |
| `consume_queue.py` | `python3 consume_queue.py <recipient> <mesh> --once` | 0 done/idle · 1 runtime · 2 missing · 3 validation · 4 security halt · 5 adapter failure | `find_root`, `verify_unit_cell`, `persist_state` |
| `continuation_schema.py` | Imported formation library | N/A | Standard library; checked-in schemas |
| `resume_thread.py` | `python3 resume_thread.py <intent_uuid> --dry-run [--at <ISO-8601>] [--boot-id <uuid>] [--current-token-source <source> --current-token-model capped|metered] [--start <path>]` | 0 resumable · 10 active · 11 human · 12 terminal · 20 reconcile · 30 invalid · 40 unavailable | `find_root`, `continuation_schema` |
| `checkpoint_intent.py` | `python3 checkpoint_intent.py arm ...` or `python3 checkpoint_intent.py checkpoint <intent_uuid> ...` | 0 recorded/idempotent · 3 invalid · 4 conflict · 5 unavailable | `find_root`, `continuation_schema`, `resume_thread` validation helpers |
| `continuation_reflex.py` | Imported formation handoff library | N/A | `continuation_schema`, `resume_thread`; consumed by the authenticated plugin bridge, while engine dispatch remains owned by `AgentContext.continuation_turn()` |
| `generate_continuation_fixtures.py` | `python3 generate_continuation_fixtures.py --test-only --output-root <new-path>` | 0 generated · 2 refused/invalid | `continuation_schema` |

---

*End of Recursive Field Architecture Specification v1.0.0*