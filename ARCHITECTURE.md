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
  `tools/validate_measures.py`, `scripts/cutcheck.py` and `tests/` own
  the rest of the mechanical half; everything none of them checks — the
  Return law's field substance included — is owned by review under the
  library lens. `tests/` also freeze canonical bytes, and
  `tests/pins.json` is where `validate.py` reads them from.
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
- `scripts/` — repository-root scripts — stdlib Python 3, Windows and
  POSIX, no network at run time — one owner each:
  `scripts/cutcheck.py` owns cut-defect detection over an issued ticket
  set, run by `orch-decompose` and read by its cut lens;
  `scripts/doclint.py` owns grading any repository's markdown — every
  relative link resolves, every paragraph has one home — and with it the
  one near-duplicate method, which `tools/validate.py` calls rather than
  keeps a second copy of; `scripts/friction.py` owns
  friction logging; `scripts/isolate.py` owns exporting one revision
  into a tree beside the repository, where a check reads one lane's
  result alone; `scripts/migrate_state.py` owns copying a pre-existing
  state tree into the sink, never deleting from the source;
  `scripts/search_plan.py` owns the canonical bounded candidate-search
  advance, named by bare filename from the evolve template's campaign
  stub, its request and response shapes stated in
  `docs/search-plan-protocol.md` — docs/ is canonical and ships, and a
  protocol beside the script did not;
  `scripts/state_root.py` owns resolving the state sink,
  the one channel every other script reaches it through;
  `scripts/tickets.py` owns the ticket directory: issuing, instantiating
  a template, the gate stubs, claims and statuses, dispatch packets, the
  executor's own sections, the rendered worklog view, and the run-state
  and improvement records under the sink; its `tickets.py
  help` is operator-only: usage a reader asks for, never a step a skill
  runs; `scripts/trace.py` owns trace extraction, consumed by
  `orch-self-improve`; `scripts/ui.py` owns the read-only local view of
  run state; `scripts/workspace.py` owns the workspace lifecycle stamps
  and the isolation grade at the join.
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
