# Export contract

A raw skill is one installable directory with `SKILL.md` and needed `agents/`, `references/`, `scripts/` and `assets/`. It has no runtime dependency on Orchflows, its home/registry or other installed workflows. Declare required host capabilities, tools and runtimes. Single-file/single-agent export is an additional caller constraint.

## Resolve and bundle

Traverse workflows, guidance/reference links, script imports and data dependencies. Track visited resources to bundle shared dependencies once and terminate reference cycles; preserve intentional workflow loops/bounds. For dynamic dependencies, define supported scope or disclose unresolved capability rather than claiming universal coverage.

Resolve guidance through [library context](../../../references/library-context.md). Snapshot selected core/library layers with order, common criteria, Make/Review additions, explicit paths and call applicability. Local extensions stay local; corrections remain removable. For runtime domain selection, bundle supported domains and preserve selection rules. Missing explicit domains remain gaps; never silently freeze open-ended selection to the trial domain or discard library-only specializations.

Flatten composed decisions into entrypoint/local references. Replace native skill invocation/package resolution with local instructions/paths; shared contracts have one local owner. Remove obsolete package setup/registration after retaining behavior-bearing architecture/host rules.

Copy scripts/assets with transitive local dependencies. Resolve their paths/imports/data from the export and task inputs/outputs from the caller workspace. Exclude author-machine paths, credentials, caches, trial outputs and unrelated package files/manifests; plugin packaging requires a separate request. Preserve licenses/attribution.

Optional integrations remain optional only when the source defines useful behavior without them; invent no substitute. Declare external tools/runtimes/authentication without provisioning them. Bundle required non-Orchflows skills or report unresolved dependencies.

## Preserve or disclose

Preserve source defaults. Authoring/trial settings become runtime defaults only on explicit caller request.

| Source feature | Standalone contract |
| --- | --- |
| `orch-work` | Fresh native maker with assignment, workspace/input state, applicable common/Make guidance and scoped choices |
| `orch-review` | Fresh nonmaker with applicable common/Review guidance; no repairs or repair delegation |
| Composition, parallelism, joins/handoffs | Same coordinator, scoped inputs/guidance; references add no agents/reviews or reset bounds. Carry core Execution rules verbatim. Preserve dependencies, ownership, counts, caller constraints, outputs, bounds and partial results through native tools. |
| Repairs/loops/checkpoints/continuous runs | Preserve stopping/promotion rules and consumed attempts through resume; host execution/resume remains necessary. A skill adds no scheduler. |
| Model/effort | Carry core Model and effort rules verbatim. |
| Isolation | Preserve workspace/revision and required uncommitted inputs through native isolation or explicit worktrees. Missing required isolation blocks that step. |
| Guidance/corrections | Snapshot precedence, roles and removable layers. Upstream refresh/new-library discovery requires re-export. |
| Home/helpers | Bundle dependencies; require no Orchflows runtime/resolver. |
| Host APIs/history/environment mutation | Adapt to declared target capabilities/ownership. Editing Orchflows itself requires an explicit new target for a generic equivalent; disclose limits. |

Retain guarantees in runtime instructions. Missing native delegation cannot become self-review. A requested single-agent adaptation must disclose losses of fresh context, parallelism, independent judgment and per-agent controls. Serialization is equivalent only when concurrency is outside source guarantees/bounds.

A single-file export must inline required text. Scripts, binaries and invocation sidecars cannot simply disappear: identify conflicts, offer folder form or caller-requested adaptation, and never claim sidecar-dependent settings for a bare file.

## Verify portability

Relocate a copy to an unrelated workspace. Check Markdown targets, script entrypoints/imports/resources, supported frontmatter, invocation metadata and reference reachability. Inspect absolute paths/package names by meaning: provenance may name the source; runtime must not require it.

Trial the copy with declared prerequisites, without source checkout, Orchflows home or unrelated installed skills. Follow core's workflow-trial contract in a fresh top-level session; unavailable sessions are execution gaps, not permission for child orchestration. Instructions to avoid source files alone do not establish filesystem isolation.

Exercise representative behavior with realistic synthetic inputs and simulated external effects. For retrieval, fake discovery and source-inspection responses, including relevant failures; report live access unvalidated. Supplied documents are read-only fixture-design references. Keep real independent reviewers; service fakes do not replace judgments. Trial containment does not change the export's production permissions or capabilities.

Compare observed outputs/orchestration with source contracts. Report untested failures, dynamic branches, hosts and future source changes separately from unresolved dependencies. Link/metadata checks establish packaging, not behavior; simulation establishes no live integration.
