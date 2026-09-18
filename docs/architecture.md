# Architecture

## Two primitives

- [orch-work](../skills/orch-work/SKILL.md): a fresh native child makes a result under chosen guidance.
- [orch-review](../skills/orch-review/SKILL.md): a fresh native child who did not make it reviews without fixing.

The host executes agents. The coordinator applies workflows—saved procedures—to inputs and uses their results. Workflows compose to any depth; loading one does not launch an agent, add a review or reset a bound. Prompts supply tasks; workflows preserve processes; user-owned guidance supplies quality criteria, methods and taste.

## Invocation

An explicitly selected workflow or primitive owns the process. Otherwise, [orch-dynamic-workflow](../skills/orch-dynamic-workflow/SKILL.md) may be selected automatically for top-level tasks, using core operations and guidance with review proportional to the work. Children follow assignments without starting another dynamic workflow. Other shipped skills are manual-only. Write and verify [host invocation settings](hosts.md#invocation-policy); report unenforceable policies. Selection is native, with no separate routing runtime.

Workflows compose processes and primitives directly. Explicit caller amendments may change the process; state changed guarantees, preserve primitive meanings and honor actual permissions. Each operation has one public name. Removed interfaces fail clearly, without compatibility aliases, silent substitutions or automatic migrations.

## Composition

A reusable workflow declares inputs, dependencies, process, useful result and stopping conditions; no fixed headings or record format. Apply nested workflows in the same coordinator with scoped inputs, constraints, settings and guidance. Local additions and output locations neither overwrite the parent nor leak into siblings. Pass artifacts to dependent work.

An explicit `orch-work` call requires a fresh maker; ordinary production steps leave staffing to the coordinator. Use separate sessions for isolation or context needs, including [workflow trials](hosts.md#workflow-trials), regardless of procedure depth.

## Execution

Only the top-level orchestrator launches, assigns and continues agents. Children return results and requests without delegating, including to existing agents or through other tools. Composition stays at the top level.

Resolve dependencies, guidance, settings and caller constraints before dependent work. Honor scoped settings when working directly, continuing a suitable maker or using `orch-work`. Run independent work concurrently within host limits; give shared edits and external operations one owner. Gather required outcomes before dependent work; report missing work as a gap. Preserve authorization and reconcile uncertain actions before retrying.

Return results, evidence and unresolved gaps. Keep durable state when needed by consumers or resumption; short tasks need no checkpoint protocol. Preserve workflow repetition, stopping rules and caller limits. Missing capabilities block only dependent work. Report unsupported controls; never replace required independent review with self-review.

## Iteration bounds

Count each bounded-loop attempt before its first work, including failed or paused attempts. For resumable loops, first record the attempt identity, starting state and updated count durably. Resumption keeps the same attempt; stale checkpoints do not reset consumption. Each workflow defines its iteration, limit and stopping conditions. No shared event format or runtime is required.

## Review

Keep candidates stable during review; gather every required completed judgment before repairs. Verdicts apply only to the inspected state and scope; changes do not inherit them. Reviewers may run checks and write separate evidence without changing candidates. Task-only context excludes the maker's argument; disclose unavailable required context isolation or blinding.

Workflows own review and repair counts. [orch-review-revise-once](../skills/orch-review-revise-once/SKILL.md) requires explicit selection; it never wraps a workflow automatically.

## Model and effort

Model and effort are optional for work, review, stages and named assignments. Resolve each separately: current caller instructions override saved preferences; within either source, named assignment overrides stage, then operation default. Runtime assignments inherit stage choices. Leave unspecified controls unset and preserve scope through composition.

Save preferences beside assignments only when the user requests them for the generated workflow. Authoring-session settings do not become workflow defaults. Behavioral corrections belong in guidance.

Honor settings for every assignment, including repairs. Work directly or reuse a worker only when those settings can be honored; otherwise use a fresh worker. Primitives use [native host controls](hosts.md#model-and-effort); report unsupported settings as gaps without substituting values.

## Guidance selection

Makers and reviewers apply common guidance criteria plus their optional `## Make` or `## Review` section. Keep temporary model corrections separately removable; role-only files remain valid. Select `orchflows` for authoring; the domain being extended is source material for its author.

Brevity, style and approximate file size are preferences, not acceptance gates unless the user or output contract makes them strict. Correctness, allowed effects and explicit resource bounds remain binding.

Pass an ordered list of applicable guidance paths, including caller-supplied files. Selection determines applicable preferences, not file access; reading another scope's guidance as evidence does not adopt it. Guidance must work without its original recipe. Techniques may be optional; tool and correctness contracts in references remain required. Extensions refine scoped preferences, not caller constraints, authority or workflow obligations. Resolve conflicts that precedence cannot settle.

For named domains, resolve paths with this convenience rule, including a leaf invoked alone:

1. Select independent domain names, such as `writing`, `visual-design`, `short-video.marketing`.
2. Visit each name's dotted prefixes from general to specific; at each, read core then selected libraries in caller order. Example: `short-video` across packages, then `short-video.marketing` across packages.
3. Keep each resolved file once, in first-use order. More specific guidance wins within its domain; independent domains compose.
4. Implicit parents may be missing; library-only domains are valid. Explicit selections must exist in core or a selected library; otherwise report a gap and block dependent work. Use general guidance for unfamiliar sites or genres.
5. Resolve dependencies through native skills, supplied roots or the [home CLI](home.md#resolve). Reuse absolute paths; extend selection for new work. Pass only applicable guidance and scoped request context. Explicit extensions follow their defaults; missing selected files block dependent work. Local extensions never alter siblings.

Selected libraries may supply removable model corrections under existing domain names. Normal specificity applies; model names are not domain specializations.

For authoring, package layout and maintenance, use [libraries](libraries.md).
