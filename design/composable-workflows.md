# Composable workflows refactor

Status: implemented and dogfooded; independent review completed, with its documentation findings corrected and checked. Baseline: `codex/flat-workflow-composition` at `b9675e5b`. This document is maintainer design material, not required execution context.

## Outcome

Users should be able to build a library of small workflows and use those workflows inside larger workflows without adding coordinator agents or copying their instructions. The saved workflow preserves deliberate dependencies, independent judgments, bounds and effects. Guidance carries the quality standard, taste and techniques. Better models should usually require fewer techniques and corrections without changing the user's chosen process.

Keep the two primitive meanings: `orch-work` starts a fresh maker; `orch-review` starts a fresh reviewer who did not make the candidate. Native hosts own execution. There is no workflow runtime, parser, reserved control-flow vocabulary, mandatory conformance checker or universal checkpoint format.

## Problems addressed

The current branch already supports useful composition and flat dispatch. Its recorded dogfood also found a child selecting dynamic fallback, reviews before prerequisites, a skipped game review gate, variable staffing and an output defect missed by review. These do not have one remedy. This refactor targets responsibility and context boundaries; it does not claim that shorter instructions guarantee correctness.

Current friction includes ordinary stages that require fresh makers despite flexible-staffing rules; repair policy embedded in the architecture; context described as globally unchanged even when nested work needs local guidance; Make and Review appearing to be separate quality standards; and process mixed with lengthy production technique.

Fable's proposal usefully exposes process and separates methods, but its one-level inline limit would make procedure reuse force fresh sessions. Its universal checker assumes reliable semantic events that do not yet have an owner. Neither is required to test the smaller design.

## Public behavior

### Composition

A workflow declares its useful inputs, result, dependencies and process in ordinary Markdown. It may apply another workflow at any depth in the same coordinating session. A workflow reference alone does not create an agent, add a review, reset a budget or broaden authority. No new required headings or serialization format are introduced.

The coordinating session interprets the procedures and dispatches native children. Children receive concrete assignments and return results or further-work requests; they do not launch or task agents. The instruction is not described as host enforcement where the host does not enforce it.

Each call gets applicable caller constraints and scoped settings, relevant inputs, an output location when needed, and guidance for that work. Local guidance additions, output names and counters stay local to the call. Completed outputs feed the next call. Independent work may run concurrently with clear ownership. Missing prerequisites stop dependent work while unrelated authorized work may continue.

Recursion depth is not a session boundary. Actual context or isolation needs may require a separate session. Workflow trials use fresh top-level sessions to exclude authoring history; that capability stays in host/trial documentation, not a third universal primitive.

### Work and review

An explicit `orch-work` call always launches a fresh native maker. Ordinary production language such as “draft the brief” leaves staffing to the coordinator, which may work directly, continue a suitable maker or delegate through the primitive. Required independence and caller model/effort settings take precedence over this flexibility.

`orch-review` receives the intended result, shared quality criteria, relevant Review guidance, a stable candidate and inspectable evidence. Prefer task-only context that excludes the maker's persuasive narrative and unrelated authoring history. Fresh identity alone does not prove clean context or blinding. Reviewers can execute checks and write separate evidence; they do not modify the candidate or delegate repairs.

Gather required completed reviews before changing their candidate. A verdict is scoped to the state and coverage inspected. Later changes need their own checks and cannot inherit an unchanged approval claim. If required independent execution is unavailable, report a gap rather than substituting self-review.

### A reusable repair workflow

Move the existing standard review/repair process out of the architecture into `orch-review-revise-once`, an ordinary core workflow, not a third primitive. There are already multiple consumers: dynamic workflow, authoring, export, self-improve, Benchmaker and the shared package. This earns a shared owner without a dependency from core onto an optional library.

The component reviews once, waits for completion, repairs at most once within scope, performs affected and caller-required checks, and returns the original review separately from the delivered revision and its evidence. Repair staffing remains flexible. It does not add another review, approval pause or external release.

Keep `shared:review-revise-once` as a thin compatibility entry to this core workflow. Update all live consumers to one of these explicit calls. Remove architecture's process definition; retain universal review identity and dependency rules. Other workflows retain their own deliberate repair loops.

### Guidance

The minimal interface is an ordered list of resolved guidance files applicable to the assignment. A file's common quality criteria apply to maker and reviewer. Optional Make and Review sections add role-specific methods. Corrections are optional, scoped and removable; no model-name registry is added.

The existing named/dotted domain resolver remains a convenience for producing this list. Preserve its general-to-specific and package ordering for compatibility. Support explicit paths without requiring domain registration. Required selected files must exist. Cache resolved paths, but extend selection when a nested workflow introduces new work. Do not mutate sibling or parent selections.

A more specific preference can override a general preference in its scope. It cannot override caller constraints, required workflow behavior or authority. Independent conflicting requirements with no defined precedence require resolution. Technique may be optional; tool contracts, frozen evaluation criteria and other correctness dependencies remain required even when stored in references.

Migrate representative core guidance to shared criteria plus useful role methods. Do not mechanically reclassify every Make instruction as universal: some are genuinely maker-only methods. Preserve deliberate preferences and avoid duplicating them in Review.

### Invocation and installation

Make dynamic fallback opt-in, matching the proposal's small explicit library. Its manual invocation remains available, and its top-level-only boundary remains. Set both native invocation metadata fields consistently. Document how users can opt into fallback and hosts that cannot enforce manual-only discovery. Preserve existing user registrations and settings during this development task.

Readable package files, resolved dependencies and native child tools are sufficient for execution. The home CLI remains an optional setup/resolution convenience. Missing a home runtime alone does not block supplied native resources; missing a capability blocks only work that actually requires it. Do not silently replace requested model settings or independent review.

Ship the new skill through the existing complete-package installer. Align versions across host manifests and checkout catalogs. Core owns its required links; no core dependency points into optional example packages. Package layout and authoring mechanics move to author-facing documentation so ordinary workers do not need them.

## A concrete composition

A user's `launch-pack` can say: “Apply `research-brief` to the supplied packet under research guidance. Then write a campaign concept from the returned brief under campaign guidance. Return both.” The `research-brief` workflow can draft directly, apply `shared:review-revise-once`, and return the delivered brief with its original review and verification. The compatibility component applies core `orch-review-revise-once`, which uses `orch-review` for its independent judgment.

That is four levels of reusable procedure. One coordinating session can draft both outputs and launch one reviewer. Another host may choose separate makers. Both preserve the selected process. The campaign style applies only to the campaign; it does not become the brief's quality standard. Campaign guidance is still an accessible file, not a secret. The campaign receives no review unless its workflow or caller selects one.

Each component is useful alone. A larger workflow can consume `launch-pack` without copying these steps or inheriting local output names. A caller can also use the same research guidance for a direct assignment without the saved process. The maintained [composition fixture](../example-workflows/shared/trials/composition/request.md) makes this example executable; its evaluator expectations are separate from the input packet.

## Migration scope

1. Core architecture, work/review primitives, reusable review/repair workflow, dynamic and authoring workflows, invocation metadata, core guidance and relevant home/host documentation.
2. Shared compatibility component and every live consumer of the architecture's old standard pattern. Keep comparison as a reusable workflow, preserving its scope and no-adoption contract.
3. Design Loop production components: remove compulsory fresh makers where freshness has no deliberate purpose. Preserve its cycle bound, before/after evaluation, independent comparison, adoption and resumption rules.
4. Evolve: expose a short process; move proposal/search technique into its domain guidance. Keep confirmation, evaluator versioning, bounded attempts, harness-test independence and state identity required. Define attempt consumption before work begins, not by an arbitrary checkpoint write.
5. Browser game: expose the two real review dependencies, preserve the two mechanics experiments and repair limits, and move production methods into the existing relevant guidance/references. Preserve usable-outcome verification after repair.
6. README, library context and package metadata affected by these semantics. Specialized acquisition scripts and host installer mechanics are unchanged unless a concrete trial exposes a necessary fix.

Existing entrypoint names remain usable. The shared repair alias avoids a breaking rename. Guidance with only Make/Review remains supported; new common criteria are additive. The opt-in fallback change is intentional and must be visible in release documentation. Version changes identify the altered package contract.

## Implementation and early dogfooding

### Stage 1: bootstrap the minimal core

Write this design, capture baseline tests, implement the composition/guidance rules, primitives and reusable review/repair component. Use those new instructions immediately for the next bounded authoring assignment and independent review. Keep the candidate stable while it is reviewed; record which version was used.

Before a wide migration, run a cold composition with ordinary source inputs in a disposable workspace. It should exercise at least three levels of procedure reuse and one real independent review. Observe the actual agent tree and artifacts. A root-only trial does not prove cross-host behavior.

### Stage 2: use the revised library to migrate consumers

The authoring coordinator applies revised `orch-build-workflow`; makers receive bounded file ownership through revised `orch-work`. Apply `orch-review-revise-once` after trials, using reviewers with task-only context. Migrate independent consumer groups concurrently when their files do not overlap. Children do not run composing trials; the top-level authoring coordinator owns those sessions.

Dogfood meaningful output, not only self-description: generated workflow behavior, source-grounded output, repair evidence, scoped guidance, missing capabilities, and a small iterative artifact. Use an unrelated disposable workspace and record preparation/intervention. Trial failures change the narrow owning instruction or expose a design change; they do not automatically produce a new universal rule.

### Stage 3: consolidate and verify

Run required core checks and skill metadata validation. Inspect all changed links, invocation policies and package versions. Run affected package tests where mechanics changed. Retest behavior affected by repairs; do not repeat unrelated trials merely to increase the count. Review the final changed artifacts with the actual evidence and disclose untested hosts or branches.

Use matched baseline/candidate trials before claiming improved quality, cost or latency. Successful candidate trials establish feasibility only. Keep records outside installed packages; a concise maintained validation report can point to the local evidence and name its limitations.

## Trial acceptance

| Case | Observable requirement |
| --- | --- |
| Nested composition | Reuse at least three procedure levels; children remain leaf assignments; required review actually happens. |
| Small production task | Correct result without a compulsory maker solely because a stage has a name. Staffing choice is observed, not assumed optimal. |
| Scoped guidance | A local extension changes its intended output and does not leak into a sibling's requirements. Both roles receive the shared quality criteria. |
| Revision | Completed review precedes mutation; delivered changes and their checks remain distinguishable from the original verdict. |
| Missing capability | Useful independent work can finish, but missing required review or prerequisite is not reported as success. |
| Loop | Attempts and accepted state survive interruption; confirmation precedes promotion; resumption does not reset bounds. |
| Authoring | A workflow built using the refactored authoring process works from its declared inputs without this conversation. |
| Portability | Exercise Codex and Claude Code independently where available; registration, authentication and execution are separate observations. |

## Stop and return to the user

A significant nonstarter is a demonstrated incompatibility with the core premise: ordinary nested composition cannot preserve obligations without a new runtime or repeated user intervention; usable native hosts cannot supply required independent review; or scoped guidance repeatedly cannot be carried without an instruction burden comparable to the removed machinery.

Stop dependent migration, preserve the smallest reproduction and report the finding, its practical scope and a recommended alternative. A local syntax error, missing optional host, isolated model miss or narrow wording defect is not automatically a premise failure. Fix routine issues and continue; report validation limits honestly.

## Validation record

- Baseline core suite: 126 tests, 125 passed and one platform skip.
- Implementation, observed defects, corrections and remaining coverage limits are recorded in [refactor validation](refactor-validation.md). Candidate trials establish feasibility in the tested environments, not a comparative quality, cost or latency improvement.
