# Workflow ladder: run driver

Spec of record: `research/workflow-ladder-spec-2026-09-02.md`. The goal and
details files beside this one are generated from it by `generate.py`; edit the
spec, re-run the generator, never edit a generated file.

## Before the run

- Branch from `main` at `6b02c226` or later (PR #170 is required: per-item
  environments). Suggested branch: `claude/workflow-ladder-build`.
- The installed library must be current: `python install.py` from that `main`,
  then `orchflows sync`. `tickets.py` runs from `~/.orchflows/bin/`.
- Interpreter on this host: `uv run --no-project python`. Every `done` below
  names it, because a bare `python` is the Windows Store stub. A ticket's
  `done` is split as argv and run without a shell: one command, no `&&`.
- Lane: **team**. One frame, waves in the order the spec's section 4 fixes.

## Open the frame

    tickets.py frame-open <run> --goal-file research/workflow-ladder-tickets/root.goal.md --shape "U0 > [U1, U2, U3, U4, U11] > [U5, U7a, U7b, U7c, U9, U10, U12] > U7d > U8 > gate"

Until U3 lands, the frame law is these three lines; after it lands the trunk
prints them at every `frame-open`:

1. Before each call, re-read this frame's `## Report` and its children's states.
2. After each call, append the decision with `tickets.py result <run> <frame> --by <frame>`;
   keep every returned `artifact:` and `findings:` line verbatim and hand the
   line itself to the next goal file.
3. Close with `tickets.py frame-close <run> <frame> --done <command>` run
   outside the children; a close over two or more `do` children needs a
   judging child or an `unjudged: <reason>` line.

## One unit

Every unit is the same four commands. `<unit>` is one of the table's; the
bound is the table's.

    tickets.py do <run> --pack orch-code-pack --goal-file research/workflow-ladder-tickets/<unit>.goal.md --details-file research/workflow-ladder-tickets/<unit>.details.md --parent <frame> --isolation required --workspace <this checkout> --bound "<= <N> tool calls" --done {"form":"command","value":"uv run --no-project python tools/run_required.py"}

Quote the `--done` JSON the way your shell needs. Invoke the emitted `launch`
verbatim. When the child returns:

    tickets.py land <run> <id> --assignment-seal <seal> --dispatch-id <dispatch> --outcome-record-id outcome --by <frame>

`land` runs the `done` in the integrated tree. Then one judge over the landed line:

    tickets.py judge <run> --pack orch-code-pack --goal-file research/workflow-ladder-tickets/judge.goal.md --details-file research/workflow-ladder-tickets/<unit>.details.md --artifacts "git:<sha from the artifact: line>" --parent <frame>

Where the judge blocks, `bounded-repair`: copy `repair.goal.template.md` to
`.orch-notes/repair-<unit>.md`, paste the `findings:` line into it verbatim,
then one `do` with that goal file and the unit's details file, land, and one
re-judge. Two rounds is the bound; a third block closes the unit `stalled`
and the frame's journal says so.

Launch every unit of a wave before landing any of them. Land, judge and
append each as it returns. Open the next wave only when every unit of the
current wave is `complete` or `stalled`, and cut the next wave's worktrees
from the integrated tree.

## Waves and bounds

| wave | unit | bound (tool calls) | waits on |
|---|---|---|---|
| 1 | U0 contracts, ring kind, pin plumbing, flags | 200 | base |
| 2 | U1 sheets | 200 | U0 |
| 2 | U2 applied skills | 120 | U0 |
| 2 | U3 frame law, lib dirs, body sweep | 150 | base |
| 2 | U4 law and docs | 150 | base |
| 2 | U11 the repo's own bundle | 80 | base |
| 3 | U5 kernel sentences | 40 | U4 |
| 3 | U7a three sheets | 80 | U1 |
| 3 | U7b checkpointed-build | 200 | U3, U4 |
| 3 | U7c bakeoff | 150 | U3, U4 |
| 3 | U9 bundle manifest | 150 | U4 |
| 3 | U10 orchflows check | 150 | U4 |
| 3 | U12 tools, node, prune | 200 | U4 |
| 4 | U7d convert super-research | 200 | U2, U7a, U11 |
| 5 | U8 browser-fps dogfood | 400 | U7a, U7b, U12 |

Wave 3 is seven children. If the host's concurrency or your attention will not
carry seven, split it into [U5, U7a, U9, U10] then [U7b, U7c, U12]; the
dependencies allow either order.

## Gate

At the joined tip, once, outside every child:

    uv run --no-project python tools/run_required.py --no-cache
    uv run --no-project python tools/run_serial_compat.py --write-manifest
    uv run --no-project python install.py --dry-run
    git diff --check

Then `install.py`, `orchflows sync`, `orchflows check` on the home ring, and
`orchflows list`. Judge the seams first: one content-pack `judge` over every gallery body the
run touched, against `rules/composition.md` and `docs/custom-workflow-authoring.md`
as amended by U4, or an `unjudged: <reason>` line.
Then close the frame:

    tickets.py frame-close <run> <frame> --done {"form":"command","value":"uv run --no-project python tools/run_required.py --no-cache"}

## When something goes wrong

- A unit refuses a section 0 decision: it reports the observation and
  continues; the decision is yours to reopen after the run, not the child's.
- A `done` fails at `land`: that is the repair door, not a reason to edit the
  candidate from the root. Root and `role: none` never author.
- Two wave-mates conflict at the join: `land` reports the overlap; the later
  lander repairs against the integrated tree.
- A scratch run inside U7b, U7c, U7d or U8 does not close `complete`: the
  unit closes `limited` with the successor written; the gate reads the frame's
  status, never a claim.
- Friction: after two attempts, a missing tool, a surprising output, or a law
  gap, log it and continue (the host block's command).
