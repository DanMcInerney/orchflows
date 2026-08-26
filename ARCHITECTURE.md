# Architecture

Agent-facing cold ownership map. Ceiling: 850
whitespace-delimited words. Terms are
[the vocabulary](docs/vocabulary.md)'s.

## Four tiers

- **T0 — [`contracts/`](contracts/):** the narrow waist. Each contract
  owns one pure data shape, hash-pinned: a field or enum change breaks
  it even when the prose meaning holds.
- **T1 — [`skills/`](skills/):** callable packages. `kernel/` owns
  skill-free primitives; `engines/` control flow; `workflows/`
  domain-blind behavior; `instances/` domain executors/lenses;
  `utilities/` generic leaves. A package owns its `SKILL.md`,
  `references/`, `scripts/`.
- **T2 — [`packs/`](packs/):** domain data satisfying the
  [pack signature](contracts/pack-signature.md), never control flow.
  Cells bind generic workflows to the domain concerns the signature
  lists; the signature owns term-placement constraints, `craft` domain
  vocabulary and domain-only shape.
- **T3 — [`compositions/`](compositions/):** named workflow templates.
  Their ticket stubs follow the
  [work-item contract](contracts/work-item.md) via `orch-build`.

## Cross-cutting owners

- [`rules/`](rules/) owns cross-cutting law. Scope, dependency,
  canonical-fact ownership are [visibility](rules/visibility.md) §§1–3's.
- [`docs/`](docs/) owns on-demand reference. `vocabulary.md` owns
  library terms; `documentation.md` documentation design and the
  reading order; each remaining file its named subject.
- [`scripts/`](scripts/) owns repository automation. Programs use Python 3.9+
  on Windows and POSIX, no network at run time. An unprefixed family module is the public command
  and import facade; same-family helpers own internal concerns.
  `tickets_format.py` owns syntax, closed parsers, and the
  installed pack mechanism registry; `tickets_markdown.py`
  is its private byte-preserving mechanism; `tickets_inputs.py` typed
  identity resolution; `tickets_scope.py` mutation/edge closure;
  `tickets_admission.py` composes those into receipts lifecycle and packet
  modules consume. `tickets_successor_context.py` owns dependency digest
  hydration, canonical Context precedence, and legacy Carry provenance.
  `tickets_project.py` owns run-project binding,
  `tickets_emission.py` emission grading, `tickets_ceiling.py` instruction
  ceiling, `tickets_dispatch_gate.py` the gate family and
  mutation plan, `cutcheck_pricing.py` cut pricing.
  Cutcheck imports those owners, never the tickets facade; it and admission
  never cross-import.
- [`tools/validate.py`](tools/validate.py) owns mechanical library-text
  admission; [`tools/check_source_sizes.py`](tools/check_source_sizes.py)
  executable-source line ceilings.
  [`tools/run_required.py`](tools/run_required.py) owns the local
  required-check run and its tree-keyed verdict cache.
  [`tools/affected_tests.py`](tools/affected_tests.py) owns
  write-scope-to-test-module derivation.
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
  probed before an owned prior generation moves.
  [`requirements-runtime.in`](requirements-runtime.in)
  and [`requirements-runtime.txt`](requirements-runtime.txt) own direct pins
  and the hash-locked runtime closure; [`pyproject.toml`](pyproject.toml)
  mirrors them for tooling.
- [`package.json`](package.json) and [`pnpm-lock.yaml`](pnpm-lock.yaml) own the
  exact browser build graph; Node and pnpm stop at the repository boundary.
  [`tools/ui_frontend.py`](tools/ui_frontend.py) owns deterministic build,
  license, browser-smoke, capture, accessibility, visual-diff admission.
  [`web/src/app/catalog.ts`](web/src/app/catalog.ts) owns route
  matching/building, navigation order, view loading, data binding;
  [`web/src/app/shell/`](web/src/app/shell/) owns browser location and
  reader chrome. [`web/src/features/`](web/src/features/) owns each
  feature's routes, schemas, requests, projections, models, views,
  fixtures, styles, tests.
  [`web/src/shared/transport/`](web/src/shared/transport/) owns
  feature-blind HTTP, ETag, retry, generation, polling mechanics.
  [`web/src/design/`](web/src/design/) and [`web/src/styles/`](web/src/styles/)
  own tokens. Dependency direction: `shell -> catalog -> feature -> shared`,
  with one named reuse edge: the Now view renders the Workflows-owned
  [`SummaryFlow`](web/src/features/workflows/view/SummaryFlow.tsx) flowchart
  and its stylesheet rather than paralleling it; Workflows keeps ownership, and a
  second summary-flow component is a defect.
  `web/dist` owns the committed content-hashed distribution the installer
  copies; the installed reader never runs a package manager or build.
- [`DESIGN.md`](DESIGN.md) owns non-normative rationale; [`README.md`](README.md)
  is the human entry surface, not an owner of agent law.

## Runtime routing pins

Helper membership derives from code, not inventoried here. Two
non-derivable facts: `scripts/cutcheck.py` owns cut-defect
detection over issued ticket sets; `scripts/tickets.py` owns
the public ticket facade, the one root/gate
family, immutable run identity (`opened_at`, installed version, source commit),
immutable terminal timing (`terminal_at`, terminal ticket, `elapsed_ms`).
`tickets.py help` is operator-only: it answers usage requests.
`tickets.py grant` is operator-only: only the dispatcher widens claimed
authority.

The UI reader family keeps one closed boundary: `scripts/ui_api.py` owns
route assembly, query validation, shared JSON ETags and closed failures,
security middleware, loopback Starlette/Uvicorn with fallback parity.
Domain projections belong to `scripts/ui_artifacts_projection.py`,
`scripts/ui_now_projection.py`,
`scripts/ui_runs_projection.py`, `scripts/ui_workflows_projection.py`,
`scripts/ui_sessions_projection.py`, `scripts/ui_friction_projection.py`.
The Workflows projector owns `/api/v1/workflows`,
`/api/v1/workflows/{workflow_id}`,
`/api/v1/workflows/{workflow_id}/sources/{source_id}`; the typed catalog
owns their browser counterparts under `/workflows`.
`scripts/ui_experience.py` owns only the `orchflows.experience.v1`
compatibility projection: closed feature slices, navigation contract,
SPA-path recognition. `scripts/ui_assets.py` owns contained immutable-asset
reads and the standard-library compatibility server; `scripts/ui_readiness.py`
owns canonical readiness facts and causal explanations. Legacy rendering
stays in `scripts/ui_server.py`.
[The platform contract](docs/ui/platform.md) owns the complete boundary.

## State boundary

- state sink — root, trust boundary, write law, record requirements,
  failure behavior: [visibility §6](rules/visibility.md). Resolver:
  [`scripts/state_root.py`](scripts/state_root.py). Research evidence lives in
  the sink's `research/` tree.
- `.orch/` holds tracked `canary/` fixtures and legacy generated `bin/`
  scripts named by project receipts; cleanup stays receipt-driven through
  uninstall.

## Dependency direction

Arrows point from reader or binder to dependency:

`AGENTS.md` → `rules/` → `contracts/` → `skills/` → package `scripts/`.

Packs depend on contracts and may name instance skills. Generic skills
never name a pack or domain. Composition stubs bind skills or scripts as
executors; no skill depends on a composition template. A lower layer
may link the law or contract binding it; a rule never depends on
package internals for its meaning. Shared packages never name project packages;
project packages may name visible ones.
