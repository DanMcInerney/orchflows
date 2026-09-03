# Library cleanup: run driver

Spec of record: `research/library-cleanup-spec-2026-09-03.md`. The goal and
details files beside this one are sliced from it by hand; where they and the
spec disagree, the spec wins and the file is fixed.

## Before the run

- Branch from `main` at `468dbdc9` or later. Suggested branch:
  `claude/library-cleanup`.
- Installed library current: `python install.py` from that `main`, then
  `orchflows sync`. `tickets.py` runs from `~/.orchflows/bin/`.
- Interpreter on this host: `uv run --no-project python`. Every `done` names
  it. A ticket's `done` is split as argv and run without a shell.
- Lane: **team**. One frame, waves in the order the spec's section 4 fixes.

## Open the frame

    tickets.py frame-open <run> --goal-file research/library-cleanup-tickets/root.goal.md --shape "U0 > [U3, U4, U5, U6, U7] > [U1, U2] > U8 > judge"

The trunk prints the frame law at `frame-open`; follow it.

## One unit

    tickets.py do <run> --pack orch-code-pack --goal-file research/library-cleanup-tickets/<unit>.goal.md --details-file research/library-cleanup-tickets/<unit>.details.md --parent <frame> --isolation required --workspace <this checkout> --bound "<= <N> tool calls" --done {"form":"command","value":"uv run --no-project python tools/run_required.py"}

Invoke the emitted `launch` verbatim. When the child returns:

    tickets.py land <run> <id> --assignment-seal <seal> --dispatch-id <dispatch> --outcome-record-id outcome --by <frame>

No judge per unit (user ruling, 2026-09-03: "The judge and fix should
only occur at the end of all the waves"). After wave 4 lands, one judge per
landed unit over its `artifact:` line, all issued together:

    tickets.py judge <run> --pack orch-code-pack --goal-file research/library-cleanup-tickets/judge.goal.md --details-file research/library-cleanup-tickets/<unit>.details.md --artifacts "git:<sha from the artifact: line>" --parent <frame>

Where a judge blocks, *bounded-repair*: "Where the judge blocks, one repair
`do` is handed the `findings:` line verbatim, then one re-judge; two rounds is
the bound." Copy `repair.goal.template.md` to `.orch-notes/repair-<unit>.md`,
paste the line, one `do` with the unit's details file, land, re-judge.

Launch every unit of a wave before landing any. Open the next wave only when
every unit of the current one is `complete` or `stalled`, cutting the next
wave's worktrees from the integrated tree.

## Waves and bounds

| wave | unit | bound (tool calls) | waits on |
|---|---|---|---|
| 1 | U0 pin and supersession apparatus | 200 | base |
| 2 | U3 ticket family dead surface | 200 | U0 |
| 2 | U4 packs, kernel, adapters, sheets | 200 | U0 |
| 2 | U5 reader and human-surface oracles | 200 | U0 |
| 2 | U6 installer | 150 | U0 |
| 2 | U7 tools and tests | 250 | U0 |
| 3 | U1 law text | 150 | wave 2 |
| 3 | U2 vocabulary, DESIGN, README | 150 | wave 2 |
| 4 | U8 prose inside code | 200 | wave 3 |

Five children in wave 2. If concurrency will not carry five, split
[U3, U4] then [U5, U6, U7]; the dependencies allow either order.

## Gate

At the joined tip, once, outside every child:

    uv run --no-project python tools/run_required.py --no-cache
    uv run --no-project python install.py --dry-run
    git diff --check
    grep -r "T0 supersession" contracts/
    test ! -e tests/pins.json

Then `install.py`, `orchflows sync`, `orchflows list`, and the law-text
count appended to the journal. One content-pack `judge` over `rules/`,
`contracts/`, `docs/vocabulary.md` and `DESIGN.md` against the spec's
decision 2, or an `unjudged: <reason>` line. Then:

    tickets.py frame-close <run> <frame> --done {"form":"command","value":"uv run --no-project python tools/run_required.py --no-cache"}

## When something goes wrong

- A unit disagrees with a section 0 decision: it reports the observation
  and continues; the decision is reopened after the run, not by the child.
- A `done` fails at `land`: that is the repair door. Root never authors.
- U7 cannot show the seam coverage decision 6 asks for: it keeps the serial
  lane as a manual command, closes `limited`, and says which seam.
- Friction: after two attempts, a missing tool, a surprising output, or a
  law gap — log it and continue.
