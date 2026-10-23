# Formation Observation Frame

## Purpose

Provide a thin, non-authoritative, public-safe grammar for recording how formation support architecture is observed. The frame describes evidence and relations; it does not define architecture, confer authority, or prescribe implementation.

## Status and Evidence Vocabulary

Consequential claims use the Chapter 1 vocabulary:

- **Verified Current** — directly supported by inspected source or sanitized observation.
- **Target Requirement** — a capability or boundary the formation is intended to satisfy.
- **Decision** — an adopted documentary boundary.
- **Open** — evidence or design remains unresolved.
- **Not Implemented** — the capability does not presently exist as Recursive Field capability.

An observation may additionally record one bounded outcome. These outcomes do not replace the status vocabulary:

- **Not observed** — the subject was in scope, but the available evidence did not show it.
- **Not attempted** — no observation or exercise was performed.
- **Not understood** — evidence exists, but its meaning or relation is unresolved.
- **Not currently testable** — the bounded inquiry cannot be tested with its present authority, access, or method.
- **Disproved within scope** — evidence contradicts the proposition for the stated vantage, scope, and time; this is not a universal disproof.

Absence of observation is not evidence of absence. Each outcome must retain its declared scope.

## Seven-Plane Boundary

The frame recognizes exactly these seven planes:

| # | Plane | Documentary concern |
| --- | --- | --- |
| 1 | Public source lineage | Reviewable source, decisions, implementation lineage, and verification evidence that are safe to publish. |
| 2 | Private formation continuity | Situated instructions, records, knowledge, memory, and operating context that remain outside public lineage. |
| 3 | Runtime manifestation | A replaceable execution environment through which source and state become action. |
| 4 | Durable data | Participant-scoped durable state and shared resources explicitly intended to survive runtime replacement. |
| 5 | Generated projections | Rebuildable renderings, indexes, caches, assembled context, logs, and similar derivations. |
| 6 | Secrets | Secret-bearing values and stores that may be referenced but never disclosed in public evidence. |
| 7 | Recovery authority | An independent, accountable capacity to recover, restrain, or reconstitute the system. |

Concerns such as identity, policy, capability, ingress, knowledge, and memory may cross these planes; they do not create additional planes.

## Observation Record

A record is complete enough for local use when it contains:

| Field | Required content |
| --- | --- |
| Recorded time | When the record was made, distinct from the time of the subject evidence. |
| Vantage | The documentary, source, runtime, participant, or recovery perspective from which the relation is visible. |
| Scope and time | Included and excluded boundaries, the evidence interval, and any revision or dated observation anchor. |
| Subject and utility | What is being followed and why this observation matters to the current inquiry. |
| Evidence | Sanitized source anchors, attributable records, observations, or test results; generated output may carry evidence but cannot authorize itself. |
| Epistemic status | One Chapter 1 status and, when useful, one bounded observation outcome. |
| Authority and mutability | Which source governs the subject, who may change it, and whether the observed artifact is authoritative, durable, replaceable, generated, or unknown. |
| Directional relations | `origin -> adapter or boundary -> destination`, including plane crossings and the relation carried across each hop. |
| Observable effects | What changed or became visible at the destination without inferring hidden causes. |
| Constraint shadow | Relevant exclusions, suppressed nuance, access limits, alternative causes, and claims the evidence cannot support. |
| Unresolved questions | Questions whose answers would discriminate among remaining explanations or target relations. |
| Stopping and reopening conditions | Why the local trace can stop, and what new evidence, contradiction, scope change, or decision would reopen it. |

## Recording Rules

1. Record each hop independently; do not infer an end-to-end path merely because both endpoints exist.
2. Name the crossing relation and preserve direction. A reverse path requires its own evidence.
3. Separate documentary evidence from operative authority and observed effect from inferred cause.
4. Treat generated projections as non-authoritative unless an explicit later **Decision** promotes one.
5. Sanitize private continuity, participant data, secrets, coordinates, and live identifiers; record only the relation needed for public understanding.
6. Prefer a bounded unknown outcome over an unsupported completion claim.
7. Stop when the current decision can distinguish supported relations from unresolved ones; preserve questions that require another vantage or authorized exercise.

## Prohibitions

This frame must not mint or select a formation identity, canonical root, manifest or schema, desired state, hard routing, or implementation. It must not expose private contents or coordinates, convert reachability into authorization, convert discoverability into trust, convert writable storage into durability, or convert a generated projection into authority.

## Local Closure

An observation closes locally when its scope, evidence, supported hops, effects, constraint shadow, and unresolved questions are explicit enough for the current decision. Closure is documentary and reversible. It is not architecture approval, implementation authorization, parity proof, or a claim that the wider formation is understood.
