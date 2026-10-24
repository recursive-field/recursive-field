# Chapter 2 Context Dependency Observation

## Purpose

Determine whether current Agent Zero source can derive a public-safe, content-free continuity dependency closure for one context, and identify the exact boundaries where resolution falls back to mutable coordinates, installation-global stores, runtime-only state, private values, or unexported effective composition.

This is an incremental source inquiry under the [Formation Observation Frame](../architecture/formation-observation-frame.md). It does not define formation identity, select implementation, inspect private content, or authorize runtime mutation.

## Bounded Method

The inquiry is divided into small, durable passes so interruption cannot erase completed reasoning or force a full replay. The [Chapter 2 Inquiry Calibration](chapter-2-inquiry-calibration.md) bounds pass shape, checkpoint handoff, one optional predeclared widening, and retrospective scoring. Pass A remains the baseline.

| Pass | Bounded concern | Completion output |
| --- | --- | --- |
| A | Persisted context, project linkage, and profile linkage | Context-to-project path with persistence and relocation limits |
| B1 | Project metadata and memory namespace | Project-to-memory dependency path |
| B2 | Knowledge source and imported projection state | Knowledge-to-projection dependency path |
| C | Settings, variables, and secret references | Effective-configuration dependency path without values |
| D1 | Profile and skill resolution | Selected-profile and skill-root dependency path |
| D2 | Plugins, extensions, tools, and capability registration | Capability presence, winning-source visibility, and trust gaps |
| E1 | Scheduler and persisted context/project references | Continuing-obligation dependency path |
| E2 | Task, background, and provider-state relations | Cross-context and lifecycle dependencies |
| F | Closure synthesis | Derivable, conditional, and non-derivable dependency closure |

Each pass is source-bounded, records findings here immediately, and stops at its first consequential unresolved boundary. Later passes may revise earlier inferences without erasing their evidence. Evidence-gathering workers receive only their local substantive question and bounds; calibration tags are assigned retrospectively.

## Observation Record

| Field | Record |
| --- | --- |
| Recorded time | Begun 2026-10-23. |
| Vantage | Read-only inspection of the pinned Agent Zero source. |
| Scope and time | Agent Zero revision `b1cbd1f960a1a5c4482b324dcff4742aa67b7a51`; one abstract context with no private contents or live identifiers. |
| Subject and utility | Whether a context's continuity dependencies can be enumerated by relation rather than inferred from storage adjacency. |
| Evidence | Source anchors recorded per completed pass; Chapter 1 and the continuity-state observation supply previously bounded persistence and recovery facts. |
| Epistemic status | **Complete as a bounded source inquiry.** Passes A through E2 are **Verified Current** from source within their stated boundaries; Pass F is a documentary synthesis. Instance-specific behavior, external systems, and recovery remain explicitly **Open**. |
| Authority and mutability | This record observes current dependency resolution. It is not a manifest, dependency authority, or desired state. |

## Pass A — Persisted Context and Project Linkage

### Source-grounded path

```text
user or task AgentContext
-> context id and serializable context data
-> usr/chats/<context-id>/chat.json
-> persisted `project` name and agent profile
-> usr/projects/<project-name>
-> .a0proj project adapter state
```

### Hop findings

| Hop | Identifier and scope | Persistence and owner | Dependency status | Portability and protection | Evidence |
| --- | --- | --- | --- | --- | --- |
| Context construction | Context ID plus type `user`, `task`, or `background`; runtime registry is process-local | `AgentContext._contexts` is runtime-only | ID is required for the persisted chat coordinate; type governs persistence | Registry does not survive process replacement | `agent.py:50-110`, `agent.py:168-183` |
| Context persistence | Non-background contexts serialize beneath `usr/chats`; background contexts are skipped | Installation-global user state containing participant and task records | Required for chat-carried continuity; absent by design for background work | Survives runtime replacement when user state survives; included by default backup and outside normal project Time Travel | `helpers/persist_chat.py:17-20`, `helpers/persist_chat.py:35-96` |
| Serialized context | ID, name, dates, type, agent chain, selected profile, bounded logs, public context data, output data, and agent history | Chat-scoped durable record; underscore-prefixed context keys are excluded | Required fields and histories vary by context; private runtime helper state is intentionally omitted | Deserialization can reconstruct context and agent chain from the record, subject to current profile availability and engine compatibility | `helpers/persist_chat.py:179-247`, `helpers/persist_chat.py:250-323` |
| Project selection | Context data key `project` stores the project name; activation also stores display output and reconciles the profile | Chat-scoped reference to project adapter state | Conditional: a context may have no active project | Runtime replacement is supported by persisted chat plus user state; project rename breaks the stored name unless repaired | `helpers/projects.py:27`, `helpers/projects.py:448-487`, `helpers/projects.py:669-670` |
| Project resolution | Project name is joined to the installation projects root; `.a0proj` is derived beneath that folder | Project adapter coordinates under installation-global user state | Required when a project is selected | Absolute installation-root relocation may be handled elsewhere, but project rename or a changed parent convention is not neutral in this relation | `helpers/projects.py:11-17`, `helpers/projects.py:77-97` |
| Profile linkage | Main and subordinate profiles are serialized by profile name; deserialization initializes current configuration from those names | Chat-scoped reference to capability definitions resolved from current source/state | Conditional but consequential to behavioral reconstruction | If a profile is unavailable after project activation, reconciliation selects a fallback and mutates the context configuration; original effective behavior is not guaranteed | `helpers/persist_chat.py:179-232`, `helpers/persist_chat.py:250-323`, `helpers/projects.py:402-419` |

### Forward and reverse resolution

**Verified Current — forward:** a non-background context can persist a project name and profile name; source can derive the conventional project and metadata paths from that name and initialize current profile configuration during deserialization.

**Partially derivable — reverse:** a loaded context exposes its selected project through context data. The project surface does not itself carry a durable index of all chats, tasks, or background contexts that depend on it. Current helper operations can scan loaded contexts, while an at-rest reverse lookup would require scanning installation-global chat records or another observation surface.

### Continuity consequences

- `user` and `task` contexts can bear durable participant or operational relations; `background` contexts are intentionally ephemeral.
- The persisted project relation is a mutable application coordinate, not formation identity.
- A context record preserves the selected profile name but not a complete versioned closure of the profile and capabilities that produced prior behavior.
- Project activation can reconcile an unavailable profile to a current fallback. This preserves operability but can alter behavioral continuity.
- The context-to-project link survives runtime replacement only when its chat record, named project, and compatible interpretation surfaces survive together.

### Pass A failure boundaries

1. Project rename or relocation is not represented as a durable alias or lineage transition.
2. A project cannot enumerate all persisted contexts that refer to it without a broader scan.
3. Profile names do not identify exact profile source, version, shadowed alternatives, or transitive capabilities.
4. Runtime-only and underscore-prefixed context data are intentionally absent from persistence.
5. Background contexts have no durable continuity relation through chat persistence.

### Pass A local closure

**Verified Current:** current source derives a content-free `persisted context -> project name -> conventional project path` relation and preserves profile names for user and task contexts.

**Open:** this relation is insufficient for continuity closure because it is mutable, one-directional at rest, and does not enumerate the project, memory, knowledge, configuration, capability, scheduler, or recovery dependencies needed to interpret the context faithfully.

## Pass B1 — Project Metadata and Memory Namespace

### Checkpoint

| Field | Record |
| --- | --- |
| Local question | How does an abstract persisted project name resolve project metadata and the context's memory namespace, and where does that route first become conditional, mutable, or non-reversible? |
| Vantage and scope | Read-only source inspection at the pinned revision; project metadata and memory namespace only. No private state or values were read. |
| Previous checkpoint read | Pass A's project-name coordinate, derived project path, rename/relocation gap, and absence of durable background-context persistence. |
| Boundary-crossing delta | Entered project metadata, scoped plugin configuration, logical memory namespace, physical memory placement, runtime memory cache, and durable vector-store placement. Left chat persistence and profile behavior as prior evidence. |
| Widening | The predeclared knowledge-source trigger did **not** fire. No adjacent knowledge module was inspected. |
| Completion state | **Complete** for the bounded source question. |

### Source-grounded route

```text
context data `project` name
-> conventional `usr/projects/<name>` project root
-> `.a0proj/project.json` metadata coordinate
-> project/profile-aware `_memory` configuration precedence
-> `project_memory_isolation` branch
-> logical `projects/<name>` or configured/shared namespace
-> project-local `.a0proj/memory` or installation-global `usr/memory/<namespace>`
-> process-local cache and on-disk vector-store artifacts
```

### Findings

| Relation | Documentary evidence | Finding |
| --- | --- | --- |
| Name to project metadata | `helpers/projects.py:11-16`, `77-86`, `167-173` | Project metadata is conventionally derived as `usr/projects/<name>/.a0proj/project.json`. The loader injects the supplied route name into returned metadata; it does not recover an independent stable project identifier. |
| Context to scoped memory configuration | `helpers/plugins.py:600-654`, `707-717`, `766-829`; `plugins/_memory/plugin.yaml:1-8` | `_memory` configuration is selected through project- and profile-aware first-existing precedence, bundled fallback, and a generic post-load hook. Candidate sources are enumerable, but the winning effective result is conditional and mutable. |
| Configuration to logical namespace | `plugins/_memory/helpers/memory.py:697-715`; `plugins/_memory/default_config.yaml:1-16` | Project isolation is a default, not an invariant. With isolation and a project name, the namespace is `projects/<name>`; otherwise a configured shared namespace or `default` is used. |
| Namespace to physical state | `plugins/_memory/helpers/memory.py:666-673` | Project namespaces map to `.a0proj/memory`; other namespaces map under installation-global `usr/memory`. Location is derivable once the effective branch inputs are known. |
| Physical state to runtime projection | `plugins/_memory/helpers/memory.py:69-94`, `133-245`, `497-551` | A process-global cache is runtime-only. On cache miss, initialization may create directories and write vector-index and embedding metadata artifacts. Persisted files may be reloaded subject to integrity and model-compatibility behavior. |
| Convention-based reverse enumeration | `helpers/projects.py:373-399`; `plugins/_memory/helpers/memory.py:718-742` | Current helpers can enumerate directory-derived project names and memory namespaces, but this is not relocation-stable identity recovery. |

### Forward and reverse resolution

**Verified Current — forward:** once effective `_memory` configuration is known, source can project the context's project name into either a project-local or shared memory namespace and physical path.

**Conditional:** source cannot derive the branch from the project name alone. Scoped configuration precedence and the isolation setting intervene.

**Partially derivable — reverse:** conventional directory scans reconstruct names from current placement and vector-index existence. No inspected resolver maps an arbitrary relocated metadata or memory path back to the original persisted project relation.

### Constraint shadow

- The earlier assumption that an active project necessarily owns an isolated memory namespace is no longer supportable. Isolation depends on available configuration, a truthy isolation setting, and a project name.
- Profile-specific configuration may change the isolation decision, while an isolated namespace normally omits profile and converges participants in one project on `projects/<name>`.
- Namespace calculation is read-only, but obtaining a memory instance can cross into directory creation and vector-store writes.
- Storage location alone does not establish backup, Time Travel, restore, or migration coverage.
- Rename and relocation fragility are inferred from the name/path coupling; no rename workflow or runtime behavior was inspected.
- Integrity-failure replacement, model-mismatch reindexing, and recovery effects remain untested.

### Parked branches

Knowledge-source and import behavior; semantic retrieval; plugin activation; effective configuration values; backup and Time Travel coverage; rename/migration behavior; cross-runtime and cross-node resolution; formation identity.

### Local closure and reopening

**Verified Current:** Agent Zero can derive project metadata and a conditional memory namespace from a context's mutable project-name coordinate plus effective `_memory` configuration.

**Open:** the route does not provide relocation-stable identity, content-free effective-configuration closure, or recovery semantics.

Reopen Pass B1 if project rename/relocation must be established, backup or Time Travel coverage must be proven, effective configuration disagreement must be observed, or an arbitrary state path must reverse-resolve to a durable project relation.

## Pass B2 — Knowledge Source and Imported Projection State

### Checkpoint

| Field | Record |
| --- | --- |
| Local question | How do knowledge source files become imported projection state for one abstract project-scoped context, what content-free provenance and freshness facts remain discoverable, and where does the path cease to be reversible or reproducible? |
| Vantage and scope | Read-only source inspection at the pinned revision; one abstract project-scoped knowledge-source-to-projection route. No private state or content was read. |
| Previous checkpoint read | Pass B1's conditional `projects/<name>` namespace, project-local memory path, replaceable runtime cache, durable vector artifacts, and relocation-stability gap. |
| Boundary-crossing delta | Entered configured knowledge roots, source scanning, import ledger, freshness comparison, loader-produced documents, provenance metadata, vector insertion, durable projection, and rebuild branching. Left settings, retrieval, recovery, and live behavior outside. |
| Widening | The predeclared namespace-consumption trigger did **not** fire. The primary import/projection pair was sufficient. |
| Completion state | **Complete** through the first consequential projection-consistency boundary. |

### Source-grounded route

```text
project-scoped memory namespace
-> configured knowledge roots plus project `.a0proj/knowledge`
-> source scan and area assignment
-> absolute-path-keyed import ledger
-> whole-file checksum comparison
-> loader-produced documents with provenance metadata
-> random document IDs and insertion timestamp
-> embeddings, vector index, docstore, and persisted import ledger
```

### Findings

| Relation | Documentary evidence | Finding |
| --- | --- | --- |
| Namespace to knowledge roots | `plugins/_memory/helpers/memory.py:69-94`, `676-689`, `745-752`; `helpers/projects.py:11-16`, `77-86` | A project-scoped memory namespace appends the project's `.a0proj/knowledge` root to configured knowledge roots. Root traversal order is observable; authority or source identity is not added. |
| Roots to scanned areas | `plugins/_memory/helpers/memory.py:307-335`; `plugins/_memory/helpers/knowledge_import.py:48-57`, `98-106` | Root files enter `main`; named area directories are scanned recursively. Admission depends on supported type and visibility conventions. |
| Source to freshness ledger | `plugins/_memory/helpers/knowledge_import.py:17-30`, `128-151`, `196-200`; `plugins/_memory/helpers/memory.py:268-305` | Freshness is whole-file MD5 equality. The durable ledger retains absolute source path, checksum, and projected IDs; transient documents and state are removed before persistence. |
| Source to projected provenance | `plugins/_memory/helpers/knowledge_import.py:149-177`; `plugins/_memory/helpers/memory.py:475-504` | Projected documents carry area, basename, absolute source path, type, knowledge-source flag, random ID, and insertion timestamp. The inspected route leaves `import_timestamp` null. |
| Change to durable projection | `plugins/_memory/helpers/memory.py:283-296`, `445-488`, `547-580` | Changed or removed sources delete prior recorded IDs; changed sources receive new random IDs. Vector persistence, embedding metadata, import ledger, and index hash are separate mutually dependent artifacts. |
| Reload and rebuild | `plugins/_memory/api/knowledge_reindex.py:5-18`; `plugins/_memory/api/import_knowledge.py:8-48`; `plugins/_memory/helpers/memory.py:125-130`, `179-245` | The reindex surface reloads the memory instance. An embedding-model change can rebuild from an intact docstore, but a missing or hash-rejected index can yield a fresh empty projection without forcing unchanged sources to reimport. |

### Forward and reverse resolution

**Verified Current — forward:** source files can be scanned, checksummed, loaded, split, enriched with provenance coordinates, assigned random projected IDs, embedded, and persisted with an import ledger.

**Partially derivable — reverse:** projected metadata can expose a current absolute source coordinate, and a projected ID can be searched in the import ledger. Neither route recovers durable source identity, original bytes, source history, or relocation lineage.

**Not reproducible from the ledger alone:** loader and split versions are not recorded, projected IDs are random, embeddings are model-dependent, and the checksum is not a source copy.

### Consequential consistency boundary

If the vector index is missing or rejected while `knowledge_import.json` survives, initialization can create an empty projection. Byte-identical sources remain `original`, so preload does not reinsert them. The surviving ledger can therefore name projected IDs absent from the new index.

This is a source-grounded control-flow inference, not a live failure reproduction. It disproves the stronger assumption that durable source files plus an import ledger necessarily imply a source-complete rebuild.

### Constraint shadow

- The source pin was supplied to the isolated pass; its worker did not inspect Git state.
- No loader-library internals, private source files, vector contents, settings, or runtime behavior were inspected.
- The inspected hash protects `index.faiss` only; absence of its sidecar or verification exceptions are accepted by the shown path.
- Transactionality, locking, crash consistency, concurrent import, and cross-version serialization remain unknown.
- Storage durability cannot be promoted to deterministic or complete projection reproducibility.
- Backup and Time Travel capture are inherited open questions; no protection implementation was inspected in this pass.

### Parked branches

Effective settings and plugin enablement; retrieval and prompt use; loader-specific chunk stability; concurrency; repair of stale ledger IDs; archive and Time Travel coverage; restore order and recovery authority; relocation and migration.

### Local closure and reopening

**Verified Current:** the current source exposes a content-free path from knowledge roots through freshness and provenance metadata into a durable projection.

**Open:** the projection is coordinate-bound and only partially reversible; cross-artifact consistency and source-complete rebuild are not guaranteed by the inspected route.

Reopen Pass B2 when recovery semantics are examined, ledger invalidation changes, relocation lineage is introduced, loader or embedding versions become provenance, or rebuild behavior is authorized for testing.

## Pass C — Settings, Variables, and Secret References

### Checkpoint

| Field | Record |
| --- | --- |
| Local question | How are ordinary effective settings and non-secret variables resolved for one abstract project-scoped context, how are secret references represented without values, and where does the route first become conditional, mutable, lossy, runtime-only, or dependent on unexported effective composition? |
| Vantage and scope | Read-only inspection of the pinned Agent Zero source. No private settings, environment, variable, secret, chat, memory, provider, or runtime values were read. |
| Previous checkpoint read | Passes A–B2 established the mutable project coordinate, conditional project memory namespace, coordinate-bound knowledge projection, and incomplete reverse resolution. |
| Boundary-crossing delta | Entered global settings resolution, narrow `AgentConfig` projection, task-local prompt snapshots, project-variable persistence, context-sensitive secret-source composition, masked observability, immediate pre-tool unmasking, and extension mutation seams. |
| Widening | Fired once into `initialize.py` because call-site overrides and runtime arguments determine the winning exported agent configuration after ordinary settings resolution. Inspection stopped at the runtime-argument reference. |
| Completion state | **Complete** for the bounded structural question at revision `b1cbd1f960a1a5c4482b324dcff4742aa67b7a51`; instance-specific effective composition remains deliberately unresolved. |

### Source-grounded route

```text
mutable context project coordinate
-> globally cached, persisted, or default ordinary settings
-> normalization and sensitive runtime overlay
-> optional initializer override
-> narrow AgentConfig projection
-> matching runtime-argument overwrite
-> task-local prompt settings snapshot
-> global non-secret prompt variables

global secret storage
+ filtered runtime credential source
+ conditional active-project secret source
-> uppercase-key aliases serialized without values
-> immediate pre-tool replacement in top-level string arguments

all extensible steps
-> dynamically discovered, ordered, cached hooks
-> possible input/result/exception mutation or core-body replacement
```

### Findings

| Relation | Documentary evidence | Finding |
| --- | --- | --- |
| Ordinary setting ownership | `helpers/settings.py:24-54`, `182-186`, `382-390`, `443-485`, `520-524`, `569-619` | The core settings loader is global rather than project-parameterized. It selects process cache, persisted settings, or defaults, then normalizes through version adjustment, unknown-key removal, missing-key fill, type coercion, and invalid-value replacement. Environment entries shape defaults rather than unconditionally overriding valid persisted values. |
| Settings to agent configuration | `initialize.py:7-20`, `84-102` | `initialize_agent` shallow-merges optional explicit overrides, projects selected fields into `AgentConfig`, and then lets matching runtime arguments overwrite projected attributes. The exported configuration is therefore narrower and may differ from the ordinary settings object. |
| Prompt-time stability | `helpers/settings.py:393-418`; `_functions/agent/Agent/prepare_prompt/start/_99_snapshot_settings.py`; paired end hook | Prompt preparation uses a task-local settings snapshot returned by deep copy, with reset on exit and optional reload. This bounds intra-prompt drift but does not export source ownership or value provenance. |
| Project versus prompt variables | `helpers/projects.py:281-308`, `673-683`; `system_prompt/_13_secrets_prompt.py:22-33`; `helpers/settings.py:614` | Project `.a0proj/variables.env` is connected to project editing and persistence. The tracked core prompt reads the global settings object's `variables` field. An exhaustive tracked-Python reference search found no core merge from the project file into that prompt block at the pinned revision. |
| Secret alias grammar | `helpers/secrets.py:17-31`, `256-270`; `prompts/agent.system.secrets.md:1-12` | Secret references use a canonical uppercased key alias. Prompt serialization retains aliases and non-value structure while intentionally omitting values; plain variables are rendered separately as non-sensitive text. |
| Context-sensitive secret sources | `helpers/secrets.py:157-207`, `522-540` | The manager orders global secret storage, filtered runtime credentials, and—when a project is active—the project secret source. Sequential parsing means a later duplicate key wins, making the conditional project source the highest-precedence base source in the inspected manager. |
| Safe observability | `api/settings_get.py:5-9`; `helpers/settings.py:269-349` | The settings endpoint masks credentials, exposes presence rather than values, and returns limited runtime metadata. It is a safety projection, not a provenance-bearing effective-composition export. |
| First secret-value actuation boundary | `tool_execute_before/_10_unmask_secrets.py:5-21`; `helpers/secrets.py:276-295` | Immediately before tool execution, aliases in top-level string arguments are replaced in place through the context-sensitive manager. The observed hook does not recurse through nested non-string structures. |
| Extension composition | `helpers/extension.py:57-103`, `167-209`, `326-351` | Start and end hooks may rewrite arguments, results, or exceptions, skip the core body, or replace its result. Dynamic classes are agent-path-resolved, filename-deduplicated with first occurrence winning, sorted, and cached. Installed effective composition is therefore conditional and mutable. |

### Forward and reverse resolution

**Verified Current — forward:** source establishes ordinary setting selection and normalization, initializer/runtime override order, prompt snapshotting, global prompt-variable use, secret-source order, value-free alias rendering, and immediate pre-tool alias replacement.

**Conditional:** actual winners depend on private cache, persistence, environment-shaped defaults, explicit initializer overrides, runtime arguments, active project, secret-source contents, and dynamically discovered extensions.

**Incomplete reverse resolution:** a projected `AgentConfig`, normalized value, prompt variable, secret alias, or masked API response cannot recover the complete input set, winning source provenance, duplicate history, runtime snapshot, or extension winner that produced it. The alias intentionally identifies a normalized key relation without exposing a value or source.

No inspected public-safe surface joins project selection, ordinary-setting provenance, project-variable status, secret-source winner, runtime overrides, prompt snapshot identity, and extension composition into one effective record.

### Selection, enforcement, and actuation boundary

This pass distinguishes three relations without collapsing them:

1. settings, variables, source order, and extension precedence **select or transform** inputs;
2. masked settings and prompt aliases **project** a deliberately incomplete view;
3. pre-tool alias replacement crosses from a public-safe reference into execution-bearing value state.

None of those relations establishes that the resulting tool call is authorized. Precedence is not authority, masking is not enforcement, and successful replacement is not permission to actuate.

### Constraint shadow

- Source causality was inspected; no running instance's effective values were observed.
- Normalization is lossy: unknown, invalid, missing, and type-coerced input history is not recoverable from the normalized result.
- Project variables may be consumed by an uninspected installed extension even though tracked core does not merge them into the prompt variable block.
- Secret aliases and masked exports intentionally suppress winning-source and value provenance.
- Dynamic user, project, profile, or plugin extensions can alter effective results; their installed bodies and cache membership were outside scope.
- The prompt snapshot provides bounded temporal consistency, not durable provenance, identity, or cross-process agreement.
- Nested secret replacement, provider configuration, project MCP composition, settings write side effects, and cross-node consistency remain unexamined.

### Parked branches

Runtime argument parsing and values; installed extension bodies and cache membership; model-provider resolution; project-scoped MCP composition; settings write/apply side effects; intent of project `variables.env`; a public-safe effective-composition exporter; nested secret replacement; and cross-process or cross-node settings consistency.

### Local closure and reopening

**Verified Current:** current source exposes the algorithms, precedence structure, alias grammar, masking behavior, prompt snapshot, and first value-actuation seam described above.

**Open:** actual instance winners and full post-extension composition are not derivable from public source alone, and no inspected public-safe effective-composition record joins their provenance.

Reopen Pass C when the source revision changes, project variables gain a core prompt consumer, settings become project-aware, initializer/runtime precedence changes, secret-source or alias semantics change, nested unmasking changes, extensions gain an effective-composition manifest, or authorized runtime evidence contradicts the source-derived route.

## Pass D1 — Profile and Skill Resolution

### Checkpoint

| Field | Record |
| --- | --- |
| Local question | How does a persisted or selected profile become an effective prompt and skill-resolution scope, which candidate wins when names collide, and what continuity or trust facts remain unavailable from the resolved result? |
| Vantage and scope | Read-only source inspection at the pinned revision; one abstract project-scoped agent, its selected profile, profile-composed prompt roots, and skill discovery/load path. No installed private skill bodies, prompt contents, chat contents, or live effective values were read. |
| Previous checkpoint read | Pass C's mutable project coordinate, narrow runtime configuration, extension-mutability seam, and absence of a public-safe effective-composition record. |
| Boundary-crossing delta | Entered profile availability/reconciliation, ordered profile resource roots, skill-root discovery, name/path resolution, visibility and active-skill policy, and history-borne skill loading. Tool and plugin registration remain for Pass D2. |
| Widening | The predeclared adjacent-capability-root trigger fired laterally: profile interpretation required the ordered resource roots that also expose prompts, skills, tools, and extensions. D1 inspected only prompt and skill consequences; tool/capability registration was parked for D2. |
| Completion state | **Complete** for the bounded source question at revision `b1cbd1f960a1a5c4482b324dcff4742aa67b7a51`; installed effective composition and behavioral trust remain unresolved. |

### Source-grounded route

```text
persisted or selected profile name
-> currently enabled profile catalog for active project
-> reconciliation or fallback when unavailable
-> ordered project/profile/user/plugin/default resource roots
-> prompt lookup and profile settings overlay
-> ordered skill roots
-> discoverable skill metadata
-> scope/chat visibility and activation entries
-> first matching name or explicit visible path
-> skill body injected into visible chat history
```

### Findings

| Relation | Documentary evidence | Finding |
| --- | --- | --- |
| Profile availability and fallback | `helpers/projects.py:402-419`, `448-465`; `helpers/subagents.py:314-332` | A context's profile name is accepted only while currently available and enabled for the active project. Project activation can reconcile an unavailable profile to the current global/default choice or another available profile and persist that mutation. Operability is preserved, but original behavioral closure is not. |
| Profile resource precedence | `helpers/subagents.py:335-428` | Resource roots are ordered from project-profile and project scope through user profile, enabled plugin profile, bundled profile, user-wide, enabled plugins, and default. The ordered path list is cached. Earlier matches can shadow later resources, but the resolved file does not carry a complete provenance or shadowed-alternative record. |
| Profile metadata composition | `helpers/subagents.py:180-254`, `257-307` | Profile definitions from bundled, plugin, user, and project roots can be merged by name. Later roots override set metadata and same-named prompt entries while origin labels accumulate. This exposes ancestry categories, not exact content identity or compatibility. |
| Prompt and profile-settings projection | `agent.py:686-714`; `extensions/python/agent_init/_15_load_profile_settings.py:6-45` | Prompt lookup uses the ordered profile resource roots. Profile settings overlays are applied in root order through dictionary update and can reconstruct agent configuration while retaining the current profile or MCP value unless explicitly overridden. Installed extensions can still alter this route. |
| Skill root and name precedence | `helpers/skills.py:71-101`, `108-129`, `372-402`, `1477-1536`; `helpers/subagents.py:335-428` | For an agent, skill roots inherit the same ordered profile/project/plugin hierarchy. Discovery recursively scans visible roots; duplicate normalized names are deduplicated with the earliest root winning. Explicit path entries must remain inside a visible root; name entries select the first match. |
| Skill visibility and activation | `helpers/skills.py:666-735`, `851-971`, `1406-1452` | Plugin configuration supplies limits, scope-active entries, hidden entries, and visibility policy; chat state can add, disable, or re-expose entries. Scope entries precede chat entries, limits truncate the merged list, and policy can remove discoverable skills. Selection is conditional and mutable rather than a trust judgment. |
| Skill loading and durable trace | `tools/skills_tool.py:188-249`; `helpers/skills.py:974-1006`; `extensions/python/message_loop_prompts_after/_65_include_loaded_skills.py:24-69` | Loading resolves a visible skill, injects its full body into visible chat history with source metadata, and records its name in context data. Missing bodies can be reattached later from the currently winning skill of that name. The history preserves text and some metadata, but name-based reattachment can bind to changed content after replacement or shadowing. |

### Forward and reverse resolution

**Verified Current — forward:** given the active project, selected profile, enabled roots, plugin policy, chat skill state, and current files, source can derive ordered prompt/skill candidates and select a winning profile resource or skill.

**Conditional:** reconciliation, root enablement, cache state, duplicate names, project activation, profile overlays, visibility policy, active/hidden entries, and extensions can all change the effective result.

**Incomplete reverse resolution:** a generated prompt fragment, loaded skill name, or current profile name cannot recover the full ordered candidate set, shadowed alternatives, exact source bytes, version, compatibility decision, policy snapshot, or the historical winner used in an earlier turn. A loaded skill body in chat is stronger evidence of prior supplied instructions than its name alone, but it does not establish authorization, correct application, or current compatibility.

### Selection, trust, and inheritance boundary

Profile and skill machinery selects and supplies behavioral material; it does not establish that the material is trusted, authorized for the present consequence class, semantically compatible with the current engine, or entitled to widen tool access. Project/profile scope can shadow or merge resources, while chat-carried skill instructions persist as participant history. These are distinct inheritance modes with different replacement and revocation behavior.

### Constraint shadow

- No private project/profile skill or prompt body, live cache membership, or generated prompt was inspected.
- Filesystem position and first-match precedence do not establish authorship, integrity, compatibility, or authority.
- Profile origin labels are category-level and do not version the merged definition or prompt closure.
- Visibility, activation, loading, and tool permission are separate relations; a visible or loaded skill is not an executable capability grant.
- Loaded skill text can remain in chat history after later hiding or source removal; the inspected path explicitly treats history bodies as non-removable.
- Cached resource paths and current-source reattachment can diverge from the historical source that produced an earlier turn.

### Parked branches

Plugin enablement and registration; tool discovery and policy; extension ordering and code trust; MCP capability resolution; profile/skill revocation semantics for already-loaded history; compatibility manifests; signed provenance; runtime cache invalidation; and behavioral tests of skill application.

### Local closure and reopening

**Verified Current:** current source exposes a project/profile-aware resource hierarchy and deterministic first-match skill resolution under current files and policy, plus a history-borne skill-loading path.

**Open:** the resolved result is not a provenance-complete or trust-bearing capability closure. Historical reconstruction can fail when profiles, roots, policy, or same-named skill bodies change.

Reopen Pass D1 if profile merging, root order, skill deduplication, visibility/activation policy, history reattachment, or project-profile reconciliation changes; or if a capability manifest begins exporting exact winners, shadowed alternatives, integrity, compatibility, and revocation state.

## Pass D2 — Plugin, Extension, Tool, and Capability Registration

### Checkpoint

| Field | Record |
| --- | --- |
| Local question | How do present plugin, extension, local-tool, and MCP registrations become an effective capability surface; which mechanisms merely select or advertise capability; and where is execution structurally constrained? |
| Vantage and scope | Read-only source inspection at the pinned revision; registration, enablement, discovery, prompt/schema projection, tool policy, and first enforcement seam. No private plugin configuration, MCP servers, tool arguments, or live execution was inspected. |
| Previous checkpoint read | Pass D1 established project/profile-aware resource roots, first-match skill resolution, history-borne skill loading, and the unresolved distinction among visibility, trust, and executable authority. |
| Boundary-crossing delta | Entered plugin roots and toggles, scoped plugin configuration, extension discovery and mutation, local and MCP tool catalogs, canonical tool identity, prompt/schema projection, and pre-execution policy enforcement. Scheduler and continuing obligations remain for Pass E1. |
| Widening | The predeclared combined trigger fired: registration alone could not establish effective capability presence. The pass crossed once into scoped tool-policy filtering and the pre-tool enforcement hook; lifecycle and behavioral execution remain parked. |
| Completion state | **Complete** for the bounded source question at revision `b1cbd1f960a1a5c4482b324dcff4742aa67b7a51`; instance winners, code integrity, and behavioral capability trust remain unresolved. |

### Source-grounded route

```text
user and bundled plugin roots
-> name-deduplicated plugin catalog
-> global/project/profile toggle composition
-> scoped config or default config plus plugin hook
-> project/profile-aware extension, prompt, and tool roots
-> first-match local implementation plus MCP-discovered tools
-> canonical tool identifier and generated model-facing schema
-> scoped allow/block/default policy
-> prompt filtering and immediate pre-execution enforcement
```

### Findings

| Relation | Documentary evidence | Finding |
| --- | --- | --- |
| Plugin discovery and shadowing | `helpers/plugins.py:225-260`, `270-341` | User and bundled plugin roots are searched with user roots first; plugin names deduplicate, so a same-named user plugin shadows the bundled plugin. Metadata can report version and, for custom Git repositories, current commit details, but registration does not validate compatibility or code trust. |
| Effective enablement | `helpers/plugins.py:437-524`, `527-535`, `556-596` | Plugins are enabled by default unless layered toggle files change state; always-enabled plugins cannot be disabled through the normal toggle path. Project/profile paths participate ahead of root paths, and results are cached. Enabled presence is a scoped selection fact, not authorization for every capability supplied by that plugin. |
| Scoped plugin configuration | `helpers/plugins.py:599-654`, `707-829`, `892-920` | The first matching project-profile, project, user-profile, plugin-profile, user-plugin, or bundled config wins; default config is used otherwise. A plugin hook can transform the standard result. Effective configuration therefore depends on current roots, caller context, hooks, and caches and is not exported as a provenance-complete record. |
| Extension composition | `helpers/extension.py:56-103`, `145-214`, `326-351`; `helpers/subagents.py:335-428` | Explicit and implicit extension points can mutate arguments, results, and exceptions or bypass the wrapped body. Classes are discovered through ordered agent resource roots, deduplicated by extension filename with the first occurrence winning, then sorted by filename. This is executable composition, not merely metadata registration. |
| Local and MCP capability discovery | `helpers/tool_policy.py:64-138`, `146-194`, `280-355`; `helpers/mcp_handler.py:874`, `1142-1247` | Local tools derive from first-occurring filenames in ordered resource roots; MCP tools derive from per-agent server state. Canonical IDs distinguish local/plugin/MCP origins for policy, while unavailable policy references may remain catalogued. Discovery and canonical naming still do not establish semantic compatibility or authority. |
| Model-facing tool projection | `helpers/responses_tools.py:216-244`, `275-290`, `318-373` | Tool prompts and MCP definitions are projected into model-facing declarations. Local schemas may come from embedded prompt JSON, bundled parameter metadata, or permissive inference; a custom implementation shadows the bundled contract. The advertised schema can therefore be looser than executable behavior or become mismatched with a shadowing implementation. |
| Selection versus enforcement | `helpers/tool_policy.py:40-61`, `161-209`, `212-250`; `plugins/_tool_access/extensions/python/tool_execute_before/_10_enforce_tool_policy.py:1-9`; `helpers/mcp_handler.py:438-445` | Custom scoped policy can allow, block, or default local and MCP tools. Policy filters model-visible prompts and is checked again immediately before local tool execution; MCP execution also calls the policy guard. This is a structural enforcement seam, unlike skill visibility or prompt omission, though two non-configurable tools remain framework/runtime invariants. |
| Change and cache lifecycle | `helpers/plugins.py:122-223`, `447-475`; `helpers/extension.py:326-351` | Watchdogs clear plugin, extension, and API caches and may purge Python namespaces after observed changes. Cached effective composition can persist until invalidation, and source inspection alone does not prove that every mutation path triggers the required refresh. |

### Forward and reverse resolution

**Verified Current — forward:** under current roots, toggles, scoped configuration, extension files, MCP state, and tool policy, source can derive a model-visible tool surface and enforce allow/block decisions at the local and MCP execution seams inspected.

**Conditional:** enabled plugins, first-match code, hook transformation, extension filename collisions, MCP connectivity, prompt/schema extraction, caches, and scoped policy all affect the effective capability set.

**Incomplete reverse resolution:** a visible tool declaration, canonical ID, successful policy decision, or executed tool name cannot recover the exact implementation bytes, plugin commit, extension chain, configuration winner, schema derivation route, cache generation, MCP server identity, or authorization rationale that produced it.

### Capability-trust and enforcement boundary

This pass establishes a real distinction: discovery, prompt inclusion, schema generation, plugin enablement, and skill loading are selection or projection; `ensure_tool_allowed` at execution is enforcement within its configured policy domain. However, policy answers only whether a canonical tool ID is allowed under current configuration. It does not establish code provenance, compatibility, behavioral correctness, least privilege inside the tool, downstream authorization, or safe consequences.

### Constraint shadow

- No private/custom plugin code, scoped config value, MCP endpoint, or live tool call was inspected.
- User plugin shadowing can replace bundled behavior under the same plugin name; metadata is not an integrity or compatibility proof.
- A permissive or inherited policy permits by default; enforcement existence does not imply restrictive policy.
- Extension code can alter policy-adjacent and execution-adjacent paths; its exact installed chain remains outside the public-safe closure.
- Prompt filtering reduces model-visible affordances but is not the enforcement boundary.
- Tool-level permission does not constrain argument scope, target identity, external side effects, or authority exercised behind the tool.
- Cache invalidation and module refresh were source-inspected but not behaviorally exercised.

### Parked branches

Tool argument and target authorization; plugin installation/scanning trust; signature or digest verification; MCP server custody and transport trust; extension sandboxing and revocation; provider-native tool transport; live policy behavior; cache invalidation tests; and post-success side-effect observation.

### Local closure and reopening

**Verified Current:** current source has project/profile-aware capability selection plus a distinct tool-policy enforcement seam for local and MCP execution.

**Open:** effective capability closure remains unexported and only partially attributable. Capability trust requires provenance, compatibility, lifecycle, failure-isolation, revocation, argument-scope, and consequence evidence beyond registration and allow/block state.

Reopen Pass D2 if plugin roots, toggle/config precedence, extension deduplication, tool canonicalization, schema derivation, MCP resolution, policy defaults, or enforcement hook placement changes; or if an effective-composition/trust record makes exact winners and revocation state publicly inspectable.

## Pass E1 — Scheduler and Persisted Context/Project References

### Checkpoint

| Field | Record |
| --- | --- |
| Local question | How does a persisted scheduler obligation retain and re-enter a context and project, and what must survive for that obligation to remain interpretable and runnable after process or runtime replacement? |
| Vantage and scope | Read-only source inspection at the pinned revision; scheduler task model, persistence, due-state evaluation, context reconstruction, project activation, and chat persistence. No saved task contents, attachments, project state, or live task execution were inspected. |
| Previous checkpoint read | Pass D2 established conditional capability composition and a distinct but limited pre-execution tool-policy seam; Pass A established chat-scoped project/profile continuity and the absence of durable background-context persistence. |
| Boundary-crossing delta | Entered durable scheduler obligations, their context/project coordinates, lifecycle state, context reconstruction, and chat persistence. Crossed laterally into recoverable chat state because obligation continuity cannot be classified from `tasks.json` alone. |
| Widening | The predeclared lateral trigger fired. Scheduler state and chat state were recorded separately, then related only at the reconstruction boundary. Provider response-state continuity remains for Pass E2. |
| Completion state | **Complete** for the bounded source question at revision `b1cbd1f960a1a5c4482b324dcff4742aa67b7a51`; restart behavior and instance-specific task records remain unverified. |

### Source-grounded route

```text
usr/scheduler/tasks.json
-> typed task with UUID, context ID, schedule/plan, prompts, attachments, and project name
-> due-state or explicit-run selection
-> existing in-process context lookup
   OR new context initialized with current defaults
-> optional activation of persisted project name
-> scheduler prompt appended to selected/reconstructed context
-> chat persisted before and after execution
-> task state/result persisted separately
```

### Findings

| Relation | Documentary evidence | Finding |
| --- | --- | --- |
| Obligation persistence | `helpers/task_scheduler.py:29`, `162-180`, `521-589`, `1174-1278` | Scheduler obligations persist installation-globally in `usr/scheduler/tasks.json`. The record carries UUID, context ID, task type and timing, system/user prompts, attachment coordinates, project name/color, lifecycle timestamps, last result, and type-specific state. It does not carry a profile closure, effective settings, capabilities, secret winners, or provider continuation state. |
| Dedicated versus shared context | `helpers/task_scheduler.py:177-180`, `229-230`, `1174-1199` | A missing context ID defaults to the task UUID; equality marks a dedicated context. A different supplied context ID binds the obligation to a shared chat coordinate. This classification is persisted and derivable, but it does not prove that the referenced chat exists or is semantically compatible. |
| Temporal interpretation | `helpers/task_scheduler.py:33-71`, `91-159`, `330-417`, `420-501` | Scheduled tasks normalize a named timezone and evaluate cron windows; planned tasks persist todo, in-progress, and done times. Local/user aliases are resolved through current localization, so a symbolic local timezone can acquire changed meaning after migration or user-setting change. |
| Context reconstruction | `helpers/task_scheduler.py:822-858` | The scheduler first uses an in-process context with the stored ID. If absent, it creates a new context from current `initialize_agent()` defaults, then optionally activates the stored project name and saves a chat record. A missing shared context therefore does not halt reconstruction; it can become a fresh context under the old coordinate. |
| Project relation | `helpers/task_scheduler.py:162-180`, `822-838`; `helpers/projects.py:448-487` | Project linkage is a persisted mutable name. Reconstruction activates the currently resolved project and reconciles profile availability under current rules. The task record does not preserve project identity, revision, profile, or the effective formation present when the obligation was created. |
| Execution and dual persistence | `helpers/task_scheduler.py:865-1015` | Each run appends the scheduler prompt and task-specific system message to the context, persists chat before and after `agent.monologue()`, and updates task lifecycle/result state separately. There is no inspected transaction joining chat mutation and scheduler-state mutation, so interruption can leave their records at different lifecycle points. |
| Recovery-oriented state repair | `helpers/task_scheduler.py:966-1009` | After apparent success or failure, the scheduler reloads persisted task state and repairs an unexpected lifecycle marker; final cleanup attempts another save. This improves local state convergence but does not independently verify external effects, semantic completion, or exactly-once execution. |

### Forward and reverse resolution

**Verified Current — forward:** a persisted task can be deserialized, evaluated for due state, associated with a context coordinate, and run in an existing or newly constructed current context with optional current project activation.

**Conditional:** interpretation depends on current timezone/localization, project availability, profile reconciliation, initializer settings, capabilities, attachment reachability, chat presence, and current source behavior.

**Partially derivable — reverse:** a task can be found by UUID, name, or context ID, and a chat snapshot can identify a task context when the task UUID and context ID coincide. A context does not durably enumerate all obligations that may target it without scanning scheduler state, and the task cannot reconstruct the historical effective formation that created it.

### Continuing-obligation boundary

The scheduler preserves an instruction and launch relation, not a closed future executor. Its durability can outlive the configuration, authority, profile, project interpretation, capability set, secret sources, provider state, and external conditions under which it was authored. Re-entering the same context ID or project name therefore establishes coordinate continuity only; it does not establish renewed authority or semantic continuity.

### Constraint shadow

- No task records or live scheduler behavior were inspected; findings are source-derived.
- The JSON write path was inspected, but filesystem atomicity, multi-process exclusion, crash consistency, and backup coverage were not proven.
- A reconstructed missing shared context can silently lose prior chat/profile state while retaining the old context coordinate.
- Task prompts and attachment coordinates can become stale, unavailable, or newly unsafe; persistence does not revalidate them.
- State repair after execution is not exactly-once delivery, idempotency, downstream verification, or rollback.
- Scheduler state is installation-global and only name-linked to a project; project relocation, rename, removal, or semantic replacement remains fragile.

### Parked branches

Task creation/update API authorization; attachment custody; concurrent schedulers; missed-run policy; exactly-once semantics; archive and Time Travel coverage; external side-effect verification; project rename/migration; live restart tests; and provider continuation state.

### Local closure and reopening

**Verified Current:** Agent Zero persists continuing obligations separately from chat state and can reconstruct a runnable current context from stored task and project coordinates.

**Open:** the obligation does not preserve or attest the historical effective formation, renewed authority, exactly-once semantics, or a transactionally closed recovery unit. Future execution must be re-grounded against current target, authority, configuration, and recovery conditions.

Reopen Pass E1 if task persistence, context reconstruction, timezone interpretation, project activation, chat persistence, lifecycle repair, or archive coverage changes; or if behavioral restart evidence contradicts the source-derived route.

## Pass E2 — Task, Background, and Provider-State Relations

### Checkpoint

| Field | Record |
| --- | --- |
| Local question | How do task and background contexts differ in durable continuity, and how does provider-managed response state interact with local history when a context continues, is reconstructed, changes model, loses remote state, or is removed? |
| Vantage and scope | Read-only source inspection at the pinned revision; context types, chat serialization, native Responses state, local-history projection, fallback, and provider-state cleanup. No provider account, response body, live context, private history, or actual restart was inspected. |
| Previous checkpoint read | Pass E1 established that scheduler obligations and chat state persist separately, and that a missing context may be reconstructed under the old coordinate from current defaults. |
| Boundary-crossing delta | Entered context-type persistence and provider/local response-state continuity. Crossed once into the local-history fallback relation because durability differs through the combined lifecycle of persisted agent state, message metadata, provider storage, and reconstructed prompts. |
| Widening | The predeclared combined trigger fired. Task/background persistence cannot be interpreted independently of provider-state fallback and locally retained history. No external provider behavior or live deletion was inspected. |
| Completion state | **Complete** for the bounded source question at revision `b1cbd1f960a1a5c4482b324dcff4742aa67b7a51`; provider behavior and restart semantics remain unverified. |

### Source-grounded route

```text
context type: user | task | background
-> user/task chat serialization; background intentionally omitted
-> agent data plus history and per-message response metadata
-> model-key-matched provider response state
-> provider continuation by previous response ID
   OR local Responses projection from retained native history
   OR Chat Completions fallback
-> provider response cleanup when persisted chat is removed, unless disabled
```

### Findings

| Relation | Documentary evidence | Finding |
| --- | --- | --- |
| Context lifecycle classes | `agent.py:50-110`, `168-175`, `237-295`; `helpers/persist_chat.py:50-92` | User, task, and background contexts share the in-process registry and execution machinery. User and task contexts are serializable; background contexts are intentionally skipped by bulk and per-context chat persistence. Process replacement therefore erases background continuity unless another owner captures its output or obligation. |
| Background construction | `helpers/parallel_tools.py:514-550`; `helpers/fasta2a_server.py:94-116`; `helpers/mcp_server.py:139-167` | Parallel direct-tool, A2A, and new MCP work can create temporary background contexts from current configuration and optionally copy or activate a project coordinate. Their parent/project relations are operational conveniences, not durable child lineage. |
| Local persistence of provider coordinates | `agent.py:774-794`, `1023-1076`; `helpers/llm_result.py:52-115`, `211-268`; `helpers/persist_chat.py:179-232`, `250-323` | A successful native response stores response IDs, prior ID, provider-model key, history sequence, and accumulated response IDs in non-private agent data; response metadata is also attached to serialized history messages. These records preserve continuation coordinates and native items, not the provider-held response object or a guarantee that it remains available. |
| Provider-state eligibility | `agent.py:930-1000`, `1023-1054`; `helpers/litellm_transport.py:855-893` | Provider continuation is used only when saved state has a response ID and its provider-model key matches the current model. New local history since the saved sequence is sent alongside the prior response coordinate. A model change makes the saved provider state ineligible even if the local chat remains. |
| Local and transport fallback | `helpers/litellm_transport.py:80-172`, `402-461`, `1478-1515`, `2023-2042`; `helpers/responses_history.py:14-62`, `98-145` | Unsupported provider storage can fall back to local Responses state, and unsupported Responses transport can fall back to Chat Completions before output begins. Local reconstruction projects prepared history conservatively and retains native groups only when prefix affinity, tool-call structure, and secret checks qualify. Continuity can remain usable while changing transport and state semantics. |
| Completion boundary | `agent.py:1235-1243`, `1420-1426`; `helpers/history.py:736-755` | A loop-breaking response clears active prior-response coordinates while retaining accumulated IDs and history. This prevents a later turn from treating a completed chain as pending provider state, but it does not delete the provider-held objects. |
| Deletion and custody | `helpers/persist_chat.py:162-168`, `390-454`; `helpers/litellm_transport.py:1440-1461` | Removing a persisted chat collects locally known response IDs and attempts provider deletion unless deletion is disabled. Local chat custody and provider object custody are therefore coupled by best-effort coordinates; a failed or incomplete remote deletion is not repaired by the inspected path. |
| Scheduler reconstruction interaction | `helpers/task_scheduler.py:822-858`; `helpers/persist_chat.py:250-323` | When a scheduler finds no loaded context, it creates a current-default context rather than first deserializing a stored chat in the inspected route. Unless prior chat state was already loaded into the process, that reconstructed context begins without historical agent data, message metadata, or provider continuation state despite retaining the scheduler's context ID. |

### Forward and reverse resolution

**Verified Current — forward:** user and task contexts can persist local history plus provider continuation coordinates; eligible same-model turns may continue provider state, while local Responses or Chat Completions can reconstruct from retained local history under their respective admission rules.

**Conditional:** continuity depends on context type, successful chat persistence/load, current model identity, provider object availability, transport support, intact message metadata, qualifying local-history projection, project/profile reconstruction, and current extensions.

**Incomplete reverse resolution:** response IDs and metadata do not recover provider-held state, retention policy, exact prior request, deleted objects, current availability, or the effective formation that authored the turn. A provider object likewise does not enumerate the complete local context, project, scheduler obligation, or authority relation that gave it meaning.

### Lifecycle and inheritance boundary

The durable unit is not simply “the chat” or “the provider response.” Continuation spans at least local context serialization, agent history, provider-state coordinates, current model affinity, and transport fallback behavior. Task contexts may carry that relation durably; background contexts intentionally do not. Scheduler persistence can preserve an obligation after its corresponding local/provider conversational closure has disappeared.

This establishes an inheritance limit: continuing the same coordinate can inherit text and native response items, but it does not automatically inherit the prior formation's authority, effective capabilities, provider custody, or semantic state.

### Constraint shadow

- No provider-side retention, deletion, response lookup, outage, or compatibility behavior was observed.
- Local fallback can preserve conversational utility while changing token use, tool representation, cache behavior, reasoning custody, and provider-state semantics.
- Process-local unsupported-capability caches are not durable evidence about later provider behavior.
- Background work can affect external state even though its context is not persisted; ephemerality is not consequence containment.
- Best-effort deletion based on locally known IDs cannot prove complete erasure across provider logs, derived state, or IDs not retained locally.
- The scheduler reconstruction finding is source-specific and does not prove how startup ordering populates contexts in every deployed process.

### Parked branches

Provider retention and deletion contracts; encrypted reasoning custody; exact startup ordering; background-result custody; interrupted parallel jobs; provider/model migration; task cancellation effects; attachment lifecycle; external side-effect idempotency; and live restart/fallback tests.

### Local closure and reopening

**Verified Current:** context type materially changes durability, and native model continuity is a composite local/provider relation with explicit model affinity and fallback paths.

**Open:** the current system does not export a single continuity record joining obligation, local history, provider state, effective formation, authority renewal, cleanup status, and recovery evidence. Coordinate continuity remains weaker than semantic or authorized continuity.

Reopen Pass E2 if chat serialization, background persistence, response metadata, provider-state selection, transport fallback, completion clearing, scheduler reconstruction, or provider deletion changes; or if live provider/restart evidence contradicts the source-derived relation.

## Pass F — Dependency-Closure Synthesis

### Checkpoint

| Field | Record |
| --- | --- |
| Local question | What minimum dependency closure must be observable to interpret one persisted context without mistaking mutable coordinates, selected inputs, provider state, or discovered capabilities for continuity, authority, or recovery? |
| Vantage and scope | Synthesis of completed Passes A through E2 only. No new source, private state, runtime, provider, or external boundary was inspected. |
| Previous checkpoint read | All bounded passes, their forward paths, reverse-resolution limits, constraint shadows, and reopening conditions. |
| Boundary-crossing delta | No new dependency class entered. This pass joins the completed local findings and tests whether they are sufficient to order a first safe build slice. |
| Widening | None permitted. |
| Completion state | **Complete** as a documentary synthesis at revision `b1cbd1f960a1a5c4482b324dcff4742aa67b7a51`. |

### Minimum closure

```text
persisted context coordinate and serialized participant history
├─ mutable project selector
│  ├─ current project metadata and instruction roots
│  ├─ effective memory-isolation branch
│  │  └─ project-local or shared memory namespace and physical store
│  ├─ knowledge source roots
│  │  └─ freshness ledger, projection artifacts, and rebuild branch
│  ├─ project variable and secret-reference sources
│  └─ project-scoped profile, skill, plugin, extension, and tool roots
├─ selected profile
│  ├─ current availability and fallback reconciliation
│  ├─ ordered prompt and skill roots
│  └─ profile settings and capability roots
├─ effective composition
│  ├─ global settings, normalization, initializer overrides, and runtime arguments
│  ├─ prompt-time settings snapshot and non-secret variables
│  ├─ secret aliases and context-sensitive winning value sources
│  └─ extension transformations and caches
├─ effective capability surface
│  ├─ plugin enablement and scoped configuration
│  ├─ first-match extensions and local/MCP tools
│  ├─ model-visible schemas and prompts
│  └─ tool-policy selection and execution-time enforcement seam
├─ continuing obligations
│  ├─ scheduler records, temporal interpretation, and attachment coordinates
│  ├─ existing or reconstructed current context
│  └─ separately persisted task and chat lifecycle state
└─ conversational and external continuation
   ├─ local history and native response metadata
   ├─ model-affine provider response coordinates
   ├─ local Responses or Chat Completions fallback
   ├─ intentionally ephemeral background contexts
   └─ unproven provider custody, external effects, and recovery material
```

This is a dependency closure for interpretation, not a manifest or identity model. A context is not closed by any single root, chat file, provider response, project name, memory directory, scheduler record, or generated prompt. Its effective meaning arises from currently resolved relations across these classes.

### Resolution classification

| Class | Forward relation | Reverse or continuity limit | Consequence |
| --- | --- | --- | --- |
| Context and project | **Verified Current** from persisted context to current named project | No relocation-stable identity or project-to-all-context reverse index | Names and paths may be reported only as mutable coordinates. |
| Memory namespace | **Verified Current, conditional** once scoped `_memory` configuration is known | Project name alone cannot determine isolation; path does not recover original relation | Inspection must report the branch and its winning source or mark it unknown. |
| Knowledge projection | **Verified Current** through scan, checksum ledger, projection, and persisted artifacts | Ledger and projection do not preserve authoritative source bytes, loader/version closure, or guaranteed rebuild consistency | Source, ledger, projection, and retrieval state must remain separate evidence classes. |
| Settings and secrets | **Verified Current structurally** through precedence, masking, and first value-actuation seam | No public-safe export joins actual winners, overrides, secret provenance, snapshots, and extension mutations | A first slice may expose sources and unknowns, never secret values or authority claims. |
| Profiles and skills | **Verified Current structurally** through ordered roots, reconciliation, discovery, and history-borne loading | Names and rendered text do not recover exact historical winners, shadowed alternatives, trust, or revocation | Profile/skill presence is behavioral input, not capability authority. |
| Plugins and tools | **Verified Current structurally** through registration, projection, policy, and execution guard | Implementation provenance, compatibility, argument scope, downstream authority, and consequences remain unresolved | Inventory and policy state may be observed; actuation remains out of scope. |
| Scheduler obligations | **Verified Current structurally** through persistence, due selection, context reconstruction, and dual state updates | Obligation cannot reconstruct historical effective formation or exactly-once semantics | Every future actuation requires current re-grounding rather than inherited authority. |
| Provider and background state | **Verified Current structurally** for local persistence, model affinity, fallback, and intentional background ephemerality | Provider custody, remote retention, full deletion, external effects, and background recovery are unproven | Continuation coordinates must not be treated as semantic continuity or consequence containment. |

### First safe build slice now orderable

The completed closure is sufficient to order a first build slice whose sole function is a **public-safe effective-formation observation surface**. Its initial scope can be limited to one selected context and may report:

1. the mutable context, project, and profile coordinates used for resolution;
2. candidate source classes and the winners that can be identified without reading protected values;
3. shadowed alternatives, conditional branches, caches, and runtime-only dependencies where structurally discoverable;
4. memory and knowledge source/projection roles without exposing participant content;
5. capability registrations, model-visible declarations, and the distinct execution-policy decision where available;
6. scheduler and provider/background dependencies as external or continuing relations rather than local closure;
7. evidence anchors, unknowns, observation time, source revision, and explicit non-authority.

It must not mint identity, choose desired state, expose secrets or private content, authorize tools, mutate configuration, claim recovery, infer semantic continuity from coordinates, or become the sole input to consequential actuation.

### Acceptance boundary for that slice

The slice is acceptable only when, for a bounded sanitized fixture or authorized content-free context:

- every reported relation identifies its evidence class and observation vantage;
- current winners and unresolved candidates are distinguished rather than collapsed;
- names, paths, hashes, IDs, and provider coordinates are labeled as coordinates or sameness evidence, not identity or trust;
- selection, projection, enforcement, and authority are reported separately;
- secret values and participant content are absent while source classes and presence may remain observable;
- unavailable, dynamic, or extension-controlled composition is surfaced as unknown rather than silently omitted;
- the report is read-only, non-canonical, time-bounded, source-revisioned, and independently disposable;
- removal of the observer does not alter the observed formation;
- post-success review confirms that the surface did not enlarge tool reach, policy authority, private disclosure, or blast radius.

### What remains blocking for stronger slices

The closure does **not** authorize or substantiate runtime identity, relocation-stable continuity, profile/capability trust, behavioral memory quality, actuation tiers, external ingress, lifecycle mutation, portable recovery, readiness, or parity. Those require some combination of design decision, implementation, authorized behavioral observation, external-boundary evidence, and recovery exercise.

### Local closure and reopening

**Locally closed:** the minimum dependency classes, their principal forward routes, their reverse-resolution limits, and the boundary of a first safe observational build slice are sufficiently explicit for construction ordering.

**Still open by design:** instance-specific effective winners, relocation-stable continuity, behavioral memory semantics, trust and authority, external boundaries, recovery, and readiness remain outside documentary closure.

Reopen Pass F if any earlier pass reopens materially, if the observer design requires a dependency not represented here, if a live comparison exposes a missing class, or if the proposed surface cannot remain read-only and non-authoritative.

## Pass Completion

**Complete.** The retrospective meta-pass is recorded in [Chapter 2 Inquiry Calibration](chapter-2-inquiry-calibration.md). The resulting disposition of the wider understanding table and construction order is recorded in [Chapter 2 Understanding Disposition](chapter-2-understanding-disposition.md).

## Constraint Shadow

- No chat, history, memory, knowledge, setting, or secret content was read.
- No live context was selected as representative; findings describe source-supported relations only.
- Persistence placement does not prove semantic equivalence after replacement.
- Current names and paths are observed application coordinates, not proposed formation identity or architecture.
- Backup and Time Travel statements inherit the bounded findings of the continuity-state observation; no archive or restore was inspected here.

## Current Stopping and Reopening Condition

Pass A stops because its path, persistence behavior, reverse-resolution limit, and relocation failure are source-established. Reopen it if context serialization, project selection, profile reconciliation, chat storage, or project path derivation changes, or if a later pass establishes an alias, provenance, or effective-composition relation that repairs one of its failure boundaries.

Passes B1 through E2 retain their local reopening conditions above. The larger context-dependency inquiry is locally closed because all declared classes and the final synthesis are complete. Reopen it when a pass-specific condition fires, the first observer reveals a missing dependency class, or later behavioral, external, or recovery evidence contradicts the source-derived closure.
