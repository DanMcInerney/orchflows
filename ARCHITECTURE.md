# Architecture

Codemap: where the thing that does X lives, who owns it, and which way
dependencies point. Terms: `docs/vocabulary.md`.

## Tiers and ownership

- `contracts/` — T0, the narrow waist: five pure data shapes (verdict,
  work-item, worklog, pack-signature, result).
  Hash-pinned by `tests/`; a shape change is breaking
  even when prose meaning is unchanged.
- `skills/` — T1, everything callable, one directory per sublayer:
  `kernel/` (primitives, call no skill, frozen), `engines/` (control
  flow), `workflows/` (assembled, domain-blind), `instances/` (concrete
  domain executors and lenses bound by pack cells), `utilities/` (leaf
  generic skills). Each package owns one `SKILL.md` plus its
  `references/` and `scripts/`.
- `packs/` — T2, functor arguments: data satisfying
  `contracts/pack-signature.md`, never control flow. One pack per
  domain (code, content, research, design); specificity thickens only in
  `craft` (budgeted).
- `compositions/` — T3, named workflows: ticket-stub templates per
  [contracts/work-item.md](contracts/work-item.md)'s Template and stub,
  admitted through `orch-build`.
- `rules/` — cross-cutting law (composition, delegation, verification,
  loops, roles, token-economy, topology, visibility, improvement);
  using one is `rules/visibility.md` §3's.
- `docs/` — `vocabulary.md` owns every library term of art;
  `documentation.md` owns documentation design law for this library and
  the projects it builds; the rest of the directory is reference
  material, one owner each, and `ls` is its list.
- `DESIGN.md` — root-level rationale: why each structure is shaped as
  it is; non-normative.
- `templates/` — host-block source; installer-owned; rendered to
  `~/.orchflows/host-block.md` by `install.py`.
- `tools/validate.py` — the compiler: the mechanical checks over the
  library's own text, read the script for the current list.
  `tools/check_source_sizes.py` owns the tracked physical-line ceilings
  for executable source and the deterministic report of every excess.
  `tools/validate_measures.py`, `scripts/cutcheck.py` and `tests/` own
  the rest of the mechanical half; everything none of them checks — the
  Return law's field substance included — is owned by review under the
  library lens. `tests/` also freeze canonical bytes, and
  `tests/pins.json` is where `validate.py` reads them from.
- `install.sh` / `install.cmd` + `install.py` — setup and teardown; what
  each scope writes, detects and removes is `install.py`'s docstring's.
  `install.py` is the compatibility facade; `installer/` owns the static
  support modules, including the private-runtime lifecycle in
  `installer/runtime.py`. User scope owns one private runtime at
  `~/.orchflows/runtime`; project scope verifies and borrows it, renders
  caller-local paths, and never creates an environment in a repository.
  Runtime replacement is staged and probed before an installer-owned prior
  generation is moved.
- `requirements-runtime.txt` — the installed runtime's dependency contract.
  `pyproject.toml` mirrors its current empty dependency set for repository
  tooling; this revision installs no third-party package.
- `scripts/` — repository-root scripts — Python 3.9+, Windows and
  POSIX, no network at run time — one owner each. The unprefixed family
  module is the public CLI and import compatibility facade; implementation
  dependencies point from that facade into its static `<name>_*` helpers,
  while callers outside the family depend on the facade. An internal helper
  owns its named concern but is not a second public entry point; explicit
  compatibility-seam synchronization does not reverse that ownership:
  `scripts/cutcheck.py` owns cut-defect detection over an issued ticket
  set, run by `orch-decompose` and read by its cut lens, and beside the
  defects it reads that set's graph — the critical path and each level's
  width — as a reading and never as a finding; `scripts/cutcheck_commands.py`
  owns extraction and classification of oracle commands;
  `scripts/cutcheck_contract.py` owns shared cutcheck constants and mutable
  invocation state; `scripts/cutcheck_coverage.py` owns reading and grading
  cut coverage maps; `scripts/cutcheck_execute.py` owns executing and
  discriminating oracle commands; `scripts/cutcheck_executor.py` owns pack
  cell resolution and executor-legality grading; `scripts/cutcheck_graph.py`
  owns ticket-graph layout grading and graph readings;
  `scripts/cutcheck_scope.py` owns citation, path, and write-scope closure
  grading; `scripts/cutcheck_scratch.py` owns cutcheck scratch-tree creation,
  inspection, and removal; `scripts/cutcheck_search.py` owns search-span and
  whole-suite command-shape grading; `scripts/cutcheck_state.py` owns
  repository and run-state resolution for cutcheck;
  `scripts/cutcheck_ticket.py` owns assembling all findings for one issued
  ticket;
  `scripts/doclint.py` owns grading any repository's markdown — every
  relative link resolves, every paragraph has one home — and with it the
  one near-duplicate method, which `tools/validate.py` calls rather than
  keeps a second copy of; `scripts/friction.py` owns
  friction logging; `scripts/isolate.py` owns exporting one revision
  into a tree beside the repository, where a check reads one lane's
  result alone; `scripts/migrate_state.py` owns copying a pre-existing
  state tree into the sink through its public compatibility facade, never
  deleting from the source; `scripts/migrate_state_plan.py` owns migration
  planning, collision handling, and application;
  `scripts/migrate_state_records.py` owns record attribution and
  transformation for state migration;
  `scripts/search_plan.py` owns the public compatibility facade for the
  canonical bounded candidate-search transformation, named by bare filename
  from the evolve template's campaign stub, its request and response shapes
  stated in `docs/search-plan-protocol.md` — docs/ is canonical and ships,
  and a protocol beside the script did not; `scripts/search_plan_advance.py` owns
  generation advance over a validated bounded-search projection;
  `scripts/search_plan_archive.py` owns Pareto-archive updates and
  deterministic archive ordering; `scripts/search_plan_projection.py` owns
  projection validation and deterministic search-slot proposals;
  `scripts/search_plan_protocol.py` owns canonical request parsing and
  bounded-search protocol validation;
  `scripts/state_root.py` owns resolving the state sink,
  the one channel every other script reaches it through;
  `scripts/tickets.py` owns the public CLI and import compatibility facade
  for the ticket directory, including the one root/gate family in a run,
  immutable run identity (`opened_at`, installed version and source commit),
  and immutable terminal timing (`terminal_at`, terminal ticket and
  `elapsed_ms`); `scripts/tickets_format.py` owns ticket frontmatter,
  section, criterion, and format validation primitives;
  `scripts/tickets_store.py` owns sink paths, repository/workspace identity,
  run identity, locking, and atomic file primitives; `scripts/tickets_issue.py`
  owns ticket rendering, issue, placement, and pre-claim amendment;
  `scripts/tickets_lifecycle.py` owns listing, readiness, claim, grant, check,
  and status transitions; `scripts/tickets_packet.py` owns by-reference
  dispatch packet construction and gate-child prompts;
  `scripts/tickets_result.py` owns executor-section, run-state, and
  improvement-record writes; `scripts/tickets_worklog.py` owns template-graph
  defects and rendered worklog production; `scripts/tickets_dispatch.py`
  owns template instantiation, root-gate creation, help, improvement routing,
  and top-level command dispatch;
  its `tickets.py
  help` is operator-only: usage a reader asks for, never a step a skill
  runs; its `tickets.py grant` is operator-only: widening a claimed
  item's authority is the dispatching caller's decision, never a step the
  item's own executor runs; `scripts/trace.py` owns the public
  trace-extraction compatibility facade, consumed by `orch-self-improve`;
  `scripts/trace_claude.py` owns Claude Code session extraction;
  `scripts/trace_codex.py` owns Codex rollout extraction;
  `scripts/trace_render.py` owns canonical trace normalization and Mermaid
  rendering; `scripts/ui.py` owns the public CLI facade for the read-only
  local view of run state; `scripts/ui_discovery.py` owns state-sink and
  transcript discovery; `scripts/ui_layout.py` owns dependency and session
  graph layout; `scripts/ui_model.py` owns shared UI models, parsing, and
  safe-path primitives; `scripts/ui_render.py` owns HTML and SVG primitives
  and session-view rendering; `scripts/ui_server.py` owns route rendering,
  validators, and the loopback HTTP server; `scripts/ui_sessions.py` owns
  transcript parsing, caching, and session models; `scripts/workspace.py`
  owns the public workspace CLI, lifecycle stamps, and isolation grade at the
  join; `scripts/workspace_git.py` owns git lifecycle operations and guarded
  ticket stamps for that facade; `scripts/workspace_scope.py` owns
  segment-exact write-scope normalization and grading for that facade.
- state sink — root, law and resolver:
  [rules/visibility.md](rules/visibility.md) §6; layout: `tickets/<run>/`
  (the local tracker, ticket
  `## Handoff` sections included), `runs/<run>/` (worklog, `run.json`,
  composition instances), `research/` (research-lane outputs),
  `handoffs/` (cross-session handoff documents), `friction/` (JSONL
  logs), `improvement/proposals/`, `improvement/covered.jsonl` (the
  coverage record). Every record names the project it arose in.
- `.orch/` — what stays in a repository: `canary/` (tracked golden
  fixture, one file every worktree checks out and whose change reaches
  the repository by merge) and, for a project-scope install, `bin/`
  (installed run-local scripts). Nothing else.

## Dependency direction

`AGENTS.md` → `rules/` → `contracts/` → `skills/` → package `scripts/`.
Packs depend on contracts and name instance skills; generic skills
never name a pack or a domain. A lower layer links the law and
contracts that bind it; a rule may name a canonical owner file but
never depends on package internals for its meaning. A template's stubs
bind skills or scripts as executors; no skill depends on a template.
