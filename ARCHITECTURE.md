# Architecture

Cold ownership map for executing agents. Ceiling: 850
whitespace-delimited words. Use terms exactly as
[the vocabulary](docs/vocabulary.md) defines them.

## Four tiers

- **T0 — [`contracts/`](contracts/):** the narrow waist. Each contract
  owns one pure data shape. Contract shapes are hash-pinned; a field or
  enum change is breaking even when the prose meaning is unchanged.
- **T1 — [`skills/`](skills/):** callable packages. `kernel/` owns
  primitives that call no skill; `engines/` own control flow;
  `workflows/` own assembled domain-blind behavior; `instances/` own
  concrete domain executors and lenses; `utilities/` own generic leaf
  behavior. A package owns its `SKILL.md`, `references/`, and `scripts/`.
- **T2 — [`packs/`](packs/):** domain data satisfying the
  [pack signature](contracts/pack-signature.md), never control flow.
  Cells bind generic workflows to domain slicing, execution, assembly,
  review, oracles, workspace semantics, required spec fields, and craft.
  The signature owns term-placement constraints; `craft` is the
  standing owner for domain vocabulary and domain-only shape.
- **T3 — [`compositions/`](compositions/):** named workflow templates.
  Their ticket stubs follow the
  [work-item contract](contracts/work-item.md) and are admitted through
  `orch-build`.

## Cross-cutting owners

- [`rules/`](rules/) owns cross-cutting law. Scope, dependency, and
  canonical-fact ownership are [visibility](rules/visibility.md) §§1–3's.
- [`docs/`](docs/) owns on-demand reference. `vocabulary.md` owns
  library terms; `documentation.md` owns documentation design and the
  reading order; each remaining file owns its named subject
  ([documentation design](docs/documentation.md)).
- [`scripts/`](scripts/) owns repository automation. Its programs use
  Python 3.9+, run on Windows and POSIX, and require no network at
  run time. An unprefixed family module is the public command and import
  facade; same-family helpers own internal concerns. In the ticket family,
  `tickets_format.py` owns syntax, closed parsers, and the installed pack
  mechanism registry; `tickets_markdown.py` is its private byte-preserving
  Markdown mechanism,
  `tickets_inputs.py` owns typed identity resolution, `tickets_scope.py` owns
  mutation/edge closure, and `tickets_admission.py` composes those pure lower
  graders into receipts. Lifecycle and packet modules consume admission.
  Cutcheck imports those lower owners directly, never the tickets facade;
  admission and cutcheck never import each other.
- [`tools/validate.py`](tools/validate.py) owns mechanical library-text
  admission; [`tools/check_source_sizes.py`](tools/check_source_sizes.py)
  owns executable-source line ceilings. [`tests/`](tests/) owns regression
  evidence and pinned canonical bytes. [`AGENTS.md`](AGENTS.md) owns required
  checks and local-versus-CI guidance.
- [`templates/`](templates/) owns host-block source. [`install.py`](install.py)
  is the installation compatibility facade; [`installer/`](installer/) owns
  static support, `installer/runtime.py` owns the private runtime at
  `~/.orchflows/runtime`, and the planning/application/uninstall modules own
  the immutable frontend at `~/.orchflows/ui`. User scope creates or reuses
  both; project scope verifies and borrows them, never creating an environment
  or UI distribution in a repository. Replacement is staged and probed before
  an owned prior generation moves. [`requirements-runtime.in`](requirements-runtime.in)
  and [`requirements-runtime.txt`](requirements-runtime.txt) own direct pins
  and the hash-locked runtime closure; [`pyproject.toml`](pyproject.toml)
  mirrors direct pins for tooling.
- [`package.json`](package.json) and [`pnpm-lock.yaml`](pnpm-lock.yaml) own the
  exact browser build graph; Node and pnpm stop at the repository boundary.
  [`tools/ui_frontend.py`](tools/ui_frontend.py) owns deterministic build,
  license, browser-smoke, capture, accessibility, and visual-diff admission.
  [`web/src/app/catalog.ts`](web/src/app/catalog.ts) is the one explicit typed
  owner of route matching/building, navigation order, view loading, and data
  binding; [`web/src/app/shell/`](web/src/app/shell/) owns browser location and
  reader chrome. [`web/src/features/`](web/src/features/) owns feature-local
  routes, schemas, requests, projections, models, views, fixtures, styles, and
  tests. [`web/src/shared/transport/`](web/src/shared/transport/) owns
  feature-blind HTTP, ETag, retry, generation, and polling mechanics.
  [`web/src/design/`](web/src/design/) and [`web/src/styles/`](web/src/styles/)
  own tokens. Dependency direction is `shell -> catalog -> feature -> shared`.
  `web/dist` owns the committed content-hashed distribution copied by the
  installer. The installed reader never invokes a frontend package manager or
  build.
- [`DESIGN.md`](DESIGN.md) owns non-normative rationale. [`README.md`](README.md)
  is the non-normative human entry surface, not an owner of agent law.

## Runtime routing pins

Helper membership is derived from code, not inventoried here. Two
non-derivable admission facts stay pinned: `scripts/cutcheck.py` owns
cut-defect detection over issued ticket sets; `scripts/tickets.py` owns
the public ticket facade, the one root/gate
family, immutable run identity (`opened_at`, installed version, source commit),
and immutable terminal timing (`terminal_at`, terminal ticket, `elapsed_ms`).
`tickets.py help` is operator-only: it answers an operator's usage request.
`tickets.py grant` is operator-only: only the dispatcher widens claimed
authority.

The UI reader family keeps one closed boundary: `scripts/ui_api.py` owns
explicit route assembly, query validation, shared JSON ETags and closed
failures, security middleware, and loopback Starlette/Uvicorn with fallback
parity. Domain projections belong to `scripts/ui_artifacts_projection.py`,
`scripts/ui_now_projection.py`,
`scripts/ui_runs_projection.py`, `scripts/ui_workflows_projection.py`,
`scripts/ui_sessions_projection.py`, and `scripts/ui_friction_projection.py`.
The Workflows projector owns `GET /api/v1/workflows`,
`GET /api/v1/workflows/{workflow_id}`, and
`GET /api/v1/workflows/{workflow_id}/sources/{source_id}`; the typed catalog
owns their browser counterparts `/workflows`, `/workflows/{workflow}`, and
`/workflows/{workflow}/sources/{source}`. Existing `/runs/{run}` and
`/runs/{run}/tickets/{ticket}` remain nav-hidden Workflows children.
`scripts/ui_experience.py` owns only the `orchflows.experience.v1`
compatibility projection, its closed feature slices, navigation contract, and
SPA-path recognition. `scripts/ui_assets.py` owns contained immutable-asset
reads and the standard-library compatibility server; `scripts/ui_readiness.py`
owns canonical readiness facts and causal explanations. Legacy rendering
stays in `scripts/ui_server.py`.
[The platform contract](docs/ui/platform.md) owns the complete boundary.

## State boundary

- state sink — root, trust boundary, write law, record requirements, and
  failure behavior: [visibility §6](rules/visibility.md). Resolver:
  [`scripts/state_root.py`](scripts/state_root.py). Research evidence lives in
  the sink's `research/` tree.
- `.orch/` holds tracked `canary/` fixtures and project-scope installed `bin/`
  scripts only.

## Dependency direction

Arrows point from a reader or binder to what it depends on:

`AGENTS.md` → `rules/` → `contracts/` → `skills/` → package `scripts/`.

Packs depend on contracts and may name instance skills. Generic skills
never name a pack or domain. Composition stubs bind skills or scripts as
executors; no skill depends on a composition template. A lower layer may
link the law or contract that binds it, but a rule never depends on
package internals for its meaning. Shared packages never name project
packages; project packages may name visible shared packages.
