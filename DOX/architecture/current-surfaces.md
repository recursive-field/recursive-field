# Current Surfaces

## Purpose

Record the publicly supportable surfaces of the examined modern system and the limits of that evidence.

## Evidence Basis

**Verified Current** claims below are tied to Agent Zero revision `b1cbd1f960a1a5c4482b324dcff4742aa67b7a51` and a read-only observation on 2026-10-22. No private host coordinates, credentials, project records, or legacy artifacts are part of this record.

## Source-Verified Surfaces

| Surface | Verified Current | Boundary |
| --- | --- | --- |
| Project selection | A project is selected per persisted chat context rather than inferred from the process working directory. | This is application scope, not a Recursive Field formation identity. |
| Project metadata | Project metadata, instructions, capability material, knowledge, and local configuration occupy a project-scoped state boundary. | The project adapter is not the formation as a whole. |
| Instruction assembly | Main project instructions, path-owned rules, additional instruction files, and bounded prompt includes can contribute to model context. | The rendered context is a generated projection. |
| Search precedence | Project-profile, project, user-profile, plugin-profile, bundled-profile, user, plugin, and core roots resolve in deterministic priority order where applicable. | Effective resolution is not yet exported as a formation-level manifest. |
| Profiles | Bundled, plugin, user, and project definitions merge, with project scope carrying the highest authority. | Availability and fallback remain application behavior. |
| Skills | Skills are discovered from scoped roots, searched by metadata, explicitly loaded, and recorded in visible history. | Discovery does not establish trust or compatibility. |
| Knowledge and memory | Configured knowledge can be imported into semantic memory; active projects can use isolated memory and knowledge roots. | Index freshness, retrieval quality, and isolation were not behaviorally tested. |
| Extensions | Backend hooks resolve through scoped roots, deduplicate by filename, and execute in filename order; unhandled failures propagate. | This establishes an extension mechanism, not a safety proof. |
| Plugins and tools | User-owned plugins can shadow bundled plugins. Tools resolve lazily through scoped roots, with model-protocol and lifecycle hooks around execution. | Installed or discoverable does not mean authorized for every context. |
| Settings | Ordinary settings persist separately from secret-bearing values; defaults may be environment-parameterized and prompt builds can snapshot settings. | A unified Recursive Field configuration schema does not exist. |
| Response loop | Prompt assembly, model turns, extensions, and tools continue until an explicit terminal response breaks the loop. | This is current engine behavior, not verified self-formation agency. |
| Backup declaration | The built-in backup surface declares user-owned state as its default scope while excluding generated time-travel material. | No successful restore or off-host copy was verified. |

### Source Anchor Index

Line ranges refer to the pinned revision:

- project resolution, loading, activation, and instruction assembly: `helpers/projects.py:77-97,167-205,275-356,402-469,512-648`;
- scoped search roots and profile resolution: `helpers/subagents.py:44-149,180-253,314-428`;
- skill discovery, precedence, search, and loading: `helpers/skills.py:72-129,157-194,303-402,433-504,545-600` and `tools/skills_tool.py:188-297`;
- extension dispatch, ordering, and propagation: `helpers/extension.py:57-255,326-369`;
- plugin precedence and hook loading: `helpers/plugins.py:225-262,478-536,707-831,892-920`;
- settings loading, secret separation, persistence, and snapshots: `helpers/settings.py:24-54,382-428,443-565,569-619`;
- knowledge import, project-isolated memory, and retrieval: `plugins/_memory/helpers/memory.py:69-89,259-383,666-710,745-752`;
- prompt, model, tool, and response-loop paths: `agent.py:495-626,943-983,1111-1243,1574-1608` and `tools/response.py:5-14`;
- initialization and startup: `initialize.py:7-20,49-102` and `run_ui.py:9-87`; and
- declared backup scope: `helpers/backup.py:37-67`.

## Live-Observed Surfaces

| Observation | Classification | Limit |
| --- | --- | --- |
| The running manifestation used a clean framework checkout at the pinned revision and public image `agent0ai/agent-zero@sha256:a38802ee1ddb83747836521931a99b8f6af000c586e1176478c533dcb08de8c4`. | Verified Current | The live container identifier is intentionally excluded; image and source identity do not prove every loaded module's import-time hash. |
| Exactly one host-managed local volume projected user-owned state read-write at `/a0/usr`; its storage shared the host's local ext4 root filesystem. No attached block volume was present. | Verified Current | This resolves basic storage placement, not independent durability or recovery. |
| The runtime root was a writable overlay rather than a read-only image surface. | Verified Current | Runtime writes outside declared durable state may disappear with replacement. |
| Host-side observation found only SSH and HTTP listeners, with HTTP port 80 published into the container. Docker forwarding rules were present and the host firewall frontend was inactive. | Verified Current | This is reachability evidence, not authorization, exposure-policy, or security proof. |
| No host TLS listener or separately observed tunnel termination was established. | Open | External gateway and TLS policy are deferred to Chapter 2. |
| Provider control-plane observation found automated backups disabled and two same-region point-in-time snapshots present. | Verified Current | Restoration, integrity, retention policy, and independent or off-region recovery remain Open. |
| The selected project and public repository were visible beneath durable user-owned state, and a local health surface returned success. | Verified Current | Private coordinates and runtime identifiers are intentionally omitted. |

## Authority Separation

| Plane | Current authority | Classification |
| --- | --- | --- |
| Public source lineage | This repository and its attributable commit history. | Decision |
| Private formation continuity | Private situated instructions, records, knowledge, memory, and operating context outside public lineage. | Decision |
| Runtime manifestation | A replaceable execution environment that projects source and state into action. | Target Requirement |
| Durable data | State explicitly intended to survive runtime replacement. | Target Requirement |
| Generated projections | Prompt renderings, semantic indexes, caches, assembled settings, logs, and similar derivations. | Decision: non-authoritative unless promoted |
| Secrets | Dedicated secret-bearing stores and references outside public documentation. | Decision |
| Recovery authority | An independent human-controlled path capable of recovering or restraining the system. | Decision |

## Open Current Facts

- **Open — deferred to Chapter 2:** external gateway, authorization, TLS, firewall policy, and any tunnel termination beyond the observed host publication.
- **Open — deferred to Chapter 2:** snapshot restoration, integrity, retention policy, and independent or off-region recovery.
- **Not Implemented — deferred to Chapter 2:** a context-specific export of enabled plugins, extensions, policies, and winning resolution roots.
- **Open — deferred to Chapter 2:** semantic-index freshness, corpus coverage, retrieval quality, and project-isolation behavior.
- **Open:** a reverse-resolvable relation from a runtime manifestation to a durable formation continuity root.

## Not Implemented

- A Recursive Field formation identity or identity marker.
- An executable formation schema or configuration grammar.
- A formation-level effective-composition manifest.
- Verified cross-node discovery or recovery.
- Verified agency over deployment, storage, backup, or infrastructure.
