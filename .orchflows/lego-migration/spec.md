# Lego migration — execution spec (hand-run, no orchflows)

2026-08-31. Executes `.orchflows/lego-design-2026-08-31.md` (with
amendments A1–A7) to its minimal landable form. Like stage 1: no
orchflows runs — the driver hand-dispatches subagents from these
tickets, one worktree per parallel worker, gate-green at every wave
tip. Stop point: PR merged, library reinstalled; dogfooding follows.

## Frozen goal

The library converges to bricks, frames, and prose:

1. **Two T1 verbs** — `orch-do`, `orch-judge` — with tombstones for
   `orch-execute`, `orch-check`, `orch-outline`, `orch-slice` (planning
   craft survives as pack sections read by a planning `do`).
2. **One-door bricks**: `tickets.py do|judge <run> --pack P
   --goal-file F [--details-file D] [--parent ID] [--done …]` folds
   new + stamp + validate + seal + establish + launch-emit into one
   command; child ids auto-mint under the parent. The generated prompt
   gains: the explicit closing-commit line, the typed artifact return
   line (`git:<sha>` | `doc:<path@digest>` | `evidence:<id>`), and for
   judge the verbatim `findings: <path>` line.
3. **Frames**: `tickets.py frame-open|frame-close`; `parent` field
   links the ticket tree into the call tree; frame-close over ≥2
   do-children refuses without a judge child or an `unjudged: <reason>`
   journal line (A2); `orchflows resume` lists this project's open
   frames with age, journal presence, open children, live leases.
4. **The trunk floor is fixed first** (A4): land integrates into the
   run's branch (never the checkout's incumbent), integrate refuses a
   dirty tip-equals-base candidate, retire never prescribes `--force`
   over unintegrated work, and an attempt that ended before launch
   returns status ownership to `set-status`.
5. **Deleted with no fallback**: the loop lane (`tickets_loop`,
   marker, iteration grammar, loop shapes), the template/instantiate/
   placeholder layer and entry kinds, the reader's workflow-summary
   manifest requirement, `ready`/frontier as public doors, the gate
   choreography (`gate`, `checker-stage`, `review_order` — critique→
   repair survives as prose over judge/do; findings JSON + accepted
   flow at land unchanged), admission's graph-shape checks (parentage
   replaces cut membership; the sealed-cut law gives way to
   seal-through-parent for all runtime children).
6. **All eight example workflows become workflow skills** — prose
   bodies calling bricks. super-research and self-improve are crafted
   conversions (the proofs); the other six are mechanical (each stub
   is already a frozen brick call). All render manual-invocation-only.
7. **Docs single-ownered**: vocabulary defines brick/frame/workflow/
   journal and the do/judge/planning-section mapping;
   custom-workflow-authoring.md is rewritten around bricks/frames/
   prose, the four-question router, A5 containment, A7 pack binding;
   host block's graph route becomes frames+bricks+resume.

Acceptance at the tip: `run_required.py --no-cache` exit 0 and
`preflight.py` exit 0; grep proves the deleted surfaces gone; a
temp-sink end-to-end test drives frame-open → do → judge → frame-close
including the A2 refusal and a resume listing.

## Waves and workers

Parallelism is bounded by real file hotspots (shapes.json, registry,
vocabulary, tickets.py command table, serial manifest). Waves:

| wave | tickets | parallel | why this split |
|---|---|---|---|
| W0 | trunk-floor | 1 | the floor every brick lands on; smallest; first |
| W1 | doors-and-contracts | 1 | the load-bearing core; sole owner of shapes/work-item.md this wave |
| W2 | frames-resume ∥ verbs-rename | 2 | scripts vs registry/skills/docs — disjoint files |
| W3 | deletions-1 ∥ workflows-convert | 2 | loop/gate/ready deletions vs example-workflows content — disjoint |
| W4 | deletions-2 ∥ docs-sweep | 2 | instantiate/reader/installer vs pure docs — disjoint |

Driver protocol per wave: fresh worktree per parallel worker off the
migration branch tip; workers commit locally and NEVER push; driver
merges wave branches (conflict on the serial manifest resolves by
regeneration with rulings carried by owner), runs the full gate at the
wave tip, then cuts the next wave's worktrees. One migration branch,
one PR at the end. CI watched to completion, merged, reinstalled;
STOP before dogfooding.

## Standing laws (every worker's brief inherits these)

- Interpreter: `uv run --no-project python …` for everything; bare
  `python` is a Windows Store stub.
- Never pipe gate/test output through tail/head/grep — run plainly
  with a large timeout and read the real exit code.
- Foreground only; run each check to completion in the turn it starts;
  never loop the full gate — diagnose.
- NEVER touch `git stash` (shared stack, foreign entries). WIP commit
  to set work aside. Edit/Write tools, never shell heredocs; forward
  slashes in command paths.
- Scoped tests while working (`tools/run_tests.py --scope …`); case
  modules (`tests/test_*_cases/**`) also need their owning shard run
  by name — the affected-tests mapper is blind to them.
- Test add/remove/rename → `run_serial_compat.py --write-manifest`
  LAST before the gate; NEEDS_RULING → classify per
  `tools/serial-compat-policy.md`, carrying renamed modules' rulings
  by owner.
- T0 changes: hand-edit `contracts/shapes.json` →
  `tools/render_shapes.py --write`; batched
  `T0 supersession record sha256:<predecessor pin>:` per changed
  contract; `tools/validate.py --pin` LAST (pins tangled →
  `git checkout HEAD -- tests/pins.json`, re-pin).
- Near-dup ratchet zero headroom; word budgets are law (host block
  ≤400 words/≤8 demands with its pin updated in-commit; AGENTS.md 230;
  skill bodies per tier budget); reader projections and
  `tests/fixtures/ui/` move with their script-side owners.
- No fallback code, no legacy shims; tombstones refuse-with-remedy and
  never execute legacy behavior. Deletion-first commit ordering.
- Every prescription in a ticket carries its evidence and an escape
  hatch: where following it would break the Goal, deviate and report
  the deviation with grounds. Where the ticket did not investigate,
  the choice is yours — say what you chose and why.
- Report style: what a reader needs and cannot re-derive — every
  command's observed exit code, what changed and why, what you
  deliberately did not do and why, deferrals with reasons. End every
  commit message with:
  Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
