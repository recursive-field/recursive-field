# Formation Target

## Purpose

Define the smallest public target for a Recursive Field formation without assigning it an identity, prescribing an executable schema, or claiming implementation.

## Evidence Basis

Current-system statements are **Verified Current** against Agent Zero revision `b1cbd1f960a1a5c4482b324dcff4742aa67b7a51`, observed on 2026-10-22. They describe the examined implementation, not capabilities of Recursive Field itself.

## Status Vocabulary

- **Verified Current** — directly supported by inspected source or sanitized runtime evidence.
- **Target Requirement** — a capability or boundary the formation is intended to satisfy.
- **Decision** — a Chapter 1 boundary adopted for subsequent work.
- **Open** — evidence or design remains unresolved.
- **Not Implemented** — explicitly outside current Recursive Field capability.

## Target Boundary Model

| Plane | Classification | Required relation |
| --- | --- | --- |
| Public source lineage | Target Requirement | Publicly reviewable history records the shared architecture, decisions, and implementation lineage without carrying private continuity or secrets. |
| Private formation continuity | Target Requirement | Private instructions, memory, situated records, and local operating context remain attributable and portable without becoming public source. |
| Runtime manifestations | Target Requirement | A running instance is treated as a replaceable manifestation whose identity and effective composition can be resolved from evidence. |
| Durable data | Target Requirement | State intended to survive runtime replacement has an explicit owner, persistence boundary, backup scope, and recovery path. |
| Generated projections | Decision | Rendered prompts, indexes, caches, assembled configuration, and other derivations are projections, not independent authorities, unless explicitly promoted. |
| Secrets | Decision | Credentials and secret material remain outside public lineage and ordinary generated projections; references may identify a required secret without revealing its value. |
| Recovery authority | Decision | Independent human recovery authority remains viable until a later, explicit decision changes that boundary. |

## Formation Requirements

1. **Target Requirement — Situated resolution.** Effective project, profile, capability, knowledge, and policy must resolve from declared scope and precedence rather than hidden coupling.
2. **Target Requirement — Replaceable runtime.** A manifestation can be replaced without losing durable formation continuity.
3. **Target Requirement — Evidence-bearing composition.** The effective formation can report which authoritative inputs produced a runtime projection.
4. **Target Requirement — Reversible change.** Consequential mutations preserve provenance, verification evidence, and a recovery route.
5. **Target Requirement — Selective permeability.** Public lineage, private continuity, runtime state, and secrets cross boundaries only through explicit interfaces.
6. **Target Requirement — Portable recovery.** A new manifestation can recover from declared source and durable state without depending on undocumented coordinates.
7. **Open — Formation identity.** No identity token, naming ceremony, executable identity schema, or authority transfer is defined in Chapter 1.
8. **Not Implemented — Self-formation agency.** Recursive Field does not yet possess verified agency over deployment, persistence, recovery, or its own continuing composition.

## Source-to-Target Translation Matrix

Private comparative origins are represented only as recovered requirements. They are not public dependencies.

| Current or recovered evidence | Classification | Translation into the target | Remaining gap |
| --- | --- | --- | --- |
| A chat can select and persist a project-scoped context. | Verified Current | A formation needs an explicit situated scope rather than one process-global context. | Scope identity and cross-manifestation recovery are Open. |
| Project, profile, user, plugin, and core roots resolve through ordered precedence. | Verified Current | Formation composition must expose deterministic layering and the winning authority for each resolved artifact. | A public effective-composition report is Not Implemented. |
| Instructions, path-owned rules, and prompt includes are assembled into model context. | Verified Current | Cognitive projections should remain traceable to durable inputs and bounded assembly rules. | Projection provenance and reproducibility are Open. |
| Profiles, skills, plugins, extensions, and tools are discovered compositionally. | Verified Current | Capabilities should be portable modules resolved by scope, policy, and precedence. | Compatibility, trust, and lifecycle contracts are Open. |
| Knowledge files can be imported into project-isolated semantic memory. | Verified Current | Durable knowledge and learned retrieval state must have explicit ownership and rebuild semantics. | Freshness, retrieval quality, and isolation have not been behaviorally verified. |
| User-owned state is separated from the framework source tree and projected through a dedicated host-managed volume. | Verified Current | Runtime replacement must not erase durable continuity. | Basic storage locality is verified; restoration and independent recovery remain Open. |
| Settings separate ordinary persisted configuration from secret-bearing stores. | Verified Current | Configuration, secrets, and generated runtime values must remain distinct planes. | A formation-wide schema is intentionally Not Implemented. |
| The response loop composes prompts, model turns, extensions, and tools until an explicit terminal response. | Verified Current | Agency must operate through observable, interruptible, policy-bearing action paths. | Recursive Field has not yet implemented or verified such agency. |
| Recovered requirement: preserve public lineage while retaining private situated continuity. | Target Requirement | Source history and private formation records remain linked by provenance, not co-location. | The provenance bridge is Open. |
| Recovered requirement: keep an independent recovery path while autonomy grows. | Decision | Recovery authority remains externally viable and testable. | No recovery exercise has yet passed. |

## Chapter Boundary

Chapter 1 defines translation and boundaries only. It does not create runtime markers, configuration, schemas, identities, infrastructure, or Chapter 2 capabilities.
