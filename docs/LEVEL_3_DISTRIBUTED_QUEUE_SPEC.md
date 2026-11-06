# Level 3 Distributed Task Queue Specification

Status: **Draft for independent review**

Specification version: **0.1.0-draft**

Inspection baseline: Recursive Field commit `08b5ce62a95531596f5bfca858c15830f1bd905e`

## 1. Scope and epistemic boundary

### 1.1 Scope

This document proposes the Level 3 contract for distributing the existing bounded asynchronous task loop across failure domains. It defines task identity, immutable envelopes, lease claims, fencing, lifecycle states, durable evidence, contention backoff, trust checks, recovery, and verification. It does not implement them.

The interpreting vantage is the current single-node `delegate_task.py` and `consume_queue.py` contract, viewed from the durable mesh task coordinate. The decision served is: what semantics must remain true before any cross-host transport or multi-writer implementation can be selected?

### 1.2 Authority boundary

This draft is normative only after approval. Until then:

- **Documentary evidence** describes behavior observed in the inspected baseline.
- **Proposed contract** uses **MUST**, **MUST NOT**, **SHOULD**, and **MAY** in their usual standards sense.
- **Unresolved** marks a decision that this draft deliberately does not canonize.

The queue authority is the storage or service that linearizes lifecycle compare-and-swap (CAS) operations for one mesh queue. A transport may carry objects but does not become authoritative merely by possessing a copy. Agent observation logs, local worker state, replicas, gateways, and schedulers are evidence or projections, not lifecycle authorities.

### 1.3 Assumptions

- Every mesh, field genesis, agent, droplet, container, and boot has a stable coordinate in its own namespace.
- A queue deployment designates exactly one authoritative lifecycle domain per mesh partition at a time.
- The authority can issue strictly monotonic fencing tokens and linearizable CAS for a task state record, or can provide an equivalent transactional primitive.
- UTC timestamps use RFC 3339 with an explicit `Z` or numeric offset and are normalized to UTC for comparison.
- Payloads remain data. They are never interpreted as shell commands.
- Task adapters and execution policies remain allowlisted and capability-gated.

### 1.4 Exclusions

This draft does not select Tailscale, WireGuard, NFS, object storage, a database, a broker, consensus software, gateway ingress, or replication topology. Tailscale/WireGuard and gateway ingress are later projections constrained by this contract. It also does not define arbitrary code execution, exactly-once external side effects, global ordering across meshes, priority scheduling, workflow DAGs, or replacement of the current bounded `consume_queue.py --once` path.

### 1.5 Inquiry bounds and stopping condition

Admitted evidence is limited to the baseline queue producer/consumer, current mesh and worker-state conventions, focused project documentation, and focused tests. No live host, droplet, network, or external service was inspected. This specification stops at a transport-neutral contract and parks choices that require implementation experiments or an authority decision.

## 2. Baseline documentary evidence

The baseline establishes these current invariants:

1. Async delegation writes `mesh/<mesh>/tasks/<uuid>.json`, then appends dispatch evidence to `mesh/<mesh>/queue.jsonl` and sender/recipient observation logs.
2. The version `1.0.0` envelope binds payload text and SHA-256, sender and recipient slugs/UUIDs, mesh slug/UUID, field genesis UUID, required `coordinate` capability, optional active-prompt hash, dispatch time, task type, and execution policy. Its digest is sorted-key, compact, UTF-8 JSON with `ensure_ascii=false`, excluding the digest field.
3. The current `task_id` is a random canonical UUID. It is not derived from origin, payload, genesis time, or idempotency key.
4. The worker validates envelope, dispatch, endpoint, identity, genesis, payload, and digest bindings; revalidates current capability before claiming; and supports only `inspect_unit_cell` under `allowlisted` policy.
5. Claims currently live at `agents/<agent>/worker_state/claims/<task_id>.json`, are created with local `O_EXCL`, use a 300-second wall-clock lease, and increment an `attempt` on stale recovery. They have no boot identity, heartbeat, predecessor hash, CAS generation, or fencing token.
6. Results are hashed artifacts under `mesh/<mesh>/results/`. Recovery preserves an existing valid result artifact and repairs missing events, claim finalization, cursor advancement, and persistence evidence.
7. `agents/<agent>/worker_state/<mesh>.cursor.json` is a durable single-worker scan cursor. Optional systemd execution uses one non-overlapping `--once` worker per agent/mesh under local `flock`.
8. `_append_event_once` performs read-then-append deduplication by `(event_type, task_id)`. That is idempotent in the bounded single-writer path but is not a concurrent transaction.
9. Current cross-host documentation lists shared mounts, Git synchronization, block-volume attachment, and overlay/VPN networking as possibilities. It does not establish distributed CAS, fencing, or exactly-once semantics.

These are evidence, not proof that the same mechanisms are safe across hosts.

## 3. Versioning and canonicalization

### 3.1 Schema policy

Level 3 records MUST carry:

```json
{
  "schema_name": "recursive-field.distributed-task-envelope",
  "schema_version": "2.0.0"
}
```

Major versions are incompatible. A reader MUST reject an unsupported major version before acting. Minor versions may add optional fields whose absence preserves semantics. Patch versions may clarify validation without changing accepted meaning. Unknown fields MUST be retained when forwarding but MUST NOT influence execution unless the accepted schema version defines them. Security-sensitive fields MUST never be treated as ignorable extensions.

Schemas, once published, MUST be immutable and content-addressed. An implementation SHOULD bind `schema_sha256` in each record. Migration creates a new record with explicit predecessor lineage; it never rewrites an accepted envelope.

### 3.2 Canonical JSON

All identity and integrity digests in this specification use:

1. UTF-8 encoding without a byte-order mark;
2. JSON object keys sorted lexicographically by Unicode code point;
3. separators `,` and `:` with no insignificant whitespace;
4. JSON strings emitted without ASCII-only escaping;
5. no duplicate object keys;
6. integers only where a numeric field is specified; no floating-point values;
7. timestamps normalized to RFC 3339 UTC with `Z` before hashing;
8. the digest field for the object being hashed omitted from its own digest input.

This deliberately preserves the current Python canonicalization shape while tightening timestamps and number handling. Cross-language implementations MUST pass common canonicalization fixtures before interoperability is claimed. Adoption of RFC 8785 is unresolved because it would differ in some edge cases; it may replace this profile only in a new major schema version.

## 4. Immutable task envelope

### 4.1 Coordinates

An origin or target coordinate is a complete identity binding:

```json
{
  "field_genesis_uuid": "2fd8336b-2cb1-4f36-a82e-503bcb9d1158",
  "mesh_slug": "example-mesh",
  "mesh_id": "8b4d65ac-9a46-4bd8-b3ae-2e5ea0a181bd",
  "agent_slug": "sender-agent",
  "agent_id": "10d1a37c-26d1-4583-9838-301c65eb95ea"
}
```

The target uses the same shape for the recipient. Slugs are locators; UUIDs and genesis bindings prevent slug reuse from silently changing identity. An implementation MUST verify both against current authoritative manifests and mesh endpoints.

### 4.2 Task identifier

`payload_hash` is lowercase hexadecimal SHA-256 over the exact payload representation defined by `payload.media_type` and `payload.encoding`. For the current text payload, it is SHA-256 over the UTF-8 bytes.

`task_id` is lowercase hexadecimal SHA-256 over the canonical JSON encoding of exactly:

```json
{
  "genesis_timestamp": "2026-11-05T20:00:00Z",
  "idempotency_key": "sender-scope/example-request-0001",
  "origin_coordinate": {},
  "payload_hash": "64-lowercase-hex-characters"
}
```

`origin_coordinate` is the complete object defined above, not a display string. `genesis_timestamp` is the immutable task-creation timestamp chosen before dispatch; it is distinct from field inception time and from later transport receipt times. The identifier input field names and object shape are fixed by schema version. Implementations MUST recompute `task_id` and reject a mismatch.

The producer MUST ensure an `idempotency_key` is unique within its origin coordinate for the intended logical operation. Reusing the same key with different payload bytes creates a different `task_id` but MUST be reported as an idempotency conflict, not accepted as an unrelated retry.

### 4.3 Envelope structure

The immutable envelope MUST contain:

- schema name/version and optional schema digest;
- `task_id`, `genesis_timestamp`, and `idempotency_key`;
- complete `origin_coordinate` and `target_coordinate`;
- payload media type, encoding, value/reference, length, and `payload_hash`;
- `task_type`, `execution_policy`, and `required_capabilities`;
- security bindings: producer identity, authorization context digest, optional recipient prompt/config digest, and signature/MAC references where the trust model requires them;
- lineage: field genesis, parent task IDs, predecessor envelope digest when migrated, and dispatch generation;
- `envelope_sha256` over the entire envelope except `envelope_sha256` and detached signatures.

The current `sender_*`, `recipient_*`, `mesh_*`, `field_genesis_uuid`, `required_capability`, `active_prompt_hash`, `task_type`, and `execution_policy` fields map into these structured bindings. Level 3 MUST NOT weaken any of them.

### 4.4 Authority-owned idempotency slots and duplicate delivery

The authority MUST own an idempotency-slot namespace keyed by the canonical JSON digest of exactly `(origin_coordinate, idempotency_key)`. Slot acquisition is a linearizable create-if-absent or CAS performed in the same authority transaction that accepts the immutable envelope and creates the task's initial `PENDING` state. A slot immutably binds:

- canonical origin coordinate and idempotency key;
- `payload_sha256`;
- every other immutable task-identity input, including `genesis_timestamp`;
- resulting `task_id` and `envelope_sha256`;
- acceptance receipt ID and current archival/tombstone status.

An exact retry whose canonical immutable inputs, payload digest, task ID, and envelope digest all match MUST return the existing task and acceptance receipt without creating another executable task. Reuse of the slot key with a changed payload or any conflicting immutable input MUST atomically preserve a typed `IDEMPOTENCY_CONFLICT` receipt containing the existing and proposed digests, actor, authority epoch, and timestamp; it MUST NOT create, replace, reset, or enqueue another task. A conflict receipt is evidence about the rejected proposal and does not mutate the accepted envelope.

Network delivery is at-least-once. Duplicate delivery of byte-identical envelopes with the same valid `task_id` is a no-op plus auditable duplicate-receipt evidence. A second envelope with the same `task_id` but different bytes or digest is an integrity conflict and enters `AMBIGUOUS`, never last-write-wins.

An idempotency slot MUST remain authoritative for at least the longer of the task/effect audit-retention period, all downstream retry horizons, and the producer's key-reuse horizon. Archival MUST replace the live slot with an immutable or authority-CAS-protected tombstone retaining the slot-key digest, origin digest, idempotency-key digest or protected value, payload digest, task ID, terminal receipt digest, authority epoch, and retention deadline. A tombstone continues to reject key reuse. Physical deletion is permitted only after an approved namespace-generation change that prevents old keys from colliding; elapsed retention alone MUST NOT silently free a key.

Execution is at-most-once only relative to a fenced authority and an adapter that enforces the sink fence at every consequential write. End-to-end exactly-once effects are not claimed. If an effect boundary cannot reject stale fences or deduplicate effects, the adapter is unsupported for automatic execution/replay and MUST fail closed or enter explicit reconciliation.

#### Non-authoritative idempotency-slot example

```json
{
  "schema_name": "recursive-field.idempotency-slot",
  "schema_version": "2.0.0",
  "slot_key_sha256": "1212121212121212121212121212121212121212121212121212121212121212",
  "origin_coordinate_sha256": "1313131313131313131313131313131313131313131313131313131313131313",
  "idempotency_key": "sender-scope/example-request-0001",
  "payload_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
  "immutable_inputs_sha256": "1414141414141414141414141414141414141414141414141414141414141414",
  "task_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "envelope_sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
  "acceptance_receipt_id": "a6d9bc09-cf45-46f1-8169-1ff5587db3b3",
  "status": "LIVE",
  "authority_epoch": 7,
  "slot_version": 1,
  "slot_sha256": "1515151515151515151515151515151515151515151515151515151515151515"
}
```

### 4.5 Non-authoritative envelope example

```json
{
  "schema_name": "recursive-field.distributed-task-envelope",
  "schema_version": "2.0.0",
  "schema_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "task_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "genesis_timestamp": "2026-11-05T20:00:00Z",
  "idempotency_key": "sender-scope/example-request-0001",
  "origin_coordinate": {
    "field_genesis_uuid": "2fd8336b-2cb1-4f36-a82e-503bcb9d1158",
    "mesh_slug": "example-mesh",
    "mesh_id": "8b4d65ac-9a46-4bd8-b3ae-2e5ea0a181bd",
    "agent_slug": "sender-agent",
    "agent_id": "10d1a37c-26d1-4583-9838-301c65eb95ea"
  },
  "target_coordinate": {
    "field_genesis_uuid": "2fd8336b-2cb1-4f36-a82e-503bcb9d1158",
    "mesh_slug": "example-mesh",
    "mesh_id": "8b4d65ac-9a46-4bd8-b3ae-2e5ea0a181bd",
    "agent_slug": "worker-agent",
    "agent_id": "da61d9bf-b9a5-4ace-a774-71a23d829a77"
  },
  "payload": {
    "media_type": "text/plain; charset=utf-8",
    "encoding": "inline-utf8",
    "value": "inspect the unit cell",
    "length_bytes": 21
  },
  "payload_hash": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
  "task_type": "inspect_unit_cell",
  "execution_policy": "allowlisted",
  "required_capabilities": ["coordinate"],
  "security": {
    "producer_principal": "agent:sender-agent",
    "authorization_context_sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
    "target_prompt_sha256": null
  },
  "lineage": {
    "field_genesis_uuid": "2fd8336b-2cb1-4f36-a82e-503bcb9d1158",
    "parent_task_ids": [],
    "predecessor_envelope_sha256": null,
    "dispatch_generation": 1
  },
  "envelope_sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
}
```

Example digest values are placeholders and intentionally do not verify.

## 5. Lease claim, monotonic time, and persistent fencing

### 5.1 Claim structure and resolved token scopes

Every successful claim generation produces an immutable claim-generation record and atomically updates the authoritative task state pointer. Level 3 uses two explicit token scopes:

1. `lease_generation_token` is strictly monotonic within one authoritative queue partition and orders claim ownership and task-lifecycle writes. It is allocated once per successful claim/takeover and never reused.
2. `sink_fence` is strictly monotonic within a declared consequential `protected_resource_scope`. It is registered with, or atomically enforced by, that sink before an effect. One lease token may map to multiple sink fences; a lease token is not assumed to order unrelated resources.

A claim MUST include task/envelope/slot digest bindings, `claim_id`, `claim_generation` starting at 1, `predecessor_claim_sha256`, `lease_generation_token`, owner exactly `{DROPLET_ID}:{CONTAINER_SLUG}:{boot_id}`, owner components, monotonic lease coordinates, audit UTC projections, heartbeat coordinates, authority identifier/epoch, and claim digest. `boot_id` MUST be the current Linux boot UUID or an equivalently strong boot-incarnation identifier. Container restart identity MUST NOT substitute for host boot identity; both are bound.

The authority MUST maintain a durable highest-seen register for each queue partition and task lifecycle, keyed by `(authority_id, authority_epoch, partition_id)`, containing at least the greatest allocated lease-generation token and greatest committed token per task. Every consequential sink MUST maintain or transactionally consult its own durable register keyed by `(protected_resource_scope, authority_lineage)` and containing the greatest accepted sink fence plus the task/effect binding. Register advancement is CAS from the exact previous value; successful advancement and the accepted write MUST be atomic at the protected sink.

### 5.2 Non-authoritative claim and sink-fence example

```json
{
  "schema_name": "recursive-field.distributed-task-claim",
  "schema_version": "2.0.0",
  "task_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "idempotency_slot_sha256": "1515151515151515151515151515151515151515151515151515151515151515",
  "envelope_sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
  "claim_id": "9de27aae-ef61-4d99-887e-8f4d64f8caf7",
  "claim_generation": 3,
  "predecessor_claim_sha256": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
  "lease_generation_token": 1042,
  "lease_owner": "droplet-42:worker-field-scout:9a85522e-d39f-41a9-b816-9c28f1eb35c4",
  "owner": {
    "droplet_id": "droplet-42",
    "container_slug": "worker-field-scout",
    "boot_id": "9a85522e-d39f-41a9-b816-9c28f1eb35c4"
  },
  "authority": {
    "authority_id": "queue-authority/example-mesh/0",
    "authority_epoch": 7,
    "partition_id": "example-mesh/0"
  },
  "claimed_monotonic_tick": 8800000000,
  "expires_monotonic_tick": 9100000000,
  "monotonic_unit": "nanoseconds",
  "claimed_at_utc": "2026-11-05T20:00:01Z",
  "lease_expires_at_utc_projection": "2026-11-05T20:05:01Z",
  "heartbeat_interval_seconds": 60,
  "renewal_cutoff_monotonic_tick": 9095000000,
  "last_heartbeat_sequence": 0,
  "claim_sha256": "1111111111111111111111111111111111111111111111111111111111111111"
}
```

```json
{
  "schema_name": "recursive-field.protected-resource-fence",
  "schema_version": "2.0.0",
  "protected_resource_scope": "mesh/example-mesh/result-store",
  "authority_epoch": 7,
  "lease_generation_token": 1042,
  "sink_fence": 5018,
  "task_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "effect_digest": "1616161616161616161616161616161616161616161616161616161616161616",
  "previous_register_sha256": "1717171717171717171717171717171717171717171717171717171717171717",
  "register_version": 88,
  "registered_at_utc": "2026-11-05T20:03:00Z",
  "register_sha256": "1818181818181818181818181818181818181818181818181818181818181818"
}
```

### 5.3 Monotonic authority time and heartbeat

Lease eligibility MUST be based on elapsed ticks from one authority incarnation's monotonic clock, not UTC or any worker clock. `claimed_monotonic_tick`, `expires_monotonic_tick`, `renewal_cutoff_monotonic_tick`, monotonic unit, authority epoch, and monotonic-incarnation ID are authoritative. UTC timestamps are audit projections only and MUST NOT make a lease eligible, renew it, or expire it.

The authority MUST configure a maximum cross-node audit-clock uncertainty and a separate monotonic scheduling uncertainty margin. The heartbeat interval MUST be no greater than one-third of lease duration. Renewal is accepted only before the monotonic renewal cutoff and only when heartbeat sequence, claim generation, lease token, owner boot, state version, and authority epoch match. A late, duplicated, or reordered heartbeat is rejected durably and cannot resurrect a lease.

Takeover is eligible only after the authority itself observes monotonic time at or beyond `expires_monotonic_tick + monotonic_uncertainty_margin`, the state is reclaimable, and effect evidence permits replay. Worker timestamps and apparent UTC expiry are never sufficient. Fencing remains the final stale-writer barrier even when clocks agree.

On authority process restart, monotonic ticks from the prior process/boot MUST NOT be compared directly unless the substrate provides a restart-stable monotonic source and proves continuity. Otherwise the authority MUST enter recovery, stop claims/renewals/takeovers, advance authority epoch, recover the durable highest-seen registers, invalidate prior renewals, and wait at least the maximum remaining lease duration plus uncertainty margin or obtain a stronger substrate proof that every prior lease is fenced. UTC rollback or audit-clock uncertainty above its bound freezes UTC projections but cannot extend a monotonic lease. Monotonic rollback or continuity failure freezes actuation and requires the failover procedure.

### 5.4 Claim, register, and heartbeat CAS rules

A claim CAS supplies the expected idempotency slot, task state/version, prior claim generation/digest, highest-seen lease register, and authority epoch. Success atomically verifies eligibility, increments generation, allocates a token greater than the durable register, persists the claim, advances the register, and points state to `CLAIMED`.

A heartbeat CAS may extend monotonic expiry but MUST NOT change owner, generation, lease token, task, slot, or envelope binding. A lifecycle commit CAS succeeds only for the current claim, lease token, authority epoch, state version, and an effect/result proof accepted under every required sink fence.

A sink write MUST present authority epoch, lease-generation token, protected resource scope, expected sink-register version, new sink fence, task ID, and effect digest. The sink atomically rejects a token/fence not greater than its durable highest-seen register, a reused fence with different content, or a mismatched authority lineage. Successful write and register advancement are one sink transaction. Rejection creates immutable stale-writer evidence.

### 5.5 Failover, non-reuse, and split-brain limits

Authority failover MUST allocate a new epoch from durable authority lineage, recover the greatest token ever allocated in all predecessor epochs, and initialize the new epoch's first token strictly above that global high-water mark. Epoch change is not permission to reset or reuse numeric tokens. The old authority MUST be prevented from advancing registers or reaching consequential sinks before the new authority serves claims.

If continuity of the high-water mark, exclusive authority, or protected-sink register cannot be proven, claims and consequential writes fail closed and affected tasks enter `AMBIGUOUS` or `RECONCILIATION_REQUIRED` according to section 6.5. If a sink cannot atomically enforce and persist its fence, that sink is `UNSUPPORTED_FOR_DISTRIBUTED_EFFECTS`; the adapter MUST fail before effect. If an effect may already have occurred, the task enters reconciliation or ambiguity and MUST NOT silently claim fencing safety.

Fencing limits stale writers only where every consequential sink checks its register. During a partition, a minority or disconnected worker loses renewal and commit authority. If two authorities can advance the same lineage, safety is lost; reconciliation may detect but cannot retroactively undo effects.

## 6. Lifecycle and directory ownership

### 6.1 Normative states

The primary lifecycle is:

`PENDING -> CLAIMED -> COMMITTED`

or:

`PENDING -> CLAIMED -> RECLAIMABLE -> CLAIMED`

Additional states preserve failure and uncertainty honestly:

- `FAILED_FINAL`: verified semantic failure with an immutable result and terminal receipt; no automatic retry.
- `AMBIGUOUS`: conflicting envelope, claim, result, authority, or effect evidence; execution and automatic takeover stop.
- `RECONCILIATION_REQUIRED`: artifacts appear individually valid but required lifecycle/ledger evidence is missing or inconsistent.
- `QUARANTINED`: trust, schema, signature, identity, capability, or integrity validation failed before safe execution.
- `CANCELLED`: authority-approved cancellation before consequential commit; cancellation does not assert that no external effect occurred.

`COMMITTED` means the authority accepted a terminal receipt and all required effect attestations for the declared task type. It is stronger than “adapter returned successfully” and weaker than an unqualified claim of exactly-once reality.

### 6.2 Transition table

| From | Event/guard | To | Required durable evidence |
| --- | --- | --- | --- |
| none | slot/task CAS accepts valid envelope | `PENDING` | immutable slot, envelope, acceptance receipt, ledger entry |
| none | slot key exists with changed immutable input | none | typed `IDEMPOTENCY_CONFLICT`; no task created |
| `PENDING` or `RECLAIMABLE` | step-1 reservation CAS succeeds | `CLAIM_RESERVING` | claim reservation and expected versions |
| `CLAIM_RESERVING` | step-2 register/state CAS succeeds | `CLAIMED` | claim generation, lease token, monotonic expiry, high-water register |
| `PENDING` | trust/integrity validation fails | `QUARANTINED` | rejection receipt and reason |
| `CLAIMED` | valid heartbeat CAS before monotonic cutoff | `CLAIMED` | heartbeat evidence and renewed monotonic expiry |
| `CLAIMED` | effect attempt recorded | `CLAIMED` | `EFFECT_ATTEMPTED` evidence under current fences |
| `CLAIMED` | effect/result attested and step-4 CAS succeeds | `COMMITTED` | result, effect attestations, terminal receipt, committed-token register |
| `CLAIMED` | verified final semantic failure and step-4 CAS succeeds | `FAILED_FINAL` | failure result, required attestations, terminal receipt |
| `CLAIMED` | monotonic expiry plus margin; replay policy/evidence permit | `RECLAIMABLE` | reclamation receipt and prior claim digest |
| `RECLAIMABLE` | takeover protocol succeeds | `CLAIMED` | next generation and greater lease/sink fences |
| any nonterminal | contradictory or outcome-indeterminate effect evidence | `AMBIGUOUS` | preserved conflict bundle and freeze receipt |
| any | noncontradictory missing evidence with authoritative query/repair path | `RECONCILIATION_REQUIRED` | discrepancy record and referenced artifacts |
| `PENDING` or safely stopped `CLAIMED` | authorized cancellation CAS | `CANCELLED` | cancellation receipt and effect-status attestation |
| `RECONCILIATION_REQUIRED` | authorized deterministic repair proves one legal state | proven state | reconciliation authorization and receipt linking all evidence |

Terminal records MUST NOT transition by mutation. Correction is a new reconciliation record that references the preserved terminal evidence.

### 6.3 Exact authoritative directory model

For a filesystem-backed authority, one mesh partition owns:

```text
mesh/<mesh>/
├── channel.json
├── queue.jsonl
└── tasks/
    ├── pending/<task_id>/
    ├── claimed/<task_id>/
    ├── reclaimable/<task_id>/
    ├── completed/<task_id>/
    ├── failed/<task_id>/
    ├── ambiguous/<task_id>/
    ├── reconciliation/<task_id>/
    ├── quarantined/<task_id>/
    ├── cancelled/<task_id>/
    ├── idempotency/slots/<slot_key_sha256>.json
    ├── idempotency/tombstones/<slot_key_sha256>.json
    ├── claims/<task_id>/<claim_generation>.json
    ├── heartbeats/<task_id>/<claim_generation>/<sequence>.json
    ├── fence-registers/queue/<partition_id>.json
    ├── fence-registers/tasks/<task_id>.json
    ├── effects/<task_id>/<attestation_sha256>.json
    ├── receipts/<task_id>/<receipt_id>.json
    ├── results/<task_id>/<result_sha256>.json
    ├── outbox/<receipt_id>.json
    └── ledger/events.jsonl
```

Each state directory contains an immutable `envelope.json` plus an authority-written `state.json` pointer. A task appears in exactly one state directory in the authoritative namespace. Idempotency slots/tombstones, claims, heartbeats, fence registers, effects, receipts, results, and outbox records are authority-owned evidence referenced by digest from `state.json`; they are not alternative lifecycle locations. Protected sinks additionally own their resource-scoped highest-seen fence registers.

Ownership is exact:

- the authenticated producer may propose an envelope but only the queue authority creates `pending` and its acceptance receipt;
- only the lease authority allocates claims, tokens, heartbeats, and state transitions;
- a worker may submit a proposed result/effect evidence but only a token-validating authority publishes it to `results` and commits state;
- the ledger authority records accepted transitions;
- replicas are read-only until promoted through an epoch-changing authority procedure;
- `agents/<agent>/worker_state/` may cache scan, scheduling, or last-seen data, but MUST NOT be authoritative for Level 3 ownership or fencing.

The legacy `mesh/<mesh>/tasks/<task_id>.json`, `mesh/<mesh>/results/<task_id>.json`, and agent-local claims require a migration adapter; they are not silently reinterpreted as Level 3 records.

### 6.4 Receipts, results, and ledger evidence

Every accepted transition produces an immutable receipt containing the prior and next state digests, claim generation and lease token when applicable, sink-fence bindings, authority epoch, actor, authoritative monotonic coordinate, UTC audit projection, and receipt digest. Results bind task, idempotency slot, envelope, claim, lease token, sink fences, adapter version, status, result payload digest, and effect attestations.

`queue.jsonl` remains an audit/event projection and compatibility surface. It is not the Level 3 CAS database. `tasks/ledger/events.jsonl` is also evidence unless its append and uniqueness rules are transactionally coupled to state changes. Periodic snapshots SHOULD hash all authoritative task records into the formation `state/ledger.jsonl`, preserving the current persistence pattern without treating a later snapshot as the transition authority.

### 6.5 Pre-receipt effect attestation and reconciliation

Before the authority may issue a terminal receipt for any consequential effect, it MUST persist an immutable pre-receipt effect attestation. The attestation binds:

- `task_id`, idempotency-slot digest, envelope digest, claim ID/generation, lease-generation token, authority epoch, and every relevant sink fence;
- adapter name/version and execution attempt;
- target/effect coordinate and protected-resource scope;
- canonical request digest and observed effect/response digest;
- observed status: `NOT_ATTEMPTED`, `ACCEPTED`, `REJECTED`, `UNKNOWN`, or `CONTRADICTORY`;
- sink-generated proof, receipt, transaction, or query coordinate and its digest;
- observation method, observer identity, monotonic observation coordinate, and UTC audit projection;
- predecessor attestation digest and attestation digest.

The lifecycle is `PROPOSED -> EFFECT_ATTEMPTED -> ATTESTED -> TERMINAL_RECEIPTED`. `EFFECT_ATTEMPTED` MUST be recorded before or atomically with sending the effect request. `ATTESTED` requires durable sink evidence or a durable statement that evidence is unavailable. A terminal receipt is forbidden until all required effects are `ATTESTED` and classification is deterministic.

```json
{
  "schema_name": "recursive-field.pre-receipt-effect-attestation",
  "schema_version": "2.0.0",
  "task_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "idempotency_slot_sha256": "1515151515151515151515151515151515151515151515151515151515151515",
  "envelope_sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
  "claim_id": "9de27aae-ef61-4d99-887e-8f4d64f8caf7",
  "claim_generation": 3,
  "execution_attempt": 3,
  "authority_epoch": 7,
  "lease_generation_token": 1042,
  "protected_resource_scope": "mesh/example-mesh/result-store",
  "sink_fence": 5018,
  "adapter": {
    "name": "inspect_unit_cell",
    "version": "2.0.0"
  },
  "effect_coordinate": "result-store/task/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "request_sha256": "1919191919191919191919191919191919191919191919191919191919191919",
  "effect_sha256": "2020202020202020202020202020202020202020202020202020202020202020",
  "observed_status": "ACCEPTED",
  "sink_proof": {
    "query_coordinate": "result-store/receipt/example-proof-1",
    "proof_sha256": "2121212121212121212121212121212121212121212121212121212121212121"
  },
  "observed_by": "queue-authority/example-mesh/0",
  "observed_monotonic_tick": 8990000000,
  "observed_at_utc": "2026-11-05T20:03:10Z",
  "predecessor_attestation_sha256": null,
  "attestation_sha256": "2222222222222222222222222222222222222222222222222222222222222222"
}
```

Classification is deterministic:

- `RECONCILIATION_REQUIRED` applies when accepted immutable records do not contradict each other and an authorized, side-effect-free sink query can determine or repair missing proof, projection, register, or receipt state.
- `AMBIGUOUS` applies when valid-looking records contradict, the sink reports `UNKNOWN` after its proof horizon, an effect may have occurred but no authoritative query can distinguish outcomes, authority/fence lineage conflicts, or replay could duplicate an unfenced effect.
- A verified sink `REJECTED` under the current fence is not ambiguous; policy may produce `FAILED_FINAL` or a new authorized attempt.
- A verified sink `ACCEPTED` with matching request/effect digest and fence may be reconciled into a terminal receipt without replay.

Only a principal holding the configured reconciliation capability and independent of the failed worker MAY reconcile. It MUST issue an immutable reconciliation authorization naming permitted sink queries and whether replay is allowed. Replay requires proof of `NOT_ATTEMPTED` or `REJECTED`, a current claim and fresh sink fence, and adapter policy that permits replay. `AMBIGUOUS` replay additionally requires an explicit higher-authority risk acceptance; default is no replay. Contradictory evidence is never deleted or overwritten.

### 6.6 Crash boundaries and replay

| Crash boundary | Recovery rule |
| --- | --- |
| Before idempotency/task-slot CAS | Redelivery retries acquisition; no executable task exists. |
| After slot/task acceptance, before claim reservation | Exact retry returns the accepted task/receipt; scheduling resumes from `PENDING`. |
| After claim/fence reservation, before worker starts | Lease expires monotonically; safe tasks become `RECLAIMABLE`. |
| After `EFFECT_ATTEMPTED`, before sink response | Query the bound sink proof coordinate; classify under section 6.5 before replay. |
| After sink effect/register acceptance, before attestation persistence | Reconstruct attestation from sink proof; if proof is unavailable or contradictory, classify `AMBIGUOUS`. |
| After attestation, before terminal CAS | Validate current claim/fences and commit without repeating the effect. |
| After terminal CAS, before event/ledger projection | Repair hash-linked projections from the immutable terminal receipt; never rerun the adapter. |
| After cursor/cache update failure | Rebuild caches from authoritative lifecycle state. |

Replay MUST validate the current envelope, idempotency slot, identities, capabilities, adapter policy, claim, lease token, sink fences, authority epoch, effect attestations, and any existing result. A terminal receipt suppresses execution regardless of duplicate network delivery or stale local cursor state.

## 7. Atomicity model

### 7.1 Filesystem boundary

Same-directory temporary-file write plus `fsync` plus atomic rename can provide a strong local artifact replacement primitive on a qualifying local filesystem. `O_EXCL` can provide local create-if-absent. Neither primitive automatically becomes distributed CAS across separate filesystems, replicated hosts, asynchronous sync tools, object replicas, or network filesystems with weaker semantics.

A directory move is a lifecycle CAS only when source, destination, state metadata, claim generation, and receipt are changed by one authority transaction. Moving files independently and appending evidence afterward creates observable crash windows that require reconciliation.

### 7.2 Deployment classes

1. **Single authoritative storage:** all writers use one linearizable storage authority. Local rename/CAS may be sufficient if filesystem semantics, locking, durability, and failover epochs are proven.
2. **Replicated object transport:** replicas carry immutable envelopes/results. A separate authority must linearize claims and commits; object “last write wins” is prohibited for lifecycle state.
3. **Multi-writer shared filesystem:** allowed only after proving create, rename, locking, cache coherency, fencing, failure, and failover semantics on the exact filesystem/mount configuration. Advisory locks alone do not fence a paused or partitioned writer.

Git synchronization and detached block-volume movement may transport durable history, but do not provide concurrent claim CAS. A block volume that is not safely multi-attach may host a single authority only.

### 7.3 Consequential-write fencing

Every consequential write MUST carry `task_id`, `claim_generation`, `lease_generation_token`, `authority_epoch`, `protected_resource_scope`, and the sink fence allocated for that scope. The receiver MUST atomically reject a stale or conflicting authority lineage, token, register version, fence, task binding, or effect digest. This applies to result publication, state transition, ledger acceptance, external effects, and cleanup that can destroy authoritative evidence.

A path that cannot enforce and durably persist its protected-resource fence is unsupported for distributed effects and MUST fail before execution. If prior effect is uncertain, it enters `RECONCILIATION_REQUIRED` or `AMBIGUOUS`; it is never silently treated as safe.

### 7.4 Exact four-step authority protocol

The authority protocol is ordered and may not skip a step:

1. **Idempotency/task slot plus claim reservation.** In one linearizable authority transaction, acquire or validate the idempotency slot, accept the immutable envelope/task if new, CAS the task from eligible state to `CLAIM_RESERVING`, and persist an immutable claim-reservation record with expected state version, predecessor claim digest, owner, boot ID, and reservation ID. Exact duplicate input returns the existing acceptance/claim outcome; a slot conflict writes typed conflict evidence and stops.
2. **Fencing registration plus state-pointer advancement.** In one authority transaction, CAS the reservation and queue/task highest-seen registers, allocate a never-reused `lease_generation_token`, persist the claim generation and monotonic lease coordinates, and advance the task pointer from `CLAIM_RESERVING` to `CLAIMED`. No execution or effect is permitted before this transaction commits. Required sink fences are then CAS-registered at each sink; each sink write and its register advancement are one sink transaction.
3. **Execution/effect-proof persistence under the fence.** Before effect, persist `EFFECT_ATTEMPTED` bound to the claim and fences. The sink atomically applies or rejects the request with its fence-register CAS. Persist immutable result data and the pre-receipt effect attestation, including sink proof/query coordinates, under the same task/claim/fence bindings. These records may be separate from the queue-authority transaction only because they are immutable and hash-linked; their sink acceptance and sink-register advancement may not be separated.
4. **Terminal receipt plus committed-state advancement.** In one linearizable authority transaction, validate current task/claim/register versions and all required attestations, persist the immutable terminal receipt, advance the task pointer to `COMMITTED` or `FAILED_FINAL`, and record the committed lease token. Event, ledger, observation, and replica projections may follow through a hash-linked transactional outbox; they are not part of terminal truth.

The selected authority substrate MUST atomically perform each transaction named above, enforce uniqueness of slot/task/reservation/receipt keys, and durably persist CAS versions and highest-seen registers before acknowledging success. It need not atomically combine queue-authority storage with an external sink; that boundary is joined by sink-fence CAS, effect digest, immutable attestation, and reconciliation. If the substrate cannot provide the named transaction, it is not a conforming Level 3 authority.

Crash evidence and deterministic recovery are:

| Last durable evidence | Deterministic recovery |
| --- | --- |
| No step-1 reservation | Retry step 1; no executable task or claim exists. |
| Slot/task accepted but `CLAIM_RESERVING` only | Resume or cancel that exact reservation by CAS; never create a second task for the slot. |
| Step 2 claim/register committed | Treat the claim as owned until monotonic expiry; execution may begin once required sink fences are registered. |
| Some sink fences registered, no effect-attempt record | Register remaining fences or abandon claim; no effect may be inferred. |
| `EFFECT_ATTEMPTED`, no sink proof | Query the bound sink and classify via section 6.5; replay is forbidden meanwhile. |
| Sink register/effect committed, attestation missing | Reconstruct from sink proof; absent proof becomes reconciliation or ambiguity, never blind replay. |
| Attestation/result durable, no terminal receipt | Validate current fences and execute step 4 without repeating the effect. |
| Terminal receipt/state committed, projections missing | Replay outbox/projections from receipt digest; never re-execute. |

### 7.5 Append limitation

The current `_append_event_once` is read-then-append. Two concurrent writers can both observe absence and append duplicates; a crash can also separate lifecycle state from event evidence. Level 3 MUST either:

- include uniqueness and append in the same transaction as the state transition;
- serialize appenders under a lock whose ownership is fenced by the authority; or
- accept duplicate append-only projections and run transactional reconciliation keyed by immutable receipt ID.

Simple read-then-append deduplication MUST NOT be presented as distributed idempotency.

## 8. Non-harmonic contention backoff

### 8.1 Applicability and ownership

This backoff applies only after a contested distributed lease or lifecycle CAS. It does not alter the current bounded `consume_queue.py --once` path, its local systemd timer, or an uncontested empty poll.

The scheduler owns delay, cancellation, fairness bookkeeping, and requeue timing. The lease authority owns eligibility, its monotonic elapsed-time source, CAS, token allocation, and expiry. A scheduler MUST NOT infer ownership from sleeping longer or shorter than another contender.

### 8.2 Exact attempt and delay contract

The per-task contention counter begins at `n=0`. The scheduler submits CAS attempt `n`; only an authoritative `CAS_CONFLICT` or `LEASE_CONTESTED` response increments the next attempt to `n+1`. `AUTHORITY_UNAVAILABLE`, timeout, malformed response, authentication failure, transport failure, and local cancellation do not increment or reset this counter; they use separate bounded policies. `STALE_EXPECTATION` counts as contention only when the authority also proves another eligible owner/version won the same claim coordinate.

The counter resets to `0` only after `CLAIM_ACQUIRED`, `TERMINAL`, `INELIGIBLE`, `CANCELLED`, or `NOT_FOUND` is authoritatively observed, or after the mandatory yield completes and a newly read state version is used. `CLAIM_HELD_BY_OTHER` increments and does not reset. A successful heartbeat or commit pertains to an owner, not a waiting contender, and does not reset other contenders.

For consecutive contested attempts `n = 0..11`:

- `base = 250 ms`;
- Fibonacci numbers use `F0=0`, `F1=1`;
- `window_n = min(30000 ms, base * F(n+2))`;
- `phi = (1 + sqrt(5)) / 2`;
- `node_phase` is the unit interval derived from the first 64 bits of `SHA-256(task_id || lease_owner || authority_epoch)`;
- `phase_n = fractional_part(node_phase + n / phi)`;
- deterministic delay is `window_n * (0.5 + 0.5 * phase_n)`, capped absolutely at 30 seconds.

A deployment MAY replace `phase_n` with cryptographically random uniform jitter in `[0,1)` when nondeterministic scheduling is acceptable. It MUST document which mode is active. Deterministic phase improves replayability but can preserve collisions if identities are cloned; random phase reduces correlated retries but complicates reproduction. Node and boot identity validation is required in either mode.

After the response to attempt 11 is contested, the contender MUST emit `CONTENTION_YIELD`, stop attempting that task for at least one heartbeat interval, and enter the fairness queue. On release, the scheduler MUST reread authoritative state and reset to attempt 0; it MUST NOT resume at 12. Eligible tasks are ordered by oldest authoritative `pending_since_monotonic` first, with round-robin tie-breaking among equal age buckets and a per-task dispatch quantum of one claim attempt before another eligible task is considered. This oldest-first rule is normative.

A task waiting longer than `max(2 * lease_duration, 5 minutes)` MUST emit `STARVATION_DETECTED` and page/alert the configured operator surface. This is a fairness signal, not authority to bypass CAS, fences, capability checks, or ordering. Level 3 guarantees only that an eligible task is reconsidered once per complete fairness-queue rotation while the scheduler and authority are available; it does not guarantee acquisition under an indefinitely held lease or unavailable authority.

These rules apply only to contested distributed lease/CAS acquisition. They never apply to the current `consume_queue.py --once` idle path, empty polls, its systemd timer, or transport retries.

### 8.3 Observability

Every attempt, delay, reset, yield, and starvation decision MUST emit an immutable or transactionally projected event with: event type, task ID, idempotency-slot digest, authority ID/epoch, lease owner, protected partition, expected and observed state version, authority response class, attempt before/after, Fibonacci window, chosen delay, 30-second cap indicator, jitter mode/phase, pending age, fairness-queue position, heartbeat/lease duration, monotonic event coordinate, UTC audit projection, and outcome. Metrics MUST include CAS conflicts by response class, claim latency, yields, resets, takeover count, stale-token rejection, starvation age, queue rotations, and per-node win rate. Secret material and payload content MUST NOT appear.

## 9. Trust, identity, partitions, and recovery

### 9.1 Trust and security

Producers and workers MUST authenticate to the authority. Authorization is evaluated at envelope acceptance, claim, heartbeat renewal, result proposal, and commit. The worker MUST revalidate current target identity, mesh membership, task type, execution policy, required capabilities, schema support, payload/envelope digests, and security bindings before execution. Capability at dispatch is evidence, not perpetual authority.

Signatures or MACs, when selected, MUST bind the canonical envelope/claim/receipt digest, key identifier, algorithm, and trust-domain epoch. Key rotation MUST preserve verification of retained evidence. Unknown algorithms, revoked principals, or broken lineage fail closed to `QUARANTINED` or `RECONCILIATION_REQUIRED` according to whether evidence is invalid or merely unavailable.

Payload references MUST be content-addressed, access-controlled, size-bounded, and verified before use. No credential, bearer token, private key, or live endpoint secret belongs in an envelope, receipt, result, or audit projection.

### 9.2 Node and boot identity

`DROPLET_ID` comes from an authenticated deployment inventory or instance identity document, not a caller-supplied display name. `CONTAINER_SLUG` is unique within a droplet deployment generation. `boot_id` is read at worker start and rechecked before every heartbeat and consequential commit. A boot change invalidates all leases from the previous boot, subject to authoritative expiry/takeover rules; it does not allow immediate local deletion or claim reuse.

Cloned node identities are a safety violation. The authority MUST reject simultaneous owners with an identical owner tuple but contradictory authenticated sessions.

### 9.3 Clock and partition behavior

Workers MUST NOT decide lease expiry from local or UTC time. A partitioned worker loses renewal and commit authority. It may checkpoint pure computation locally, but its later result is only a proposal and is rejected by a newer lease token or sink fence. Section 5.3 exclusively defines monotonic expiry, uncertainty margin, restart continuity, and rollback behavior; fencing registers remain the final stale-writer barrier.

Authority failover MUST change `authority_epoch`, recover every queue/task and sink high-water register, allocate tokens strictly above all predecessor values, and prevent the prior authority from accepting writes. If exclusive authority or register continuity cannot be proven, actuation freezes and affected tasks are classified under section 6.5.

### 9.4 Retention and auditability

At minimum, idempotency slots or tombstones, envelopes, all claim generations, fence-register lineage, effect attestations, terminal results, terminal/reconciliation receipts, and ledger evidence MUST be retained for the longer of the operational audit period, all downstream retry horizons, and the producer key-reuse horizon. Slot tombstones continue rejecting reuse until an approved namespace-generation change. Heartbeats may be compacted only into a digest-linked summary after the task is terminal and policy permits it. Compaction is additive: it writes a signed summary and tombstone receipt before deleting eligible detail.

Audit reconstruction MUST answer: who proposed the task, which exact bytes were accepted, which identity/capability checks passed, who held each lease, which tokens were rejected or accepted, what result/effect evidence was committed, and how any ambiguity was resolved. Audit evidence does not itself prove an external-world effect.

### 9.5 Recovery procedure

Recovery MUST:

1. freeze new claims for the affected partition;
2. identify authority epoch and greatest durable fencing token;
3. verify immutable record digests and lineage;
4. rebuild lifecycle state from accepted receipts, not worker caches;
5. classify gaps as repairable projection loss, `RECONCILIATION_REQUIRED`, or `AMBIGUOUS`;
6. revalidate identity, boot, capability, and adapter replay policy;
7. issue reconciliation receipts for repairs;
8. resume claims only after a single authority and token sequence are proven.

No recovery procedure may delete contradictory evidence to make the state appear clean.

## 10. Normative invariants

1. An accepted `task_id` deterministically binds origin coordinate, payload hash, genesis timestamp, and idempotency key.
2. The authority atomically binds one idempotency slot to one immutable input set and task; conflicts never create executable work, and tombstones prevent silent key reuse.
3. An envelope is immutable after acceptance; corrections create a new lineage record.
4. One authoritative lifecycle state exists per task and queue partition.
5. Claim generation and queue-partition lease token strictly increase; protected sinks independently persist monotonically increasing resource fences.
6. Tokens and fences are never reused across authority epochs, and every consequential write atomically validates and advances the applicable durable register.
7. Authority monotonic elapsed time alone determines lease eligibility; worker/UTC clocks are audit-only and fencing is the final stale-writer barrier.
8. Duplicate transport delivery never causes envelope overwrite or automatic re-execution.
9. A valid terminal receipt suppresses execution even when cursors, projections, or replicas lag.
10. Every consequential effect has a pre-receipt attestation; crash-after-effect evidence is reconciled or classified ambiguous before replay.
11. Existing valid results and contradictory evidence are preserved, never rewritten or deleted in place.
12. Capability, identity, schema, digest, slot, claim, and fence checks are repeated at execution and commit boundaries.
13. Automatic reclamation is prohibited when effect ambiguity cannot be fenced, queried, or deduplicated.
14. The four authority steps execute in order with the specified atomic boundaries and hash-linked cross-sink evidence.
15. Append-only projections are not treated as transactional state unless their storage proves that property.
16. Agent-local worker state is a cache/evidence surface, not Level 3 lease authority.
17. PHI/Fibonacci delay applies only after authoritative contested distributed CAS responses and obeys exact reset, yield, fairness, and observability rules.
18. Transport and gateway choices cannot weaken lifecycle, trust, fencing, or audit requirements.
19. Reconciliation is explicit, independently authorized, receipt-bearing, and preserves contradictory evidence.

## 11. Documentary mismatches and dispositions

| Baseline evidence or prior blueprint | Level 3 disposition | Constraint shadow |
| --- | --- | --- |
| Current `task_id` is UUIDv4. | **Supersede** with canonical SHA-256 identifier in schema major version 2. | Requires migration and dual-reader boundary; existing IDs remain historical. |
| Current envelope canonicalization is Python sorted-key compact JSON. | **Adapt** with stricter cross-language timestamp/number rules. | Fixtures are required; RFC 8785 remains parked. |
| Current claim is agent-local `O_EXCL` with a 300-second lease. | **Supersede** as authority; preserve as documentary evidence/cache only. | Distributed safety requires CAS, boot identity, heartbeat, generations, and fencing. |
| Expired current claims are replayed because the sole adapter is read-only. | **Preserve conditionally** as an adapter-specific replay rule. | Must not generalize to arbitrary side effects. |
| Current result-first crash recovery preserves the result artifact. | **Preserve** as an immutable-result reconciliation invariant. | Commit still requires current token/effect evidence. |
| Current cursor serializes one queue scan. | **Retire as authority**, optionally preserve as a local scheduling cache. | Cursors cannot arbitrate distributed ownership. |
| Current `queue.jsonl` is an append-only lifecycle/event surface. | **Adapt** into an audit projection. | `_append_event_once` is not concurrent deduplication. |
| Multi-node docs say a shared or synced queue enables cross-host delegation. | **Clarify/limit**: it enables transport visibility only. | Shared/synced bytes do not establish CAS, fencing, or coherent identity. |
| Existing systemd timer uses fixed five-second boundaries and local `flock`. | **Preserve for Level 2 only**. | Distributed contention backoff is a separate scheduler contract. |
| Gateway/VPN examples imply possible routing. | **Park transport projection**. | Routing and confidentiality do not confer queue authority. |

## 12. Unresolved substrate and policy decisions

The following semantic points are settled by this specification and are not open design choices: authority-owned idempotency-slot CAS/conflict/tombstones; queue-partition lease tokens plus protected-resource sink fences; durable non-reused high-water registers across epochs; authority-monotonic lease eligibility; pre-receipt effect attestations and deterministic ambiguity/reconciliation classification; exact contention counter/fairness rules; and the four-step transaction order.

Only implementation-specific choices remain:

1. Which authority substrate implements the required linearizable transactions, monotonic source, durable registers, uniqueness, and transactional outbox?
2. Which protected-resource scope names and sink adapters implement the required resource fences? Scope semantics are fixed; the concrete inventory is deployment-specific.
3. What numeric lease duration, renewal cutoff margin, monotonic uncertainty margin, and audit-clock uncertainty satisfy each tested substrate? Their roles and fail-closed behavior are fixed.
4. Will canonical JSON remain the tightened project profile or adopt RFC 8785 in version 2 before implementation?
5. What signature/MAC model and key authority bind producers, workers, attestations, receipts, and retained evidence?
6. Which adapters are pure, idempotent, fenced, compensatable, or unsupported, and what sink proof query does each expose?
7. Which principals receive reconciliation and higher-authority ambiguity-risk capabilities, and what independent review is required?
8. Are lifecycle directories the primary transactional filesystem representation or a projection of another conforming authority?
9. What concrete retention durations, namespace-generation procedure, payload limits, and privacy classifications apply while preserving mandatory slot tombstones?
10. How are partitions sharded and rebalanced while preserving one active authority epoch and global token high-water lineage?
11. Should heartbeat detail remain as immutable files or reside transactionally with periodic signed summaries?
12. How will legacy UUID tasks be drained, imported, or isolated from Level 3 SHA-256 tasks?
13. Which transport later carries immutable objects and notifications? Tailscale/WireGuard, gateways, and other choices remain out of scope.

## 13. Implementation phases

### Phase 0: bind substrate parameters

Select a substrate that can satisfy the settled four-step protocol. Bind concrete lease/uncertainty values, resource-scope inventory, trust principals, adapter effect classes/query coordinates, retention durations, and canonical fixtures. The six audited semantic contracts MUST NOT be reopened as transport or substrate options.

### Phase 1: authority core and idempotency

Implement version 2 envelopes, authority-owned slot CAS, exact-retry return, typed conflict evidence, tombstones, claim reservation, monotonic lease state, durable queue/task high-water registers, and transactional outbox. Fault-inject every step-1/step-2 boundary. Run beside unchanged Level 2 with no shared task namespace.

### Phase 2: protected sinks and effect evidence

Implement resource-scoped sink fences, atomic sink register/write enforcement, `EFFECT_ATTEMPTED`, pre-receipt attestations, proof queries, reconciliation authorization, and step-3/step-4 transactions. Unsupported sinks fail closed. Prove stale-writer rejection and crash-after-effect classification.

### Phase 3: scheduler fairness and replicated transport

Implement exact PHI/Fibonacci contention response classification, reset/yield, oldest-first fairness queue, starvation events, and observability. Replicate immutable envelopes/results/attestations and notifications while retaining one authority. Test duplication, delay, reordering, corruption, and partitions.

### Phase 4: failover and authority epochs

Implement reviewed authority failover, monotonic-continuity proof or mandatory wait, durable high-water recovery, never-reused tokens, epoch change, old-authority exclusion, sink-register continuity, and disaster reconciliation. Verify on the exact storage topology.

### Phase 5: transport/gateway projection

Select and harden network transport and any gateway ingress. Demonstrate that routing, authentication, confidentiality, and replay handling satisfy this contract without becoming an accidental second authority.

### Phase 6: migration and operational acceptance

Drain or isolate Level 2 tasks, migrate only with explicit lineage receipts, exercise recovery/retention procedures, establish SLOs and alerts, and obtain independent review before multi-writer production use.

## 14. Verification matrix

| Area | Verification | Required result |
| --- | --- | --- |
| Canonicalization | Cross-language golden fixtures, Unicode, timestamps, key ordering, integer limits | Identical bytes and SHA-256 |
| Task identity | Same tuple, duplicate key, changed payload, changed origin, changed timestamp | Stable identity for exact retry; changed immutable input rejected |
| Envelope integrity | Bit flips, unknown major schema, endpoint/genesis mismatch, stale prompt/config binding | Fail closed before claim |
| Idempotency slot | Concurrent exact/conflicting submissions, archive, tombstone, namespace change | One executable task; exact retry returns receipt; typed conflict durable; tombstone rejects reuse |
| Claim reservation/CAS | Hundreds of simultaneous contenders and crashes between steps 1 and 2 | One reservation/winner per generation; deterministic resume/cancel |
| Monotonic lease | Reorder/delay heartbeats, UTC rollback, process restart, monotonic discontinuity | Only pre-cutoff renewal accepted; takeover after observed expiry plus margin; unsafe restart freezes |
| Queue/task fencing | Pause old worker, expire/take over, resume old worker, fail over epoch | Durable high-water never decreases/reuses; stale lifecycle write rejected |
| Sink fencing | Concurrent effects, stale token, register loss, unsupported sink | Write/register atomic; stale effect rejected; absent enforcement fails closed |
| Effect attestation | Crash before request, after effect, before attestation, and before terminal receipt | Proof query yields deterministic commit/reconciliation/ambiguity; no blind replay |
| Boot identity | Container restart and host reboot during claim | Old boot cannot renew or commit |
| Capability drift | Revoke `coordinate` after dispatch and after claim | Execution/commit blocked according to boundary policy |
| Four-step protocol | Fault inject before/after every transaction and cross-sink boundary in section 7.4 | Legal resume from last durable evidence; no duplicate task/effect/terminal receipt |
| Result preservation | Result durable before commit projection | Reconciled without rewriting bytes |
| Append concurrency | Concurrent duplicate projections | Transactional uniqueness or harmless duplicates plus deterministic repair |
| Partition | Isolate worker, authority, replica, sink, and old authority after failover | Minority cannot commit; ambiguity explicit where proof/fencing is absent |
| Backoff/fairness | Exercise every response class, attempts 0–11, yield, rotations, starvation | Exact increment/reset; delay at most 30s; oldest-first reconsideration and complete observability |
| Replication | Duplicate, reorder, corrupt, and delay immutable objects | Digest rejection and no lifecycle authority leakage |
| Retention | Compact heartbeats, archive slot, attempt key reuse, restore audit chain | Tombstone blocks reuse; digest-linked audit remains reconstructable |
| Security | Authentication, authorization, signature rotation/revocation, payload access | Unauthorized or unverifiable records fail closed without secret leakage |
| Migration | Legacy UUID task beside version 2 SHA-256 task | No namespace confusion; explicit lineage or isolation |
| Operational recovery | Loss and promotion of authority on exact substrate | Epoch/token continuity proven before resume |

## 15. Acceptance criteria for this specification

The Level 3 design is ready to implement only when:

- all normative invariants have an owning component and executable verification plan;
- one authority substrate and failure model are selected;
- every initial adapter has a declared replay/effect class;
- stale writers are rejectable at every consequential sink;
- authority time, failover epoch, token recovery, and partition behavior are specified;
- legacy coexistence is explicit;
- unresolved transport choices remain projections rather than hidden lifecycle dependencies; and
- independent reviewers can reconstruct each transition from immutable evidence without trusting worker-local state.

Until then, the current `consume_queue.py --once` path remains a bounded single-node contract and MUST NOT be described as a distributed queue merely because its files are copied, mounted, or routed across hosts.
