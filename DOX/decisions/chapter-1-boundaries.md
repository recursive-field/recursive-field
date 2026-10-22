# Chapter 1 Boundaries

## Status

**Decision.** Adopted for Chapter 1 documentation; subject to the reopening conditions below.

## Evidence Basis

These decisions translate evidence from Agent Zero revision `b1cbd1f960a1a5c4482b324dcff4742aa67b7a51`, observed on 2026-10-22. Current behavior remains **Verified Current** only for that evidence basis.

## Decisions

### 1. Evidence classes remain explicit

Every consequential statement must be recognizable as **Verified Current**, **Target Requirement**, **Decision**, **Open**, or **Not Implemented**. Intention is not implementation, and a generated projection is not evidence of its own authority.

### 2. Public lineage and private continuity remain separate

Public source lineage carries reviewable architecture, decisions, implementation, and verification. Private formation continuity carries situated instructions, memory, records, and operating context. Their relation is provenance, not forced co-location.

### 3. Runtime manifestations are replaceable

A runtime is an expression of source, configuration, durable data, and environment. It does not become the formation merely by running. Runtime-specific identifiers and coordinates are operational evidence, not public identity.

### 4. Durable data must be declared

State intended to survive replacement requires an explicit owner, persistence boundary, backup scope, and tested recovery path. Presence on a writable or mounted filesystem is not by itself proof of recoverability.

### 5. Generated projections are subordinate

Rendered prompts, semantic indexes, caches, assembled settings, logs, and similar products are rebuildable projections unless a later decision explicitly promotes one to an authoritative record.

### 6. Secrets remain outside public documentation

Public documentation may name a required secret relation or authority boundary, but must not contain credentials, private keys, tokens, sensitive endpoints, or private coordinates.

### 7. Recovery authority remains independent

A human-controlled recovery path must remain viable while formation agency is unimplemented or unproven. Chapter 1 does not transfer, mint, or automate recovery authority.

### 8. Comparative private evidence becomes recovered requirements

Requirements learned from private continuity or prior operating experience may enter public DOX only as neutral, source-independent requirements. Private systems, paths, terminology, and copied material remain outside public lineage.

### 9. Chapter 1 does not mint identity or implementation

Chapter 1 defines boundaries and translation. It does not create an identity marker, executable schema, configuration grammar, runtime marker, code path, infrastructure change, or Chapter 2 capability.

### 10. Chapter 1 closes on truthful translation

**Decision.** Chapter 1 is Complete on 2026-10-22. Immutable public image and framework-source identity, basic host storage placement, and basic HTTP publication are Verified Current. Recovery exercise, external gateway and TLS policy, context-specific effective-composition export, and behavioral knowledge and memory tests remain Open or Not Implemented and are deliberately deferred to Chapter 2. This closure records an accurate modern translation; it is not capability proof.

## Open Matters Deferred to Chapter 2

- **Open:** snapshot restoration, integrity, retention policy, and independent or off-region recovery.
- **Open:** external gateway, authorization, TLS, firewall, and tunnel policy beyond observed host publication.
- **Not Implemented:** a context-specific effective-composition export.
- **Open:** behavioral knowledge and memory freshness, retrieval-quality, and isolation tests.
- **Open:** the durable identifier, if any, for a formation and for each runtime manifestation.
- **Open:** the authoritative provenance bridge between public source lineage and private formation continuity.
- **Open:** trust and compatibility policy for discovered capabilities.
- **Open:** conditions under which recovery authority could be shared or delegated.

## Reopening Conditions

Reopen these boundaries when any of the following occurs:

1. evidence shows that a generated projection must become authoritative;
2. a proposed implementation requires private continuity in public lineage;
3. runtime identity cannot be resolved without becoming formation identity;
4. recovery tests require a different authority model;
5. Chapter 2 evidence contradicts the current source-to-target translation; or
6. a security or privacy review identifies an unsafe boundary crossing.

Reopening changes the decision record; it does not silently reinterpret prior evidence.
