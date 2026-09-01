Implement M1 of `.orchflows/self-improve-design-2026-09-01.md` (in your
worktree; its "Move 1" section is normative, including the amended CLI):
the deterministic harvest door.

Deliverables:

1. `scripts/harvest.py` — stdlib-only, cross-platform (Windows + POSIX),
   read-only over the state sink except the one digest file it writes at
   `--out`. Sink resolution through `scripts/state_root.py` via deferred
   guarded imports exactly as `scripts/friction.py` does (partial-install
   safe; console discipline via `console.py`). One JSON document on
   stdout is NOT required — this is a file-writing tool; print one
   summary line on success, errors to stderr with non-zero exit.

2. CLI, exactly this surface (design doc "Move 1"):
   `python harvest.py --out <digest.json> [--since <ts|Nd>] [--until <ts>]
   [--on <date>]... [--session <id>]... [--run <id>]... [--project <name>]
   [--workflow <name>] [--skill <orch-name>] [--host <host>]`
   plus the resolver mode `python harvest.py --list-runs [window flags]`
   (no `--out`; prints one line per run in the window: run id, workflow
   name and goal first-line read from frame-open events when present else
   null, earliest/latest entry timestamps, friction and event counts).
   Selectors AND across kinds, OR within a repeated flag; each `--on` is
   one whole UTC day and repeats to form disjoint unions; `--since`
   accepts an ISO timestamp or `<N>d`; no selector at all means
   "everything since the newest covered watermark in
   `improvement/covered.jsonl`" (no covered file: everything).

3. Behavior, in order: slice `friction/*.jsonl` and `events/*.jsonl`
   (the events stream is being added by a sibling ticket — read it if
   present, tolerate its absence); apply every `covered.jsonl` entry's
   `matcher` regex list to entries at or before that entry's `watermark`,
   dropping matches and counting the drops; cluster remaining friction
   entries by observed-text similarity (normalize case/paths/hashes/
   numbers, 3-word shingles, greedy union at one fixed Jaccard-threshold
   module constant); compute improvement law §4 arithmetic per cluster
   (member count, distinct sessions, distinct run/host pairs where
   sessions are absent) and mark `recurrence_met`.

4. Digest shape: JSON with a header (window echo, streams read, entry
   totals, covered-exclusion counts) and `clusters` ranked by member
   count, each carrying `cluster_key` (slug from shared shingles),
   counts, `recurrence_met`, `matcher_draft` (shared shingles as regex
   strings), and `members` — entries verbatim, capped at 12 with an
   `omitted` count.

5. `tests/test_harvest.py` — cover at least: since/until edges; two
   disjoint `--on` days select nothing between them; covered-matcher
   exclusion (at-or-before watermark drops, after survives); cluster
   determinism (same input, same digest modulo the header timestamp);
   `--list-runs` output with and without frame-open events; empty-sink
   and empty-window behavior; Windows path handling. Use a temp
   `ORCHFLOWS_STATE_HOME` fixture sink; never touch the real sink. If
   the serial-compat manifest must list the new module, regenerate it
   with `uv run --no-project python tools/run_serial_compat.py
   --write-manifest` and commit the result.

6. Installer: `harvest.py` ships to the installed bin like friction.py
   does — wire whatever manifest/plan `install.py` reads, and verify
   `uv run --no-project python install.py --dry-run` lists it.

Constraints: no imports beyond stdlib; do not modify friction.py,
state_root.py, or any tickets_*.py; do not write anywhere in the sink.
Run the scoped checks before closing:
`uv run --no-project python tools/run_tests.py --scope scripts/harvest.py,tests/test_harvest.py`
and `uv run --no-project python tools/validate.py`.
