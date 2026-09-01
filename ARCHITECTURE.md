# Architecture

Ceiling: 925 whitespace-delimited words. Terms are
[the vocabulary](docs/vocabulary.md)'s. Raised from 850 for the ring
family's five owner modules.

## Four tiers

- **T0 — [`contracts/`](contracts/):** the narrow waist. Each contract
  owns one pure data shape, hash-pinned: a field or enum change breaks
  it even when the prose meaning holds.
  [`dispatch.md`](contracts/dispatch.md) owns v1 grammar.
- **T1 — [`skills/`](skills/):** callable packages. `kernel/` owns the
  two bricks; `workflows/` domain-blind behavior. Control
  flow is not a tier: it is the caller's prose. A package
  owns its `SKILL.md`, `references/`, `scripts/`.
- **T2 — [`packs/`](packs/):** domain data satisfying the
  [pack signature](contracts/pack-signature.md), never control flow.
  Cells bind generic workflows to the domain concerns the signature
  lists; the signature owns term-placement constraints, `craft` domain
  vocabulary and domain-only shape.
- **T3 — [`example-workflows/`](example-workflows/):** named workflows, each
  a skill body calling bricks; their authoring standard is
  [custom workflow authoring](docs/custom-workflow-authoring.md).

## Cross-cutting owners

- [`rules/`](rules/) owns cross-cutting law. Scope, dependency,
  canonical-fact ownership are [visibility](rules/visibility.md) §§1–3's.
- [`docs/`](docs/) owns on-demand reference. `vocabulary.md` owns
  library terms; `documentation.md` documentation design and the
  reading order; each remaining file its named subject.
- [`scripts/`](scripts/) owns repository automation. Programs use Python
  3.9+, Windows and POSIX, then no network. An unprefixed family module is
  the public command and import facade; same-family helpers own internal concerns.
  `tickets_format.py` owns syntax, closed parsers, and the pack registry;
  `tickets_markdown.py` semantic payload parsing and byte preservation;
  `tickets_admission.py` receipt lifecycle; `tickets_generations.py` immutable
  generation and seal identities; `tickets_project.py` run-project binding;
  `tickets_dispatch_schema.py` validates dispatch grammar; `tickets_attempts.py`
  mutates atomically;
  `tickets_join.py` reserved outcome import and outcome-fenced lifecycle joins;
  `tickets_emission.py` emission grading; `tickets_issue_render.py`
  issuance markdown; `tickets_brick.py` and `tickets_frame.py` the brick
  and frame doors;
  `tickets_dispatch_launch.py` resolves the host launch binding. `cutcheck.py`
  owns structural graph validation.
  Cutcheck imports those owners directly, never the tickets facade;
  admission and cutcheck never import each other.
- [`scripts/workspace.py`](scripts/workspace.py) owns a candidate worktree's
  whole life: `establish` creates and records it, `prepare` installs what it
  declares, `retire` removes it. [`scripts/state_root.py`](scripts/state_root.py)
  alone derives that path and branch; nothing else computes either.
- [`scripts/rings.py`](scripts/rings.py) owns the one ring resolution order —
  project, home, pinned imports, lib — with its reserved-prefix floor and
  shadow notices; `packs_support.py` and `tickets_adapters.py` route through
  it and spell no root of their own. `rings_trust.py` owns the never-portable
  trust ledger. `orchflows.py` is the ring and resume command surface over
  `orchflows_home.py` (home layout, the committed/regenerable line, pins),
  `orchflows_scaffold.py` (`new` skeletons) and `orchflows_adapters.py`
  (generated inert host adapters).
- [`tools/validate.py`](tools/validate.py) owns mechanical library-text
  admission; [`tools/check_source_sizes.py`](tools/check_source_sizes.py)
  the warn-only executable-source size report.
  [`tools/regen.py`](tools/regen.py) owns every derived artifact's generator and
  the drift check validate calls.
  [`tools/run_required.py`](tools/run_required.py) owns the local
  required-check run and its tree-keyed verdict cache.
  [`tools/affected_tests.py`](tools/affected_tests.py) owns
  changed-path-to-test-module derivation.
  [`tools/run_report.py`](tools/run_report.py) owns the retrospective speed
  report. [`tools/verify_at.py`](tools/verify_at.py) owns running a command
  in a detached worktree at an exact revision;
  [`tools/run_tests_scope.py`](tools/run_tests_scope.py) scoped test
  selection.
  [`tests/`](tests/) owns regression evidence and pinned canonical
  bytes; [`AGENTS.md`](AGENTS.md) required checks and local-versus-CI
  guidance.
- [`templates/`](templates/) owns host-block source. [`install.py`](install.py)
  is the installation compatibility facade; [`installer/`](installer/) owns
  static support, `installer/runtime.py` the private runtime at
  `~/.orchflows/runtime`, and the planning/application/uninstall modules the
  immutable frontend at `~/.orchflows/ui`. User installation is the sole scope,
  creating or reusing both; replacement is staged and
  probed before an owned prior generation moves. A script module shared with the
  reader is carried in two layouts and must be listed for both — flat `bin/`
  through `installer/inventory.py`, the reader package through
  `installer/planning_support.py` — or the reader fails at first import.
  [`requirements-runtime.in`](requirements-runtime.in)
  and [`requirements-runtime.txt`](requirements-runtime.txt) own direct pins
  and the hash-locked runtime closure; [`pyproject.toml`](pyproject.toml)
  mirrors them for tooling.
- [`reader/`](reader/) owns the Observe browser, projection family, and
  committed content-hashed distribution; its closed `/api/v1` API is the sole
  state-sink seam and the installed reader never runs a package manager or
  build. Its browser dependency direction is `shell -> catalog -> feature ->
  shared`, with one named reuse edge: the Now view renders the Workflows-owned
  [`SummaryFlow`](reader/web/src/features/workflows/view/SummaryFlow.tsx)
  flowchart and stylesheet rather than paralleling it.
- [`DESIGN.md`](DESIGN.md) owns non-normative rationale; [`README.md`](README.md)
  is the human entry surface, not an owner of agent law.

## Runtime routing pins

Helper membership derives from code, not inventoried here. Two
non-derivable facts: `scripts/cutcheck.py` owns cut-defect
detection over issued ticket sets; `scripts/tickets.py` owns
the public ticket facade, the one root and
review family, immutable run identity (`opened_at`, installed version, source commit),
immutable terminal timing (`terminal_at`, terminal ticket, `elapsed_ms`).
Its `dispatch` owns one launch and its `land` one return, each a single
transaction over the granular operations, which stay public for recovery.
`tickets.py help` is operator-only: it answers usage requests.

The reader family keeps one closed boundary: `reader/scripts/ui_api.py` owns
route assembly, query validation, shared JSON ETags and closed failures,
security middleware, and loopback Starlette/Uvicorn. Domain projections belong
to the sibling modules under `reader/scripts/`; the typed catalog owns browser
counterparts under `/workflows`. `reader/scripts/ui_assets.py` owns contained
immutable-asset reads and `reader/scripts/ui_readiness.py` owns canonical
readiness facts and causal explanations.
[The platform contract](reader/docs/platform.md) owns the complete boundary.

## State boundary

- state sink — root, trust boundary, write law, record requirements,
  failure behavior: [visibility §6](rules/visibility.md). Resolver:
  [`scripts/state_root.py`](scripts/state_root.py). Research evidence lives in
  the sink's `research/` tree.
- `.orch/` is generated, never tracked: legacy `bin/` scripts named by
  project receipts, whose cleanup stays receipt-driven through
  uninstall.

## Dependency direction

Arrows point from reader or binder to dependency:

`AGENTS.md` → `rules/` → `contracts/` → `skills/` → package `scripts/`.

Packs depend on contracts and may name callable skills. Generic skills
never name a pack or domain. A workflow calls skills and
scripts; no skill depends on a workflow. A lower layer
may link the law or contract binding it; a rule never depends on
package internals for its meaning. Shared packages never name project packages;
project packages may name visible ones.
