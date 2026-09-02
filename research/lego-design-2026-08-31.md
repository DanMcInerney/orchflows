# The lego design — bricks, frames, prose

2026-08-31. Status: PROPOSED. Successor design to the four-verb library,
drafted with the user across the 2026-08-31 session; supersedes the
pipeline-stanza sketch. Evidence base: the seven investigations of
2026-08-30 (research/subagent-simplification-design-2026-08-30.md), the
rings design (research/orchflows-rings-2026-08-31.md), and the
super-research dogfood run (20260831T112728Z-super-research-delivery,
14 frictions).

## The idea in one paragraph

Workflows and skills are the same kind. A workflow is a skill whose
prose calls other skills — deterministically (literal calls written in
the body) or flexibly (a planning call decides the calls) — down to two
core bricks that do all real work. Composition is a programming language
of functions calling functions; the interpreter is whatever agent the
user is already talking to. Durability comes from one move: every
invocation opens a ticket, and parent links make the ticket tree mirror
the call tree — a durable stack any orchestrator on any harness can
resume.

## Positioning law (the firstmate test)

orchflows never owns a loop. No daemon, no watcher, no resident process.
It ships skills, scripts, and a state directory, and upgrades whatever
agent loaded the host block — a Claude Code session, Codex, Grok, or an
agent some other supervisor (e.g. firstmate) spawned. Every design
element must pass: "does this require a resident process or harness
privileges?" If yes, it belongs to the host, not the library. The
orchestrator's model is the user's session choice; child models come
from the two profiles (planner, worker) in the host records.

## The stack

```
 USER
   │  utterance; model chosen in the harness UI
   ▼
 ORCHESTRATOR = the harness session (host block routes; rings resolve)
   │  reads prose, decides; may die; `orchflows resume` recovers
   ▼
 WORKFLOW SKILLS (T2/T3/T4… — no structural difference, only depth)
   prose glue: order, parallelism, loops, conditionals
   each invocation opens a FRAME ticket (durable stack frame)
   ▼
 T1 BRICKS — exactly two:
   do(pack, goal)     one agent, one artifact, own ticket lifecycle
   judge(pack, goal, artifacts)   read-only, structurally independent
   ▼
 MECHANICAL TRUNK (scripts; no LLM; every guarantee lives here)
   ▼
 STATE SINK (durable truth) + GIT (candidate worktrees, landings)
```

## Packs: same craft, two doors

Packs are unchanged — 4-cell SKILL.md + one craft.md with the mandatory
sections. The four verbs were four doorways into the craft; now two:

- `do` making an artifact reads ## Workspace, ## Stages, ## Shape,
  ## Evidence.
- `do` planning (goal = a frozen goal or a call plan) reads ## Outline,
  ## Spec fields, ## Slicing.
- `judge` reads ## Lens (weighing law and blocking rule included).

orch-outline and orch-slice retire as verbs; their craft survives as
the planning sections. orch-execute → do, orch-check → judge.

## Frames — the durable call stack

- Every workflow invocation opens a frame ticket: goal sealed at open,
  `--parent` linking it under its caller's frame. Brick tickets hang
  under the frame that called them. The ticket tree IS the call tree.
- The frame's ## Report is the orchestrator's journal: one appended
  line per wave/decision. Habit, not law — the floor beneath it is
  re-derivation: a resumed orchestrator holds the sealed goal plus all
  completed children's evidence, and terminal tickets never re-run, so
  resumption is idempotent by construction.
- `orchflows resume` lists this project's open frames: goal, age, open
  children, live leases, journal presence. Pull-based. Frames carry no
  lease (the orchestrator is a session, not a dispatched child); a
  stale open frame is shown with its age and the human judges —
  unknown never decays into idle.
- A called workflow's frame may be driven inline by the caller or
  handed to a spawned orchestrator agent; the tree is identical either
  way. Durability lives in the tree, not in the driver.

## Bricks — where every guarantee lives

One door in, one machine line out:

```
 do(pack, "goal…")
 ┌───────────────────────────────────────────────────────────┐
 │ open:  goal sealed · pack digest pinned · absolute lease  │
 │ work:  spawned agent (planner/worker profile per hosts)   │
 │        idempotent records (dispatch_id + record_id)       │
 │ close: done = real command → exit code, never a claim     │
 │ land:  evidence bound · candidate merged · worktree gone  │
 └───────────────────────────────────────────────────────────┘
 returns: "ticket: <path>   artifact: git:<sha>"
```

The parent passes that returned line verbatim wherever a later brick
needs the artifact — the one-line contract that remains of the packet.
Judges keep the machine half of review: findings as a JSON file the
land binds (accepted-blockers flow unchanged).

## Control flow is prose

Loops, nested loops, branches, retries, tournaments: the calling
skill's language, with `judge` as every loop's exit condition and
`bound` fields as the budget. No loop machinery in the library.

```
 n = 1
 ┌──► do(code-pack, "attempt n; prior findings attached")
 │       judge(code-pack, artifact)
 │  FAIL + findings ──┘  (n ≤ bound)
 └── PASS ──► frame close (done: required gate)
```

## Example: nested loops across tiers

/market-thesis (T3): outer loop — fan out /super-research (T2) per open
question, draft/revise via do(content), judge the thesis; findings feed
the next round; ≤3 rounds; frame done = a verifier command.
/super-research (T2): parallel do(research) per source; inner loop —
judge coverage, targeted do per named gap, ≤2 rounds; frame done = the
dossier verifier. Every rung at every depth is a sealed, leased,
evidence-bearing, resumable ticket.

## What this deletes (the diet)

- tickets_loop and the loop marker/iteration grammar (both 2026-08-31
  loop-lane fixes become unnecessary; they de-risked the interim).
- The template/instantiate/placeholder layer; entry kinds; the reader's
  workflow-summary manifest requirement.
- Cut generations and the stamp/validate/seal door parade as separate
  public doors (compare-and-swap sealing survives inside frame/brick
  open).
- Admission's graph-shape checks (parentage replaces cut membership);
  ready/frontier.
- The gate choreography (gate/checker-stage verbs, review_order); the
  critique→repair pattern survives as prose over judge and do.
- The pipeline-stanza proposal (subsumed by prose).

## What survives, and why (the perfect-model test)

Kept only where a perfect model still could not: resume a crashed
session (frames, sink), prove an unwatched claim (seal, done-as-exit,
idempotent return, lease), see a composition from a member's seat
(judge over N artifacts), audit later (sink, friction). Rings, packs,
digest trust, hosts/profiles: unchanged.

## Eyes-open costs

1. Frames without journals recover by re-derivation, not replay.
   Accepted floor; journaling is one cheap habit.
2. Parent-mediated handoffs can drift; the verbatim machine-line is
   the mitigation and it is one line.
3. The composition vantage is opt-in (write the judge line). The
   four-question router (needs a second agent? survives a crash? lands
   somewhere risky? needs the audit trail?) moves to authoring craft in
   the one workflow-authoring doc.
4. Sunk cost stated plainly: parts of PR #144/#147 (loop lane) and the
   instantiate half of #145 are deleted by this design.

## Amendments after the 2026-08-31 Fable review

A1. **The journal is the driver's working memory, not a habit.** The
review's sharpest finding: the common failure of a prose driver is not
death but degradation — context compaction mid-workflow silently
paraphrases the verbatim lines the parent was trusted to relay, and
resume never fires because nothing died. The incumbent's ready/frontier
statelessness was accidentally load-bearing. Fix in this design's own
vocabulary: waves are pull-based for the LIVING driver too — each wave
begins by re-reading the frame journal and child states from the sink,
then appends its decision. The journal stops being append-only memory
insurance and becomes the source of truth the driver returns to.
2. **Judge-or-say-why at multi-child close.** Composition-invisibility
is an information-access problem, so it passes the perfect-model test
and deserves structure: frame close over two or more do-children
refuses unless the tree holds a judge child or the journal carries an
explicit `unjudged: <reason>` line. One mechanical check; converts the
silent under-review hole into an auditable, ledger-visible decision.
3. **Typed return lines.** The one-line contract was git-shaped. The
artifact line is typed per adapter (`git:<sha>` | `doc:<path@digest>` |
`evidence:<id>`), and judge returns a second verbatim line
(`findings: <path>`) so findings relay never rides through paraphrase —
the loop example's "prior findings attached" gets the same machine-line
treatment as the artifact.
4. **Trunk first.** The migration's first stage is the kept trunk's
open defects (integration targets the run branch, integrate refuses a
dirty tip-equals-base candidate, retire never prescribes --force at
unintegrated work) — bricks must not launch atop the floor's known
holes.
5. **Containment default for imported prose.** A ring-imported
workflow's prose executes as orchestrator reasoning — a wider surface
than a sealed child prompt. Default: bundles you authored may drive
inline; imported bundles drive in a spawned frame agent unless the user
says otherwise.
6. **The brick lease stays (review rebutted on this point).** The
review called it borderline under perfect models; it is not a
capability mechanism — it arbitrates writer contention on dispatchable
work, which no model quality removes. The asymmetry is now explicit:
frames have a singular session-bound driver (age-display suffices);
bricks are dispatchable by anyone holding the sink (the lease is the
arbiter).

7. **Packs bind to bricks; frames are pack-less; no tier rule.** Every
`do`/`judge` call names exactly one pack — that call's craft, workspace
semantics, and evidence discipline. Workflows at any depth mix packs
freely because bricks never share a workspace: each adapter owns its
own brick's world, and the only cross-pack carriers are the frame
journal and the typed artifact lines (A3). One brick = one pack = one
artifact (two domains in one deliverable = two bricks + a handoff, or
one pack whose craft already covers both). Frames carry no pack: a
frame is a journal, not craft-governed work — its done is a command or
a judge brick that brings its own pack. The old one-pack-per-run law is
formally dead; the adapter-compatibility concern it guarded dissolves
with shared workspaces.

## Migration sketch

1. Brick doors: `do`/`judge` one-command open (fold new+stamp+
   validate+seal), frame open/close with `--parent`; `orchflows
   resume`.
2. Registry to two verbs with tombstones (outline/slice → planning
   craft); packs' section mapping doc updated.
3. Convert self-improve (mine = one do; deliver = do + judge, gated by
   prose) and super-research (workflow skill with literal per-source
   calls + coverage-judge loop) as the proofs; manual-only launchers.
4. Deletion inventory above, staged gate-green; docs/vocabulary follow;
   the authoring doc rewritten around bricks/frames/prose and the
   four-question router.
```
