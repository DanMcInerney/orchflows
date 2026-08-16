# Repository guidance

This repository is the canonical `orchflows` source: a four-tier library
for orchestrator > subagent work. `ARCHITECTURE.md` maps boundaries,
ownership, and dependency direction. `docs/vocabulary.md` owns every library
term of art and a pack's craft cell owns its domain's; use terms with
exactly their defined meanings. `rules/` owns cross-cutting law, and
`rules/visibility.md` §3 governs what every other file may do with it.

Routing, the state sink and the friction law are the host block's —
`templates/host-block.md`, installed at `~/.orchflows/host-block.md` —
and nothing here restates them; from this checkout the friction
command is `python scripts/friction.py "<what happened>" "<what was
expected or missing>"`, same sink, same flags. `orch-off` suspends
routing for the session on request.

- Project-scope custom item: `super-research` — keyless read-only acquisition from public surfaces — at `.orchflows/skills/super-research/SKILL.md`.

## Required checks

Through the interpreter verified for this host (`uv run --no-project
python` where bare `python` is a Windows Store stub; Python 3.9 or newer,
`install.py`'s floor):

python tools/validate.py
python tools/run_tests.py                # sharded, one process per module
python -m unittest discover -s tests -v  # serial; proves no cross-module residue
python install.py --dry-run
git diff --check

A green run here is provisional until the CI matrix in
`.github/workflows/checks.yml` agrees — one host, one interpreter, one
shell locally; the matrix discriminates a host defect from a real one.
Before pushing, `python tools/preflight.py` runs the suite under every
CI interpreter installed here; what it covers and what stays CI's is its
docstring's.
