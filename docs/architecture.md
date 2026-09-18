# Architecture

## Two primitives

- [orch-work](../skills/orch-work/SKILL.md): a fresh native child makes a result under chosen guidance.
- [orch-review](../skills/orch-review/SKILL.md): a fresh native child who did not make it reviews without fixing.

The host executes agents. The top-level orchestrator applies composed skills as instructions and dispatches their assignments through these primitives. Loading a skill does not launch an agent. Workflows preserve process; prompts supply the current task; guidance supplies methods and taste.

## Where things live

Give each instruction and mechanism one owner; reference shared facts. READMEs address humans; other live documentation addresses agents.

| Concept | Owner / location |
| --- | --- |
| Request and defaults: question, dates, sources, bounds, model, effort, output location | Caller prompt; [model and effort](#model-and-effort) covers saved preferences |
| Saved process: dependencies, independence, gates, repetition, stopping conditions and allowed effects | Composing workflow's `SKILL.md` |
| Actual assignments, concurrency, ownership and integration | Caller applying the execution rules |
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

[orch-dynamic-workflow](../skills/orch-dynamic-workflow/SKILL.md) is the automatic fallback for top-level requests when no more specific workflow or skill fits. Other core skills, every workflow under `example-workflows/`, and custom workflows in `~/.orchflows/libraries/` (including `personal`) are manual-only by default; automatic selection for those skills requires the caller's opt-in. When creating or copying a workflow, write and verify the [host invocation settings](hosts.md#invocation-policy) for every skill, including helpers; report a host that cannot enforce this policy.

Saved workflows compose their chosen processes and primitives directly. The dynamic fallback is not a component. Explicit caller amendments can change the process; state any changed guarantee, preserve primitive meanings and honor actual permissions.

## Execution

Only the top-level orchestrator launches agents, assigns work and continues agents. Children do their assignments without delegating, including to existing agents or through other tools; they return results and requests to the orchestrator. Composition stays at the top level.

Resolve dependencies, guidance, settings and caller constraints before planning. The orchestrator does clear work directly when settings permit and chooses maker staffing. Split when useful; run independent work concurrently within host limits. Gather the required outcomes before dependent work, keeping missing work as a gap. Give each shared fix, integration and external operation one owner. Preserve authorization and reconcile uncertain actions before retrying.

Return compact handoffs with inspectable evidence. Keep checkpoints and native handles when resuming. Preserve the workflow's repetition and stopping rules and explicit caller limits; report unsupported controls. Extra stages require a caller amendment. Persistent inability to progress returns a gap; continuous work follows its requested stop conditions.

## Standard review and repair

A workflow may select this pattern after producing and joining its result. One independent child who made none of it reviews the whole stable result through `orch-review`, reporting findings and coverage gaps without edits. Wait for the reviewer to finish before repairs.

If needed, make one coordinated repair pass. Use the orchestrator, a continued maker or `orch-work`, honoring the fixer's settings. Prefer one fixer; independent repairs may use several, with one owner per shared fix. Run affected checks and caller-required verification even when no repair was needed. There is no second review; a revision does not inherit the original verdict.

Workflows may select different processes, such as comparison, specialist reviews or confirmation. Gather every required judgment before repairing. Selecting this pattern does not add reviews to its internal stages.

## Model and effort

Model and effort are optional choices for work, review, a stage or a named assignment. Resolve each separately: current caller instructions override saved preferences; within either source, the named assignment overrides its stage, then the operation default. Runtime assignments inherit their stage's choices. Leave unspecified controls unset. Preserve scope through composition.

Record saved preferences beside the relevant assignments only when the user asks the generated workflow to use them. The authoring session's settings do not become workflow defaults. Behavioral corrections remain in guidance.

Apply these choices to every assignment, including repairs. Direct coordinator work or reuse of an existing worker is valid only when it honors that assignment's settings; otherwise use a fresh worker. The primitives apply choices through [native host controls](hosts.md#model-and-effort); report an unsupported setting as a gap instead of substituting another value.

## Guidance selection

Guidance records domain preferences in `## Make` and `## Review`; omit empty sections. Apply Make when producing and Review when assessing. Workflows name required domains; select `orchflows` for authoring workflows, guidance or libraries. A domain being extended is source material for its author.

Guidance must work without its original recipe and expose relevant supporting references. It may explain techniques within an assignment; delegation and gates belong in workflows. Route guidance by role or kind of work, not numbered child.

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
├── README.md                       composition, stopping rules, dependencies
├── references/                     shared context and contracts
├── guidance/<domain>.md            domain or dotted specialization
├── skills/<skill>/SKILL.md          frontmatter, invocation policy; instructions
├── skills/<skill>/agents/openai.yaml Codex invocation policy and UI metadata
├── skills/<skill>/references/       knowledge used by this skill only
├── skills/<skill>/scripts/          mechanics; sibling tests/
└── trials/                         request.md, expected-behavior.md
```

Skill identity is `<library>:<skill>`; [host invocation syntax](hosts.md#invocation-policy) can differ. Keep links within the package; reach other packages by native skill name or resolved paths. Never embed machine-specific paths. Declare runtime dependencies in the README; setup installs none for libraries. Root `plugin.json` declares `name`, `version` and `skills: "./skills/"` and also serves Antigravity. Keep the name and version aligned across host manifests; Kimi's manifest declares `skills: "./skills/"`. Existing user libraries need that manifest before installation in Kimi.

A reusable component declares inputs, dependencies, process, allowed effects, outputs and stopping conditions. Domain components stay in their libraries; optional shared libraries own cross-domain processes. Core remains independent of them.

## Invariants

- Skills name scripts, inputs and results; scripts own their internals.
- Establish behavior with a real bounded trial. Valid frontmatter proves no behavior; unexercised failure paths remain untested.
