# Architecture

## Two primitives

- [orch-work](../skills/orch-work/SKILL.md): a fresh native child makes a result under chosen guidance.
- [orch-review](../skills/orch-review/SKILL.md): a fresh native child who did not make it reviews without fixing.

All delegation goes through these primitives. The host owns agent execution; orchflows adds no runtime, scheduler or workflow language. Loading a `SKILL.md` applies its instructions in the caller's context; it does not launch an agent. Composing workflows add only their own decisions and supply each child's assignment and context.

Workflows preserve commitments between pieces of work. Prompts supply the current task; guidance supplies quality, methods and taste. The caller applies the [execution rules](#execution) before dispatch. A stage is not an agent: several stages may share a maker, and one stage may use several workers where the selected workflow permits it.

## Where things live

Give each instruction and mechanism one owner; reference shared facts. READMEs address humans; other live documentation addresses agents.

| Concept | Owner / location |
| --- | --- |
| Request and defaults: question, dates, sources, bounds, model, effort, output location | Caller prompt; [model and effort](#model-and-effort) covers saved preferences |
| Saved process: dependencies, independence, gates, repetition, allowed effects and default bounds | Composing workflow's `SKILL.md` |
| Actual assignments, concurrency, ownership, integration and cumulative use | Caller applying the execution rules within the saved process and current request |
| Quality criteria, including source-specific preferences | `guidance/<domain>.md` |
| Shared contracts and operational knowledge | Library `references/`; skill-local `references/` for one consumer |
| Package dependencies and guidance requirements | `references/library-context.md`, reused by entrypoints |
| Resolved paths and request context | Outermost entrypoint; pass through composed calls |
| Deterministic mechanics | Owning skill's `scripts/`, with sibling `tests/`; core CLI in `scripts/` |
| Package identity | Root `plugin.json` |
| Native skill discovery | Host manifests and catalogs per [hosts.md](hosts.md) |
| Host registration, execution and isolation facts | [hosts.md](hosts.md) |
| Setup, updates and home paths | [home.md](home.md) |
| Transcript access and interpretation | [history.md](history.md) |
| Run outputs and evidence | Caller workspace, never a package |

## Invocation

[orch-dynamic-workflow](../skills/orch-dynamic-workflow/SKILL.md) is the automatic fallback when no more specific workflow or skill fits the request. Other core skills, every workflow under `example-workflows/`, and custom workflows in `~/.orchflows/libraries/` (including `personal`) are manual-only by default; automatic selection for those skills requires the caller's opt-in. When creating or copying a workflow, write and verify the [host invocation settings](hosts.md#invocation-policy) for every skill, including helpers; report a host that cannot enforce this policy. An explicitly requested workflow still supplies its own composition and guidance.

An explicit caller amendment can select a modified process; state any changed guarantee. Skipping review produces an unreviewed result. Vague urgency does not cancel a required stage, and an amendment does not redefine the primitives or bypass actual permissions.

## Execution

Resolve the result, dependencies, selected guidance, scoped settings and bounds before planning assignments. Split work around shared prerequisites, useful independence and edit conflicts. Run independent assignments concurrently within host and resource limits; start dependent work when its inputs are ready. Give each assignment enough context, clear ownership and a useful result to return. Gathering and integration are ordinary coordination, not extra agents or required helper skills.

Gather every actual outcome, reconcile overlaps and give each shared fix or integration task one owner. Missing or unfinished work is a gap. Return compact handoffs with useful results, artifact identities or paths, evidence, decisions and gaps; keep large raw evidence available for inspection instead of copying it through every prompt. Checkpoints and accepted-state records belong to workflows that need resumption or adoption, not every small task.

Review identified stable work with children who did not make it. When the workflow permits parallel review, assign coverage of the whole result and its interactions, then gather findings before repairs. Multiple reviewers of the same candidate form one review round; review of a revised candidate is another. A repair pass includes changes and affected checks, not another independent review. A changed candidate does not inherit the old verdict.

For external actions, preserve the selected authority boundary and reconcile an uncertain outcome before retrying. Reuse applicable authorization already supplied; do not invent approval stages.

### Bounds

Finite workflows declare a default total child-start ceiling or a finite formula from their resolved inputs, plus any repetition and stopping rules. A fixed-count recipe retains its count. State the resolved ceiling and initial allocation before dispatch, reserving allowance for required later stages. Concurrency is a separate limit, not a total budget. A requested number of independent alternatives or judges is a process requirement unless the caller changes it.

Composed calls inherit the remaining allowance; their standalone defaults never replenish it. Count failed or interrupted starts, replacements, nested trial children and any delegated integration. Rejoining a child is not a new start, but continuing work still consumes applicable time and cost limits. Resume preserves usage. Reallocate within the ceiling only where the workflow allows it; extra stages, review rounds or repairs need a caller request. If required work cannot fit, return the achievable result and gap rather than claim completion.

Honor time and spending limits using available measurements and report unsupported controls. Child count is not an exact cost bound. Explicit continuous workflows use bounded batches and cumulative checkpoints under the caller's stop conditions, without an invented total round cap.

## Model and effort

Model and effort are optional choices for work, review, a stage or a named assignment. Resolve each setting separately: current caller instructions override saved workflow preferences; within either source, the named assignment overrides its parent stage, then the operation default. Runtime assignments inherit their stage's scoped choices. Leave unspecified controls unset for the host to resolve. Keep the caller's choices and their scope with request context through composed workflows.

Record saved preferences beside the relevant assignments only when the user asks the generated workflow to use them. The authoring session's settings do not become workflow defaults. Plain language is sufficient; no model file or role registry is required. Behavioral corrections remain in guidance.

Apply these choices to every assignment, including repairs. Direct coordinator work or reuse of an existing worker is valid only when it honors that assignment's settings; otherwise use a fresh worker. The primitives apply choices through [native host controls](hosts.md#model-and-effort); report an unsupported setting as a gap instead of substituting another value.

## Guidance selection

Guidance records domain preferences in `## Make` and `## Review`; omit empty sections. Apply Make when producing and Review when assessing. Workflows name required domains; select `orchflows` for authoring workflows, guidance or libraries. A domain being extended is source material for its author.

Guidance must make relevant supporting references discoverable without its original recipe. It may explain an ordered technique within an assignment; delegation, gates and review or repair rounds belong in the workflow. Keep enough domain meaning in the workflow to identify its inputs, outputs and decisions.

Resolve once at the outer entrypoint, including a leaf invoked alone:

1. Select independent domain names, such as `writing`, `visual-design`, `short-video.marketing`.
2. For each name, visit dotted prefixes from general to specific. At each prefix, read core then selected libraries in caller-supplied order. Example: `short-video` across packages, then `short-video.marketing` across packages.
3. Keep each resolved file once, in first-use order. More specific guidance wins within its domain; independent domains compose.
4. Missing implicit parents are allowed; library-only domains are valid. An explicit selection must exist in core or a selected library; report a gap and block dependent work otherwise. Use general guidance for unfamiliar sites or genres.
5. Resolve package dependencies through native skills, supplied roots or the [home CLI](home.md#resolve). Pass absolute paths and request context unchanged to composed skills and primitives; extend only for new dependencies.

Selected libraries may supply removable model corrections under existing domain names. Normal specificity applies; model names are not domain specializations.

## Three roots

| Root | Contents / editing owner |
| --- | --- |
| Core checkout | Built-in `skills/orch-*/`, guidance, docs, CLI, tests, example libraries; orchflows developers |
| Home `~/.orchflows` | User-owned libraries and runtime; setup-managed core per [home.md](home.md) |
| Project workspace | Task outputs |

Reserve `orch-` for built-ins. Create custom workflows in `~/.orchflows/libraries/personal/skills/<workflow>/` unless the caller names another library or repository. Edit the checkout or user library, never managed core or host caches.

Setup's `CORE_ENTRIES` in `scripts/orchflows.py` owns the shipped file list. Tests and example libraries stay in the checkout; core Markdown links must resolve within the shipped core. To update core: edit the checkout, run `python -m unittest discover -s tests`, then [load it for development](hosts.md#register-and-refresh) or [run setup](home.md#setup) to update a home.

## A library

```text
<library>/
├── plugin.json                     package identity; Antigravity manifest
├── .claude-plugin/plugin.json      Claude, Grok Build and ZCode manifest
├── .codex-plugin/plugin.json       Codex manifest
├── .kimi-plugin/plugin.json        Kimi Code manifest
├── README.md                       composition, bounds, install, dependencies
├── references/                     shared context and contracts
├── guidance/<domain>.md            domain or dotted specialization
├── skills/<skill>/SKILL.md          frontmatter, invocation policy; instructions
├── skills/<skill>/agents/openai.yaml Codex invocation policy and UI metadata
├── skills/<skill>/references/       knowledge used by this skill only
├── skills/<skill>/scripts/          mechanics; sibling tests/
└── trials/                         request.md, expected-behavior.md
```

Skill identity is `<library>:<skill>`; [host invocation syntax](hosts.md#invocation-policy) can differ. Keep links within the package; reach other packages by native skill name or resolved paths. Never embed machine-specific paths. Declare runtime dependencies in the README; setup installs none for libraries. Root `plugin.json` declares `name`, `version` and `skills: "./skills/"` and also serves Antigravity. Keep the name and version aligned across host manifests; Kimi's manifest declares `skills: "./skills/"`. Existing user libraries need that manifest before installation in Kimi.

A reusable component declares its inputs and dependencies, promised process and allowed effects, outputs including gaps, and standalone bounds. Extract meaningful process commitments or useful domain interfaces, not every verb. Domain components stay in their libraries; an optional shared library can own processes used across domains. Core remains independent of optional libraries. No numbered tier hierarchy or central helper dependency is required.

## Invariants

- Skills name scripts, inputs and results; scripts own their internals.
- Resolve and declare bounds and allocation before dispatch; composition, retries and resume share cumulative usage. Preserve explicit process requirements.
- Report missing work as a gap, never as no-results evidence.
- Establish behavior with a real bounded trial. Valid frontmatter proves no behavior; unexercised failure paths remain untested.
