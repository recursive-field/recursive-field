# Chapter 2 Continuity-State Observation

## Purpose

Apply the [Formation Observation Frame](../architecture/formation-observation-frame.md) to the state that currently carries, supports, projects, or may recover continuity.

This observation asks which state is authoritative, participant-scoped and durable, shared, rebuildable, incidental, secret-bearing, or recovery material. It does not define formation identity, select a canonical root, authorize implementation, or prove recovery.

## Observation Record

| Field | Record |
| --- | --- |
| Recorded time | 2026-10-23. |
| Vantage | Read-only documentary and source inspection. No live runtime, host, provider, credential, private-content, restore, relocation, or replacement exercise was performed. |
| Scope and time | Agent Zero revision `b1cbd1f960a1a5c4482b324dcff4742aa67b7a51`, the sanitized Chapter 1 live-observation boundary recorded on 2026-10-22, and the Chapter 2 draft evidence available on 2026-10-23. |
| Subject and utility | The current state classes and relations that must be understood before runtime replacement, participant continuity, reverse resolution, or portable recovery can be designed faithfully. |
| Evidence | Current Agent Zero source, [Current Surfaces](../architecture/current-surfaces.md), [Chapter 1 Status](chapter-1.md), [Chapter 2 First Observation](chapter-2-first-observation.md), and the [Formation Utility Map](../architecture/formation-utility-map.md). |
| Epistemic status | **Verified Current** for cited source behavior and inherited Chapter 1 observations; **Open** for unexercised replacement and recovery behavior; **Not Implemented** for formation-level continuity resolution. |
| Authority and mutability | Authority remains distributed by state class. Persistence under one storage root does not make every stored artifact authoritative, equally durable, or equally recoverable. |

### Inquiry boundary

The inquiry is a cross-plane continuity crosscut. It includes state location, ownership, mutation, projection, replacement, and recovery relations. It excludes private contents, secret values, actual archive contents, effective runtime composition, restore execution, provider guarantees, identity selection, and implementation design.

## Seven-Plane Placement

| Plane | Current placement | Finding |
| --- | --- | --- |
| Public source lineage | Pinned Agent Zero source and committed Recursive Field history | **Verified Current / Decision.** Committed history is public authority. A dirty tree or backup copy remains draft or recovery evidence until deliberately committed. |
| Private formation continuity | Situated project instructions, records, knowledge, memory, and operating context | **Verified Current.** This plane contains several state classes; it is not one undifferentiated directory or authority. |
| Runtime manifestation | Process, container filesystem, loaded modules, and in-memory state | **Verified Current.** The manifestation interprets durable inputs but is replaceable and cannot establish continuity by surviving. |
| Durable data | Project memory, chats, scheduler state, settings, resources, plugin state, and participant work intended to persist | **Verified Current.** Persistence is implemented; formation-level ownership and recovery contracts are not. |
| Generated projections | Rendered context, imported indexes, embeddings, caches, and derived evidence | **Verified Current / Decision.** Rebuildability varies. A single physical store can contain both derived and non-rebuildable records. |
| Secrets | Global, runtime, and project-scoped secret stores | **Verified Current / Decision.** Secrets can be operational continuity dependencies without becoming identity or ordinary state. |
| Recovery authority | Accountable recovery actors and backup, history, or snapshot material | **Decision / Open.** Recovery surfaces exist, but their integrity, completeness, independence, and reconstitution behavior are unverified. |

A state artifact may cross planes by role. Classification therefore follows its operative relation, not its directory alone.

## Continuity-Bearing State Classes

`Backup` describes inclusion in Agent Zero's default backup declaration, not proof that an archive exists or is valid. `Time Travel` describes inclusion in a normal selectable Time Travel workspace.

| State class | Current role and authority | Replacement behavior | Backup | Time Travel | Source evidence |
| --- | --- | --- | --- | --- | --- |
| Framework source and image | Public engine behavior and reproducibility input; not private continuity | Recreated from attributable source or image | No | No | `DockerfileLocal`; `docker/run/Dockerfile`; pinned revision in Chapter 1 |
| Public Recursive Field repository | Committed Git history is authoritative public lineage; local uncommitted work is draft evidence | Independent remote history can outlive runtime, volume, and host | Included when located under user state | Nested Git worktrees are excluded | `helpers/backup.py:get_default_backup_metadata`; `plugins/_time_travel/helpers/time_travel.py:_is_nested_git_worktree_dir` |
| Project body and ordinary work artifacts | Project-scoped work whose authority depends on the artifact, not location | Survives runtime replacement with durable user storage; relocation can break references | Yes | Generally yes, subject to exclusions | `helpers/projects.py:get_project_folder`; `time_travel.py:is_snapshot_candidate` |
| Project metadata and ordinary configuration | Project title, instructions, agent availability, and related adapter configuration | Survives replacement; mutable names and paths can break dependent links | Yes | Selected `.a0proj` files and regions only | `helpers/projects.py` constants and project load/save functions; `time_travel.py:SAFE_A0PROJ_FILES`, `SAFE_A0PROJ_DIRS` |
| Project instructions and skills | Authoritative contextual and capability inputs at project scope | Durable with the project; generated context is replaceable | Yes | Yes | `helpers/projects.py:get_project_prompt`; `helpers/skills.py:get_skills_subdirs` |
| Project knowledge sources | Authoritative project knowledge resources | Durable; imported semantic projections are rebuildable subject to compatible import behavior | Yes | Yes | `helpers/projects.py:create_project_meta_folders`; `_memory/helpers/knowledge_import.py`; `_memory/helpers/memory.py:abs_knowledge_dir` |
| Project memory store | Mixed participant continuity: learned or saved memory plus imported knowledge projections | Durable if the store remains readable; learned records are not reconstructable from knowledge sources alone | Yes | Entire `.a0proj/memory` subtree excluded | `_memory/helpers/memory.py:abs_db_dir`, `get_agent_memory_subdir`; `time_travel.py:_is_safe_a0proj_candidate` |
| Chats and chat-carried project linkage | Participant history, agent context, selected project, profile, outputs, and a bounded log tail | Survives with user storage; project rename or relocation can stale the saved project name | Yes | Not part of a normal project workspace | `helpers/persist_chat.py:CHATS_FOLDER`, serialization and atomic save functions |
| Scheduler state | Installation-global scheduled intent; tasks may refer to a project and chat context | Survives with user storage; project references can stale independently | Yes | Not part of a normal project workspace | `helpers/task_scheduler.py:SCHEDULER_FOLDER` and task persistence functions |
| Ordinary settings | Installation-global persisted configuration; sensitive values are removed before writing | Survives with user storage; interpretation may change across engine revisions | Yes | Not part of a normal project workspace | `helpers/settings.py:SETTINGS_FILE`, `_read_settings_file`, `_write_settings_file` |
| Global and project secrets | Separately governed credentials for protected relations | Can be required for operational resumption; must retain separate custody | Included by default backup | Excluded | `helpers/secrets.py:get_secrets_manager`, `get_project_secrets_manager`; `time_travel.py:is_snapshot_candidate` |
| Global knowledge and memory | Installation-scoped or shared resources when project isolation does not redirect them | Survive with user storage; broader ownership than one project | Yes | Not part of a normal project workspace | `_memory/helpers/memory.py:abs_db_dir`, `abs_knowledge_dir`, `get_existing_memory_subdirs` |
| Global user plugins | Installation-global capability implementations that may be required to interpret project configuration | Capability can disappear while project bytes remain | Yes | Global user plugins excluded | `helpers/plugins.py` discovery and precedence functions; `time_travel.py:USR_ROOT_EXCLUDED_DIR_NAMES` |
| Project plugin configuration | Scoped configuration and enablement for capability implementations | Durable only as useful configuration when a compatible implementation remains available | Yes | Safe configuration leaves only | `helpers/plugins.py:get_plugin_config`; `time_travel.py:SAFE_PLUGIN_ASSET_NAMES` |
| Generated model context and in-memory snapshots | Request-local projection of instructions, retrieval, settings, capability, and precedence | Ephemeral and rebuilt; no complete provenance export exists | No as an in-memory object | No | `agent.py` prompt-building and model-turn path; `helpers/settings.py` prompt/runtime snapshots |
| Indexes, embeddings, and discovery caches | Derived optimization or search structures | Usually rebuildable; loss should affect availability, cost, or performance rather than authority | Only if placed under user state | Cache and build classes excluded | `_memory/helpers/memory.py`; `time_travel.py` exclusion sets |
| Logs and evidence | Diagnostic or audit material unless explicitly promoted | Loss can impair explanation without changing source authority | Yes when under user state | Only when inside an allowed workspace path | `helpers/persist_chat.py` bounded log serialization |
| Runtime overlay and process state | Replaceable manifestation and incidental residue | Discarded by container or process replacement | No | No | Chapter 1 live observation |
| Docker-managed user-state volume | Current physical persistence carrier for user state | Survives container/image replacement when preserved and remounted; does not survive deletion merely because it is a volume | Contents are eligible | Contains Time Travel history, but history does not snapshot itself | Chapter 1 live observation |
| Agent Zero backup archive | Operator-controlled recovery material spanning the default user-state selection | Can translate an old installation root during restore; does not translate project identity or prove semantic continuity | Not applicable | Depends on archive placement; Time Travel history is omitted from archive input | `helpers/backup.py:_get_default_patterns`, restore preview and restore functions |
| Time Travel history | Workspace-local recovery material selected by a path-derived workspace identity | Survives with the user-state volume; relocation changes the derived workspace relation | Explicitly excluded from default backup | Not applicable | `plugins/_time_travel/helpers/time_travel.py` workspace-ID and travel/revert functions |
| Host or provider snapshots | External operator recovery material | May preserve broad storage state, but restoration and post-restore validity are untested | Outside Agent Zero backup | Outside Time Travel | Chapter 1 sanitized provider observation |

## Supported Directional Relations

### Forward paths

1. `public framework source or image -> runtime manifestation`
   The engine interprets user-owned state. Runtime-local edits do not become public lineage.

2. `persisted chat -> selected project name -> project adapter -> project tree and .a0proj`
   Current application context can reselect a project after chat reload. This is an application link, not formation identity.

3. `project instructions and skills -> scoped resolution and precedence -> generated model context`
   This is the forward assembly path established by the first Chapter 2 observation.

4. `knowledge source -> checksum and import -> memory store -> retrieval -> generated context`
   The source and imported projection remain distinct even though imported knowledge and learned memory converge physically.

5. `ordinary settings + global secrets + project secrets -> normalized effective settings and credentials`
   Sensitive values are merged at runtime and removed from ordinary settings persistence.

6. `plugin implementation + scoped configuration and enablement -> runtime capability`
   Surviving configuration cannot recreate a missing or incompatible implementation.

7. `scheduler record -> project and context references -> task execution and task chat`
   Scheduled intent and participant history remain separate durable records joined by references.

8. `user-state volume -> runtime projection -> current user state`
   Storage projection provides persistence, not semantic authority.

9. `user state -> Agent Zero backup archive -> translated installation-root restore`
   Current restore code can translate installation roots; it does not repair project renames or establish continuity.

10. `workspace path -> derived workspace key -> Time Travel history -> allowed-file travel or revert`
    The mechanism supports bounded reverse mutation but begins from a mutable coordinate.

11. `host storage -> provider snapshot -> potential host reconstitution`
    Only the presence of candidate recovery material is established; the restoring path remains **Open**.

### Reverse-resolution findings

- **Verified Current:** a running or restored chat can resolve its persisted project name and derive the current project folder, metadata, memory, and knowledge roots.
- **Verified Current:** scheduler records can refer to a context and project, but those references are application coordinates rather than formation identity.
- **Verified Current:** imported knowledge retains checksums and source metadata sufficient for a private provenance fragment, not a public continuity relation.
- **Verified Current:** backup metadata can translate the Agent Zero installation root during restore; it does not translate project names or validate continuity.
- **Verified Current:** Time Travel can materialize included files from a known workspace and revision, but workspace identity is path-derived.
- **Not Implemented:** generated context cannot resolve back to a complete report of winning instructions, memory, settings, capabilities, policy, and secret references.
- **Not Implemented:** a runtime manifestation cannot resolve to durable formation continuity without depending on mutable names, paths, chat identifiers, or other private coordinates.

## Backup, Time Travel, and Snapshot Asymmetries

1. **Backup is broad while Time Travel is intentionally narrow.** Default backup includes user-owned state broadly. Time Travel excludes secrets, project memory, Git state, caches, and global plugins while admitting ordinary project files and selected project metadata, instructions, skills, knowledge, and safe plugin configuration.
2. **Default backup excludes Time Travel history.** Loss of the user-state carrier can remove both current state and workspace history, while a default Agent Zero archive cannot reconstruct that history.
3. **Secrets are backup material but not Time Travel material.** A Time Travel revert cannot reconstitute protected relations; a backup archive is therefore secret-bearing and requires stronger custody.
4. **Declared backup integrity is not verified integrity.** The examined backup service records an integrity-check setting but does not create and validate a checksum set in the inspected path.
5. **Restore composes old state with current runtime policy.** The runtime origin policy is preserved during environment-file restoration, so restore is intentionally not a wholly byte-for-byte replay.
6. **Knowledge and memory converge physically but differ semantically.** Imported knowledge can be rebuilt from source; learned or saved memory generally cannot.
7. **Project memory is backed up but excluded from Time Travel.** It lacks the same local rollback relation as instructions or knowledge.
8. **Plugin configuration can outlive plugin implementation.** Time Travel may preserve safe scoped configuration while excluding the global implementation it requires.
9. **Chats and scheduler state refer to projects without being project-owned.** Copying or relocating one project does not carry all participant or operational relations.
10. **Project relocation is not continuity-neutral.** Chat and task references use project names, memory paths derive from project names, and Time Travel workspace identity derives from path.
11. **A backup copy of Git data is not public source authority.** Only deliberate commit and publication establish public lineage.
12. **Provider snapshots are candidates, not proof.** Existing snapshots have not established restoration, integrity, retention, regional independence, or post-restore validity.

## Replacement and Loss Survival Matrix

`Supported` means established by placement or current source behavior, not an exercised continuity test. `Conditional` identifies a dependency or unresolved compatibility relation.

| State or relation | Container replacement | Project relocation or rename | Image replacement | User-state volume loss | Host loss |
| --- | --- | --- | --- | --- | --- |
| Independently committed public source | Supported | Supported | Supported | Supported | Supported while an independent remote remains |
| Local uncommitted public draft | Supported when volume remains | Conditional | Conditional | Lost unless separately copied | Lost unless separately copied |
| Project body, metadata, instructions, skills, and knowledge | Supported by durable placement | Conditional; references may break | Conditional; interpretation compatibility untested | Requires independent recovery material | Requires independent recovery material |
| Learned project memory | Supported by durable placement | Conditional; namespace relation needs repair | Conditional; format and model compatibility open | Requires broad backup or snapshot | Requires external recovery material |
| Chats and project selection | Supported by durable placement | Conditional; selected project name may stale | Conditional | Requires backup or snapshot | Requires external recovery material |
| Scheduler intent and task links | Supported by durable placement | Conditional; project reference may stale | Conditional | Requires backup or snapshot | Requires external recovery material |
| Settings and shared resources | Supported by durable placement | Conditional where names or paths are embedded | Conditional; interpretation may change | Requires backup or snapshot | Requires external recovery material |
| Secrets | Supported when secret stores remain | Conditional on custody and scope | Conditional | Requires separately protected recovery | Requires independent custody |
| Required global plugins | Supported when user state remains | Not project-portable by default | Conditional; compatibility open | Requires backup or reinstall source | Requires independent source |
| Generated context and process-local projections | Rebuilt | Rebuilt | Rebuilt | Rebuilt only if inputs survive | Rebuilt only if inputs survive |
| Runtime caches and overlay residue | Discarded by design | Not applicable | Discarded by design | Lost | Lost |
| Time Travel history | Supported when volume remains | Automatic linkage breaks because workspace identity is path-derived | Conditional on compatibility | Lost | Lost unless broader recovery captured it |
| Independently held Agent Zero backup | Supported | Conditional; old project names remain | Conditional; data restore does not prove compatibility | Available | Available |
| Backup held only on the lost carrier | Supported until carrier loss | Conditional | Conditional | Lost | Lost |
| Existing provider snapshot | Candidate only | Restores old layout rather than performing relocation | Candidate only | Candidate only | Candidate only; untested |

The matrix establishes storage and reference behavior. It does not prove that restored bytes are interpreted as the same situated continuity.

## Smallest Supported Continuity Boundary

**Verified Current / Inference:** the smallest supportable boundary is a relational closure rather than one directory or volume. Depending on the participant and work, it can require:

1. an attributable framework source or image revision;
2. authoritative project work, metadata, instructions, skills, and knowledge sources;
3. learned participant memory that cannot be regenerated from knowledge sources;
4. chats carrying participant history and current project linkage;
5. ordinary settings required to interpret those records;
6. scheduler records representing continuing obligations;
7. capability implementations and scoped configuration required to interpret or act on the state;
8. secret references and separately protected custody sufficient to resume authorized relations; and
9. independently held recovery material with verified integrity and an acceptance-bearing reconstitution path.

Not every context depends on every global resource. The current system cannot compute the minimum closure because effective composition and dependency provenance are not exported.

### Blockers to runtime-to-continuity resolution

- no formation identity or adopted continuity identifier;
- only a mutable `chat context -> project name -> path` application link;
- path-derived Time Travel workspace identity;
- global stores that can affect project behavior without project ownership;
- a memory store that mixes learned records and rebuildable knowledge projections;
- no public-safe effective-composition and provenance export;
- no versioned declaration of capability implementations required by scoped configuration;
- no tested backup integrity or restore acceptance path;
- materially different backup and Time Travel protection sets;
- separately governed secret custody; and
- no exercised evidence that recovered data restores equivalent retrieval, assembly, task linkage, authorization, or service.

**Open:** the runtime resolves an application project scope, not durable formation continuity. A project name, path, chat identifier, workspace hash, volume, archive, or snapshot cannot be promoted into formation identity from this evidence.

## Constraint Shadow

- Source behavior was inspected; replacement, restore, relocation, and loss scenarios were not executed.
- Private contents, secret values, effective plugin composition, archive contents, and provider guarantees were not inspected.
- Inclusion in backup or Time Travel does not establish creation, retention, integrity, compatibility, or successful restoration.
- Storage survival is not semantic continuity, and semantic continuity is not identity.
- The relational boundary above may shrink once effective composition can report actual dependencies for one context.
- Current paths and names are evidence of application behavior, not proposed formation coordinates.

## Consequences for the Utility Map

- Replaceable-runtime parity must be measured against a relational continuity closure, not everything under one user-state root.
- State boundaries must distinguish authoritative knowledge, learned memory, imported projections, chats, scheduler intent, capabilities, secrets, evidence, and recovery material.
- Provenance must cover memory composition and capability implementation/configuration pairs as well as prompt inputs.
- Participant continuity remains **Open**: the chat-to-project link is useful substrate evidence but is relocation-fragile and not formation identity.
- Effective inspection must report state-class dependencies and winning roots for one context without becoming authority.
- Relocation and image replacement must be explicit lifecycle transitions with reference repair and compatibility evidence.
- Recovery must distinguish public Git history, Agent Zero backup, Time Travel history, secret custody, and host/provider snapshots by what each includes and omits.
- Authority must remain differentiated across project mutation, shared capability mutation, secret custody, archive creation, restoration, and provider recovery.

## Next Discriminating Inquiry

Follow one sanitized context backward and sideways:

```text
persisted chat project link
-> project metadata
-> memory namespace
-> knowledge sources and import state
-> effective settings
-> required capability roots and configuration
-> scheduler references
-> recoverable state classes
```

The question is:

> Can current source derive a public-safe, content-free continuity dependency closure for one context, and exactly where must it fall back to mutable coordinates, global stores, or unexported effective composition?

This remains source and documentary work. It does not authorize restore, mutation, identity selection, or implementation.

## Local Closure

**Decision:** this observation closes the continuity-state inventory locally. It establishes that continuity is distributed across differentiated relations and that built-in backup, workspace history, public lineage, secret custody, and provider snapshots protect different subsets.

It does not close runtime-to-continuity resolution, effective composition, memory behavior, recovery semantics, relocation, or Chapter 2. Reopen this observation when an effective-composition trace, relocation exercise, backup restore, memory behavior test, capability change, or provider recovery exercise changes the supported dependency closure.
