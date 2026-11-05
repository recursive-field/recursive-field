# Multi-Node Orchestration Guide

**Version**: 1.0.0  
**Scaffold Baseline**: `v1.0.0-scaffold`  
**Date**: 2026-10-25  

---

## Table of Contents

1. [Architectural Premise](#1-architectural-premise)
2. [Multi-Host Topology & Resolver Mapping](#2-multi-host-topology--resolver-mapping)
3. [Persistent Storage & Volume Detach/Re-Attach](#3-persistent-storage--volume-detachre-attach)
4. [Cross-Host Mesh & Ingress Routing](#4-cross-host-mesh--ingress-routing)
5. [0-to-1 Multi-Node Bootstrap Sequence](#5-0-to-1-multi-node-bootstrap-sequence)
6. [Disaster Recovery & Phoenix Rehydration Protocol](#6-disaster-recovery--phoenix-rehydration-protocol)
7. [Security Posture Inheritance Across Nodes](#7-security-posture-inheritance-across-nodes)

---

## 1. Architectural Premise

The `v1.0.0-scaffold` baseline established that a single recursive field formation can be relocated to any filesystem path with zero drift. Multi-node orchestration extends this principle across **host boundaries**: an entire node can fail or be replaced while its identity, memory, and state persist on attached block storage or distributed volumes.

### Core Principles Extended to Multi-Node

| Principle | Single-Host | Multi-Node Extension |
| --- | --- | --- |
| Discovery-first location agnosticism | `find_root.py` discovers cwd | Each droplet runs `find_root.py` from its local clone |
| `{LIBRARY}` single-point resolver | One `.env` per formation | One `.env` per droplet, parameterized by node role |
| Structured impermanence | Container is disposable, state is durable | Entire droplet is disposable, attached volumes are durable |
| Epistemic separation | `KNOWLEDGE_DIR` swaps locally | Knowledge trees pullable from remote Git or shared volumes |
| Git vs. Generated separation | `.gitignore` isolates runtime state | Each node clones the same scaffold; runtime state never committed |

### Decentralized Multi-Origin Sourcing

> "You can't kill the network."

Canonical identity and knowledge trees are pullable from independent remote origins — Git repositories, cloud volumes, or local peer nodes. A newly provisioned droplet uses `find_root.py` and `init_environment.py` to rehydrate its local harness directly from remote sources.

```
Remote Git Repository (recursive-field/recursive-field)
    |
    ├── Droplet A (LIBRARY=tbc-castle, PORT_BASE=44000)
    ├── Droplet B (LIBRARY=tbc-fortress, PORT_BASE=45000)
    └── Droplet C (LIBRARY=tbc-cabin, PORT_BASE=46000)
```

---

## 2. Multi-Host Topology & Resolver Mapping

### 2.1 Per-Droplet Resolver Configuration

Each droplet maintains an operator-owned `.env` resolver input with a unique
`LIBRARY` and non-colliding `PORT_BASE`; the generator never rewrites it.
`LIBRARY`, `FIELD_ROOT`, and `PORT_BASE` precedence is explicit CLI/function
value, nonempty process environment, nonempty root `.env`, then the documented
defaults. Any supplied `FIELD_ROOT` must canonically equal marker discovery:

```env
# Droplet A — tbc-castle
LIBRARY=tbc-castle
KNOWLEDGE_DIR=state/knowledge/tbc_corpus
FIELD_ROOT=/mnt/rootfs/a0/usr/projects/recursive-field
PORT_BASE=44000
IMAGE_NAME=agent0ai/agent-zero:latest
```

```env
# Droplet B — tbc-fortress
LIBRARY=tbc-fortress
KNOWLEDGE_DIR=state/knowledge/tbc_corpus
FIELD_ROOT=/mnt/rootfs/a0/usr/projects/recursive-field
PORT_BASE=45000
IMAGE_NAME=agent0ai/agent-zero:latest
```

```env
# Droplet C — tbc-cabin
LIBRARY=tbc-cabin
KNOWLEDGE_DIR=state/knowledge/tbc_corpus
FIELD_ROOT=/mnt/rootfs/a0/usr/projects/recursive-field
PORT_BASE=46000
IMAGE_NAME=agent0ai/agent-zero:latest
```

### 2.2 Port Allocation Strategy

Each droplet's `PORT_BASE` is offset by 1000 to prevent host-level collisions:

| Droplet | `LIBRARY` | `PORT_BASE` | Agent 1 SSH | Agent 2 SSH | First HTTP gateway |
| --- | --- | --- | --- | --- | --- |
| A (castle, 2 agents) | `tbc-castle` | 44000 | 44022 | 44122 | 44280 |
| B (fortress, 2 agents) | `tbc-fortress` | 45000 | 45022 | 45122 | 45280 |
| C (cabin, 1 agent) | `tbc-cabin` | 46000 | 46022 | — | 46180 |

Agent slot `i` is `PORT_BASE + i*100`; only `slot+22` is published to
container SSH `22`. Active HTTP/API gateway slot `j` is
`PORT_BASE + (agent_count+j)*100`; `slot+80` is published to Nginx `80`.
Agent HTTP/API is internal-only on container `80`. There are no event ports,
host agent API ports, HTTPS formula, or `+800` spare in Phase 3.

### 2.3 Container Name Uniqueness

The `{LIBRARY}` resolver makes container names unique within each generated
Compose model/node when node-local library values do not collide. It does not
establish network-global uniqueness; that requires an external federation
registry or coordination contract.

| Droplet | Agent Service | Container Name |
| --- | --- | --- |
| A | `agent-field-sentinel` | `${LIBRARY}-field-sentinel` → `tbc-castle-field-sentinel` |
| B | `agent-field-sentinel` | `${LIBRARY}-field-sentinel` → `tbc-fortress-field-sentinel` |
| C | `agent-field-sentinel` | `${LIBRARY}-field-sentinel` → `tbc-cabin-field-sentinel` |

---

## 3. Persistent Storage & Volume Detach/Re-Attach

### 3.1 Durable State Boundaries

| Storage Tier | What Lives Here | Lifecycle |
| --- | --- | --- |
| **Ephemeral** (container filesystem) | `/a0/` runtime, scratch, temporary caches | Dies with container — `docker compose down` |
| **Durable** (attached block volume) | `agents/*/identity.json`, `observations/log.jsonl`, `state/ledger.jsonl`, `state/snapshots/`, `memory/behaviour.md` | Survives droplet destruction — re-attachable |
| **Remote** (Git repository) | Scaffold scripts, spec, seed stones, knowledge templates | Pullable from any node via `git clone` |

### 3.2 Volume Mount Topology

```
Droplet A (/mnt/volume-a)
├── /mnt/rootfs/a0/usr/projects/recursive-field/     ← Scaffold clone (from Git)
│   ├── agents/                                       ← Mounted from /mnt/volume-a/state/agents/
│   ├── mesh/                                          ← Mounted from /mnt/volume-a/state/mesh/
│   ├── gateways/                                      ← Mounted from /mnt/volume-a/state/gateways/
│   ├── state/                                         ← Mounted from /mnt/volume-a/state/
│   │   ├── ledger.jsonl                               ← Durable — survives droplet death
│   │   ├── snapshots/                                  ← Durable — SHA-256 state history
│   │   ├── control_profile.json                        ← Durable — active governance
│   │   └── hierarchy.json                             ← Durable — parent-child graph
│   └── tmp/                                           ← Ephemeral — scratch space
└── /mnt/volume-a/                                    ← Attached block storage
```

### 3.3 Detach and Re-Attach Procedure

```bash
# --- On dying droplet (before termination) ---
# 1. Flush state to durable storage
python3 persist_state.py

# 2. Verify final state integrity
python3 verify_unit_cell.py

# --- On fresh droplet (after provisioning) ---
# 3. Clone the scaffold from Git
git clone git@github.com:recursive-field/recursive-field.git

# 4. Attach the durable volume
mount /dev/volume-a /mnt/volume-a

# 5. Bind-mount durable directories at canonical coordinates
mount --bind /mnt/volume-a/state/agents/ ./agents/
mount --bind /mnt/volume-a/state/mesh/ ./mesh/
mount --bind /mnt/volume-a/state/gateways/ ./gateways/
mount --bind /mnt/volume-a/state/ ./state/

# 6. Restore resolver switchboard
cp .env.template .env
# Edit .env: set LIBRARY=tbc-castle, FIELD_ROOT=<new-path>

# 7. Re-initialize environment (updates field_env.json to new path)
python3 init_environment.py

# 8. Verify graph integrity from durable state
python3 verify_unit_cell.py
# Expected: UNIT CELL INTEGRITY OK

# 9. Activate entrypoint (re-hydrates agent from durable state)
python3 entrypoint.py field-sentinel
# Expected: container_activated event with new hostname
```

Level 2 rejects symlinks for inspected identities, manifests, queues, and
generated-output paths. External-volume symlink support is deferred.

---

## 4. Cross-Host Mesh & Ingress Routing

### 4.1 Cross-Host Mesh Architecture

Meshes (`channel.json`, `queue.jsonl`) are designed to sit outside individual agent boundaries. In a multi-node topology, meshes connect agents across host boundaries via network-level routing:

```
Droplet A (tbc-castle)          Droplet B (tbc-fortress)
├── agent-field-sentinel         ├── agent-field-scout
│   └── observations/log.jsonl   │   └── observations/log.jsonl
├── mesh/cross-host-mesh/        ├── mesh/cross-host-mesh/
│   ├── channel.json              │   ├── channel.json
│   └── queue.jsonl               │   └── queue.jsonl
└── nginx (ingress)              └── nginx (ingress)
         │                               │
         └────── cross-host bridge ──────┘
              (reverse proxy / VPN)
```

### 4.2 Nginx Cross-Host Gateway Federation

Generated Nginx uses Compose service DNS keys and internal port `80`. A manually
managed cross-host network/DNS layer may extend routing across hosts:

```nginx
# Cross-host mesh bridge
upstream cross_host_agents {
    server agent-field-sentinel:80;  # Compose service key on Droplet A network
    server agent-field-scout:80;     # separately managed cross-host DNS/network
    server agent-cabin-observer:80;  # separately managed cross-host DNS/network
}

server {
    listen 80;
    location / {
        proxy_pass http://cross_host_agents;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        # Preserve agent identity headers
        proxy_set_header X-Agent-Slug $http_x_agent_slug;
        proxy_set_header X-Agent-Id $http_x_agent_id;
    }
}
```

### 4.3 Cross-Host Task Delegation

`delegate_task.py` works across host boundaries when the mesh `queue.jsonl` is shared via a network mount or synced:

```bash
# On Droplet A — delegate to agent on Droplet B
python3 delegate_task.py field-sentinel field-scout cross-host-mesh \
    "Analyze cross-host mesh connectivity from fortress node"

# Security gating is enforced locally on each node:
# - Droplet A checks field-sentinel's security profile (local control_profile.json)
# - Droplet B checks field-scout's security profile (local control_profile.json)
# - Both must have 'coordinate' capability
```

### 4.4 Queue Synchronization Strategies

| Strategy | Mechanism | Trade-off |
| --- | --- | --- |
| **Shared NFS mount** | `queue.jsonl` on a shared network filesystem | Simple, but single point of failure |
| **Git-sync** | Periodic `git push`/`pull` of queue state | Eventual consistency, not real-time |
| **Block storage attach** | Dedicated volume for `mesh/` directory | Durable, but not simultaneous multi-attach |
| **Overlay network** | Docker network overlay or VPN mesh | Real-time, but requires network configuration |

---

## 5. 0-to-1 Multi-Node Bootstrap Sequence

### 5.1 Per-Droplet Bootstrap

Execute this sequence on each droplet to instantiate a working node:

```bash
# === Step 1: Clone scaffold ===
git clone git@github.com:recursive-field/recursive-field.git
cd recursive-field

# === Step 2: Configure resolver switchboard ===
cp .env.template .env
# Edit .env:
#   LIBRARY=tbc-castle        # unique per droplet
#   KNOWLEDGE_DIR=state/knowledge/tbc_corpus
#   FIELD_ROOT=$(pwd)          # or /mnt/rootfs/... for host mount
#   PORT_BASE=44000            # unique per droplet (offset by 1000)

# === Step 3: Initialize environment ===
python3 init_environment.py
# Output: field_env.json with discovered field_root, library, knowledge_dir

# === Step 4: Provision agents ===
python3 create_agent.py castle-sentinel "Castle node sentinel"
python3 create_agent.py castle-scout "Castle node scout"

# === Step 5: Connect via mesh ===
python3 create_mesh.py castle-mesh castle-sentinel castle-scout

# === Step 6: Expose interface ===
python3 create_gateway.py castle-gw agent castle-sentinel cli
python3 create_gateway.py castle-api-gw mesh castle-mesh http

# === Step 7: Hydrate profile from seed stone ===
python3 hydrate_profile.py castle-sentinel sentinel_observer

# === Step 8: Validate with zero mutation, then generate owned outputs ===
python3 generate_compose.py --dry-run
python3 generate_compose.py
# Output: marked docker-compose.yml and active HTTP/API gateway nginx.conf files

# === Step 9: Activate entrypoint ===
python3 entrypoint.py castle-sentinel
# Output: container_activated event with hostname, prompt hash, security profile

# === Step 10: Verify graph integrity ===
python3 verify_unit_cell.py
# Expected: UNIT CELL INTEGRITY OK
```

The Compose plan is rendered from the same immutable normalized topology as all
Nginx configs. The validated canonical absolute field root is bound into host
mount sources, with no late `${FIELD_ROOT}` interpolation. Agent coordinates are read-only; only `memory`, `observations`,
and connected queues are read-write; field-wide orchestration is read-only; the
Docker socket is never mounted. `--dry-run` completes validation and reports
create/replace/delete hashes with zero mutation. Every output has the exact
ownership marker. `docker-compose.yml` is generator-owned; an unmarked active
Nginx config requires `--adopt-existing`, while stale deletion is limited to
marked files. Compose output is fixed at canonical
`${FIELD_ROOT}/docker-compose.yml`; `--out` may only name that path. Schema
version `1.0.0` is the sole supported topology contract, and duplicate output
paths fail before staging. Apply opens canonical `FIELD_ROOT`, traverses parent
components with `O_DIRECTORY|O_NOFOLLOW`, and pins trusted parent dirfds.
Staging, final identity/digest validation, atomic replacement, stale deletion,
cleanup, and directory `fsync` use only dirfd-relative operations; replacement
of the planned parent coordinate fails closed. Atomicity is per file, not
cross-file.

### 5.2 Multi-Node Federation Bootstrap

After each droplet is individually bootstrapped, federate the nodes:

```bash
# === Step 11: Create cross-host mesh (on primary node) ===
# Requires shared queue.jsonl or network mount
python3 create_mesh.py cross-host-federation castle-sentinel fortress-scout
# Note: fortress-scout must exist in the shared agents/ directory
# or be registered via a cross-host identity exchange

# === Step 12: Verify federation integrity ===
python3 verify_unit_cell.py
# Expected: all cross-host nodes show in topology tree

# === Step 13: Inspect formation from vantage point ===
python3 inspect_formation.py --agent castle-sentinel --json
# Output: full topology including cross-host meshes and gateways
```

### 5.3 N-Droplet Scaling Matrix

| Droplet | Role | `LIBRARY` | `PORT_BASE` | Agents | Meshes | Gateways |
| --- | --- | --- | --- | --- | --- | --- |
| A | Primary (castle) | `tbc-castle` | 44000 | 2 | 2 (1 local + 1 cross-host) | 2 |
| B | Secondary (fortress) | `tbc-fortress` | 45000 | 2 | 2 (1 local + 1 cross-host) | 1 |
| C | Tertiary (cabin) | `tbc-cabin` | 46000 | 1 | 1 (cross-host only) | 1 |

---

## 6. Disaster Recovery & Phoenix Rehydration Protocol

### 6.1 The Phoenix Scenario

A droplet dies. Its containers are destroyed. Its ephemeral filesystem is gone. But the attached block volume survives — holding all durable identity, memory, observation logs, and state ledgers.

**Goal**: Provision a fresh droplet, re-attach the durable volume, and rehydrate the full formation with zero data drift.

### 6.2 Phoenix Rehydration Sequence

```bash
# === Phase 1: Provision fresh droplet ===
# (via cloud provider API or manual provisioning)
# SSH key, base image, network access configured

# === Phase 2: Clone scaffold ===
git clone git@github.com:recursive-field/recursive-field.git
cd recursive-field

# === Phase 3: Attach durable volume ===
# Cloud provider: attach volume to new droplet
mount /dev/sdb /mnt/volume-recovery

# === Phase 4: Restore durable state ===
# Bind durable directories over the scaffold's empty canonical coordinates
rm -rf agents/ mesh/ gateways/ state/snapshots/ state/ledger.jsonl
mkdir -p agents mesh gateways state
mount --bind /mnt/volume-recovery/agents/ ./agents/
mount --bind /mnt/volume-recovery/mesh/ ./mesh/
mount --bind /mnt/volume-recovery/gateways/ ./gateways/
mount --bind /mnt/volume-recovery/state/ ./state/

# === Phase 5: Restore resolver switchboard ===
cp .env.template .env
# Edit .env:
#   LIBRARY=tbc-castle              # same identity
#   FIELD_ROOT=$(pwd)                # new path — discovery-first handles this
#   PORT_BASE=44000                  # same port allocation

# === Phase 6: Re-initialize environment ===
python3 init_environment.py
# This updates field_env.json to the new field_root path
# All agent identity.json files still point to the correct genesis_uuid
# All observation logs are intact on the durable volume

# === Phase 7: Verify durable state integrity ===
python3 verify_unit_cell.py
# Expected: UNIT CELL INTEGRITY OK
# All UUID linkages intact — identity is path-independent

# === Phase 8: Verify state ledger consistency ===
python3 persist_state.py
# New snapshot appended to ledger.jsonl
# SHA-256 hashes of identity manifests match previous snapshot
# (except for observation logs that grew — expected)

# === Phase 9: Activate entrypoint ===
python3 entrypoint.py castle-sentinel
# container_activated event recorded with:
#   - new hostname (fresh droplet)
#   - same agent_id (from durable identity.json)
#   - same prompt_hash (governance-aware prompt re-assembled)
#   - same active_security_profile (from durable control_profile.json)

# === Phase 10: Resume operations ===
# The formation is fully rehydrated and operational
# Zero data drift — all identity, memory, logs, and state survived
```

### 6.3 Recovery Verification Checklist

| Check | Method | Expected |
| --- | --- | --- |
| Agent identity survived | `verify_unit_cell.py` | ✅ All UUIDs match durable state |
| Observation logs survived | `inspect_formation.py` | ✅ Event counts match pre-failure |
| State ledger survived | `persist_state.py` | ✅ New snapshot appended, old hashes match |
| Security profile survived | `system_control.py --status` | ✅ Active profile preserved |
| Hierarchy survived | `rebalance.py --dry-run` | ✅ Parent-child edges intact |
| Prompt re-assembled | `entrypoint.py --dry-run` | ✅ Same prompt_hash (if knowledge unchanged) |
| Formation rehydrated | `verify_unit_cell.py` | ✅ UNIT CELL INTEGRITY OK |

---

## 7. Security Posture Inheritance Across Nodes

### 7.1 Per-Node Security Profiles

Each droplet maintains its own `state/control_profile.json` on durable storage. Security profiles are enforced locally:

```bash
# On Droplet A
python3 system_control.py --agent castle-sentinel --set-security restricted
# control_profile.json on Droplet A's volume: active_security_profile=restricted

# On Droplet B (independent)
python3 system_control.py --agent fortress-scout --set-security lockdown
# control_profile.json on Droplet B's volume: active_security_profile=lockdown
```

### 7.2 Cross-Host Delegation Gating

When `delegate_task.py` dispatches across host boundaries, the sender's local security profile gates the delegation:

| Sender Profile | `coordinate` Capability | Cross-Host Delegation |
| --- | --- | --- |
| `open` | ✅ Yes | ✅ Allowed |
| `restricted` | ✅ Yes | ✅ Allowed |
| `lockdown` | ❌ No | ❌ Blocked (exit 4) |

The recipient's local security profile governs what the recipient can do with the received task — but the **delegation itself** is gated by the **sender's** profile.

### 7.3 Phoenix Rehydration Security Preservation

When a droplet is rehydrated from durable storage, the `control_profile.json` is restored from the attached volume — preserving the last-set security posture across host failures:

```
Droplet A (restricted) → dies → volume detached → fresh droplet → volume re-attached
→ control_profile.json restored → active_security_profile=restricted
→ entrypoint.py activates → container_activated with restricted profile
```

**Security posture survives host failure because it lives on durable storage, not ephemeral compute.**

---

## Summary

The `v1.0.0-scaffold` baseline, combined with this Multi-Node Orchestration Guide, establishes the complete operational blueprint for deploying bounded, self-organizing recursive fields across distributed host topologies with:

- **Zero path drift** across nodes (discovery-first location agnosticism)
- **Zero data drift** across host failures (structured impermanence + durable volumes)
- **Zero identity drift** across rehydration (durable identity manifests + state ledgers)
- **Zero security drift** across recovery (control profiles on persistent storage)
- **Zero code drift** across scaling (same scaffold cloned everywhere, `{LIBRARY}` resolver parameterizes each node)

**17 scripts · 13-section spec · N droplets · 1 scaffold · zero drift.** 🌱
