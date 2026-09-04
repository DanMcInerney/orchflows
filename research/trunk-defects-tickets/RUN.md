# Trunk defects: run driver

Spec of record: `research/trunk-defects-spec-2026-09-03.md`. The goal and
details files beside this one are sliced from it by hand; where they and the
spec disagree, the spec wins and the file is fixed.

## Before the run

- Branch from the library-cleanup tip `c6bc9d39` or later (or from `main`
  once that has merged). Suggested branch: `claude/trunk-defects`.
- Installed library current: `python install.py` from that base, then
  `orchflows sync`. `tickets.py` runs from `~/.orchflows/bin/`.
- **Do not reinstall while this frame is open.** U1 changes the assignment
  seal algebra; installing it mid-run recomputes every open ticket's digest
  and refuses every further write with `assignment-mismatch` — the defect
  U1 exists to remove. Reinstall after `frame-close`.
- Interpreter on this host: `uv run --no-project python`. Every `done`
  names it. A ticket's `done` is split as argv and run without a shell.
- Lane: **team**. One frame, waves in the order the spec's section 4 fixes.

## Open the frame

    tickets.py frame-open <run> --goal-file research/trunk-defects-tickets/root.goal.md --shape "U3 > [U1, U2, U4] > judge"

The trunk prints the frame law at `frame-open`; follow it.

## One unit

    tickets.py do <run> --pack orch-code-pack --goal-file research/trunk-defects-tickets/<unit>.goal.md --details-file research/trunk-defects-tickets/<unit>.details.md --parent <frame> --isolation required --workspace <this checkout> --bound "<= <N> tool calls" --done {"form":"command","value":"uv run --no-project python tools/run_required.py"}

Invoke the emitted `launch` verbatim. When the child returns:

    tickets.py land <run> <id> --assignment-seal <seal> --dispatch-id <dispatch> --outcome-record-id outcome --by <frame>

No judge per unit: one judgment pass over the joined tip after the last
wave, which is the cadence U4 makes law.

## Waves and bounds

| wave | unit | bound (tool calls) | waits on |
|---|---|---|---|
| 1 | U3 manifest stops colliding | 150 | base |
| 2 | U1 the seal reads the ticket | 150 | U3 |
| 2 | U2 a retirement can be graded | 150 | U3 |
| 2 | U4 the judgment cadence is law | 100 | U3 |

Launch every unit of wave 2 before landing any, then land them in the fixed
order U1, U2, U4. Two shared derived artifacts belong to the driver, not to
a child: `tests/serial_compat_manifest.json` (every added check rewrites
`identities`) and `docs/lifecycle.md`. Where a land conflicts on either,
resolve it at the merged tip by regenerating —

    uv run --no-project python tools/regen.py

— and record that you did. U1 and U2 both append cases to
`tests/test_staleness_and_remedies.py`; U1 lands first, U2 rebases.

## The judgment pass

After wave 2 is landed and the tip is green, one judge over the joined tip
carrying every unit's artifact:

    tickets.py judge <run> --pack orch-code-pack --goal-file research/trunk-defects-tickets/judge.goal.md --details-file research/trunk-defects-tickets/judge.details.md --artifacts "git:<U1 sha>" --artifacts "git:<U2 sha>" --artifacts "git:<U3 sha>" --artifacts "git:<U4 sha>" --parent <frame>

`judge.details.md` is a pointer file on purpose: the spec's own `##`
headings are not ticket sections, so `--details-file
research/trunk-defects-spec-2026-09-03.md` refuses with `unknown ticket
section`. Paste the four `artifact:` lines into it, verbatim, before
issuing.

Where the judge blocks: copy `repair.goal.template.md` to
`.orch-notes/repair-<unit>.md`, paste the `findings:` line into it, one
repair `do` with that unit's details file, land, then one re-judge. Two
rounds is the bound.

## Gate

At the joined tip, once, outside every child:

    uv run --no-project python tools/run_required.py --no-cache
    uv run --no-project python tools/regen.py --check
    git diff --check

Append to the journal: the `install.py --dry-run` entry count beside the
base commit's, and U4's `grep -rn "joined tip"` roster. Then:

    tickets.py frame-close <run> <frame> --done {"form":"command","value":"uv run --no-project python tools/run_required.py --no-cache"}

Then, and only then, `install.py` and `orchflows sync`.

## When something goes wrong

- A unit disagrees with a section 0 decision: it reports the observation
  and continues; the decision is reopened after the run, not by the child.
- A `done` fails at `land`: that is the repair door. Root never authors.
- A child is stopped mid-flight and cannot be landed: `tickets.py
  dispatch-retire <run> <id> --assignment-seal <seal> --dispatch-id <id>
  --record-id lifecycle:<name>`, then `tickets.py set-status <run> <id>
  stalled`. Until U2 lands, `set-status` refuses that with
  `dispatch-join-required` and the ticket is wedged terminal-less — record
  it in the journal and move on.
- Friction: after two attempts, a missing tool, a surprising output, or a
  law gap — log it and continue.
