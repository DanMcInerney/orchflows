# Export contract

A raw skill is one installable directory containing `SKILL.md` and any required `agents/`, `references/`, `scripts/` and `assets/`. It has no runtime dependency on Orchflows, its home, library registry or other installed workflows. It can still require native host capabilities, tools and language runtimes; state those requirements in the skill. A single file or a single agent is a separate constraint, used only when requested.

## Resolve and bundle

Read the dependency closure, including links from guidance and references, script imports and data files. Track visited resources so shared dependencies are bundled once and reference cycles do not cause recursive copying. Preserve any intentional workflow loop and its stopping condition. Identify dynamic dependencies that cannot be enumerated; bind an explicit supported scope or report the unresolved capability instead of claiming a universal export.

Resolve guidance by the core selection rule established in [library context](../../../references/library-context.md). Snapshot the selected core and library layers with their order and Make/Review roles intact. Keep corrections separately removable. For runtime domain selection, bundle the supported domains and retain their selection rules; an unbundled explicit domain is a gap. Do not silently freeze an open-ended workflow to the trial's domain or drop a library-only specialization.

Flatten composed workflow decisions into the entrypoint or local references. Replace native skill invocations and package resolution with local instructions and paths. Keep a shared contract in one local reference when multiple steps use it. Remove obsolete package-setup and registration instructions from runtime instructions; extract any behavior-bearing rules from architecture or host documents before dropping their links.

Copy required scripts and assets with their transitive local dependencies. Rewrite package-relative paths, imports and data lookups so they work from the exported skill directory; keep task inputs and outputs relative to the caller's workspace. Never bake author-machine paths, credentials, caches or trial outputs into the skill. Preserve applicable licenses and attribution. Omit unrelated package files and plugin manifests unless the caller separately requests plugin packaging.

Optional integrations may remain optional only when a usable bundled or native fallback preserves the source's contract. Required external tools, runtimes and authentication remain declared prerequisites; the export does not provision them. A required non-Orchflows skill must be bundled too, or remain an explicitly unresolved gap.

## Preserve or disclose

Preserve source defaults. Model, effort and other choices for the export session or trial do not become exported runtime defaults unless the caller asks to save them.

| Source feature | Standalone treatment |
| --- | --- |
| `orch-work` | Replace with direct native delegation to a fresh child, carrying the assignment, workspace/input state, resolved local Make guidance and scoped caller choices. |
| `orch-review` | Replace with a fresh native child who did not make the candidate, applying local Review guidance without making or delegating repairs. |
| Composition, parallel work, joins and handoffs | Only the top-level orchestrator launches, assigns and continues agents; children return results and further-work requests. Preserve dependencies, ownership, process counts, caller constraints, output contracts, bounds and partial-result handling using native host tools. |
| Repairs, loops, checkpoints and continuous runs | Preserve requested stopping and promotion rules. Host execution/resume remains required; a skill does not add a scheduler. |
| Model and effort choices | Preserve saved assignment settings and caller overrides; current caller beats saved, named assignment beats its operation default within each source, resolved separately per field. Unspecified fields stay unset. Apply through supported native controls; prompt text alone does not select a model. Reuse an agent only if its settings fit. Unsupported settings are gaps, never silent substitutions. |
| Isolation | Preserve the intended workspace and input revision, including required uncommitted inputs. Use native isolation or an explicit worktree when available; missing required isolation blocks the affected step. |
| Layered guidance and model corrections | Bundle a snapshot with precedence, roles and removable layers. Shared upstream updates and discovery of new libraries stop; re-export to refresh them. |
| Home resolution and installed helper workflows | Replace with bundled local dependencies. No setup-managed runtime or Orchflows resolver remains necessary. |
| Host-specific APIs, history or environment mutation | Adapt to declared target capabilities and ownership paths. If the purpose depends on editing Orchflows itself, a generic standalone equivalent needs an explicit new target; disclose that limitation. |

Keep the behavioral guarantees in the exported instructions. Missing native delegation does not turn an independent review into self-review. If the caller requests a single-agent adaptation, label the loss of fresh context, parallelism, independent judgment and per-agent controls. Serial execution is equivalent only where concurrency is not part of the source contract or its bounds.

A requested single-file export must inline required textual guidance and contracts. Required scripts, binary assets and Codex invocation metadata cannot simply be discarded: disclose which constraints prevent a faithful single-file result, and offer the folder form or a caller-requested adaptation. Do not represent a bare file as preserving settings that require a sidecar.

## Verify portability

Move a copy of the completed folder to an unrelated workspace. Check local Markdown targets, script entrypoints, imports and resource loading there. Inspect remaining package names and absolute paths by meaning: provenance can name the source, runtime instructions cannot require it. Verify supported frontmatter, invocation metadata and that every bundled reference is reachable when needed.

The bounded trial must run using that copy and declared prerequisites, without reading the source checkout, Orchflows home or unrelated installed skills. Run a composing export in a fresh top-level session with only those inputs, following core's workflow-trial contract. If that session is unavailable, report the execution gap; a child cannot become a nested coordinator. Do not claim filesystem isolation merely because the child was instructed to avoid the source.

Choose a trial that exercises the workflow's primary capability with available, authorized tools. For live retrieval, exercise discovery and source inspection; a fixture-only trial validates only the offline path. If the primary capability cannot be exercised, report it as unvalidated.

Compare observed outputs and orchestration with the source contract. A successful path does not establish failure handling, all dynamic branches, another host or future source changes. Report those limits separately from unresolved required dependencies. Passing link and metadata checks alone establishes packaging, not behavior.
