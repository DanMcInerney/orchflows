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
  stdlib Python 3, run on Windows and POSIX, and require no network at
  run time. An unprefixed family module is the public command and import
  facade; same-family helpers own internal concerns.
- [`tools/validate.py`](tools/validate.py) owns mechanical library-text
  admission. [`tests/`](tests/) owns executable regression evidence and
  pinned canonical bytes. [`AGENTS.md`](AGENTS.md) owns the repository's
  required check commands and local-versus-CI guidance.
- [`templates/`](templates/) owns host-block source. [`install.py`](install.py)
  owns installation and removal behavior; its docstring is the detailed
  write-scope owner.
- [`DESIGN.md`](DESIGN.md) owns non-normative rationale. [`README.md`](README.md)
  is the non-normative human entry surface, not an owner of agent law.

## Script responsibility index

Cut checking: `scripts/cutcheck.py` owns cut-defect detection over issued
ticket sets; `scripts/cutcheck_commands.py` owns oracle-command extraction
and classification; `scripts/cutcheck_contract.py` owns shared constants and
invocation state; `scripts/cutcheck_coverage.py` owns coverage-map grading;
`scripts/cutcheck_execute.py` owns oracle execution and discrimination;
`scripts/cutcheck_executor.py` owns pack-cell resolution and executor-legality
grading; `scripts/cutcheck_graph.py` owns graph-layout grading and readings;
`scripts/cutcheck_scope.py` owns citation, path, and write-scope closure;
`scripts/cutcheck_scratch.py` owns scratch-tree lifecycle;
`scripts/cutcheck_search.py` owns search-span and whole-suite command grading;
`scripts/cutcheck_state.py` owns repository and run-state resolution;
`scripts/cutcheck_ticket.py` owns per-ticket finding assembly.

General utilities: `scripts/doclint.py` owns repository Markdown grading;
`scripts/friction.py` owns friction logging; `scripts/isolate.py` owns isolated
revision export; `scripts/state_root.py` owns state-sink resolution.

State migration: `scripts/migrate_state.py` owns the public migration facade;
`scripts/migrate_state_plan.py` owns collision-aware planning and application;
`scripts/migrate_state_records.py` owns record attribution and transformation.

Bounded search: `scripts/search_plan.py` owns the public bounded-search facade;
`scripts/search_plan_advance.py` owns generation advance;
`scripts/search_plan_archive.py` owns Pareto-archive updates and ordering;
`scripts/search_plan_projection.py` owns projection validation and search-slot
proposals; `scripts/search_plan_protocol.py` owns request parsing and protocol
validation.

Tickets: `scripts/tickets.py` owns the public ticket facade, the one root/gate
family, immutable run identity (`opened_at`, installed version, source commit),
and immutable terminal timing (`terminal_at`, terminal ticket, `elapsed_ms`);
`scripts/tickets_dispatch.py` owns instantiation, root-gate creation, help,
improvement routing, and top-level dispatch; `scripts/tickets_format.py` owns
frontmatter, section, criterion, and format validation;
`scripts/tickets_issue.py` owns rendering, issue, placement, and pre-claim
amendment; `scripts/tickets_lifecycle.py` owns listing, readiness, claim, grant,
check, and status transitions; `scripts/tickets_packet.py` owns dispatch packets
and gate-child prompts; `scripts/tickets_result.py` owns executor-section,
run-state, and improvement-record writes; `scripts/tickets_store.py` owns sink
paths, identities, locking, and atomic file primitives;
`scripts/tickets_worklog.py` owns template-graph defects and worklog rendering.
`tickets.py help` is operator-only: it answers an operator's usage request.
`tickets.py grant` is operator-only: only the dispatcher widens claimed
authority.

Trace: `scripts/trace.py` owns the public trace-extraction facade;
`scripts/trace_claude.py` owns Claude Code extraction;
`scripts/trace_codex.py` owns Codex rollout extraction;
`scripts/trace_render.py` owns normalization and Mermaid rendering.

UI: `scripts/ui.py` owns the read-only local-view facade;
`scripts/ui_discovery.py` owns sink and transcript discovery;
`scripts/ui_layout.py` owns dependency and session-graph layout;
`scripts/ui_model.py` owns UI models, parsing, and safe-path primitives;
`scripts/ui_render.py` owns HTML, SVG, and session-view rendering;
`scripts/ui_server.py` owns route rendering, validators, and the loopback server;
`scripts/ui_sessions.py` owns transcript parsing, caching, and session models.

Workspaces: `scripts/workspace.py` owns the public workspace facade, lifecycle
stamps, and join isolation grade; `scripts/workspace_git.py` owns Git lifecycle
and guarded ticket stamps; `scripts/workspace_scope.py` owns segment-exact
write-scope normalization and grading.

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
