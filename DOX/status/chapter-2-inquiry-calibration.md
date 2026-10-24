# Chapter 2 Inquiry Calibration

## Question Served

How can Chapter 2 deepen recursive inquiry without concentrating so much breadth, evidence gathering, and synthesis inside one model call that a usage-window interruption erases the return?

This is a bounded calibration of inquiry shape. It does not optimize a provider plan, establish a universal recursion limit, or replace the substantive Chapter 2 evidence standard.

## Bounded Field

| Field | Declaration |
| --- | --- |
| Vantage | Coordinator observing completed and interrupted Chapter 2 inquiry attempts. |
| Scale | One context-dependency trace, divided into independently closable source passes. |
| Time | Pass A is the retained baseline; calibration continues through the remaining dependency passes and one final meta-pass. |
| Actors | A coordinating inquiry, isolated pass workers where available, and a final scorer that does not participate in evidence gathering. |
| Included region | Pass scope, permitted boundary crossings, durable checkpoint quality, source-tied findings, build-path narrowing, completion, and interruption recovery. |
| Excluded region | Provider billing optimization, universal token thresholds, model-quality ranking, live infrastructure, private contents, and implementation selection. |
| Topology | A time-limited cone: each pass follows one dependency class or pair, may cross one predeclared adjacent boundary, then returns to a durable checkpoint. |
| Local stopping condition | Stop after the dependency passes and final meta-pass can compare the baseline with post-baseline returns, or earlier if the sample cannot discriminate inquiry shape from scope. |

## Variables and Epistemic Status

| Variable | Status in this field |
| --- | --- |
| Pass A | **Observed baseline:** completed, source-tied, durably recorded, and not designed under this calibration protocol. |
| Completion or interruption | **Observed event** per pass. |
| Source-tied finding count | **Configured measure:** count only findings carrying a stable source symbol or exact source range. |
| Build-path narrowing | **Inference:** whether a finding removes an ambiguity, exposes a dependency, or sharpens an acceptance boundary. |
| Pure, lateral, or combined shape | **Inference assigned only by the final meta-pass from the record.** |
| Provider capacity and remaining usage | **Latent:** not directly measured and not inferred from one interruption. |
| Scope difficulty | **Controlled imperfectly** by using adjacent segments of one dependency trace. |
| Model and provider variation | **Temporarily frozen where possible; otherwise recorded as a confound.** |

## Mapping the Proposed Additions to the Existing Skill

### Checkpoint origin

The proposed origin field overlaps substantially with the bounded-inquiry vocabulary, so duplicate labels are not added where the skill already carries the meaning.

| Proposed element | Existing skill term | Disposition |
| --- | --- | --- |
| Standing | Vantage, scale, and included region | **Drop the duplicate label.** Every checkpoint states the dependency class or pair at which the pass stopped under `Vantage and scope`. |
| Displacement | Permitted boundary crossings and exploration topology | **Retain only the missing delta.** Each checkpoint records a `Boundary-crossing delta`: classes entered or left since the prior checkpoint. |
| Assumption flag | Temporarily frozen assumptions, constraint shadow, and reopening conditions | **Drop the duplicate label.** A checkpoint must identify any earlier finding whose standing no longer supports its assumption under `Constraint shadow`. |

The next pass reads the previous checkpoint's vantage and scope, boundary-crossing delta, and relevant constraint shadow before beginning. This is a handoff condition, not an authority chain.

### Widening type

The skill already requires permitted boundary crossings, topology, parked branches, and stopping conditions. It does not distinguish the epistemic shape of a widening, so the following addition is retained:

- **Lateral widening:** inspect one adjacent dependency class and record its evidence separately. Do not form a cross-class finding inside that pass.
- **Combined widening:** inspect one predeclared adjacent class because the finding cannot be stated from either class's evidence alone. Record the cross-class dependence explicitly.

Widening order is fixed before evidence inspection:

1. Complete the contained route for the pass's declared class or pair.
2. Evaluate only the predeclared widening trigger.
3. If it fires, use only the predeclared widening type.
4. Checkpoint immediately after that one widening.
5. Park every other adjacent pair as an open item.

A pass may widen once. Widening is an occasional collision test, not the default unit of inquiry.

### Blinded scoring

Blinding is not supplied by the bounded-inquiry skill and is retained as an experimental control.

- Evidence-gathering workers receive only their local source question, scope, permitted widening, stopping condition, and required finding form.
- They do not receive the sweet-spot hypothesis, expected classification, baseline comparison, or scoring rule.
- The coordinator preserves raw returns before interpretation.
- After the dependency passes, a separate meta-pass tags each source-tied finding as `pure`, `lateral`, or `combined` from the records alone and marks whether it narrows the build path.
- These shape tags supplement; they never replace observation, documentary evidence, inference, hypothesis, decision, implementation, or verification labels.

Blinding is **partial** if a worker can inspect this calibration record, inherits the coordinating conversation, or receives coordinator commentary beyond its local pass. Any such exposure must be recorded rather than silently treated as blinded.

## Conflicts With the Skill

No direct conflict was found.

- The skill requires each inquiry to declare its question and decision served. A blinded worker still receives its own substantive source question; only the meta-hypothesis and scoring expectation are withheld.
- The skill permits widening while a branch materially affects fidelity or interpretation. The one-widening limit is a stricter local bound, not a contradiction.
- The skill requires locally honest closure. Blinding does not permit a worker to omit unknowns, constraint shadows, or reopening conditions.

If the one-widening limit prevents a truthful finding, the skill wins: the pass stops at the unresolved boundary rather than manufacturing closure. The additional crossing becomes an open item for a later pass.

## Pass Sequence and Predeclared Widening

Pass A remains the baseline. The former broad passes are divided into smaller checkpoints so total depth accumulates across durable returns.

| Pass | Contained class or pair | Predeclared widening trigger | Allowed widening type |
| --- | --- | --- | --- |
| A | Persisted context and project/profile linkage | Baseline; no retrospective widening | None |
| B1 | Project metadata and memory namespace | The namespace cannot be interpreted without the knowledge source that feeds it | Lateral |
| B2 | Knowledge source and imported projection state | Import provenance cannot be interpreted without the memory namespace that consumes the projection | Combined |
| C | Effective settings and secret/variable references | Winning non-secret configuration cannot be identified without one adjacent precedence source | Combined |
| D1 | Profile and skill resolution | The winning profile cannot be interpreted without one adjacent capability root | Lateral |
| D2 | Plugin, extension, tool, and capability registration | Effective capability presence cannot be stated from registration evidence alone | Combined |
| E1 | Scheduler and persisted context/project references | A continuing obligation cannot be classified without one adjacent recoverable state class | Lateral |
| E2 | Task, background, and provider-state relations | Durability differs only through a cross-class lifecycle relation | Combined |
| F | Dependency-closure synthesis | No widening; consumes only completed pass records | None |
| Meta | Retrospective calibration | No new source inspection | None |

The alternation does not force widening to occur. It only fixes the permitted shape if the declared trigger fires.

## Pass Record

Every post-baseline pass records:

1. **Local question served**
2. **Vantage, scale, time, and included region**
3. **Previous checkpoint read**
4. **Boundary-crossing delta**
5. **Observed and documentary evidence**
6. **Inference, hypothesis, or valid no-result**
7. **Widening trigger and outcome**
8. **Constraint shadow**, including assumptions invalidated by the current standing
9. **Parked branches**
10. **Local closure and reopening conditions**
11. **Completion state**: complete, interrupted, resumed, or abandoned
12. **Durable return**: source-tied findings and exact anchors

Workers do not score their own returns as pure, lateral, or combined and do not judge the sweet-spot hypothesis.

## Baseline: Pass A

Pass A completed one context-to-project route and established five failure boundaries. It produced source-tied findings, narrowed runtime-to-continuity resolution, and left a durable artifact after one bounded cycle.

For calibration it is treated as:

- completed rather than interrupted;
- contained rather than widened;
- source-tied;
- build-path relevant;
- not blinded, because it preceded this protocol;
- not directly comparable on provider demand, because exact usage and remaining-window telemetry were not captured.

This makes Pass A a loose baseline for return shape and durability, not a controlled estimate of token efficiency.

## Constraint Shadow

- The combined/lateral judgment is itself a later model inference, not an observed property of the source.
- Widening may fire too rarely to support comparison.
- This tests collision as an occasional move, not as the default inquiry unit.
- A source-tied relation may be correct but trivial; build-path narrowing is therefore scored separately.
- A small number of occasions cannot separate inquiry shape from source scope, module complexity, model variation, or latent provider capacity.
- Pass A was not prospectively blinded and has no exact demand telemetry.
- Successful completion does not by itself establish high fidelity; interrupted completion does not by itself establish poor inquiry shape.
- Any worker exposure to this record weakens blinding and must be declared.

## Retrospective Meta-Pass

### Scope and evidence

This meta-pass consumed only the durable Pass A–F records in [Chapter 2 Context Dependency Observation](chapter-2-context-dependency-observation.md). It performed no new source inspection. Scoring is **partially blinded at best**: the coordinator knew the calibration hypothesis, and some completed returns were integrated after provider-window interruption. No exact token, duration, or provider-capacity telemetry exists.

### Pass classification

| Pass | Completion | Widening observed | Retrospective shape | Source-tied findings | Build-path narrowing |
| --- | --- | --- | --- | ---: | --- |
| A | Complete baseline | None | Pure/contained baseline | 6 | Yes: exposed mutable project/profile coordinates and missing reverse closure. |
| B1 | Complete | Trigger did not fire | Pure | 6 | Yes: made memory isolation conditional and separated logical namespace from storage path. |
| B2 | Complete | Trigger did not fire | Pure | 6 | Yes: exposed the ledger/index consistency boundary and limits of hash/projection evidence. |
| C | Complete after durable worker return and integration | One combined crossing into initializer/runtime override order | Combined | 7 | Yes: separated settings, projections, aliases, extension mutation, and value actuation. |
| D1 | Complete after resumed integration | One lateral crossing into adjacent capability roots | Lateral | 7 | Yes: distinguished resource precedence, history-borne inheritance, trust, and revocation. |
| D2 | Complete | One combined crossing into execution-time tool policy | Combined | 8 | Yes: located a real enforcement seam without promoting it into full authority. |
| E1 | Complete | One lateral crossing into recoverable chat state | Lateral | 7 | Yes: separated durable obligation from historical executor formation and exactly-once semantics. |
| E2 | Complete | One combined crossing into local/provider fallback | Combined | 8 | Yes: established composite continuation and background ephemerality limits. |
| F | Complete synthesis | None permitted | Cross-pass synthesis, not scored as a source pass | 0 new | Yes: bounded the first safe observational build slice and its acceptance conditions. |

The finding count is a configured count of table rows carrying exact source anchors, not a quality score. Pass F adds no source findings by design.

### Calibration result

1. **Checkpoint durability worked.** Provider-window interruption did not erase Pass C or D1 because their local returns could be read and integrated without restarting the whole inquiry.
2. **Contained passes remained useful.** B1 and B2 did not widen, yet each exposed a build-relevant failure boundary. Widening was therefore not required for depth.
3. **One predeclared crossing was sufficient in the sampled passes.** C, D1, D2, E1, and E2 each reached a truthful local closure without a second adjacent crossing. No pass records that the one-widening bound forced false closure.
4. **Lateral and combined widening produced different value.** Lateral passes preserved class separation while locating an adjacent dependency; combined passes were useful where the finding itself depended on both classes, especially selection/enforcement and local/provider continuity.
5. **The sample does not establish an optimum.** Scope complexity, model/provider state, prior context, and coordinator involvement remain confounds. Completion and source-tied row count cannot estimate token efficiency or universal recursion depth.

### Decision

Retain checkpointed micro-passes with:

- a local source question;
- one optional predeclared crossing;
- an immediate durable return;
- explicit constraint shadow and reopening conditions; and
- later synthesis that does not repeat source gathering.

Do not require alternation between lateral and combined forms in future work. Choose the crossing type from the dependency relation. Do not claim blinded scoring unless the worker cannot inspect the calibration record or coordinating conversation.

### Closure and reopening

**Locally closed:** for this inquiry, checkpointed micro-passes preserved useful depth and recoverability through interruption while allowing a final dependency synthesis.

**Confidence:** high that durable checkpoints improved interruption resilience in this case; moderate that the one-crossing bound preserved fidelity; low for any quantitative or universal sweet-spot claim.

Reopen the calibration if two consecutive future passes fail without durable return, a pass requires multiple crossings to state a truthful finding, checkpoint overhead dominates the inquiry, or a larger sample with demand telemetry supports a different topology.

## Local Decision and Closure

**Decision:** the calibrated inquiry has completed. Reuse its checkpointed, one-crossing pattern as a contextual method rather than a universal recursion limit.

The original stopping condition is met: Passes A through F and this meta-pass are durably recorded, build-path narrowing is visible, and the remaining uncertainty is attributable to evidence class rather than erased by interruption.
