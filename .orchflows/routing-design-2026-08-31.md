# The routing design — need-bought machinery

2026-08-31. Status: PROPOSED. Successor to the host block's
answer/single/graph/outline/fix routes, designed from scratch on the
lego substrate (PR #153: bricks, frames, prose). Drafted with the user
across the 2026-08-31 session from three investigations: the friction
inventory (sink `friction/2026-08.jsonl`, 7,283 lines;
`research/orchflows-speed-spec-2026-08-23.md`; the errand-lane handoff
`handoffs/20260825T200632Z-errand-lane/HANDOFF.md`), the routing
archaeology (git history `e46ce0de`..`4bad0a4a`), and the mechanical
cost model of the shipped surface. Supersedes the errand-lane handoff's
mechanism while keeping its two principles (below); the four rulings in
§Decisions were made by the user's delegate in-session.

## The idea in one paragraph

Every prior default routing paid a classification tax before any work
happened: the orchestrator predicted the work's size (pack? outline?
slice?), then bought ceremony to match the prediction — and a wrong
prediction cost hours (a one-line fix: 2h50m, 21 agent spawns, 7 runs,
5 cold suite runs). This design inverts it. The machinery sells exactly
four things — a second context, durability across crash/sessions, a
safe landing, an audit trail — and each is bought separately, when the
work demonstrably needs it, never on prediction. The empty set is a
real tier: work needing none of the four gets none of the machinery.
Escalation replaces classification: start at the lowest plausible lane;
named tripwires promote on evidence. Misrouting down costs seconds (a
promotion); misrouting up used to cost hours. That asymmetry is the
whole argument.

## Laws inherited (violate these and the design dies like its ancestors)

1. **The routed set never grows.** Every route addition died in hours
   (first-class `errand`: PR #106 08:58 → killed PR #107 11:47,
   2026-08-26). This design SHRINKS the set: five named routes → four.
2. **Size is never a field.** "Small, medium and large are explanatory
   mappings, never ticket fields" (vocabulary, standing law). The lanes
   here route by need, not size; tier names below are explanatory.
3. **The always-paid surface stays fixed.** The host block's routes
   paragraph stays inside the 400-word/8-demand budget; growth happens
   in named things called from it (DESIGN.md, ticket-set redesign).
4. **Ceremony prices to blast radius, not library size**, and **a
   consequence is part of the change, never a new run** (errand-lane
   handoff — the two sentences that survive it).

## The four lanes

### act — the tier that never existed

`answer` generalized from "context evidence decides" to "context
evidence decides, and a change this session can make, check narrowly,
and record in its medium's own history, it makes itself." Edit, run the
narrow check, commit. No ticket, no child, no frame, no review: for
tiny user-facing work the user reading the diff IS the review, and any
machinery review on top of it is theater. Target: seconds.

Two boundaries keep it honest:

- **The medium's own durable trace is the record** — a commit, an
  install receipt, a versioned artifact. A mutation whose medium keeps
  no history is not `act`; that absence is itself the signal the work
  needs a brick. No journal line beside the commit: the commit already
  records what/who/when/why, and a second record is the
  one-fact-two-homes defect.
- **A `role: none` root never acts.** Roots run deterministic commands
  whose output is derived (regen, render, format) — that is glue — and
  author nothing. Grounds: root edits bypass the candidate/land
  integration story (the still-alive isolation-lie friction class);
  A1's degradation finding ("the common failure of a prose driver is
  not death but degradation") makes just-fixing-things a drift vector
  with no tripwire; and a consequence spotted mid-run folds into the
  responsible child's ticket, never into root authorship.

### brick — one `do`, the real single

Work wanting isolation, a fresh context, or an oracle-checked landing:
one parentless `tickets.py do` (or `judge` over handed artifacts).
This is already the mechanically cheapest shipped path — 2 driver
commands, 1 child. `done: command` whenever a deterministic oracle
exists; `land` running it in the integrated tree is the one outside
execution. **No judge by default at this lane, ever** — a
deterministic verdict costs zero agents (the 76k-token/12-min
re-verifier, commit `419a3f44`, and the 14.1M-token verify child,
commit `60b73b8d`, are the tombstones). A frame is optional here for
durability on long single-brick work; with one child A2 never fires.

The documented `single` route (`new --file` → `dispatch` → `land`) is
dead code — `new` strips seals and the sealing doors retired into the
`do` fold — so this lane is a rename to the truth, not a behavior
change.

### frame — parallel, resumable, audited

Work needing parallel children, resume, or an audit trail:
`frame-open`, children in parallel, journal as working memory (A1),
close under A2 (judge the seams or say `unjudged: <reason>`). Children
run scoped checks only; the full required suite runs ONCE, at the
close, in the integrated tip (§One-suite law). The A2 gate stays
exactly as shipped — the one review mechanism the migration made
STRICTER, correctly: it converts silent non-review into an auditable
one-line decision.

### outline — unresolved goals only

When the goal itself is unresolved (missing evidence, undecided kind
boundaries, pending user decisions): one planning `do` seals the root,
then `frame` drives it. The only lane that pays before working, because
the payment is the work. The planner never drives the run.

### Tripwires (promotion on evidence, never prediction)

- A second concern surfacing mid-`act` promotes to `brick`.
- A child's scope splitting promotes to `frame`.
- **An unknown or unverified cause investigates before anything
  edits** — no lane authors a fix for a cause nobody confirmed (the
  verify-the-critic episode is the standing evidence). `fix` retires as
  a route name; this tripwire is its surviving content. A known cause
  routes by blast radius like everything else.

Demotion is free: a frame with one child closes without ceremony.

## Review, rebuilt from zero

The archaeology shows six weeks re-litigating WHO reviews (five
reviewer identity changes) when the stable question was WHEN review
pays. The shipped end-state — review is not a role but a `judge` brick
sequenced by prose; the dormant `review_kind` apparatus is structurally
unreachable — is taken as the ground, and three principles replace all
choreography:

1. **Deterministic verdicts cost zero agents.** `done` at land,
   already law. Every lane states its deciding command when one exists.
2. **The judge reads seams, not repeats.** At a multi-worker close the
   one judge's goal is composition: do the parts fit, did any worker's
   green go vacuous at the merged tip (the join-side vantage law). It
   never re-runs per-child oracles — those ran, scoped, at each land.
   This is also the honest answer to the PR #80 dissent (checkers
   caught real defects): those catches were protocol defects whose
   protocol is deleted; what a fresh reader uniquely catches now is
   seam-blindness, so that is the whole job description.
3. **Repair is one prose round, then the predicate decides.** Findings
   → one `do` fixing accepted blockers → land re-runs `done`. No second
   critique child (repair invalidated the verdict context — the
   `ac9122b5` law; the "new verifier" is the free predicate re-run). A
   second round requires a journal line saying why round one did not
   stick; two byte-identical round results are `stalled` (existing
   law). Loops cannot spiral because nothing re-arms silently.

**A2 keeps its escape hatch, deliberately.** Auto-judge at ≥N workers
is mandatory review in a new hat; every automatic review mechanism in
the history decayed into theater because automation cannot price
semantic risk. Compare failure modes honestly: a rubber-stamp judge
costs a child AND launders false confidence (a green that does not
bite — the worst documented defect class); a rubber-stamp `unjudged:`
line costs nothing and is VISIBLY a skipped review — greppable,
attributable, mineable. The teeth are the feedback loop, not the gate:
`unjudged:` reasons accumulate in frame journals, `self-improve` mines
them, and bad patterns become craft amendments. Evidence → law, never
prediction → ceremony.

## The one-suite law

Routing owns WHERE the full required suite runs: **once per landing
surface, at the integrated tip, as the closing `done` — and nowhere
below.** Children run the narrow affected checks their craft names.
`act` work never runs the suite: the narrow check locally; CI at the PR
is its suite at the tip. This kills the re-verification multiplier —
the #1 still-alive friction (646 full-suite mentions in 8 days; per-unit
oracles executed 3+ times; the tree-hash cache covers only clean trees
and small work lives in dirty ones).

## The UX contract: say the lane out loud

One line, always, before work starts: "acting directly — one-line
change, the commit is the record" / "one brick — isolation wanted,
done: the affected test" / "opening a frame — 3 workers, one suite at
the tip, seam-judge at close." Costs nothing; converts every misroute
from a discovery-after-hours into a correction-in-seconds. The user's
redirect is lane control with no new flags and no new fields.

## Decisions (ruled in-session, 2026-08-31)

- **D1 — act's record is the medium's trace, nothing else.** No journal
  line beside a commit; no-trace media are not `act`.
- **D2 — act is for interactive sessions; roots stay glue-only**, with
  the derived-deterministic-command carve-out stated in the routes.
- **D3 — A2 unchanged**; strengthen via the `unjudged:`-mining loop,
  never via an auto-judge threshold.
- **D4 — `fix` deleted as a route name**; its unknown-cause sentence
  survives as a tripwire. Routed set: act, brick, frame, outline.

Naming note: `brick` and `frame` as lane names are the same benign
metonymy `graph` was — the lane named by the thing it buys. The
vocabulary's routing-shape entry rewrites accordingly; the judge-noun /
`orch-judge` collision stays the separately-flagged naming debt.

## The host-block routes paragraph, drafted verbatim

Replaces the current routes text at parity length (~250 words; the
block's surrounding preamble — role refusals, `orch-off`, user-only
relay — is untouched). Delivery re-counts the full block against the
400-word/8-demand budget and updates the pin in-commit; the
demand-anchor tests (`TestHostBlockBrickFlags`, thin-orchestrator route
pins) move with it.

> Route by need, smallest first; name the lane in one line before
> working. **act** — context evidence decides an answer; a change this
> session can make, check narrowly, and record in the medium's own
> history it makes itself — the commit is the record; no durable trace,
> no act. A `role: none` root never acts: derived deterministic
> commands only, authoring nothing. **brick** — work wanting isolation,
> a fresh context, or a checked landing takes one `tickets.py do <run>
> --pack <pack> --goal-file <f> [--parent <frame>] [--workspace
> <tree>]`, or `judge` over artifacts it is handed; invoke the emitted
> `launch` verbatim adding nothing, then `tickets.py land`: it reads
> `done`, integrates, prints the freed frontier. Declaring none, grade
> with `land --status`. **frame** — parallel children, resume, or an
> audit trail opens `tickets.py frame-open <run>`; each wave re-read
> its `## Report`; append decisions through `result`, relaying
> `artifact:` and `findings:` lines verbatim; children run scoped
> checks — the full suite runs once, at the close, in the integrated
> tip; end at `frame-close`, judging the seams or saying
> `unjudged: <reason>`; `orchflows resume` lists open frames.
> **outline** — an unresolved goal seals first through one planning
> `orch-do`; the planner never drives. Tripwires promote, never
> predict: a second concern mid-act enters brick; splitting scope
> enters frame; an unknown cause investigates before any edit.
> Skill/workflow/pack/contract/router work carries
> `docs/custom-workflow-authoring.md` in Context. `install.py doctor`
> diagnoses dispatch; `evolve` and `benchmaker` run only when named.

## Walkthroughs

- "Fix the typo in the blog post" → act: edit, commit, "done — the
  diff is one line." Seconds. Against the measured baseline: 2h50m,
  21 spawns, 7 runs (PR #95).
- "Add retry logic to the API client" → brick: one `do(orch-code-pack)`
  with `done:` the affected test command; land runs it integrated.
  Minutes; zero review children.
- "Build the export feature" → frame: 3 `do` in parallel, seam-judge
  (1 child, not 3-per-lens), one suite at the tip, close.
- "Redesign the docs" → outline: kind boundaries unresolved; a
  planning `do` seals the root first.

## Mechanical follow-ups (delivery scope, mostly deletions)

- M1: rewrite the host block routes (draft above); budget arithmetic +
  pin + demand-anchor tests in the same commit.
- M2: delete the unreachable `review_kind` apparatus
  (`tickets_review.py` checker_plan/adjudicate/repair_outcome readers,
  `tickets_join.py` review joins, `REVIEW_KINDS`, the `--review-kind`
  usage remnant, `contracts/work-item.md:87`'s lane text) — the
  no-legacy law applies to dormant code. Keep whatever the findings/
  accepted flow at `land` actually still reads; delete by
  surviving-reader census, W3a-style.
- M3: decide `new --file`'s fate — `do --goal-file --details-file`
  covers hand tickets; the unsealable `new` path dies rather than
  gaining a seal door.
- M4: add the scope sentence ("narrow affected checks; the full suite
  is the close's row") to the four packs whose craft lacks it
  (content/data/design/research — today only orch-code-pack carries
  the anchor `_craft_scope()` extracts).
- M5: sweep the ~19 orphaned pre-migration modules out of the
  installed `bin/` (installer hygiene; they will confuse the next
  archaeologist).
- M6: vocabulary — routing-shape entry rewritten to the four lanes;
  `answer`/`single`/`graph` retire as names; tripwires' one home is
  the host block (the authoring doc's four-question router remains the
  authoring-time counterpart and must not restate the lanes).

## Acceptance at the tip

Gate + preflight green; the PR #95 shape replayed as `act` completes in
one session turn with zero children and one commit; a single-brick task
runs exactly one child and one `done` execution; a 3-worker frame runs
the full suite exactly once; grep proves `single`, `graph`, `fix`, and
`review_kind` route nowhere; the errand-lane handoff is marked
superseded by this file.
