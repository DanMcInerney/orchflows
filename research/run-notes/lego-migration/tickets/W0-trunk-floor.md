# W0 — trunk-floor (wave 0, serial, worker: opus)

## Goal

The four measured trunk defects of 2026-08-31 are extinguished, each
with a check that fails on the prior tree: (1) land's
workspace-integrate merges into the RUN'S branch, recorded at
establishment, never the main checkout's incumbent branch (the run that
produced commit e18ff25e on an unrelated checked-out branch is the
evidence); (2) integrate refuses a candidate whose worktree is dirty
while its branch tip equals its base, instead of replaying — the silent
no-op that stranded two members' whole deliveries uncommitted;
(3) a retire refusal at a tree holding unintegrated work names a
work-preserving remedy, never `remove --force`; (4) a dispatch attempt
that opened and self-retired before any launch returns status ownership
to `set-status` (today a never-launched ticket is permanently wedged:
set-status refuses dispatch-join-required, retire refuses
stale-attempt, and no join can exist without an outcome).

## Context

- owners: `scripts/tickets_land.py`, `scripts/workspace_candidate.py`
  (AT 509/510 LINES — split first at its integrate/retire seam per the
  existing task-chip analysis, ~100 lines beside `workspace_git.py`),
  `scripts/tickets_attempts.py`, `scripts/tickets_transitions.py`
- evidence identities: the 2026-08-31 friction entries at 12:03:01Z,
  12:28:15Z, 13:37:05Z, and the set-status/dispatch-retire wedge logged
  ~15:4xZ, all in the sink's friction ledger for 2026-08
- the run's branch: establishment already records the workspace branch
  and baseline; the run's target branch should be derived from what
  establish recorded for the run (first establishment wins and is
  recorded on run.json), not from `git -C <main_root>` incumbency

## Details

- Split `workspace_candidate.py` FIRST (mechanical, own commit) so the
  fixes have room; keep one owner per moved function.
- (1): record the integration target on the run at first establishment;
  land reads it. If no establishment ever recorded one (all-none runs),
  integrate is already skipped — assert that path unchanged.
- (2): tip==base + dirty worktree → refuse with the remedy "commit in
  the candidate, then land again"; tip==base + clean → genuine no-op
  replay stays lawful.
- (4): smallest honest door — when the only attempt's state is retired
  AND it holds no records beyond lifecycle, `set-status` may move the
  ticket; anything with real records keeps join ownership.
- Non-scope: no brick/frame work, no deletions, no renames — this is
  the floor, wave 1 builds on it.
- Done, run to completion, exits observed:
  `uv run --no-project python tools/run_required.py --no-cache` → 0;
  `uv run --no-project python tools/preflight.py` → 0; each fix's
  can-fail reading recorded (red on prior tree, green after).
- Report: commits, the four can-fail readings verbatim, where the
  integration target now lives (one owner), line delta.

## Report
