# Level 3 Snapshot Rehydration Protocol

Status: **Draft for independent review**

Protocol version: **0.1.0-draft**

Documentary baseline: Recursive Field commit `5a8c9d92ff6d6f705390b834d0c6f7bc6a2815ff`

Governing specifications:

- [Level 3 Distributed Task Queue Specification](LEVEL_3_DISTRIBUTED_QUEUE_SPEC.md)
- [Level 3 Network Overlay Specification](LEVEL_3_NETWORK_OVERLAY_SPEC.md)

Documentary ancestry:

- [Multi-Node Orchestration Guide](../MULTI_NODE_ORCHESTRATION.md)
- [Multi-Node Deployment Configuration Matrix](../DEPLOYMENT_MATRIX.md)
- [Recursive Field Architecture Specification](../RECURSIVE_FIELD_SPEC.md)

## 1. Protocol frame

### 1.1 Scope and decision served

This protocol defines the evidence, state transitions, authority boundaries, verification gates, failure classifications, and activation proof required to rehydrate a Level 3 logical role from a snapshot or equivalent immutable image plus durable state. It governs the interval from a declared restoration candidate through role activation. It does not restore, enroll, route, activate, or attest any live node.

The decision served is whether a candidate may acquire one specific logical role without inheriting stale identity, duplicating authority, replaying uncertain effects, weakening network isolation, or converting documentary ancestry into current operational truth.

The protocol applies to exactly these origin coordinates:

| Logical coordinate | Role boundary |
| --- | --- |
| `compute-coordinator-00` | CAS lease and fencing-token authority |
| `mesh-relay-00` | Private transport relay and signal mesh |
| `state-vault-00` | Durable ledger and effect-attestation anchor |
| `cleanroom-executor-00` | Public ingress, TLS termination, and isolated verifier |
| `compute-worker-00` | Origin unit-cell container host |

These coordinates are declarations at this documentary boundary. Nothing in this protocol asserts that a corresponding snapshot, provider instance, volume, overlay identity, key, boot, route, or active role currently exists.

### 1.2 Vantage, topology, and stopping boundary

The vantage is a formation-authorized independent verifier examining an isolated candidate and content-addressed evidence. The topology is a bounded cross-plane inquiry spanning snapshot provenance, formation identity, durable state, queue authority, protected sinks, network identity, and activation governance. The unit of decision is one candidate-to-coordinate binding in one formation generation and role epoch.

The inquiry admits the two governing Level 3 specifications and focused documentary ancestry concerning formation roots, durable ledgers, resolver identity, volume-backed recovery, and graph verification. It excludes live provider inspection, live network inspection, actuation, key generation, snapshot creation, volume attachment, route changes, firewall changes, DNS publication, queue mutation, and role activation.

The protocol stops when every required gate has one receipt-backed outcome; all conflicts have been retained and classified; an authoritative acceptor has either issued a signed activation decision, issued a rollback or revocation decision, or kept the candidate quarantined; and unresolved substrate choices are parked without weakening the semantic contract.

### 1.3 Evidence classes and epistemic discipline

The following classes MUST remain distinct:

- **Documentary evidence**: declarations or prior procedures found in the cited repository documents.
- **Proposed normative contract**: requirements in this draft expressed by **MUST**, **MUST NOT**, **SHOULD**, and **MAY**.
- **Candidate evidence**: records supplied by the snapshot, durable volume, provider-neutral instance identity, protected sink, or recovery process.
- **Observed evidence**: bounded observations made by an identified verifier at a recorded time.
- **Verified evidence**: observations whose digests, signatures, lineage, scope, and acceptance rules have passed a named gate.
- **Attested evidence**: verified evidence signed by an independent verifier and bound to the candidate, coordinate, formation, epochs, and protocol baseline.
- **Authority decision**: a CAS-controlled admission, activation, rollback, or revocation decision made by the authorized acceptor.
- **Simulation**: a model, static validation, or isolated exercise; it does not prove live operational state.

A content hash proves integrity only for the declared representation and canonicalization. It does not prove source authority, semantic fitness, present validity, role exclusivity, safe replay, or authorization to activate.

### 1.4 Normative language and versioning

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are normative. An implementation MUST reject an unsupported protocol or evidence-schema major version before authority-bearing action.

A major version changes accepted identity, lifecycle, authority, or evidence meaning. A minor version may add optional evidence that does not weaken existing gates. A patch version may clarify validation without changing accepted meaning. Published schemas and accepted receipts MUST be immutable and content-addressed. Migration creates a successor record with explicit predecessor lineage; it never rewrites accepted evidence.

### 1.5 Authority boundaries

Authority is deliberately separated:

- The **candidate** may expose isolated bytes and propose evidence; it cannot self-verify or self-activate.
- A **responsible producer** creates gate-specific evidence from an authorized source.
- An **independent verifier** validates evidence and signs a gate receipt; it cannot silently grant queue or role authority.
- The **identity-binding authority** accepts or rejects unique cross-namespace coordinate bindings.
- `compute-coordinator-00` is the only role permitted to hold queue-CAS, lease-fencing, and terminal-lifecycle capabilities after activation.
- `state-vault-00` records authenticated evidence and serves proof queries; it MUST NOT perform queue CAS, issue leases, advance lifecycle truth, or make terminal decisions.
- `mesh-relay-00` transports already-authorized traffic; reachability through it grants no transitive trust.
- `cleanroom-executor-00` may terminate public ingress only after attestation and activation; it cannot convert public identity claims into queue authority.
- `compute-worker-00` may execute only under current queue, fence, boot, capability, and workload bindings.
- The **authoritative acceptor** performs CAS-controlled admission and activation decisions. It MUST be separate from the candidate and MUST be cryptographically distinct from the independent verifier for every consequential gate and activation decision: `verifier_id != acceptor_id`.

Every transition that changes identity, authority, route eligibility, role epoch, authority epoch, or active status MUST be represented by an immutable receipt and committed through the applicable compare-and-swap authority. The verifier and acceptor MUST each sign the same canonical receipt or decision payload with separate keys. Each signature MUST bind the signer's identity, authorized role, payload digest, and predecessor-lineage digest. JSON Schema cannot enforce cross-field identity inequality or cryptographic binding; the semantic validator and CAS acceptor MUST reject equal verifier/acceptor identities, missing or shared signatures, role mismatch, payload-digest mismatch, or predecessor-lineage mismatch before accepting a consequential receipt.

### 1.6 Assumptions, exclusions, and threat model

Assumptions:

- Accepted evidence can be canonically serialized, hashed, signed, retained, and independently verified.
- The formation has an authorized identity-binding and activation-decision path.
- Consequential sinks can expose durable fence/register evidence or fail closed.
- The isolated environment can prevent production routes and effects during verification.

Exclusions:

- Selection of a cloud provider, snapshot product, overlay product, queue database, ledger database, signature algorithm, certificate authority, firewall implementation, or storage technology.
- Real addresses, provider resource identifiers, credentials, private keys, secrets, commands, and live configuration.
- A claim of exactly-once external effects, current node health, current snapshot validity, or current infrastructure readiness.

Threats in scope include tampered or substituted snapshots, forged provenance, stale clones, zombie instances, duplicate coordinate bindings, inherited machine or overlay keys, compromised signing keys, stale leases, fencing-token reuse, authority partition, ledger truncation, contradictory receipts, volume substitution, queue receipt gaps, blind effect replay, wildcard ACLs, relay privilege expansion, public exposure of private roles, rollback to revoked identity, and repeated rehydration that accidentally revives superseded authority.

## 2. Identity transmutation and legacy disposition

### 2.1 Logical genesis is not a provider rename

The `-00` suffix denotes the logical genesis coordinate of a role family. It is stable across provider resources, snapshots, boots, overlay keys, addresses, and deployment generations. It is not an automatic rename of any provider instance, snapshot label, hostname, or historical machine.

Legacy or provider labels ending in `-01` are documentary provenance only. They MAY identify source lineage or migration evidence, but they confer no `-00` identity, active binding, authority epoch, key continuity, lease ownership, route eligibility, or capability. Any ambiguity between a historical label and a target logical coordinate MUST fail closed and keep the candidate quarantined.

### 2.2 Required evidence dispositions

Inherited evidence MUST receive exactly one explicit disposition:

| Disposition | Required treatment |
| --- | --- |
| **Preserve** | Retain snapshot manifests, content digests, creation records, chain-of-custody, immutable ledgers, receipts, effect attestations, contradictions, and prior activation/revocation records as provenance. Preservation does not grant current authority. |
| **Adapt** | Reuse portable configuration only after schema validation, current-policy validation, secret removal, coordinate rebinding, capability minimization, and configuration-digest issuance. |
| **Supersede** | Replace provider identity, overlay machine identity, boot identity, machine-derived credentials, host keys where required, certificates, sessions, and authority epochs with fresh, explicitly bound identities. |
| **Retire** | Revoke stale credentials, sessions, leases, renewals, role bindings, routes, certificates, and provider-neutral enrollment rights; retain revocation evidence. |
| **Build new** | Create signed coordinate bindings, current capability grants, current policy digests, fresh key references, gate receipts, activation evidence, rollback anchors, and revocation lineage. |

A byte-identical snapshot MUST NOT be treated as active merely because its former hostname, path, provider label, or content hash appears correct. Identity is reconstructed through signed cross-namespace bindings and accepted evidence, not inferred from resemblance.

### 2.3 Constraint shadow

Legacy recovery documents describe durable volumes, path-independent formation roots, resolver restoration, append-only ledgers, and graph verification. Those are useful ancestry but are insufficient for Level 3 activation. They do not independently establish queue CAS, fencing continuity, duplicate-coordinate exclusion, fresh overlay identity, public-exposure policy, or an authority-bearing activation receipt. Any earlier direct path from attachment or graph verification to activation is superseded by this protocol.

## 3. Normative evidence model

### 3.1 Common receipt requirements

Every gate, transition, reconciliation, admission, activation, rollback, and revocation receipt MUST bind:

- schema name, schema version, protocol version, and canonicalization profile;
- receipt identifier and immutable predecessor digest where applicable;
- formation identity, formation generation, and genesis identity digest;
- exact logical coordinate and role;
- candidate identity digest, snapshot provenance digest, provider-neutral resource identity digest, overlay identity digest, and boot identity digest where known;
- role epoch and authority epoch where applicable;
- gate or transition name, prior state, next state, decision, and reason codes;
- input evidence digests, output evidence digests, policy/specification digest, and repository baseline;
- producer identity, `verifier_id`, verifier role, `acceptor_id`, acceptor role, separately keyed verifier and acceptor signature references, and observation/decision times;
- expiry, revocation status, retention class, rollback anchor, canonical payload digest, and receipt digest.

For every consequential gate and activation decision, `verifier_id != acceptor_id` is a mandatory semantic invariant. Each separate signature MUST bind the signer identity and authorized role, the same canonical payload digest, and the immutable predecessor-lineage digest. Schema validation is necessary but insufficient: the semantic validator and CAS acceptor MUST verify identity inequality, signer authorization, signature separation, digest equality, and predecessor binding.

Unknown values MUST be explicit. Missing authority-critical evidence MUST NOT be represented as success. Receipts MUST be immutable; corrections create linked successor or reconciliation receipts.

### 3.2 Normative gate-receipt schema

The following schema is normative at the semantic level. Concrete canonical-JSON and signature profiles remain a deployment decision, but implementations MUST preserve every required field and constraint.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:recursive-field:schema:snapshot-rehydration-gate-receipt:1.0.0",
  "title": "Recursive Field Snapshot Rehydration Gate Receipt",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_name",
    "schema_version",
    "protocol_version",
    "canonicalization_profile",
    "receipt_id",
    "predecessor_receipt_sha256",
    "formation_id",
    "formation_generation",
    "genesis_identity_sha256",
    "logical_coordinate",
    "role",
    "candidate_identity_sha256",
    "snapshot_provenance_sha256",
    "provider_resource_identity_sha256",
    "overlay_identity_sha256",
    "boot_identity_sha256",
    "role_epoch",
    "authority_epoch",
    "gate_number",
    "gate_name",
    "prior_state",
    "next_state",
    "decision",
    "reason_codes",
    "input_evidence_sha256",
    "output_evidence_sha256",
    "policy_sha256",
    "repository_baseline",
    "producer",
    "verifier_id",
    "verifier_role",
    "acceptor_id",
    "acceptor_role",
    "verifier_signature_ref",
    "acceptor_signature_ref",
    "rollback_anchor_sha256",
    "observed_at",
    "expires_at",
    "revocation_status",
    "retention_class",
    "receipt_payload_sha256",
    "receipt_sha256"
  ],
  "properties": {
    "schema_name": {"const": "recursive-field.snapshot-rehydration-gate-receipt"},
    "schema_version": {"const": "1.0.0"},
    "protocol_version": {"type": "string"},
    "canonicalization_profile": {"type": "string", "minLength": 1},
    "receipt_id": {"type": "string", "minLength": 1},
    "predecessor_receipt_sha256": {"type": ["string", "null"], "pattern": "^[0-9a-f]{64}$"},
    "formation_id": {"type": "string", "minLength": 1},
    "formation_generation": {"type": "integer", "minimum": 0},
    "genesis_identity_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
    "logical_coordinate": {
      "enum": [
        "compute-coordinator-00",
        "mesh-relay-00",
        "state-vault-00",
        "cleanroom-executor-00",
        "compute-worker-00"
      ]
    },
    "role": {"type": "string", "minLength": 1},
    "candidate_identity_sha256": {"type": ["string", "null"], "pattern": "^[0-9a-f]{64}$"},
    "snapshot_provenance_sha256": {"type": ["string", "null"], "pattern": "^[0-9a-f]{64}$"},
    "provider_resource_identity_sha256": {"type": ["string", "null"], "pattern": "^[0-9a-f]{64}$"},
    "overlay_identity_sha256": {"type": ["string", "null"], "pattern": "^[0-9a-f]{64}$"},
    "boot_identity_sha256": {"type": ["string", "null"], "pattern": "^[0-9a-f]{64}$"},
    "role_epoch": {"type": ["integer", "null"], "minimum": 0},
    "authority_epoch": {"type": ["integer", "null"], "minimum": 0},
    "gate_number": {"type": "integer", "minimum": 1, "maximum": 10},
    "gate_name": {"type": "string", "minLength": 1},
    "prior_state": {"enum": ["declared", "isolated_rehydration", "verified", "attested", "admitted_to_overlay", "role_activated", "quarantined", "revoked"]},
    "next_state": {"enum": ["declared", "isolated_rehydration", "verified", "attested", "admitted_to_overlay", "role_activated", "quarantined", "revoked"]},
    "decision": {"enum": ["accepted", "rejected", "quarantined", "rollback-required", "revoked"]},
    "reason_codes": {"type": "array", "items": {"type": "string"}, "uniqueItems": true},
    "input_evidence_sha256": {"type": "array", "minItems": 1, "items": {"type": "string", "pattern": "^[0-9a-f]{64}$"}, "uniqueItems": true},
    "output_evidence_sha256": {"type": "array", "minItems": 1, "items": {"type": "string", "pattern": "^[0-9a-f]{64}$"}, "uniqueItems": true},
    "policy_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
    "repository_baseline": {"const": "5a8c9d92ff6d6f705390b834d0c6f7bc6a2815ff"},
    "producer": {"type": "string", "minLength": 1},
    "verifier_id": {"type": "string", "minLength": 1},
    "verifier_role": {"type": "string", "minLength": 1},
    "acceptor_id": {"type": "string", "minLength": 1},
    "acceptor_role": {"type": "string", "minLength": 1},
    "verifier_signature_ref": {"type": "string", "minLength": 1},
    "acceptor_signature_ref": {"type": "string", "minLength": 1},
    "rollback_anchor_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
    "observed_at": {"type": "string", "format": "date-time"},
    "expires_at": {"type": ["string", "null"], "format": "date-time"},
    "revocation_status": {"enum": ["not-revoked", "revoked", "unknown"]},
    "retention_class": {"type": "string", "minLength": 1},
    "receipt_payload_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
    "receipt_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}
  }
}
```

### 3.3 Normative coordinate-binding content

A coordinate binding MUST cover the candidate-to-coordinate relationship across formation, role, provider-neutral resource, snapshot provenance, volume, overlay, boot, queue, and capability namespaces. It MUST include predecessor and revocation lineage, prevent simultaneous active bindings, and fail closed when a historical label cannot be unambiguously separated from the target coordinate.

A queue-participating binding MUST bind `authority_id`, `partition_id`, the exact owner tuple `{DROPLET_ID}:{CONTAINER_SLUG}:{boot_id}`, authority epoch, queue capabilities, ledger capabilities, and accepted authorization-policy digest. Only `compute-coordinator-00` may receive queue-CAS, lease-fencing, or terminal-lifecycle capabilities. A binding for `state-vault-00` MUST explicitly deny those capabilities.

### 3.4 Non-authoritative gate-receipt example

```json
{
  "schema_name": "recursive-field.snapshot-rehydration-gate-receipt",
  "schema_version": "1.0.0",
  "protocol_version": "0.1.0-draft",
  "canonicalization_profile": "canonical-json-profile-to-be-selected",
  "receipt_id": "gate-receipt-example-0001",
  "predecessor_receipt_sha256": null,
  "formation_id": "example-formation",
  "formation_generation": 12,
  "genesis_identity_sha256": "1111111111111111111111111111111111111111111111111111111111111111",
  "logical_coordinate": "compute-worker-00",
  "role": "origin_unit_cell_container_host",
  "candidate_identity_sha256": "7777777777777777777777777777777777777777777777777777777777777777",
  "snapshot_provenance_sha256": "8888888888888888888888888888888888888888888888888888888888888888",
  "provider_resource_identity_sha256": "9999999999999999999999999999999999999999999999999999999999999999",
  "overlay_identity_sha256": null,
  "boot_identity_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "role_epoch": 3,
  "authority_epoch": null,
  "gate_number": 4,
  "gate_name": "genesis-formation-identity-verification",
  "prior_state": "isolated_rehydration",
  "next_state": "isolated_rehydration",
  "decision": "accepted",
  "reason_codes": ["root-marker-verified", "genesis-lineage-verified"],
  "input_evidence_sha256": ["2222222222222222222222222222222222222222222222222222222222222222"],
  "output_evidence_sha256": ["3333333333333333333333333333333333333333333333333333333333333333"],
  "policy_sha256": "4444444444444444444444444444444444444444444444444444444444444444",
  "repository_baseline": "5a8c9d92ff6d6f705390b834d0c6f7bc6a2815ff",
  "producer": "formation-identity-evidence-producer",
  "verifier_id": "independent-rehydration-verifier",
  "verifier_role": "formation-identity-verifier",
  "acceptor_id": "formation-activation-authority",
  "acceptor_role": "gate-receipt-acceptor",
  "verifier_signature_ref": "detached-signature:verifier-example",
  "acceptor_signature_ref": "detached-signature:acceptor-example",
  "rollback_anchor_sha256": "5555555555555555555555555555555555555555555555555555555555555555",
  "observed_at": "2030-07-10T00:00:00Z",
  "expires_at": "2030-07-10T01:00:00Z",
  "revocation_status": "not-revoked",
  "retention_class": "rehydration-audit",
  "receipt_payload_sha256": "abababababababababababababababababababababababababababababababab",
  "receipt_sha256": "6666666666666666666666666666666666666666666666666666666666666666"
}
```

This example is illustrative only. It neither verifies nor activates a node.

## 4. Normative lifecycle

The exact machine-state success sequence is:

`declared → isolated_rehydration → verified → attested → admitted_to_overlay → role_activated`

Readable labels such as “isolated rehydration,” “admitted to overlay,” and “role activated” are prose only. Every `prior_state` and `next_state` value MUST be exactly one of `declared`, `isolated_rehydration`, `verified`, `attested`, `admitted_to_overlay`, `role_activated`, `quarantined`, or `revoked`. No success state may be skipped or inferred from a later observation.

### 4.1 State meanings

| Machine state | Readable label | Meaning and permitted activity | Prohibited activity |
| --- | --- | --- | --- |
| `declared` | Declared | Topology intent names one candidate role; create only a bounded recovery case and evidence namespace. | Boot-derived authority, production routing, effects, public exposure. |
| `isolated_rehydration` | Isolated rehydration | Inspect candidate bytes and state behind default deny; prepare fresh identity and non-actuating evidence. | Production membership, queue authority, leases, sink effects, public listeners. |
| `verified` | Verified | Ten gates and role deltas have accepted receipts; assemble the attestation bundle. | Overlay admission, role authority, production effects. |
| `attested` | Attested | An independent verifier signed the complete evidence bundle; submit admission CAS. | Production routes or role execution. |
| `admitted_to_overlay` | Admitted to overlay | Unique binding and admission CAS succeeded; enable only bounded private paths for final checks. | Role authority or public exposure. |
| `role_activated` | Role activated | The acceptor issued a signed activation receipt. | Any capability or route outside the signed sets and policy. |
| `quarantined` | Quarantined | Evidence is incomplete, contradictory, ambiguous, compromised, or rollback isolation is unproved. | Activation, blind replay, production routing. |
| `revoked` | Revoked | The binding, key, role epoch, or activation decision is invalidated. | Actuation, enrollment reuse, route or capability restoration. |

`failed` and `rollback` are decision/action classifications, not lifecycle states.

### 4.2 Legal transitions and rollback actions

The semantic validator and CAS acceptor MUST validate the ordered pair `(prior_state, next_state)` against this registry; enum membership alone is insufficient.

| Legal transition | Guard and evidence | Authority action |
| --- | --- | --- |
| `declared → isolated_rehydration` | Unique recovery case, verified isolation, declaration receipt, inventory digest, policy digest. | Create the candidate attempt and evidence namespace. |
| `isolated_rehydration → isolated_rehydration` | A gate receipt records evidence without advancing lifecycle state. | Accept only the gate evidence; grant no new authority, route, or capability. |
| `isolated_rehydration → verified` | Exactly one accepted receipt for each canonical Gate 1–10, role deltas, no unresolved authority-critical ambiguity. | Fix the verified bundle digest. |
| `verified → attested` | Authorized independent verifier, complete signatures, freshness and revocation checks. | Accept attestation digest without granting routes or authority. |
| `attested → admitted_to_overlay` | Unique binding, fresh overlay identity, policy compilation, stale-instance exclusion. | Commit one binding and admission epoch. |
| `admitted_to_overlay → role_activated` | Final reachability and role invariants; complete Gate 10 activation bundle. | Issue signed activation decision and exact grant/deny sets. |
| `verified → isolated_rehydration` | Signed rollback action identifies failed verification lineage and repair evidence. | Remove eligibility and open a linked repair attempt. |
| `verified → quarantined` | Contradictory, expired, or unrepairable evidence. | Remove eligibility and preserve evidence. |
| `verified → revoked` | Compromise or invalid binding. | Revoke identities/capabilities and advance affected epochs. |
| `attested → isolated_rehydration` | Signed rollback invalidates attestation before admission. | Withdraw attestation eligibility and restore isolation. |
| `attested → quarantined` or `attested → revoked` | Ambiguity or compromise. | Remove eligibility; revoke when required. |
| `admitted_to_overlay → isolated_rehydration` | Signed rollback proves all partial/full routes, capabilities, leases, and exposure removed. | Withdraw admission, restore default deny, advance attempt lineage. |
| `admitted_to_overlay → quarantined` or `admitted_to_overlay → revoked` | Partial admission cannot be proved removed, or identity/key is compromised. | Fail closed; remove routes and capabilities; retain evidence. |
| `role_activated → quarantined` | Drift or uncertainty requires immediate containment. | Remove routes/capabilities and preserve active receipt lineage. |
| `role_activated → revoked` | Compromise, duplicate binding, or authorized revocation. | Revoke binding/capabilities and advance affected epochs. |
| Any non-revoked state `→ quarantined` | Missing, contradictory, expired, compromised, or ambiguous evidence. | Remove admission/activation eligibility. |

A rollback MUST be a signed action, never a state. It MUST name the prior receipt, reason codes, evidence, target (`isolated_rehydration`, `quarantined`, or `revoked`), capability and route removals, predecessor lineage, and resulting-state proof. Rollback from `admitted_to_overlay` MUST prove removal of partial overlay admission; otherwise the only valid target is `quarantined` or `revoked`. A `role_activated` candidate cannot roll directly back into an activation-eligible state: containment is `quarantined`, and re-entry requires a fresh successor attempt through the full sequence.

### 4.3 Prohibited transitions and shortcuts

Every pair not listed above is illegal. In particular, success-state skips, `quarantined → admitted_to_overlay`, `quarantined → role_activated`, any transition out of `revoked` into actuation, or a rollback target outside the authorized enum MUST be rejected. Activation based solely on matching bytes, hostname, provider label, path, boot, handshake, graph integrity, reachability, or a prior receipt is forbidden. Queue replay, lease renewal, authority assumption, sink writes, and public exposure before the applicable accepted state and evidence are forbidden.

## 5. Ten verification gates

Each gate applies universally unless a role delta adds stricter evidence. A role delta MUST NOT waive or weaken a universal requirement. Every gate outcome MUST have an immutable receipt, an independent verifier, an authoritative acceptor, and a rollback anchor. Gate receipt acceptance MUST semantically validate the gate index/name pair against the canonical Gate 1–10 headings below. For every consequential receipt, the verifier and acceptor MUST be distinct and must provide separate role-authorized signatures over the same receipt payload digest and predecessor lineage.

### Gate 1 — Snapshot Provenance & Integrity Proof

**Purpose.** Establish what representation was supplied and how it reached the isolated candidate without mistaking integrity for authority.

**Required inputs.** Cryptographic content and manifest hashes; signature chain; source snapshot or image provenance; creation epoch; source coordinate as a provenance claim; formation and repository baseline claims; chain-of-custody events; canonicalization profile; predecessor/successor references; and any conflict or tamper evidence.

**Guards.** Every referenced object MUST be content-addressed. Signatures MUST be verified against an accepted trust root and validity interval. Creation epoch and source lineage MUST be internally consistent. Hash mismatch, signature failure, unexplained custody gap, conflicting manifests, or unknown provenance MUST fail closed.

**Output evidence.** A provenance receipt that identifies exact bytes, accepted and rejected lineage claims, integrity status, conflicts, and retention class. The receipt MUST state that representation integrity does not establish current authority, semantic fitness, identity, freshness, or activation eligibility.

**Rollback.** Return to the declaration anchor, preserve the supplied objects and conflicts, and prevent reuse of the failed provenance digest as accepted input.

### Gate 2 — Logical `-00` Coordinate Binding

**Purpose.** Bind one isolated candidate to one logical coordinate across all relevant namespaces without inheriting identity from a historical label.

**Required inputs.** Signed cross-namespace binding proposal covering logical coordinate, role, genesis and formation identities, formation generation, candidate and provider-neutral resource identity, snapshot provenance, durable-volume identity, overlay identity, boot identity, role epoch, authority epoch, configuration digest, policy digest, queue `authority_id`, partition, exact owner tuple, queue and ledger capability scopes, validity, predecessor, and revocation lineage.

**Guards.** The identity-binding authority MUST prove that no other current provider instance, overlay identity, boot identity, policy bundle, or unrevoked binding is active for the coordinate. Historical label ambiguity MUST fail closed. A provider name, hostname, address, path, or snapshot name MUST NOT satisfy the binding. Capability scope MUST match the role boundary.

**Output evidence.** A signed candidate binding receipt marked non-active until admission, plus duplicate-coordinate and predecessor-disposition proofs.

**Rollback.** Revoke the candidate binding proposal, preserve its receipt, and return the candidate to isolation. No previously revoked binding may be revived.

### Gate 3 — Provider-Instance & Overlay-Key Replacement

**Purpose.** Prevent cloned machine, overlay, transport, host, session, or certificate identity from surviving snapshot restoration.

**Required inputs.** Inventory of inherited WireGuard/Tailscale-equivalent machine identity, SSH host identity where role policy requires replacement, cloud-init or bootstrap identity, machine ID, boot-derived credentials, tokens, sessions, certificates, workload credentials, and evidence-signing keys; retirement and revocation records; fresh public identity references created in isolation.

**Guards.** Inherited private overlay identity MUST be absent, cryptographically unusable, or explicitly revoked before overlay admission. Machine and boot-derived credentials MUST be superseded. Credentials and certificates MUST have separate identifiers and revocation scopes. A bounded rotation overlap MUST NOT permit two independent active candidates for one coordinate.

**Output evidence.** A key-and-instance replacement receipt binding retired identifiers, fresh public identity digests, revocation status, exposure window, and re-enrollment eligibility. The protocol records evidence only and does not prescribe live commands.

**Rollback.** Revoke fresh enrollment material, preserve replacement evidence, and return the candidate to `isolated_rehydration`. Compromise triggers quarantine and affected epoch advancement.

### Gate 4 — Genesis/Formation Identity Verification

**Purpose.** Prove that the candidate belongs to the intended formation without inferring identity from a path or hostname.

**Required inputs.** `.recursive-field-root` or accepted root marker evidence; genesis UUID and root signatures; repository and governing-specification baseline; identity manifests; formation generation; ledger lineage; configuration authority; resolver correspondence; mounted formation content manifest; and expected immutable/mutable boundary declarations.

**Guards.** Root-marker discovery, canonical root resolution, genesis lineage, signed manifests, and mounted content MUST agree within their declared namespaces. Path equality, hostname equality, or familiar directory layout is insufficient. Ledger and identity contradictions MUST be retained and classified.

**Output evidence.** A formation-identity receipt binding root marker, genesis, formation generation, repository/spec baseline, ledger lineage, configuration authority, and mounted-content digest.

**Rollback.** Detach the candidate from the proposed formation binding, preserve manifests and conflicts, and return to isolation or quarantine.

### Gate 5 — Boot Identity & Stale-Instance Exclusion

**Purpose.** Establish a fresh boot incarnation and prove that predecessors, stale clones, and zombie instances cannot act under the target coordinate.

**Required inputs.** Fresh boot identity; provider-neutral instance identity; current candidate binding; predecessor instance, boot, key, route, lease, session, and certificate inventory; duplicate-coordinate search evidence; revocation records; role epoch and authority epoch transition evidence.

**Guards.** The boot identity MUST be fresh and bound to the current candidate. Container restart identity MUST NOT substitute for host boot identity. Old instances and keys MUST be unable to renew leases, advance registers, reach protected sinks, or authenticate to role services. Authority-bearing recovery MUST advance the applicable epoch and invalidate prior renewals.

**Output evidence.** A stale-instance exclusion receipt, duplicate-coordinate result, fresh boot binding, predecessor isolation proof, and affected epoch-advance receipt.

**Rollback.** Revoke the candidate boot binding and keep all contenders isolated. If exclusivity cannot be proved, remain quarantined.

### Gate 6 — Durable Volume & Ledger Reconstruction

**Purpose.** Prove that the attached durable state belongs to the intended formation and reconstruct accepted evidence without silently repairing gaps.

**Required inputs.** Volume identity and provenance; mount-coordinate and read/write-intent evidence; filesystem/content manifest; immutable identity and configuration manifests; ledger head; sequence and hash-chain proofs; accepted transition and terminal receipts; snapshots; protected-sink register evidence; and state-pointer reconstruction inputs.

**Guards.** Volume identity, formation identity, mount correspondence, and intended access mode MUST agree. Ledger hashes and sequences MUST be checked from a trusted anchor. Lifecycle state MUST be rebuilt from accepted receipts, not worker caches, cursors, path placement, or a later snapshot alone. Gaps, truncations, duplicate sequence claims, and contradictions MUST be retained and classified; they MUST NOT be silently healed or deleted.

**Output evidence.** A volume-consistency receipt, content-manifest digest, reconstructed ledger head, accepted-receipt index, state-pointer reconstruction digest, and explicit gap/conflict register.

**Rollback.** Return the volume to the prior verified access state, preserve all observed bytes and contradiction evidence, and quarantine the candidate on mismatch.

### Gate 7 — Queue Receipt-Gap Classification & Reconciliation

**Purpose.** Apply the queue specification's crash boundaries and prevent blind replay when effects or receipts are uncertain.

**Required inputs.** Idempotency slots and tombstones; envelopes; task state; claim generations; lease tokens; sink fences; `EFFECT_ATTEMPTED` records; effect attestations; result proposals; terminal and reconciliation receipts; protected-sink proof/query coordinates; projections; caches; and queue high-water evidence.

**Classification.** Every gap MUST be classified as one of: `pending`, `claimed`, `effect-attempted`, `ambiguous`, `reconciliation-required`, `terminal`, or `projection-gap`.

**Guards.** Classification MUST inherit the governing queue crash boundaries:

- before slot/task CAS: no executable task exists;
- accepted task before claim: resume scheduling from accepted `pending` evidence;
- claim/fence reservation before worker start: wait for authority-monotonic eligibility before reclaim;
- effect attempted before response: query the bound sink proof coordinate before replay;
- sink acceptance before attestation: reconstruct from sink proof or classify ambiguity;
- attestation before terminal CAS: commit only under current claim and fences without repeating the effect;
- terminal CAS before projection: repair projection from the terminal receipt and never rerun the adapter;
- cache or cursor loss: rebuild from authoritative lifecycle evidence.

Reconciliation MUST be independently authorized and receipt-bearing. It MUST check sink evidence, idempotency-slot bindings, current claims, fresh fences, adapter replay policy, and protected-resource registers. Verified accepted effects reconcile to terminal evidence without replay. Unknown or contradictory effects remain ambiguous. Blind replay is prohibited.

**Output evidence.** A complete receipt-gap register, one classification per task/effect boundary, sink-query receipts, reconciliation authorizations and receipts, and a no-blind-replay attestation.

**Rollback.** Freeze affected tasks and effects, revoke replay eligibility, and return them to quarantine or the last accepted terminal state without deleting contradictory evidence.

### Gate 8 — High-Water Register Restoration & Fencing-Epoch Advancement

**Purpose.** Restore one monotonic authority and token lineage across queue/task and protected-sink scopes before admission.

**Required inputs.** Queue-partition, task-lifecycle, and protected-resource high-water registers; accepted claim and sink-fence receipts; authority lineage; role and authority epochs; current protected-sink register proofs; prior-renewal invalidation; and stale-authority exclusion evidence.

**Guards.** The evidence set MUST prove one exclusive queue authority and one strictly increasing token sequence. Every new lease token and sink fence MUST be greater than all accepted predecessor values and MUST NOT be reset or reused across epochs. Protected-sink registers remain sink-owned authoritative state; vault copies are evidence to reconcile, not permission to overwrite sink truth. If monotonic continuity is unavailable, a rehydrating coordinator MUST complete the configured maximum remaining lease plus uncertainty recovery wait or present stronger substrate proof that every predecessor lease is fenced. Rehydration of `compute-coordinator-00`, or any recovery in which authority continuity or exclusivity is uncertain, MUST advance the authority epoch before overlay admission. Every other role MUST prove that it holds no queue-CAS, lease-fencing, token-allocation, or terminal-lifecycle capability and MUST bind its evidence to the accepted current coordinator authority epoch. Incomplete evidence, authority partition, or register contradiction freezes actuation.

**Output evidence.** A high-water restoration manifest, sink-by-sink reconciliation result, authority-epoch advancement receipt, prior-renewal invalidation receipt, exclusive-authority proof, and first-new-token lower bound.

**Rollback.** Freeze claims, renewals, takeovers, CAS, and consequential writes; revoke the candidate authority binding; retain all register evidence; remain quarantined until continuity and exclusivity are proven.

### Gate 9 — Network ACL & Public-Exposure Verification

**Purpose.** Preserve isolation and default-deny behavior until identity, policy, and role evidence justify bounded overlay admission.

**Required inputs.** Signed coordinate binding; overlay public identity; role and policy epochs; explicit source/destination/plane/service-class policy; ACL compiler output; listener and route intent; key rotation and revocation set; negative-reachability plan; public-ingress policy; and rollback bundle.

**Guards.** Isolation and default drop MUST precede overlay admission. ACL compilation MUST fail on unbound identities, unresolved privileged endpoints, permissive wildcards, address collisions, legacy-label authority, or transitive forwarding. Private directional flows MUST bind exact coordinates, capabilities, and service classes. Relay reachability MUST NOT create transitive trust. Negative reachability MUST cover every prohibited tuple.

Only `cleanroom-executor-00` may expose public TCP `80` and `443`, and only after attestation, overlay admission, and role activation. `compute-coordinator-00`, `mesh-relay-00`, `state-vault-00`, and `compute-worker-00` MUST drop unsolicited public ingress at every applicable layer. Public TCP `80` is limited to approved redirect or certificate-validation behavior; private internal HTTP does not become a public listener.

**Output evidence.** ACL compilation receipt, default-deny proof, key-generation and revocation digest, positive/negative test plan, public-exposure decision, and policy rollback anchor.

**Rollback.** Restore the previous safe policy without restoring revoked identities. If safe restoration would reopen compromise, isolate the candidate.

### Gate 10 — Signed Activation Attestation & Rollback Evidence

**Purpose.** Bind all accepted gate evidence into one immutable activation decision while preserving verifier/authority separation and deterministic rollback.

**Required inputs.** All gate receipts and digests; exact logical coordinate and role; formation/genesis identity; provider-neutral resource, overlay, boot, volume, and workload identities; role, authority, policy, and key epochs; repository and specification baseline; verifier identity and scope; expiry and revocation status; reachability and role-invariant receipts; rollback anchor; and candidate attempt lineage.

**Guards.** The activation bundle MUST contain exactly one accepted receipt for each canonical gate index `01` through `10`. Each map entry MUST bind its index, canonical registry name, receipt digest, and `accepted` decision; missing, extra, rejected, duplicated-semantic, or index/name-mismatched gates invalidate activation. The independent verifier and authoritative acceptor MUST be distinct, separately authorized signers. Their signatures MUST separately bind signer identity and role, the same decision payload digest, and predecessor lineage; the semantic validator and CAS acceptor MUST enforce `verifier_id != acceptor_id`. For `decision: "activate"`, immutable canonical `granted_capabilities` and `denied_capabilities` arrays are mandatory, unique within each array, mutually disjoint, complete for the role delta, and hash/signature-bound to the decision. Denials prove explicit exclusion rather than mere absence. Unbound, incomplete, contradictory, overlapping, or role-inconsistent sets fail closed.

**Output evidence.** An immutable activation attestation and separate activation-decision receipt binding the exact ten-entry gate map, node coordinate, identities, role, epochs, baseline, predecessor lineage, distinct verifier and acceptor identities/roles/signatures, expiry, revocation terms, rollback anchor, decision, and exact grant/deny sets. A rollback receipt MUST bind the withdrawn receipt, reason, evidence, authorized lifecycle target, removed capabilities/routes, resulting-state proof, and re-entry requirements. A revocation receipt MUST bind the exposure window and affected epoch advances.

**Rollback and re-entry.** Rollback MUST remove new authority and route eligibility before declaring isolation complete. Re-entry MUST use a successor attempt, fresh receipt lineage, current revocation checks, and the entire normal lifecycle. A previous activation receipt is evidence, not reusable authority.

## 6. Gate responsibility matrix

| Gate | Responsible producer | Independent verifier | Authoritative acceptor | Principal inputs | Required output | Failure disposition | Rollback anchor |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Provenance custodian | Provenance/signature verifier | Recovery-case authority | Snapshot bytes, manifests, custody chain | Provenance and integrity receipt | Reject; remain `isolated_rehydration` or enter `quarantined` | Original declaration and object digest set |
| 2 | Identity-binding proposer | Cross-namespace identity verifier | Identity-binding authority | Formation, candidate, provider-neutral, overlay, boot, queue, capability evidence | Non-active coordinate-binding receipt | `quarantined` | Last accepted binding and revocation set |
| 3 | Credential retirement/enrollment producer | Key and machine-identity verifier | Identity-binding authority | Inherited identity inventory, revocations, fresh public identities | Replacement and retirement receipt | `quarantined` or `revoked` | Isolated candidate before enrollment |
| 4 | Formation identity custodian | Formation/genesis verifier | Formation activation authority | Root marker, genesis signatures, manifests, baseline, ledger lineage | Formation-identity receipt | Reject; remain `isolated_rehydration` or enter `quarantined` | Unbound candidate inventory |
| 5 | Boot and predecessor-exclusion producer | Duplicate/stale-instance verifier | Identity-binding authority | Fresh boot, predecessor inventory, isolation, epoch evidence | Stale-instance exclusion receipt | `quarantined` | Pre-admission isolation state |
| 6 | Volume and ledger custodian | Storage/ledger verifier | Formation activation authority | Volume identity, manifests, ledger, receipts, state pointers | Volume consistency and ledger reconstruction receipt | `quarantined` | Last verified read/write mode and ledger anchor |
| 7 | Queue evidence/reconciliation producer | Independent queue reconciler | Queue lifecycle authority | Slots, claims, fences, effects, sink proofs, receipts | Gap register and reconciliation receipt set | `quarantined` | Last accepted task/effect receipts |
| 8 | Queue authority recovery producer | Fencing/register verifier | Queue authority lineage acceptor | Queue/task/sink registers, epochs, renewal invalidation | High-water and epoch-advance receipt | `quarantined` or `revoked` | Frozen predecessor high-water set |
| 9 | Network policy producer | ACL/exposure verifier | Overlay admission authority | Binding, route policy, key set, default-deny and test evidence | ACL and exposure verification receipt | Enter `quarantined`, or signed rollback action to `isolated_rehydration` | Last safe policy bundle |
| 10 | Evidence-bundle assembler | Independent activation verifier | Formation activation authority | All gate receipts, role deltas, epochs, identities, rollback plan | Activation attestation and decision receipt | Enter `quarantined`/`revoked`, or signed rollback action to `isolated_rehydration` | Pre-admission isolation plus signed rollback bundle |

## 7. Per-role gate deltas

These deltas add evidence; they do not weaken universal gates. Each role delta MUST define its complete allowed capability universe and mandatory exclusions. For an activation decision, the canonical `granted_capabilities` and `denied_capabilities` arrays MUST be validated against that role delta, MUST be mutually disjoint, and together MUST account for every capability evaluated by the policy. A denial is affirmative exclusion evidence, not an inference from an omitted grant.

### 7.1 `compute-coordinator-00`

Before verification, the candidate MUST provide authority-epoch lineage, restart-stable monotonic continuity evidence or completed recovery-wait evidence, every queue/task and protected-sink high-water register, accepted-receipt reconstruction, prior-renewal invalidation, stale-authority exclusion, and proof of one exclusive authority with a strictly increasing token sequence. Its first permitted new token MUST be greater than every accepted predecessor high-water mark. Claims, renewals, takeovers, queue CAS, and consequential writes MUST remain frozen until Gate 8 and activation succeed.

### 7.2 `state-vault-00`

The candidate MUST prove durable volume correspondence, ledger head and hash-chain continuity, accepted-receipt rebuild, gap classifications, reconciliation-receipt set, proof-query behavior, and volume consistency. Its coordinate binding and activation receipt MUST explicitly exclude queue CAS, lease issuance, authority-epoch allocation, terminal-lifecycle decisions, and unilateral correction of sink-owned registers. The vault remains evidence-only.

### 7.3 `mesh-relay-00`

The candidate MUST prove relay-only capabilities, bounded transport-control identity, no ambient application credentials, no authority or ledger signing rights, no unrestricted exit, no general subnet transit, and no policy-bypass route. Relay compromise MUST be modeled as an availability and metadata risk, not as inherited trust between endpoints.

### 7.4 `cleanroom-executor-00`

The candidate MUST prove TLS/certificate provenance, exact public listener intent, request-boundary normalization, private-upstream authentication, and negative access to queue storage, vault management, worker administration, and unapproved routes. Public ingress MUST remain closed through `attested` and `admitted_to_overlay`; it may open only as part of the accepted role-activation decision. Public identity claims MUST NOT become queue principals, leases, capabilities, or effect authority.

### 7.5 `compute-worker-00`

The candidate MUST prove fresh workload identity, expected mount correspondence, no queue or ledger authority, current execution capabilities, current adapter policy, and private-only service exposure. It MUST NOT execute until queue identity, current claim, lease token, sink fences, authority epoch, boot identity, role binding, required capabilities, idempotency slot, and replay policy are verified at execution time.

## 8. Failure, conflict, rollback, and repetition behavior

### 8.1 Snapshot conflict or tamper

Conflicting manifests, signatures, custody claims, source coordinates, or content digests place the candidate in `quarantined`. The verifier MUST retain each competing representation and issue a conflict receipt. No conflict may be resolved by last-write-wins, deletion, or selecting the representation that most closely resembles the desired role.

### 8.2 Stale clone or zombie instance

Discovery of another instance, boot, key, route, lease, or binding that may still act under the same coordinate requires immediate quarantine. Authority-bearing roles MUST freeze writes and advance affected epochs only after durable predecessor lineage is known. Network isolation of the new candidate alone is insufficient if the predecessor can still reach a protected sink.

### 8.3 Key compromise

Suspected or proven compromise requires deny-before-re-enrollment, signed revocation, exposure-window review, and reconciliation of bindings, claims, fences, receipts, policy changes, and effects created during that window. Role epoch and, where authority may be affected, authority epoch MUST advance. Rotating a transport key alone does not repair queue or ledger lineage.

### 8.4 Incomplete or contradictory ledger

A missing projection with an accepted authoritative receipt may be repaired by a reconciliation receipt. A missing receipt, unknown sink outcome, broken lineage, or contradictory valid-looking records requires `reconciliation-required` or `ambiguous` classification as defined by the queue specification. Contradictions MUST remain visible. A later snapshot or graph-integrity result cannot erase them.

### 8.5 Volume mismatch

If volume identity, formation identity, content manifest, mount coordinate, or read/write intent conflicts, the candidate remains quarantined. The protocol MUST NOT adapt the formation identity to fit the attached volume. Re-entry requires an explicitly authorized migration or the correct volume, each with new evidence lineage.

### 8.6 Authority partition

If more than one authority can advance the same lineage, or if exclusive authority and register continuity cannot be proved, claims and consequential writes remain frozen. Availability pressure does not permit a second authority, reset token sequence, vault-side lifecycle decision, or emergency replay.

### 8.7 Rollback

Rollback is a signed transition action, not a lifecycle state or an informal configuration reversal. It MUST identify the active or admitted receipt being withdrawn; stop new leases, routes, effects, and public exposure as applicable; preserve current evidence; revoke or suspend the candidate binding; restore a known-safe policy without restoring revoked identities; and prove the resulting isolated state. If proof is incomplete, the candidate remains quarantined.

### 8.8 Repeated rehydration

Each attempt MUST have a unique attempt generation and predecessor digest. Repeated restoration from the same bytes MUST reuse provenance evidence by reference but MUST create fresh boot, candidate, binding, key, gate, and decision evidence. Attempts MUST NOT reuse leases, tokens, sink fences, sessions, activation receipts, or revoked credentials. A rejected, quarantined, or revoked attempt remains in the audit chain and cannot be rewritten as though it never occurred.

## 9. Activation attestation and proof bundle

### 9.1 Normative activation-attestation schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:recursive-field:schema:snapshot-rehydration-activation-attestation:1.1.0",
  "title": "Recursive Field Snapshot Rehydration Activation Attestation",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_name",
    "schema_version",
    "protocol_version",
    "formation_id",
    "formation_generation",
    "logical_coordinate",
    "role",
    "candidate_attempt",
    "predecessor_lineage_sha256",
    "prior_state",
    "next_state",
    "identities",
    "epochs",
    "gate_receipts",
    "specification_sha256",
    "repository_baseline",
    "verifier_id",
    "verifier_role",
    "acceptor_id",
    "acceptor_role",
    "decision",
    "rollback_anchor_sha256",
    "valid_from",
    "expires_at",
    "revocation_status",
    "decision_payload_sha256",
    "verifier_signature_ref",
    "acceptor_signature_ref",
    "attestation_sha256"
  ],
  "properties": {
    "schema_name": {
      "const": "recursive-field.snapshot-rehydration-activation-attestation"
    },
    "schema_version": {
      "const": "1.1.0"
    },
    "protocol_version": {
      "type": "string"
    },
    "formation_id": {
      "type": "string",
      "minLength": 1
    },
    "formation_generation": {
      "type": "integer",
      "minimum": 0
    },
    "logical_coordinate": {
      "enum": [
        "compute-coordinator-00",
        "mesh-relay-00",
        "state-vault-00",
        "cleanroom-executor-00",
        "compute-worker-00"
      ]
    },
    "role": {
      "type": "string",
      "minLength": 1
    },
    "candidate_attempt": {
      "type": "integer",
      "minimum": 1
    },
    "predecessor_lineage_sha256": {
      "type": "string",
      "pattern": "^[0-9a-f]{64}$"
    },
    "prior_state": {
      "enum": [
        "declared",
        "isolated_rehydration",
        "verified",
        "attested",
        "admitted_to_overlay",
        "role_activated",
        "quarantined",
        "revoked"
      ]
    },
    "next_state": {
      "enum": [
        "declared",
        "isolated_rehydration",
        "verified",
        "attested",
        "admitted_to_overlay",
        "role_activated",
        "quarantined",
        "revoked"
      ]
    },
    "identities": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "snapshot_provenance_sha256",
        "provider_resource_sha256",
        "overlay_identity_sha256",
        "boot_identity_sha256",
        "volume_identity_sha256"
      ],
      "properties": {
        "snapshot_provenance_sha256": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$"
        },
        "provider_resource_sha256": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$"
        },
        "overlay_identity_sha256": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$"
        },
        "boot_identity_sha256": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$"
        },
        "volume_identity_sha256": {
          "type": "string",
          "pattern": "^[0-9a-f]{64}$"
        }
      }
    },
    "epochs": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "role",
        "authority",
        "policy",
        "key"
      ],
      "properties": {
        "role": {
          "type": "integer",
          "minimum": 0
        },
        "authority": {
          "type": "integer",
          "minimum": 0
        },
        "policy": {
          "type": "integer",
          "minimum": 0
        },
        "key": {
          "type": "integer",
          "minimum": 0
        }
      }
    },
    "gate_receipts": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "01",
        "02",
        "03",
        "04",
        "05",
        "06",
        "07",
        "08",
        "09",
        "10"
      ],
      "minProperties": 10,
      "maxProperties": 10,
      "properties": {
        "01": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "gate_number",
            "gate_name",
            "receipt_sha256",
            "decision"
          ],
          "properties": {
            "gate_number": {
              "const": 1
            },
            "gate_name": {
              "const": "snapshot-provenance-integrity-proof"
            },
            "receipt_sha256": {
              "type": "string",
              "pattern": "^[0-9a-f]{64}$"
            },
            "decision": {
              "const": "accepted"
            }
          }
        },
        "02": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "gate_number",
            "gate_name",
            "receipt_sha256",
            "decision"
          ],
          "properties": {
            "gate_number": {
              "const": 2
            },
            "gate_name": {
              "const": "logical-00-coordinate-binding"
            },
            "receipt_sha256": {
              "type": "string",
              "pattern": "^[0-9a-f]{64}$"
            },
            "decision": {
              "const": "accepted"
            }
          }
        },
        "03": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "gate_number",
            "gate_name",
            "receipt_sha256",
            "decision"
          ],
          "properties": {
            "gate_number": {
              "const": 3
            },
            "gate_name": {
              "const": "provider-instance-overlay-key-replacement"
            },
            "receipt_sha256": {
              "type": "string",
              "pattern": "^[0-9a-f]{64}$"
            },
            "decision": {
              "const": "accepted"
            }
          }
        },
        "04": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "gate_number",
            "gate_name",
            "receipt_sha256",
            "decision"
          ],
          "properties": {
            "gate_number": {
              "const": 4
            },
            "gate_name": {
              "const": "genesis-formation-identity-verification"
            },
            "receipt_sha256": {
              "type": "string",
              "pattern": "^[0-9a-f]{64}$"
            },
            "decision": {
              "const": "accepted"
            }
          }
        },
        "05": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "gate_number",
            "gate_name",
            "receipt_sha256",
            "decision"
          ],
          "properties": {
            "gate_number": {
              "const": 5
            },
            "gate_name": {
              "const": "boot-identity-stale-instance-exclusion"
            },
            "receipt_sha256": {
              "type": "string",
              "pattern": "^[0-9a-f]{64}$"
            },
            "decision": {
              "const": "accepted"
            }
          }
        },
        "06": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "gate_number",
            "gate_name",
            "receipt_sha256",
            "decision"
          ],
          "properties": {
            "gate_number": {
              "const": 6
            },
            "gate_name": {
              "const": "durable-volume-ledger-reconstruction"
            },
            "receipt_sha256": {
              "type": "string",
              "pattern": "^[0-9a-f]{64}$"
            },
            "decision": {
              "const": "accepted"
            }
          }
        },
        "07": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "gate_number",
            "gate_name",
            "receipt_sha256",
            "decision"
          ],
          "properties": {
            "gate_number": {
              "const": 7
            },
            "gate_name": {
              "const": "queue-receipt-gap-classification-reconciliation"
            },
            "receipt_sha256": {
              "type": "string",
              "pattern": "^[0-9a-f]{64}$"
            },
            "decision": {
              "const": "accepted"
            }
          }
        },
        "08": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "gate_number",
            "gate_name",
            "receipt_sha256",
            "decision"
          ],
          "properties": {
            "gate_number": {
              "const": 8
            },
            "gate_name": {
              "const": "high-water-register-restoration-fencing-epoch-advancement"
            },
            "receipt_sha256": {
              "type": "string",
              "pattern": "^[0-9a-f]{64}$"
            },
            "decision": {
              "const": "accepted"
            }
          }
        },
        "09": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "gate_number",
            "gate_name",
            "receipt_sha256",
            "decision"
          ],
          "properties": {
            "gate_number": {
              "const": 9
            },
            "gate_name": {
              "const": "network-acl-public-exposure-verification"
            },
            "receipt_sha256": {
              "type": "string",
              "pattern": "^[0-9a-f]{64}$"
            },
            "decision": {
              "const": "accepted"
            }
          }
        },
        "10": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "gate_number",
            "gate_name",
            "receipt_sha256",
            "decision"
          ],
          "properties": {
            "gate_number": {
              "const": 10
            },
            "gate_name": {
              "const": "signed-activation-attestation-rollback-evidence"
            },
            "receipt_sha256": {
              "type": "string",
              "pattern": "^[0-9a-f]{64}$"
            },
            "decision": {
              "const": "accepted"
            }
          }
        }
      }
    },
    "specification_sha256": {
      "type": "array",
      "minItems": 2,
      "items": {
        "type": "string",
        "pattern": "^[0-9a-f]{64}$"
      },
      "uniqueItems": true
    },
    "repository_baseline": {
      "const": "5a8c9d92ff6d6f705390b834d0c6f7bc6a2815ff"
    },
    "verifier_id": {
      "type": "string",
      "minLength": 1
    },
    "verifier_role": {
      "type": "string",
      "minLength": 1
    },
    "acceptor_id": {
      "type": "string",
      "minLength": 1
    },
    "acceptor_role": {
      "type": "string",
      "minLength": 1
    },
    "decision": {
      "enum": [
        "activate",
        "deny",
        "quarantine",
        "rollback",
        "revoke"
      ]
    },
    "granted_capabilities": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "string",
        "minLength": 1
      },
      "uniqueItems": true
    },
    "denied_capabilities": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "string",
        "minLength": 1
      },
      "uniqueItems": true
    },
    "rollback_anchor_sha256": {
      "type": "string",
      "pattern": "^[0-9a-f]{64}$"
    },
    "valid_from": {
      "type": "string",
      "format": "date-time"
    },
    "expires_at": {
      "type": "string",
      "format": "date-time"
    },
    "revocation_status": {
      "enum": [
        "not-revoked",
        "revoked"
      ]
    },
    "decision_payload_sha256": {
      "type": "string",
      "pattern": "^[0-9a-f]{64}$"
    },
    "verifier_signature_ref": {
      "type": "string",
      "minLength": 1
    },
    "acceptor_signature_ref": {
      "type": "string",
      "minLength": 1
    },
    "attestation_sha256": {
      "type": "string",
      "pattern": "^[0-9a-f]{64}$"
    }
  },
  "allOf": [
    {
      "if": {
        "properties": {
          "decision": {
            "const": "activate"
          }
        },
        "required": [
          "decision"
        ]
      },
      "then": {
        "required": [
          "granted_capabilities",
          "denied_capabilities"
        ]
      }
    }
  ]
}
```

The schema makes the ten canonical gate keys and their index/name/accepted-decision bindings machine-checkable and conditionally requires both capability arrays for activation. The semantic validator and CAS acceptor MUST additionally prove that the two capability arrays are canonically ordered, mutually disjoint, exhaustive for the applicable role delta, immutable under the signed payload digest, and consistent with role policy; that `verifier_id != acceptor_id`; that signatures use distinct authorized keys and bind signer roles, payload digest, and predecessor lineage; and that `(prior_state, next_state)` is a legal transition. JSON Schema alone cannot prove those cross-field or cryptographic invariants.

### 9.2 Non-authoritative activation-attestation example

```json
{
  "schema_name": "recursive-field.snapshot-rehydration-activation-attestation",
  "schema_version": "1.1.0",
  "protocol_version": "0.1.0-draft",
  "formation_id": "example-formation",
  "formation_generation": 12,
  "logical_coordinate": "cleanroom-executor-00",
  "role": "public_ingress_tls_isolated_verifier",
  "candidate_attempt": 1,
  "predecessor_lineage_sha256": "0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f",
  "prior_state": "admitted_to_overlay",
  "next_state": "role_activated",
  "identities": {
    "snapshot_provenance_sha256": "1010101010101010101010101010101010101010101010101010101010101010",
    "provider_resource_sha256": "2020202020202020202020202020202020202020202020202020202020202020",
    "overlay_identity_sha256": "3030303030303030303030303030303030303030303030303030303030303030",
    "boot_identity_sha256": "4040404040404040404040404040404040404040404040404040404040404040",
    "volume_identity_sha256": "5050505050505050505050505050505050505050505050505050505050505050"
  },
  "epochs": {
    "role": 3,
    "authority": 0,
    "policy": 9,
    "key": 4
  },
  "gate_receipts": {
    "01": {
      "gate_number": 1,
      "gate_name": "snapshot-provenance-integrity-proof",
      "receipt_sha256": "1111111111111111111111111111111111111111111111111111111111111111",
      "decision": "accepted"
    },
    "02": {
      "gate_number": 2,
      "gate_name": "logical-00-coordinate-binding",
      "receipt_sha256": "2222222222222222222222222222222222222222222222222222222222222222",
      "decision": "accepted"
    },
    "03": {
      "gate_number": 3,
      "gate_name": "provider-instance-overlay-key-replacement",
      "receipt_sha256": "3333333333333333333333333333333333333333333333333333333333333333",
      "decision": "accepted"
    },
    "04": {
      "gate_number": 4,
      "gate_name": "genesis-formation-identity-verification",
      "receipt_sha256": "4444444444444444444444444444444444444444444444444444444444444444",
      "decision": "accepted"
    },
    "05": {
      "gate_number": 5,
      "gate_name": "boot-identity-stale-instance-exclusion",
      "receipt_sha256": "5555555555555555555555555555555555555555555555555555555555555555",
      "decision": "accepted"
    },
    "06": {
      "gate_number": 6,
      "gate_name": "durable-volume-ledger-reconstruction",
      "receipt_sha256": "6666666666666666666666666666666666666666666666666666666666666666",
      "decision": "accepted"
    },
    "07": {
      "gate_number": 7,
      "gate_name": "queue-receipt-gap-classification-reconciliation",
      "receipt_sha256": "7777777777777777777777777777777777777777777777777777777777777777",
      "decision": "accepted"
    },
    "08": {
      "gate_number": 8,
      "gate_name": "high-water-register-restoration-fencing-epoch-advancement",
      "receipt_sha256": "8888888888888888888888888888888888888888888888888888888888888888",
      "decision": "accepted"
    },
    "09": {
      "gate_number": 9,
      "gate_name": "network-acl-public-exposure-verification",
      "receipt_sha256": "9999999999999999999999999999999999999999999999999999999999999999",
      "decision": "accepted"
    },
    "10": {
      "gate_number": 10,
      "gate_name": "signed-activation-attestation-rollback-evidence",
      "receipt_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "decision": "accepted"
    }
  },
  "specification_sha256": [
    "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
  ],
  "repository_baseline": "5a8c9d92ff6d6f705390b834d0c6f7bc6a2815ff",
  "verifier_id": "independent-rehydration-verifier",
  "verifier_role": "activation-bundle-verifier",
  "acceptor_id": "formation-activation-authority",
  "acceptor_role": "activation-cas-acceptor",
  "decision": "activate",
  "granted_capabilities": [
    "isolated-verification",
    "public-tls-termination"
  ],
  "denied_capabilities": [
    "lease-fencing",
    "queue-cas",
    "terminal-lifecycle"
  ],
  "rollback_anchor_sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
  "valid_from": "2030-07-10T00:00:00Z",
  "expires_at": "2030-07-10T01:00:00Z",
  "revocation_status": "not-revoked",
  "decision_payload_sha256": "dededededededededededededededededededededededededededededededede",
  "verifier_signature_ref": "detached-signature:verifier-example",
  "acceptor_signature_ref": "detached-signature:acceptor-example",
  "attestation_sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
}
```

This example is non-authoritative and does not assert live public exposure or activation.

### 9.3 Final activation proof bundle

The final bundle MUST be content-addressed and include:

1. protocol, queue-specification, network-specification, schema, policy, and repository-baseline digests;
2. declaration, isolation, verification, attestation, overlay-admission, and activation receipts;
3. the canonical `01`–`10` gate map containing exactly one accepted receipt per registry index/name, with no missing, extra, duplicate-semantic, rejected, or mismatched entry, plus each input/output evidence manifest;
4. signed coordinate binding, predecessor disposition, duplicate-coordinate proof, and revocation set;
5. snapshot provenance, chain-of-custody, volume identity, formation identity, boot identity, overlay identity, provider-neutral resource identity, and workload identity evidence;
6. ledger reconstruction, accepted-receipt index, conflict/gap register, reconciliation receipts, and protected-sink proof references;
7. high-water register manifest, authority and role epochs, prior-renewal invalidation, stale-authority exclusion, and first-new-token constraint;
8. ACL compilation, default-deny proof, positive and negative reachability evidence, public-exposure decision, and listener/route evidence;
9. role-specific delta receipt and immutable, canonical, unique, mutually disjoint `granted_capabilities` and `denied_capabilities` arrays bound into the decision digest and both signatures;
10. distinct verifier and acceptor identities/roles, separately keyed signatures over the same decision digest and predecessor lineage, expiry/revocation terms, rollback-action bundle, and retention manifest.

### 9.4 Normative verification matrix

| Invariant | Positive proof | Mandatory negative proof | Acceptance rule |
| --- | --- | --- | --- |
| Activation capability binding | Both canonical, unique grant/deny arrays are present, disjoint, role-complete, and included in the signed decision payload. | Missing array, overlap, non-canonical order, omission, contradiction, mutation, or role inconsistency is rejected. | Schema conditional plus semantic role-delta and signature validation. |
| Verifier/acceptor separation | Distinct authorized identities and roles provide separately keyed signatures over the same payload digest and predecessor lineage. | `verifier_id == acceptor_id`, shared/missing signature, signer-role mismatch, digest mismatch, or lineage mismatch is rejected. | Semantic validator and CAS acceptance check; schema presence alone is insufficient. |
| Gate completeness | The `01`–`10` object has exactly ten canonical properties, each with the matching index, registry name, receipt digest, and `accepted` decision. | Missing/extra key, rejected receipt, duplicate semantic gate, or index/name mismatch is rejected. | Draft 2020-12 schema plus semantic receipt-digest/signature validation. |
| Lifecycle legality | State values use the exact enum and the ordered pair occurs in Section 4.2. | Skip, unauthorized recovery edge, lifecycle `failed`/`rollback`, or rollback without removal/result proof is rejected. | Semantic transition-registry check at every transition CAS. |
| Rollback validity | A signed action from `verified`, `attested`, or `admitted_to_overlay` targets `isolated_rehydration`, `quarantined`, or `revoked` and proves capability/route removal. | Partial overlay removal without proof, or direct `role_activated → isolated_rehydration`, is rejected. | Fail closed to `quarantined` or `revoked`; reactivation requires a successor attempt. |

## 10. Retention and audit

At minimum, the formation MUST retain snapshot manifests, provenance and custody records, all candidate attempts, coordinate bindings, predecessor dispositions, key replacement and revocation records, boot identities, volume manifests, ledger anchors, accepted receipts, claims, fences, effect attestations, reconciliation records, conflict registers, gate receipts, policy bundles, reachability evidence, activation decisions, rollback receipts, and revocation receipts for the longer of:

- the operational and security audit period;
- all queue, effect, credential, certificate, and downstream retry horizons;
- the producer idempotency-key reuse horizon;
- the lifetime of any descendant evidence that references them;
- any legal or governance retention requirement.

Compaction MUST be additive and receipt-backed. A signed summary and tombstone receipt MUST precede deletion of eligible detail. Evidence required to verify retained signatures, revoked keys, token lineage, sink-fence lineage, or activation decisions MUST remain available. Audit reconstruction MUST answer who supplied the candidate, which bytes were examined, which identities were retired or created, who verified each gate, which authority accepted each transition, what gaps or contradictions existed, why replay was or was not allowed, which capabilities were activated, and how rollback or revocation occurred.

Audit evidence proves what the recorded systems and verifiers asserted within their scopes. It does not by itself prove an unobserved external-world effect.

## 11. Documentary relationship and parked decisions

### 11.1 Relationship to governing specifications

This protocol specializes the [distributed queue specification](LEVEL_3_DISTRIBUTED_QUEUE_SPEC.md) for restoration-time receipt reconstruction, crash-boundary classification, reconciliation, high-water restoration, authority-epoch advancement, and stale-writer exclusion. It does not weaken the queue specification's idempotency, monotonic-time, fencing, sink-register, pre-receipt attestation, terminal-receipt, or no-blind-replay rules.

It specializes the [network overlay specification](LEVEL_3_NETWORK_OVERLAY_SPEC.md) by expanding snapshot-to-node restoration into the exact lifecycle `declared → isolated_rehydration → verified → attested → admitted_to_overlay → role_activated`, preserving cross-namespace identity binding, no transitive trust, default deny, duplicate-coordinate prevention, public/private ingress separation, and signed activation evidence.

The ancestry documents remain documentary evidence. Formation-root discovery, durable manifests, append-only ledgers, and volume-backed recovery are preserved where compatible. Provider-specific commands, direct activation after graph verification, hostname-based identity, shared-queue authority assumptions, and destructive cleanup are not imported into this protocol.

### 11.2 Parked substrate-specific decisions

The following require a separately authorized design or implementation phase:

- snapshot manifest format, attestation technology, and chain-of-custody service;
- identity-binding authority implementation and signature algorithms;
- provider-neutral resource identity evidence profile;
- queue authority substrate, transactional outbox, and restart-stable monotonic source;
- protected-resource scope inventory, sink adapters, and sink proof-query interfaces;
- concrete lease duration, recovery wait, uncertainty margins, key lifetimes, and overlap windows;
- overlay transport selection, private address plan, DNS architecture, and certificate authority;
- concrete protocols and ports for queue, ledger, relay control, enrollment, management, and attestation;
- cloud, host, overlay, workload, and public-ingress enforcement implementations;
- credential-storage technology, host-key replacement policy by role, and hardware-backed identity options;
- retention durations, privacy classifications, alert thresholds, and evidence-compaction schedule;
- canonical JSON and signature profile beyond the semantic schemas in this draft;
- authorized principals for reconciliation, ambiguity-risk acceptance, activation, rollback, and revocation.

No parked decision may reopen the settled requirements for unique logical binding, fresh identity, receipt-backed lifecycle, queue reconciliation, monotonic fencing, default deny, verifier/authority separation, or rollback evidence.

## 12. Conformance statement

A rehydration attempt conforms only if it traverses the complete success lifecycle without shortcuts; satisfies all universal gates and applicable role deltas; preserves contradictory evidence; proves one current cross-namespace coordinate binding; excludes stale instances and inherited actuation credentials; reconstructs ledger, queue, receipt, register, and protected-sink evidence without blind replay; advances epochs where required; remains isolated and default-deny until admission; and ends with separate signed verifier attestation and CAS-controlled authority decision.

This document is a protocol draft, not live verification. It does not claim that any snapshot, provider instance, overlay identity, volume, coordinate, route, queue authority, or role is currently restored, admitted, active, or valid.
