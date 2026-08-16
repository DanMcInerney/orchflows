# Architecture

Codemap: where the thing that does X lives, who owns it, and which way
dependencies point. Terms: `docs/vocabulary.md`.

## Tiers and ownership

- `contracts/` — T0, the narrow waist: six pure data shapes (verdict,
  work-item, worklog, pack-signature, result, composition).
  Hash-pinned by `tests/`; a shape change is breaking
  even when prose meaning is unchanged.
- `skills/` — T1, everything callable, in four sublayers: `kernel/`
  (primitives, call no skill, frozen), `engines/` (control flow),
  `workflows/` (assembled, domain-blind), `instances/` (concrete domain
  executors and lenses bound by pack cells). `utilities/` holds leaf
  generic skills outside the waist. Each package owns one `SKILL.md`
  plus its `references/` and `scripts/`.
- `packs/` — T2, functor arguments: data satisfying
  `contracts/pack-signature.md`, never control flow. One pack per
  domain (code, content, research, design); specificity thickens only in
  `craft` (budgeted).
- `compositions/` — T3, named workflows, invocable and admitted through
  `orch-build`. Two forms live here while the ticket set lands:
  `compositions/<name>/` — a directory of ticket stubs plus its
  `template.md` manifest, which `tickets.py instantiate` writes into one
  run's ticket directory for `orch-frontier` to run — and the
  `compositions/<name>.md` step form per `contracts/composition.md`
  (steps over skills combined by seq/par/loop; entry
  routed | named | scheduled). New work takes the template form.
- `rules/` — cross-cutting law (composition, delegation, verification,
  loops, roles, token-economy, topology, visibility, improvement);
  using one is `rules/visibility.md` §3's.
- `docs/` — `vocabulary.md` (every library term of art, one owner),
  `pack-authoring.md` (the order of work when adding a pack),
  `library-review.md` (the standing full-review prompt), and this
  file.
- `DESIGN.md` — root-level rationale: why each structure is shaped as
  it is; non-normative.
- `templates/` — host-block source; installer-owned; rendered to
  `~/.orchflows/host-block.md` by `install.py`.
- `tools/validate.py` — the compiler: every mechanical check the
  library enforces lives there, read the script for the current list.
  Everything it does not check — the Return law's field substance
  included — is owned by review under the library lens. `tests/`
  freeze canonical bytes; nothing depends on tests.
- `install.sh` / `install.cmd` + `install.py` — setup and teardown.
  The root wrappers resolve an
  interpreter (uv → python3 → python, never hardcoded) and pass
  arguments through to `install.py`. `install.py --user` auto-detects
  which host halves to configure — Claude Code only when a Claude CLI is
  on `PATH` (lib copy, `~/.claude/skills/` adapter stubs, role agents,
  concurrency setting), Codex only when a Codex CLI is on `PATH`
  (prompts, four redirect skill stubs, role agents, agent-limits config,
  hooks warning) — erroring with guidance when neither is present.
  `CLAUDE_CONFIG_DIR` and `CODEX_HOME` replace `~/.claude` and
  `~/.codex` throughout, matching each CLI. The
  always-on layer is one appended `@`-import line in the user
  `CLAUDE.md`/`AGENTS.md` pointing at installer-owned
  `~/.orchflows/host-block.md`, idempotent, replacing any legacy marker
  block; Codex takes the same import-line form only if the installed
  CLI resolves `@file` imports (verified by a read-only probe), else
  the proven marker-block upsert. Either configured half also writes
  the install receipt (`source_commit` plus prior-run drift on rerun)
  and hash-guards removal of its own generated entrypoints.
  `install.py --project PATH` writes only the two committable routing
  blocks (project `CLAUDE.md`, `AGENTS.md`) as inline marker blocks —
  self-contained for teammates — plus a minimal receipt; no project lib
  copy, no project `.claude`/`.codex` writes.
- `scripts/` — repository-root scripts, one owner each:
  `scripts/cutcheck.py` owns cut-defect detection over an issued ticket
  set, run by `orch-decompose` and read by its cut lens;
  `scripts/friction.py` owns
  friction logging; `scripts/isolate.py` owns exporting one revision
  into a tree beside the repository, where a check reads one lane's
  result alone; `scripts/migrate_state.py` owns copying a pre-existing
  state tree into the sink, never deleting from the source;
  `scripts/state_root.py` owns resolving the state sink,
  the one channel every other script reaches it through;
  `scripts/tickets.py` owns mechanical ticket queries; its `tickets.py
  help` is operator-only: usage a reader asks for, never a step a skill
  runs; `scripts/trace.py` owns trace extraction, consumed by
  `orch-self-improve`; `scripts/ui.py` owns the read-only local view of
  run state; `scripts/workspace.py` owns the workspace lifecycle stamps
  and the isolation grade at the join.
- state sink — every run's durable state and both improvement evidence
  streams, one per user and outside every repository, never an
  instruction source; the root and its law are
  [rules/visibility.md](rules/visibility.md) §6 and its resolver is
  `scripts/state_root.py`: `tickets/<run>/` (the local tracker, ticket
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
never depends on package internals for its meaning. A cross-package
reference link is a file dependency, not a call edge. Compositions
call skills and other compositions (one level of nesting); no skill
depends on a composition.

## Invariants

- One owner per fact; the validator and hash pins enforce the
  mechanical half, review under the library lens (owned by
  `orch-build`, applied through `orch-critique`) owns the rest.
- The call graph is acyclic; generic bodies are domain-blind; pack
  bodies are control-flow-free.
- Every canonical change lands through a PR passing the required checks
  in `AGENTS.md`.
