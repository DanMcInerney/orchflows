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

- Project-scope custom item: `super-research` — manual invocation only; keyless read-only acquisition from public surfaces — at `.orchflows/skills/super-research/SKILL.md`.

## Required checks

Through the interpreter verified for this host (`uv run --no-project
python` where bare `python` is a Windows Store stub; Python 3.9 or newer,
`install.py`'s floor):

python tools/validate.py
python tools/run_tests.py                # sharded, one process per module
python tools/run_serial_compat.py         # selected same-process compatibility lane
python install.py --dry-run
git diff --check

`python tools/run_required.py` runs the five, overlapping where it can,
skipping what this tree already proved green. While working, `python
tools/run_tests.py --scope <changed-paths>` runs only the affected
shards; the five decide the tip. Adding or removing tests regenerates
the manifest: `python tools/run_serial_compat.py --write-manifest`.

Selected routinely checks cross-module coupling; exhaustive
`python -m unittest discover -s tests -v` stays scheduled/manual and
pre-release. CI runs `tools/run_tests.py`: clean processes reject a
guarded whole-interpreter seam left dirty.

A green run here is provisional: one host, one interpreter, one shell;
the CI matrix in `.github/workflows/checks.yml` decides. Before pushing,
`python tools/preflight.py` replays it under every CI interpreter
installed here; its docstring owns the rest.

## Serial compatibility

`tools/serial-compat-policy.md` defines the routine lane and fallback.
