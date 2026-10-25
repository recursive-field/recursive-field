# Multi-Node Deployment Configuration Matrix

**Version**: 1.0.0  
**Scaffold Baseline**: `v1.0.0-scaffold`  
**Date**: 2026-10-25  
**Companion to**: `MULTI_NODE_ORCHESTRATION.md`

---

## Table of Contents

1. [Droplet Inventory & Roles](#1-droplet-inventory--roles)
2. [Port Allocation Matrix](#2-port-allocation-matrix)
3. [Identity & Knowledge Resolver Mapping](#3-identity--knowledge-resolver-mapping)
4. [Durable Storage Volume Mapping](#4-durable-storage-volume-mapping)
5. [Per-Droplet `.env` Templates](#5-per-droplet-env-templates)
6. [Cross-Host Mesh Topology](#6-cross-host-mesh-topology)
7. [Gateway Federation Map](#7-gateway-federation-map)
8. [Deployment Runbook](#8-deployment-runbook)

---

## 1. Droplet Inventory & Roles

| Droplet | Role | Hostname | Region | IP Range | vCPU | RAM | Disk | Volume |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | Primary (Castle) | `tbc-castle` | nyc1 | 10.0.1.0/24 | 2 | 4GB | 80GB SSD | vol-castle-01 |
| B | Secondary (Fortress) | `tbc-fortress` | sfo1 | 10.0.2.0/24 | 2 | 4GB | 80GB SSD | vol-fortress-01 |
| C | Tertiary (Cabin) | `tbc-cabin` | fra1 | 10.0.3.0/24 | 1 | 2GB | 50GB SSD | vol-cabin-01 |

### Role Descriptions

| Role | Purpose | Agents | Meshes | Gateways |
| --- | --- | --- | --- | --- |
| **Primary** (Castle) | Formation coordinator, cross-host mesh hub, primary ingress | 2-3 | 2 (local + cross-host) | 2 (CLI + HTTP) |
| **Secondary** (Fortress) | Compute node, task execution, cross-host peer | 1-2 | 1-2 (local + cross-host) | 1 (HTTP) |
| **Tertiary** (Cabin) | Lightweight observer, minimal footprint | 1 | 1 (cross-host only) | 1 (CLI) |

---

## 2. Port Allocation Matrix

### PORT_BASE Strategy

Each droplet receives a `PORT_BASE` offset by 1000 to guarantee no host-level port collisions:

| Droplet | `PORT_BASE` | Agent 1 SSH | Agent 2 SSH | Agent 3 SSH | Nginx HTTP | Nginx HTTPS | API Spare |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A (Castle) | 44000 | 44022 | 44122 | 44222 | 44080 | 44443 | 44800 |
| B (Fortress) | 45000 | 45022 | 45122 | 45222 | 45080 | 45443 | 45800 |
| C (Cabin) | 46000 | 46022 | 46122 | 46222 | 46080 | 46443 | 46800 |

### Port Allocation Formula

```
Agent SSH port  = PORT_BASE + (idx * 100) + 22
Nginx HTTP port = PORT_BASE + 80
Nginx HTTPS port = PORT_BASE + 443
API spare port  = PORT_BASE + 800
```

### Per-Droplet Agent Port Map

#### Droplet A (Castle, PORT_BASE=44000)

| Agent | Slug | SSH Port | Container Name |
| --- | --- | --- | --- |
| 1 | `castle-sentinel` | 44022 | `tbc-castle-castle-sentinel` |
| 2 | `castle-scout` | 44122 | `tbc-castle-castle-scout` |
| 3 | `castle-sub-1` | 44222 | `tbc-castle-castle-sub-1` |

| Service | Port | Container |
| --- | --- | --- |
| Nginx HTTP | 44080 | `tbc-castle-mesh-api-gw` |
| Nginx HTTPS | 44443 | `tbc-castle-mesh-api-gw` |

#### Droplet B (Fortress, PORT_BASE=45000)

| Agent | Slug | SSH Port | Container Name |
| --- | --- | --- | --- |
| 1 | `fortress-sentinel` | 45022 | `tbc-fortress-fortress-sentinel` |
| 2 | `fortress-scout` | 45122 | `tbc-fortress-fortress-scout` |

| Service | Port | Container |
| --- | --- | --- |
| Nginx HTTP | 45080 | `tbc-fortress-mesh-api-gw` |

#### Droplet C (Cabin, PORT_BASE=46000)

| Agent | Slug | SSH Port | Container Name |
| --- | --- | --- | --- |
| 1 | `cabin-observer` | 46022 | `tbc-cabin-cabin-observer` |

| Service | Port | Container |
| --- | --- | --- |
| Nginx HTTP | 46080 | `tbc-cabin-mesh-api-gw` |

---

## 3. Identity & Knowledge Resolver Mapping

### Per-Droplet Resolver Switchboard

| Droplet | `LIBRARY` | `KNOWLEDGE_DIR` | `FIELD_ROOT` | `PORT_BASE` | `IMAGE_NAME` |
| --- | --- | --- | --- | --- | --- |
| A (Castle) | `tbc-castle` | `state/knowledge/recursive_field` | `/mnt/rootfs/a0/usr/projects/recursive-field` | `44000` | `agent0ai/agent-zero:latest` |
| B (Fortress) | `tbc-fortress` | `state/knowledge/recursive_field` | `/mnt/rootfs/a0/usr/projects/recursive-field` | `45000` | `agent0ai/agent-zero:latest` |
| C (Cabin) | `tbc-cabin` | `state/knowledge/recursive_field` | `/mnt/rootfs/a0/usr/projects/recursive-field` | `46000` | `agent0ai/agent-zero:latest` |

### Namespace Uniqueness

| Property | Castle | Fortress | Cabin |
| --- | --- | --- | --- |
| Container prefix | `tbc-castle-` | `tbc-fortress-` | `tbc-cabin-` |
| Network name | `tbc-castle-bridge` | `tbc-fortress-bridge` | `tbc-cabin-bridge` |
| Volume prefix | `tbc-castle_` | `tbc-fortress_` | `tbc-cabin_` |

### Knowledge Backing Strategy

| Strategy | `KNOWLEDGE_DIR` | Use Case |
| --- | --- | --- |
| **Self-referential** (default) | `state/knowledge/recursive_field` | All nodes know the formation's own architecture |
| **Domain-specific** | `state/knowledge/tbc_corpus` | Nodes specialized for TBC legacy work |
| **Mixed-domain** | `state/knowledge/urban_ops` | Nodes specialized for urban operations |

---

## 4. Durable Storage Volume Mapping

### Volume Inventory

| Droplet | Volume Name | Volume UUID | Size | Mount Point | Contents |
| --- | --- | --- | --- | --- | --- |
| A (Castle) | `vol-castle-01` | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` | 100GB | `/mnt/vol-castle` | `agents/`, `mesh/`, `gateways/`, `state/` |
| B (Fortress) | `vol-fortress-01` | `b2c3d4e5-f6a7-8901-bcde-f12345678901` | 100GB | `/mnt/vol-fortress` | `agents/`, `mesh/`, `gateways/`, `state/` |
| C (Cabin) | `vol-cabin-01` | `c3d4e5f6-a7b8-9012-cdef-123456789012` | 50GB | `/mnt/vol-cabin` | `agents/`, `mesh/`, `gateways/`, `state/` |

### `/etc/fstab` Entries

```fstab
# Droplet A — Castle
UUID=a1b2c3d4-e5f6-7890-abcd-ef1234567890  /mnt/vol-castle  ext4  defaults,nofail  0  2

# Droplet B — Fortress
UUID=b2c3d4e5-f6a7-8901-bcde-f12345678901  /mnt/vol-fortress  ext4  defaults,nofail  0  2

# Droplet C — Cabin
UUID=c3d4e5f6-a7b8-9012-cdef-123456789012  /mnt/vol-cabin  ext4  defaults,nofail  0  2
```

### Durable State Directory Mapping

```bash
# On each droplet, symlink durable directories to the scaffold:
ln -sf /mnt/vol-castle/agents ./agents
ln -sf /mnt/vol-castle/mesh ./mesh
ln -sf /mnt/vol-castle/gateways ./gateways
ln -sf /mnt/vol-castle/state ./state
# tmp/ remains ephemeral (not symlinked)
```

### Durable vs Ephemeral Boundaries

| Path | Storage | Survives Droplet Death? |
| --- | --- | --- |
| `agents/<slug>/identity.json` | Durable volume | ✅ Yes |
| `agents/<slug>/observations/log.jsonl` | Durable volume | ✅ Yes |
| `agents/<slug>/memory/behaviour.md` | Durable volume | ✅ Yes |
| `mesh/<slug>/channel.json` | Durable volume | ✅ Yes |
| `mesh/<slug>/queue.jsonl` | Durable volume | ✅ Yes |
| `gateways/<slug>/manifest.json` | Durable volume | ✅ Yes |
| `state/ledger.jsonl` | Durable volume | ✅ Yes |
| `state/snapshots/` | Durable volume | ✅ Yes |
| `state/control_profile.json` | Durable volume | ✅ Yes |
| `state/hierarchy.json` | Durable volume | ✅ Yes |
| `tmp/field_env.json` | Ephemeral | ❌ No (regenerated by `init_environment.py`) |
| Scaffold scripts (`.py`) | Git remote | ✅ Yes (pullable) |

---

## 5. Per-Droplet `.env` Templates

### Droplet A — Castle (Primary)

```env
# Castle — Primary Node (Coordinator)
LIBRARY=tbc-castle
KNOWLEDGE_DIR=state/knowledge/recursive_field
FIELD_ROOT=/mnt/rootfs/a0/usr/projects/recursive-field
PORT_BASE=44000
IMAGE_NAME=agent0ai/agent-zero:latest
```

### Droplet B — Fortress (Secondary)

```env
# Fortress — Secondary Node (Compute)
LIBRARY=tbc-fortress
KNOWLEDGE_DIR=state/knowledge/recursive_field
FIELD_ROOT=/mnt/rootfs/a0/usr/projects/recursive-field
PORT_BASE=45000
IMAGE_NAME=agent0ai/agent-zero:latest
```

### Droplet C — Cabin (Tertiary)

```env
# Cabin — Tertiary Node (Observer)
LIBRARY=tbc-cabin
KNOWLEDGE_DIR=state/knowledge/recursive_field
FIELD_ROOT=/mnt/rootfs/a0/usr/projects/recursive-field
PORT_BASE=46000
IMAGE_NAME=agent0ai/agent-zero:latest
```

---

## 6. Cross-Host Mesh Topology

### Mesh Inventory

| Mesh Slug | Type | Endpoints | Droplets | Purpose |
| --- | --- | --- | --- | --- |
| `castle-mesh` | peer-to-peer | castle-sentinel ↔ castle-scout | A only | Local Castle mesh |
| `fortress-mesh` | peer-to-peer | fortress-sentinel ↔ fortress-scout | B only | Local Fortress mesh |
| `castle-fortress-mesh` | cross-host | castle-sentinel ↔ fortress-scout | A ↔ B | Cross-host federation |
| `castle-cabin-mesh` | cross-host | castle-sentinel ↔ cabin-observer | A ↔ C | Cross-host federation |

### Cross-Host Mesh Diagram

```
Droplet A (Castle)              Droplet B (Fortress)           Droplet C (Cabin)
┌────────────────────┐          ┌────────────────────┐        ┌────────────────────┐
│ castle-sentinel    │          │ fortress-sentinel  │        │ cabin-observer     │
│  ├ identity.json   │          │  ├ identity.json   │        │  ├ identity.json   │
│  └ obs/log.jsonl   │          │  └ obs/log.jsonl   │        │  └ obs/log.jsonl   │
│                    │          │                    │        │                    │
│ castle-scout      │          │ fortress-scout    │        │                    │
│  ├ identity.json   │          │  ├ identity.json   │        │                    │
│  └ obs/log.jsonl   │          │  └ obs/log.jsonl   │        │                    │
│                    │          │                    │        │                    │
│ castle-mesh        │          │ fortress-mesh      │        │                    │
│  ├ channel.json    │          │  ├ channel.json    │        │                    │
│  └ queue.jsonl     │          │  └ queue.jsonl     │        │                    │
└─────────┬──────────┘          └─────────┬──────────┘        └─────────┬──────────┘
          │                               │                             │
          └──── castle-fortress-mesh ─────┘                             │
          │     (cross-host queue)          │                             │
          │     channel.json + queue.jsonl │                             │
          │                               │                             │
          └──── castle-cabin-mesh ──────────────────────────────────────┘
                (cross-host queue)
                channel.json + queue.jsonl
```

### Cross-Host Queue Sync Strategy

| Strategy | Castle↔Fortress | Castle↔Cabin |
| --- | --- | --- |
| **Block storage attach** | Primary: vol-castle | Primary: vol-castle |
| **Git-sync** | Periodic push/pull | Periodic push/pull |
| **Overlay network** | Docker overlay or VPN | Docker overlay or VPN |
| **Shared NFS** | NFS mount at `/mnt/cross-host/` | NFS mount at `/mnt/cross-host/` |

---

## 7. Gateway Federation Map

### Gateway Inventory

| Gateway Slug | Type | Target | Droplet | Port | Nginx Upstream |
| --- | --- | --- | --- | --- | --- |
| `castle-gw` | CLI | agent: castle-sentinel | A | 44022 | — |
| `castle-api-gw` | HTTP | mesh: castle-mesh | A | 44080 | castle-sentinel:8000, castle-scout:8000 |
| `fortress-gw` | CLI | agent: fortress-sentinel | B | 45022 | — |
| `fortress-api-gw` | HTTP | mesh: fortress-mesh | B | 45080 | fortress-sentinel:8000, fortress-scout:8000 |
| `cabin-gw` | CLI | agent: cabin-observer | C | 46022 | — |
| `cabin-api-gw` | HTTP | mesh: castle-cabin-mesh | C | 46080 | cabin-observer:8000 |

### Nginx Federation Upstream

```nginx
# Castle — Cross-Host Federation Ingress
upstream cross_host_federation {
    server tbc-castle-castle-sentinel:8000;    # Local (Droplet A)
    server tbc-fortress-fortress-scout:8000;   # Remote (Droplet B)
    server tbc-cabin-cabin-observer:8000;      # Remote (Droplet C)
}

server {
    listen 44080;
    server_name castle.recursive-field.local;

    location /federation/ {
        proxy_pass http://cross_host_federation;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Agent-Slug $http_x_agent_slug;
        proxy_set_header X-Agent-Id $http_x_agent_id;
    }
}
```

---

## 8. Deployment Runbook

### Phase 1: Provision Droplets

```bash
# === Using DigitalOcean doctl ===

# Droplet A — Castle
doctl compute droplet create tbc-castle \
  --region nyc1 --size s-2vcpu-4gb --image ubuntu-22-04-x64 \
  --ssh-keys <ssh-key-id> --tag-names recursive-field,primary

# Droplet B — Fortress
doctl compute droplet create tbc-fortress \
  --region sfo1 --size s-2vcpu-4gb --image ubuntu-22-04-x64 \
  --ssh-keys <ssh-key-id> --tag-names recursive-field,secondary

# Droplet C — Cabin
doctl compute droplet create tbc-cabin \
  --region fra1 --size s-1vcpu-2gb --image ubuntu-22-04-x64 \
  --ssh-keys <ssh-key-id> --tag-names recursive-field,tertiary
```

### Phase 2: Create & Attach Volumes

```bash
# Volume for Castle
doctl compute volume create vol-castle-01 \
  --region nyc1 --size 100GiB --desc "Castle durable state"

doctl compute volume-action attach <volume-id-castle> <droplet-id-castle>

# Volume for Fortress
doctl compute volume create vol-fortress-01 \
  --region sfo1 --size 100GiB --desc "Fortress durable state"

doctl compute volume-action attach <volume-id-fortress> <droplet-id-fortress>

# Volume for Cabin
doctl compute volume create vol-cabin-01 \
  --region fra1 --size 50GiB --desc "Cabin durable state"

doctl compute volume-action attach <volume-id-cabin> <droplet-id-cabin>
```

### Phase 3: Mount Volumes & Clone Scaffold (per droplet)

```bash
# SSH into each droplet and execute:

# --- Mount durable volume ---
mkdir -p /mnt/vol-castle
mount /dev/disk/by-id/scsi-0DO_Volume_vol-castle-01 /mnt/vol-castle

echo "UUID=$(blkid -s UUID -o value /dev/disk/by-id/scsi-0DO_Volume_vol-castle-01) /mnt/vol-castle ext4 defaults,nofail 0 2" >> /etc/fstab

# --- Clone scaffold ---
mkdir -p /mnt/rootfs/a0/usr/projects
git clone git@github.com:recursive-field/recursive-field.git /mnt/rootfs/a0/usr/projects/recursive-field
cd /mnt/rootfs/a0/usr/projects/recursive-field

# --- Symlink durable directories ---
rm -rf agents mesh gateways state
ln -sf /mnt/vol-castle/agents ./agents
ln -sf /mnt/vol-castle/mesh ./mesh
ln -sf /mnt/vol-castle/gateways ./gateways
ln -sf /mnt/vol-castle/state ./state

# --- Configure resolver switchboard ---
cp .env.template .env
# Edit .env:
#   LIBRARY=tbc-castle
#   KNOWLEDGE_DIR=state/knowledge/recursive_field
#   FIELD_ROOT=/mnt/rootfs/a0/usr/projects/recursive-field
#   PORT_BASE=44000
```

### Phase 4: Bootstrap Formation (per droplet)

```bash
# --- Initialize environment ---
python3 init_environment.py

# --- Provision agents ---
python3 create_agent.py castle-sentinel "Castle node sentinel"
python3 create_agent.py castle-scout "Castle node scout"

# --- Connect via mesh ---
python3 create_mesh.py castle-mesh castle-sentinel castle-scout

# --- Expose interfaces ---
python3 create_gateway.py castle-gw agent castle-sentinel cli
python3 create_gateway.py castle-api-gw mesh castle-mesh http

# --- Hydrate profile ---
python3 hydrate_profile.py castle-sentinel sentinel_observer

# --- Generate compose harness ---
python3 generate_compose.py --port-base 44000

# --- Activate entrypoint ---
python3 entrypoint.py castle-sentinel

# --- Verify graph integrity ---
python3 verify_unit_cell.py
# Expected: UNIT CELL INTEGRITY OK
```

### Phase 5: Federate Cross-Host Meshes

```bash
# On Castle (Droplet A):
python3 create_mesh.py castle-fortress-mesh castle-sentinel fortress-scout
# Requires fortress-scout identity to be available via shared volume or sync

python3 create_mesh.py castle-cabin-mesh castle-sentinel cabin-observer
# Requires cabin-observer identity to be available via shared volume or sync

# Verify federation:
python3 verify_unit_cell.py
# Expected: UNIT CELL INTEGRITY OK (with cross-host meshes)

python3 inspect_formation.py
# Expected: all cross-host nodes in topology tree
```

### Phase 6: Phoenix Recovery (if a droplet dies)

```bash
# 1. Provision fresh droplet (same region/size)
# 2. Attach the same durable volume
# 3. Clone scaffold from Git
# 4. Symlink durable directories to volume
# 5. Restore .env from template (same LIBRARY, same PORT_BASE)
# 6. Run: python3 init_environment.py
# 7. Run: python3 verify_unit_cell.py
#    Expected: UNIT CELL INTEGRITY OK (from durable state)
# 8. Run: python3 persist_state.py
#    Expected: new snapshot, old hashes match (except log growth)
# 9. Run: python3 entrypoint.py castle-sentinel
#    Expected: container_activated with new hostname, same agent_id
# 10. Run: python3 rebalance.py
#    Expected: field_rebalanced, 0 issues
```

---

## Summary

| Component | Castle (A) | Fortress (B) | Cabin (C) |
| --- | --- | --- | --- |
| `LIBRARY` | `tbc-castle` | `tbc-fortress` | `tbc-cabin` |
| `PORT_BASE` | 44000 | 45000 | 46000 |
| Agents | 3 | 2 | 1 |
| Local mesh | `castle-mesh` | `fortress-mesh` | — |
| Cross-host meshes | `castle-fortress-mesh`, `castle-cabin-mesh` | `castle-fortress-mesh` | `castle-cabin-mesh` |
| Gateways | 2 (CLI + HTTP) | 1 (HTTP) | 1 (CLI) |
| Volume | `vol-castle-01` (100GB) | `vol-fortress-01` (100GB) | `vol-cabin-01` (50GB) |
| Nginx port | 44080 | 45080 | 46080 |
| Knowledge | `recursive_field` (self) | `recursive_field` (self) | `recursive_field` (self) |

**3 droplets · 6 agents · 4 meshes · 4 gateways · 3 volumes · 1 scaffold · zero drift.** 🌱
