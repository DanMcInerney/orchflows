# Standards: run driver

Spec of record: `research/standards-spec-2026-09-04.md`. The goal and details
files beside this one are sliced from it by hand; where they and the spec
disagree, the spec wins and the file is fixed.

## Before the run

- Branch from `main` at `6d47143e` or later. Suggested branch:
  `claude/standards`.
- Installed library current: `install.py --accepted-source <base>` then
  `orchflows sync`. `tickets.py` runs from `~/.orchflows/bin/`.
- **Do not reinstall while this frame is open.** U1 changes which
  frontmatter fields the assignment seal covers, and U3 renames them.
  Installing either mid-run recomputes every open ticket's digest and
  refuses every further write. Reinstall after `frame-close`.
- Interpreter on this host: `uv run --no-project python`. Every `done` names
  it. A ticket's `done` is split as argv and run without a shell.
- Lane: **team**. One frame, waves in the order the spec's §4 fixes.

## Open the frame

    tickets.py frame-open <run> --goal-file research/standards-tickets/root.goal.md --shape "U0 > [U1, U2] > U3 > judge"

The trunk prints the frame law at `frame-open`; follow it.

## One unit

    tickets.py do <run> --pack orch-code-pack --goal-file research/standards-tickets/<unit>.goal.md --details-file research/standards-tickets/<unit>.details.md --parent <frame> --isolation required --workspace <this checkout> --bound "<= <N> tool calls" --done {"form":"command","value":"uv run --no-project python tools/run_required.py"}

Note `--pack orch-code-pack`: this run renames that flag, so every unit is
dispatched with the flag the *installed* trunk still takes. It changes only
after `frame-close` and the reinstall.

Invoke the emitted `launch` verbatim. When the child returns:

    tickets.py land <run> <id> --assignment-seal <seal> --dispatch-id <dispatch> --outcome-record-id outcome --by <frame>

No judge per unit: one judgment pass over the joined tip after the last
wave, which is what the frame law states.

## Waves and bounds

| wave | unit | bound (tool calls) | waits on |
|---|---|---|---|
| 1 | U0 the contract | 120 | base |
| 2 | U1 resolution and pinning | 200 | U0 |
| 2 | U2 the items | 200 | U0 |
| 3 | U3 the rename | 250 | wave 2 |

Launch both units of wave 2 before landing either, then land them in the
fixed order U1, U2. `tests/serial_compat_manifest.json` is the driver's, not
a child's: where a land conflicts on it, regenerate at the merged tip with

    uv run --no-project python tools/regen.py

and record that you did.

U3 is alone in wave 3 and lands last. It is the largest unit in the run —
roughly forty files, mostly mechanical — and its bound is set for a sweep,
not for design work. If it comes back having designed something, that is a
finding for the judge.

## The judgment pass

After wave 3 is landed and the tip is green, one judge over the joined tip
carrying every unit's artifact:

    tickets.py judge <run> --pack orch-code-pack --goal-file research/standards-tickets/judge.goal.md --details-file research/standards-tickets/judge.details.md --artifacts "git:<U0 sha>" --artifacts "git:<U1 sha>" --artifacts "git:<U2 sha>" --artifacts "git:<U3 sha>" --parent <frame>

`judge.details.md` is a pointer file on purpose: the spec's own `##`
headings are not ticket sections, so `--details-file
research/standards-spec-2026-09-04.md` refuses with `unknown ticket
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

Redirect that first command to a file and grep it for `FAILED MODULE`. Do
not read it with `tail`: `run_tests.py` prints the failing module's whole
output near the top and a `0 failures, 0 errors` summary at the bottom, so a
tail of a red run looks green.

Append to the journal: the `install.py --dry-run` entry count beside the base
commit's 359, with its reduction decomposed into the twenty deleted host
adapters and the five collapsed second files; U3's retired-term grep; and the
host block and `AGENTS.md` word counts. Then:

    tickets.py frame-close <run> <frame> --done {"form":"command","value":"uv run --no-project python tools/run_required.py --no-cache"}

Then, and only then, `install.py --accepted-source <tip>` and
`orchflows sync`.

## When something goes wrong

- A unit disagrees with a §0 decision: it reports the observation and
  continues; the decision is reopened after the run, not by the child.
- A `done` fails at `land`: that is the repair door. Root never authors.
  Before opening a repair, re-run the `done` once — a non-reproducible
  `run_tests` exit 1 at an unchanged tree is a known flake, and the repair
  ticket it arms has to be settled by hand afterwards.
- A child is stopped mid-flight and cannot be landed: `tickets.py
  dispatch-retire <run> <id> --assignment-seal <seal> --dispatch-id <id>:d1
  --record-id lifecycle:driver-stopped`, then `tickets.py set-status <run>
  <id> stalled`.
- Friction: after two attempts, a missing tool, a surprising output, or a
  law gap — log it and continue.
