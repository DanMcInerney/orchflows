Repair the five accepted findings of seam review B1.4 (run
20260901T132749Z). The findings file is in your worktree at
`FINDINGS-B1.4-seam-review.md` — read it whole first; it carries exact
files, lines, and the live proof of each defect. The design doc
`.orchflows/self-improve-design-2026-09-01.md` stays normative. Fix all
five; nothing else.

F1 (blocker): `scripts/harvest.py:366` reads `entry.get("goal")`; the
landed writer (`scripts/tickets_frame.py:175`) emits `goal_head`. Read
`goal_head`. The `--list-runs` goal column must show the recorded goal
first-line for a run written by the real frame-open.

F2 (blocker): the digest emits no watermark, while
`example-workflows/self-improve/SKILL.md` orders the mine to carry
"the digest's cluster_key, matcher and watermark verbatim", and
`harvest.py:318` ignores covered entries whose watermark does not
parse — covered-exclusion would ship as a silent no-op. Fix on the
digest side: the digest header gains `watermark`, the newest entry
timestamp the harvest read (ISO, UTC); with an empty slice, the window
end if bounded, else null. Align SKILL.md wording only as far as
naming reality (`matcher_draft` is the field the digest emits — either
rename the field to `matcher` in harvest or make the prose say
matcher_draft; pick one spelling and use it in both).

F3 (should-fix): nothing passes `--workflow` to frame-open. In
SKILL.md, the frame-open command line gains `--workflow self-improve`.

F4 (should-fix, the vacuous-green root): `tests/test_harvest.py`'s
fixture invents the reader's spelling (it even types `sink_convention`
as a string where the real writer emits the int 2). Add a true
cross-seam test: drive the REAL writer — `tickets.py frame-open` (via
the in-repo scripts, against a temp sink-env-var sink, the
way the judge's proof did) — then run harvest `--list-runs` over that
sink and assert the workflow and goal columns carry the recorded
values. Correct the existing fixture's field spellings to match the
writer. This test must fail if either side's field names drift.

F5 (should-fix): SKILL.md binds frame-open to the mine-brick branch,
while Deliver and Return require a frame on every delivering path —
the inline-mine path reaches them with no frame open. Restore the
design's rule: the frame opens with the FIRST brick, whichever branch
mints it. Reword within the 450-word workflow budget (the file sits at
exactly 450/450 — you must free words for anything you add; do not
weaken the Never: items, the seam-judge close rule, or the
single-child unjudged sentence).

Do NOT touch the three successor findings (S1 improvement.md cycle
sentence, S2 events skill field, S3 line counts) — they are queued for
a later cycle. Do not edit `FINDINGS-B1.4-seam-review.md`, any
friction entry, or the sink.

Checks before closing, each watched to completion:
`uv run --no-project python tools/run_tests.py --scope scripts/harvest.py,tests/test_harvest.py,example-workflows/self-improve/SKILL.md`
and `uv run --no-project python tools/validate.py` and
`git diff --check`. The full required suite is not yours to run.
