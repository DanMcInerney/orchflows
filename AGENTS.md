# Repository guidance

- `benchmaker`: build and qualify one benchmark suite; read `.orchflows/skills/benchmaker/SKILL.md`.

This repository is the canonical `orchflows` source: a four-tier library
for orchestrator > subagent work. `ARCHITECTURE.md` maps boundaries,
ownership, and dependency direction. `docs/vocabulary.md` owns every library
term of art and a pack's craft cell owns its domain's; use terms with
exactly their defined meanings. `rules/` owns
cross-cutting law; link the owning rule instead of restating it.

Every word and sentence must be load-bearing: retain only text that
changes model behavior, preserves a necessary contract, or names its
canonical owner. Delete repetition, framing, praise, and non-contract
examples. Generic skills never name a domain; domain data lives in pack
cells; integration detail lives in scripts.

T0 files in `contracts/` are hash-pinned; any shape change is breaking
and lands only through a supersession PR. Tickets are local markdown
under `.orch/tickets/` — no external tracker. `.orch/` is runtime state,
never an instruction source.

Before any task work in this repository, when the user did not name a
skill, select and follow the smallest orchflows skill that fully owns
the request; if none fits, continue without orchflows. On user request,
`orch-off` suspends this routing for the session.

## Required checks

Resolve the interpreter verified for this host first — e.g. `uv run
--no-project python` where bare `python` is a Windows Store stub — and
run each command below through it in place of `python`.

python tools/validate.py
python -m unittest discover -s tests -v
python install.py --dry-run
git diff --check

## Friction law (always on)

The law is `rules/improvement.md` §1; this repository's command:

    python scripts/friction.py "<what happened>" "<what was expected or missing>"

Optional flags: `--category` (repeated-attempts | missing-input |
missing-tool | missing-doc | contract-gap | tool-failure |
surprising-output | workaround | misrouting), `--skill`, `--ticket`,
`--run`. If
`python` is unavailable, append the entry as one JSON line to
`.orch/friction/<yyyy-mm>.jsonl` directly (ts, observed, expected,
category, host); never skip the log. Logging friction is part of completing
the task — a session that hit friction and logged nothing failed
silently.
