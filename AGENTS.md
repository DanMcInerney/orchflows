# Repository guidance

The canonical `orchflows` source: a four-tier library for orchestrator >
subagent work. `ARCHITECTURE.md` maps boundaries, ownership, dependency
direction; `docs/vocabulary.md` owns every library term and a pack's
craft cell its domain's; `rules/` owns cross-cutting law, under
`rules/visibility.md` §3. The Constitution in `docs/library-review.md`
requires every sentence here.

Routing, the state sink and the friction law are the host block's —
`templates/host-block.md`, installed at `~/.orchflows/host-block.md`.
From this checkout the friction command is `python scripts/friction.py
"<what happened>" "<what was expected or missing>"`, same sink, same
flags.

- Project-scope custom item `super-research` — manual invocation only,
  keyless read-only acquisition — at
  `.orchflows/skills/super-research/SKILL.md`.

## Required checks

Through this host's verified interpreter (`uv run --no-project python`;
bare `python` is a Windows Store stub; Python 3.9 or newer,
`install.py`'s floor):

python tools/validate.py
python tools/run_tests.py                 # one process per module
python tools/run_serial_compat.py         # selected same-process lane
python install.py --dry-run
git diff --check

`python tools/run_required.py` runs the five, cached by tree; a gate
passes `--no-cache`. While working,
`python tools/run_tests.py --scope <changed-paths>` runs only the
affected shards; the five decide the tip. Adding or removing tests
regenerates the manifest with
`python tools/run_serial_compat.py --write-manifest`.

Selected routinely checks cross-module coupling; exhaustive
`python -m unittest discover -s tests -v` stays scheduled/manual and
pre-release; green here is provisional until the
`.github/workflows/checks.yml` matrix agrees — `python tools/preflight.py`
replays it, docstrings own the rest.

## Serial compatibility

`tools/serial-compat-policy.md` defines the routine lane and fallback.
