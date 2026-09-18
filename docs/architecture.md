# Architecture

## Two primitives

- [orch-work](../skills/orch-work/SKILL.md): a fresh native child makes a result under chosen guidance.
- [orch-review](../skills/orch-review/SKILL.md): a fresh native child who did not make it reviews without fixing.

The product is two primitives, reusable workflows and user-owned guidance. The host executes agents. Workflows are saved procedures: the coordinating session applies them to inputs and uses their results. They may compose to any depth; loading another workflow does not launch an agent, add a review or reset a bound. Prompts supply the task; workflows preserve the chosen process; guidance supplies quality criteria, methods and taste.

## Invocation

Orchflows provides explicitly selected primitives and workflows. It installs no catch-all fallback or automatic workflow router. An unmatched request stays with the host's ordinary agent behavior. Write and verify the [host invocation settings](hosts.md#invocation-policy) for each skill; report a host that cannot enforce this policy. Changing this product decision requires an explicit user request, not an incidental refactor or review preference.

Saved workflows compose their chosen processes and primitives directly. Explicit caller amendments can change the process; state any changed guarantee, preserve primitive meanings and honor actual permissions. Each operation has one public name. Removed interfaces fail clearly; do not retain compatibility aliases, silent substitutions or automatic migrations.

## Composition

A reusable workflow declares the inputs and dependencies it needs, its process, useful result and stopping conditions. No fixed headings or record format are required. Apply a nested workflow in the same coordinator with its scoped inputs, applicable constraints, settings and guidance. Local additions and output locations stay local; they do not overwrite the parent or leak into siblings. Pass returned artifacts to dependent work.

An explicit `orch-work` call requires a fresh maker. Ordinary production steps leave staffing to the coordinator. Separate sessions are for actual isolation or context needs, including [workflow trials](hosts.md#workflow-trials), not a limit on procedure depth.

## Execution

Only the top-level orchestrator launches agents, assigns work and continues agents. Children do their assignments without delegating, including to existing agents or through other tools; they return results and requests to the orchestrator. Composition stays at the top level.

Resolve applicable dependencies, guidance, settings and caller constraints before dependent work. The orchestrator may work directly, continue a suitable maker or use `orch-work`, honoring scoped settings. Run independent work concurrently within host limits, with one owner for shared edits and external operations. Gather required outcomes before dependent work; missing work is a gap. Preserve authorization and reconcile uncertain actions before retrying.

Return results, supporting evidence and unresolved gaps. Keep durable state when a consumer or resumption needs it; short tasks need no checkpoint protocol. Preserve the workflow's repetition and stopping rules and caller limits. Missing capabilities block dependent work, not unrelated useful work. Report unsupported controls; never substitute self-review for required independent review.

## Iteration bounds

A bounded loop counts an attempt before its first work, including failed or paused attempts. A resumable loop records the attempt identity, starting state and updated count durably before that work. Resuming unfinished work keeps the same attempt; stale checkpoints do not reset consumption. Each workflow defines its iteration, limit and stopping conditions. These are record contents, not a shared event format or runtime.

## Review

Keep candidates stable while reviewed, and gather every required completed judgment before repairs. A verdict applies only to the state and scope inspected; a changed result does not inherit the original verdict. Independent reviewers may run checks and write separate evidence without changing the candidate. Task-only context avoids inheriting the maker's argument; disclose limits when required context isolation or blinding is unavailable.

Workflows own their review and repair counts. [orch-review-revise-once](../skills/orch-review-revise-once/SKILL.md) is a reusable process a workflow may explicitly select; it is not an automatic wrapper.

## Model and effort

Model and effort are optional choices for work, review, a stage or a named assignment. Resolve each separately: current caller instructions override saved preferences; within either source, the named assignment overrides its stage, then the operation default. Runtime assignments inherit their stage's choices. Leave unspecified controls unset. Preserve scope through composition.

Record saved preferences beside the relevant assignments only when the user asks the generated workflow to use them. The authoring session's settings do not become workflow defaults. Behavioral corrections remain in guidance.

Apply these choices to every assignment, including repairs. Direct coordinator work or reuse of an existing worker is valid only when it honors that assignment's settings; otherwise use a fresh worker. The primitives apply choices through [native host controls](hosts.md#model-and-effort); report an unsupported setting as a gap instead of substituting another value.

## Guidance selection

Guidance's common quality criteria apply to makers and reviewers. Optional `## Make` and `## Review` sections supply role-specific instructions; apply the common criteria plus the relevant section. Keep temporary model corrections separately removable. Existing role-only files remain valid. Select `orchflows` for authoring; a domain being extended is source material for its author.

The basic interface is an ordered list of applicable guidance paths, including explicit caller-supplied files. Selection determines which preferences apply, not which shared files are accessible; reading another scope's guidance as evidence does not adopt its instructions. Guidance must work without its original recipe. Techniques may be optional; required tool and correctness contracts remain required in references. Extensions refine preferences within their scope, not caller constraints, authority or workflow obligations. Resolve conflicting requirements when precedence does not determine a winner.

For named domains, resolve paths with this convenience rule, including a leaf invoked alone:

1. Select independent domain names, such as `writing`, `visual-design`, `short-video.marketing`.
2. For each name, visit dotted prefixes from general to specific. At each prefix, read core then selected libraries in caller-supplied order. Example: `short-video` across packages, then `short-video.marketing` across packages.
3. Keep each resolved file once, in first-use order. More specific guidance wins within its domain; independent domains compose.
4. Missing implicit parents are allowed; library-only domains are valid. An explicit selection must exist in core or a selected library; report a gap and block dependent work otherwise. Use general guidance for unfamiliar sites or genres.
5. Resolve package dependencies through native skills, supplied roots or the [home CLI](home.md#resolve). Reuse resolved absolute paths; extend selection when a call introduces new work. Pass only applicable guidance and scoped request context. Explicit extensions follow the defaults they refine; a missing selected file blocks dependent work. Local extensions never alter sibling selections.

Selected libraries may supply removable model corrections under existing domain names. Normal specificity applies; model names are not domain specializations.

For authoring, package layout and maintenance, use [libraries](libraries.md).
