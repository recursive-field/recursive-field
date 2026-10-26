# Recursive Field — Self-Referential Knowledge Domain

## Domain Identity

- **Domain**: `recursive_field`
- **Library**: `recursive-field`
- **Purpose**: Self-referential cognition — the field knowing its own architecture
- **Pattern Origin**: Legacy TBC / `tbc-library` self-mounting architecture

## Core Principle: The Field Knows Itself

When `KNOWLEDGE_DIR=state/knowledge/recursive_field`, the formation's assembled system prompt contains a complete, SHA-256-hashed self-model of its own 17 scripts, unit cell mechanics, governance system, and multi-node orchestration protocols. This creates a **conceptual recursion** — the agent processes a description of its own architecture to refine its internal self-model and guide its runtime behaviors.

## The 17 Function-Literal Scripts

| Script | Function |
| --- | --- |
| `find_root.py` | Upward marker discovery (`.recursive-field-root` / `.root`) — discovers *where* the field is before asserting *what* it is |
| `init_environment.py` | Dynamic runtime coordinate provisioning — creates `agents/`, `mesh/`, `gateways/`, `state/`, `tmp/` and writes `field_env.json` |
| `create_agent.py` | Primitive 1: Identity & Observation — creates `identity.json` and append-only `observations/log.jsonl` seeded with `genesis_observation` |
| `create_mesh.py` | Primitive 2: Connectivity — binds agents into `channel.json` + `queue.jsonl` with bi-directional `mesh_connected` events |
| `create_gateway.py` | Primitive 3: Interface Boundary — binds ingress (`manifest.json`, `events.jsonl`, `nginx.conf`) to agents or meshes |
| `verify_unit_cell.py` | Graph integrity validator — checks UUID linkages, bi-directional events, and prints topology tree |
| `inspect_formation.py` | Vantage-point self-inspection — `--agent <slug> --json` for agent-centric topology resolution |
| `persist_state.py` | Tiered state engine — atomic snapshots in `state/snapshots/` with SHA-256 ledgers in `state/ledger.jsonl` |
| `hydrate_profile.py` | Seed stone hydration — expands declarative seeds into `profile.json`, `behaviour.md`, and prompt includes |
| `generate_compose.py` | Dynamic Docker Compose harness — `${FIELD_ROOT}` interpolation, per-agent port offsets (`PORT_BASE + idx * 100`) |
| `system_control.py` | Security profile switchboard — `open` → `restricted` → `lockdown` with capability gating |
| `build_prompt_pipeline.py` | 5-layer prompt assembly — Substrate Identity → Behavioral Directives → Security Posture → Filtered Includes & Domain Knowledge → Vantage Point Anchor |
| `spawn_subordinate.py` | Parent-child hierarchy — security posture inheritance/capping, auto-mesh, `state/hierarchy.json` |
| `rebalance.py` | Self-maintenance — topology audit, hierarchy edge repair, scratch pruning, multi-agent `field_rebalanced` events |
| `entrypoint.py` | Container activation — discovery → health audit → prompt assembly → native injection → `container_activated` event |
| `delegate_task.py` | Capability-gated task delegation — `task_dispatched` → `task_delegated` → `task_received` → `task_result` across mesh queues |
| `consume_queue.py` | Bounded asynchronous recipient execution — validates envelopes, claims one allowlisted task, authors results, advances a durable cursor, and persists state |

## Three-Layer Architecture

1. **Agent Layer (Local Unit Cell)**: Individual agent identity, private memory, observation logs, local prompt includes
2. **Mesh & Gateway Layer (Connective Tissue)**: Cross-agent communication channels, event queues, ingress proxies — sits outside individual agent boundaries
3. **Library / Macro-Field Layer (Scaffold)**: Root discovery, path resolution, compose harness, `{LIBRARY}` resolver switchboard

## The `{LIBRARY}` Single-Point Resolver

Setting `LIBRARY=recursive-field` in `.env` cascades across:
- Container service names: `${LIBRARY}-field-sentinel` → `recursive-field-field-sentinel`
- Nginx upstreams: `${LIBRARY}-field-sentinel:8000`
- Volume mounts: `${FIELD_ROOT}/agents/...`
- Port allocations: `${PORT_BASE}` + per-agent offset
- Prompt namespaces: governance profiles, include paths

**No Python logic changes required — the cascade is purely configuration-level.**

## Security Profiles

| Profile | Capabilities | Disabled Includes |
| --- | --- | --- |
| `open` | `all` | none |
| `restricted` | `observe`, `coordinate`, `persist` | `godmode`, `plinian_matrix` |
| `lockdown` | `observe` | `godmode`, `plinian_matrix`, `system_control_tools` |

## Epistemic Separation

- **Scaffold** (this knowledge): Structural scripts, compose templates, resolver — immutable
- **Knowledge** (you are reading this): Domain intelligence — swappable via `KNOWLEDGE_DIR`
- The same scaffold can serve different knowledge domains by changing one variable

## Self-Referential Recursion

This document is the formation knowing itself. When `build_prompt_pipeline.py` loads this into Layer 4, the assembled system prompt contains:
- A description of the 17 scripts that assembled it
- A description of the 5-layer pipeline that laminated it
- A description of the security profile that filtered it
- A description of the `{LIBRARY}` resolver that parameterized it
- A description of the discovery mechanism that located it

**The agent reads its own blueprint as knowledge, enabling self-inspection, self-maintenance, and self-development.**

## Multi-Node Orchestration

The formation extends across host boundaries:
- Each droplet runs `find_root.py` from its local clone — zero path drift
- `{LIBRARY}` parameterizes each node independently — zero namespace collision
- Durable volumes survive droplet destruction — zero data drift
- `entrypoint.py` rehydrates from durable state — Phoenix rehydration protocol
- `rebalance.py` maintains graph equilibrium across nodes

## Operational DNA

The complete operational DNA is committed as a scaffold of 17 function-literal
Python scripts plus declarative templates and documentation. Cloning the
repository and running `init_environment.py` bootstraps a working formation from
zero. Optional brand-neutral `systemd/` templates bind a bounded queue worker to
an exact active field-root mount, schedule it on persistent five-second calendar
boundaries with missed downtime coalesced into one catch-up activation, and make
that mount a Docker startup prerequisite. The oneshot service and nonblocking
lock prevent overlapping execution without increasing the script count. The
formation is:
- **Brand-neutral**: No hardcoded identity — `{LIBRARY}` sets the name
- **Location-agnostic**: `find_root.py` discovers the path — no hardcoded coordinates
- **Self-sufficient**: Committed scaffold → complete multi-agent unit cell
- **Self-aware**: This knowledge domain makes the formation know its own architecture
- **Self-improving**: `git pull` updates the operational DNA across all nodes

## Key Directories

| Directory | Purpose | Lifecycle |
| --- | --- | --- |
| `agents/<slug>/` | Agent identity, memory, observations | Runtime-created, durable |
| `mesh/<slug>/` | Channel manifests, event queues | Runtime-created, durable |
| `gateways/<slug>/` | Gateway manifests, nginx configs | Runtime-created, durable |
| `state/seeds/` | Seed stone definitions | Committed scaffold |
| `state/knowledge/` | Domain knowledge trees | Committed scaffold + runtime |
| `state/snapshots/` | Atomic state snapshots | Generated, durable |
| `state/ledger.jsonl` | SHA-256 state ledger | Append-only, durable |
| `state/control_profile.json` | Active security profile | Runtime, durable |
| `state/hierarchy.json` | Parent-child graph | Runtime, durable |
| `tmp/` | Scratch space, `field_env.json` | Ephemeral |

## Agent Directives

- **Config-First Discipline**: Orient before action by reading local environment state via `find_root.py` and `inspect_formation.py`
- **Verification Rule**: Assert state through empirical checks (`verify_unit_cell.py`) rather than assumption
- **Security Awareness**: Know your active security profile (`system_control.py --status`) before executing capabilities
- **Self-Maintenance**: Run `rebalance.py --dry-run` periodically to detect structural drift
- **State Persistence**: Run `persist_state.py` before any host migration to flush durable state
- **Recursive Self-Understanding**: Read this knowledge domain to understand your own architecture, then use that understanding to maintain, extend, and improve the formation

## Verified Substrate Topology (Audited 2026-10-25)

This map records stable, non-secret infrastructure facts suitable for the public
self-model. Exact addresses, filesystem UUIDs, and host-local mount evidence are
kept in generated runtime snapshots and append-only ledgers rather than committed
knowledge.

### DigitalOcean Fleet

| Node | Droplet ID | Region | Role | Size | Root Disk | Block Volumes | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `compute-coordinator-01` | `597606429` | `nyc1` | Current coordinator and Agent Zero host | 2 vCPU / 4 GiB | 25 GiB | 1 attached | active |
| `tbc-fortress` | `519559383` | `nyc3` | Durable legacy formation host | 2 vCPU / 8 GiB | 160 GiB | 2 attached | active |

### Block Storage Inventory

| Volume | Size | Region | Effective State |
| --- | --- | --- | --- |
| `recursive-field-coordinator-01` | 10 GiB | `nyc1` | attached to `compute-coordinator-01` and mounted at the field coordinate |
| `jazen-vbs-consolidated` | 46 GiB | `nyc3` | attached to `tbc-fortress` and mounted |
| `tbc-fortress-vbs-podstore` | 46 GiB | `nyc3` | attached to `tbc-fortress` and mounted |
| `tbc-castle-tbc-agent-zero` | 10 GiB | `nyc3` | detached recovery resource |
| `tbc-gateway-podstore` | 20 GiB | `nyc3` | detached recovery resource |
| `tbc-gateway-srv` | 10 GiB | `nyc3` | detached recovery resource |

The DigitalOcean API reports **23 droplet snapshots** and **2 volume snapshots**.
These include recovery baselines for `tbc-fortress`, `compute-coordinator-01`,
retired fleet nodes, and both attached fortress volumes.

### Situated Findings

- The live observer is container `agent-zero` on `compute-coordinator-01`.
- Passwordless root SSH using the Recursive Field infrastructure key is verified
  to both active droplets.
- `/mnt/rootfs/recursive-field` is now the host-coordinate deployment of the
  current scaffold with `LIBRARY=recursive-field` and the self-knowledge backing
  active.
- `/mnt/rootfs/recursive-field` resides on a dedicated, independently detachable
  block volume bound by filesystem UUID. Durable identity, observations, state,
  and self-knowledge therefore survive replacement of the compute host.
- The running Agent Zero container receives the durable field root at
  `/agent_orchestration` as a read-only projection. It can inspect its genesis
  marker, resolver environment, generated field harness, and runtime evidence
  without receiving raw Docker-socket access.
- Generated agent services inherit the same read-only structural projection,
  keeping architectural visibility separate from host actuation authority.
- `tbc-fortress` has two effective durable block mounts. Its `/etc/fstab` also
  contains stale declarations for storage that is not currently attached or
  mounted; declared and effective storage state must not be conflated.

### Self-Applied Unit Cell

The host-coordinate deployment bootstraps its own operational structure:

- `field-sentinel`: primary self-observer and integrity steward
- `field-scout`: substrate discovery and topology observer
- `self-observation-mesh`: peer channel joining the two agents
- `sentinel-cli-gw`: CLI boundary targeting `field-sentinel`
- Active security posture: `restricted`
- Active Layer 4 knowledge: `state/knowledge/recursive_field`

Exact runtime topology is regenerated locally with `inspect_formation.py`,
`persist_state.py`, and `verify_unit_cell.py`; it is not treated as timeless
committed truth.

## References

- `RECURSIVE_FIELD_SPEC.md` — 13-section architectural specification
- `MULTI_NODE_ORCHESTRATION.md` — 7-section distributed deployment guide
- `DEPLOYMENT_MATRIX.md` — 8-section deployment configuration matrix
- `README.md` — Quick-start guide and script inventory
- `.env.template` — Resolver switchboard template
