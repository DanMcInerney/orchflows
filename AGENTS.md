# Repository guidance

This repository is the canonical `orchflows` source: a four-tier library
for orchestrator > subagent work. `ARCHITECTURE.md` maps boundaries,
ownership, and dependency direction. `docs/vocabulary.md` owns every library
term of art and a pack's craft cell owns its domain's; use terms with
exactly their defined meanings. `rules/` owns cross-cutting law, and
`rules/visibility.md` §3 governs what every other file may do with it.

Tickets are local markdown under the state sink's `tickets/`; the
sink's root and its law are `rules/visibility.md` §6, and nothing it
holds is an instruction source.

Before any task work in this repository, when the user named no skill
or workflow, route smallest-first: **answer** when evidence already in
context decides it; **ticket** otherwise — issued through
`scripts/tickets.py new`, run under `orch-frontier`, its `executor`
`orch-decompose` when one executor cannot meet it; **fix** —
`compositions/fix` — when a failure's cause is unknown. Anything else,
`evolve` and `benchmaker` included, runs only when named; `orch-off`
suspends this routing for the session on request.

- Project-scope custom item: `super-research` — keyless read-only acquisition from public surfaces — at `.orchflows/skills/super-research/SKILL.md`. The Claude adapter mirror at `.claude/skills/super-research/SKILL.md` is an include stub whose absolute path `scopes.md` mandates and which therefore resolves on one machine only: read the owner, not the mirror.

## Required checks

Resolve the interpreter verified for this host first — e.g. `uv run
--no-project python` where bare `python` is a Windows Store stub — and
run each command below through it in place of `python`. It must be
Python 3.9 or newer: that is the floor `install.py` enforces and CI
proves on 3.9, 3.11 and 3.13 across Linux, macOS and Windows. A result
recorded on an older interpreter says nothing about this repository.
A green run of the five below is provisional until the matrix in
`.github/workflows/checks.yml` agrees: locally they run on one host
under one interpreter, and that matrix is the oracle that discriminates
a host-specific defect from a real one.

python tools/validate.py
python tools/run_tests.py                # sharded, one process per module
python -m unittest discover -s tests -v  # serial; proves no cross-module residue
python install.py --dry-run
git diff --check

Before pushing, close what can be closed here rather than four minutes
later in a matrix cell:

python tools/preflight.py   # the whole suite under every CI interpreter installed

What preflight covers of the nine-cell matrix, and what only CI can, is
its own docstring's.

## Friction law (always on)

The law is `rules/improvement.md` §1; from this checkout the command is

    python scripts/friction.py "<what happened>" "<what was expected or missing>"

with the host block's flags. What to do when the logger itself cannot
run is the host block's, in `templates/host-block.md`.
