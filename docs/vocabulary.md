# Vocabulary

The library's nouns. Each term is defined once, here, and used with exactly
this meaning everywhere — skills, rules, contracts, tickets, logs. A document
that needs a different meaning needs a different word. A term names its
mechanism in plain words; a metaphor is permitted only where it is already
domain-standard computing usage (kernel, cache, shard, sentinel), never
invented for this library.

## Structure

- **tier** — one of four layers: T0 contracts, T1 skills, T2 packs, T3
  workflows. T0 is the only data interface between them; a higher
  tier may still name a lower one's files and skills, per
  `ARCHITECTURE.md`'s dependency direction. A role's capability is a
  **capability class**, never a tier.
- **contract** — a T0 file defining a pure data shape. Hash-pinned; a shape
  change (below) is breaking even when prose meaning is unchanged.
- **shape change** — a change to a named field or enum in a T0 contract;
  breaking, so it lands only through a supersession PR. A T0 edit moving no
  field or enum is a prose edit, re-pinned without a supersession PR.
- **waist** — the T0 layer as a whole: the one narrow interface many hosts
  sit below and many packs and workflows sit above.
- **skill** — one callable package: a directory whose `SKILL.md` states a
  contract in Require / procedure / Never / Return anatomy.
- **body** — a skill's procedure text: the always-paid part of its
  `SKILL.md`, budgeted by `rules/token-economy.md`.
- **kernel** — the primitive skills under `skills/kernel/`; a kernel
  skill calls no skill.
- **workflow skill** — an assembled T1 skill calling primitives or other
  skills; always domain-blind. It lives under `skills/workflows/`.
- **callable** — one of the two T1 kernel skills under `skills/kernel/`,
  `orch-do` and `orch-judge`, that do all real work. Each is invoked
  through one minting command — `tickets.py do` and `tickets.py judge` —
  which mints the ticket, seals it through its parent, pins the pack
  digest, takes the lease, establishes the workspace, and emits the
  launch, in that one command.
- **frame** — one workflow invocation's durable stack frame: the ticket
  carrying `frame: true` that `tickets.py frame-open` opens and
  `tickets.py frame-close` closes. It binds no executor and stamps no pack,
  because the orchestrator session drives it and a journal is not
  craft-governed work; `contracts/work-item.md` owns the marker, the close
  refusal, and the **parent** link that makes the ticket tree the call tree.
  `orchflows resume` lists this project's open frames.
- **journal** — a frame's `## Report`: the driver's own working memory,
  appended one line per wave through `tickets.py result` and re-read at the
  start of the next. It is where a driver that died — or merely compacted —
  recovers what it already decided, so it is read before a wave and not only
  after a crash.
- **typed artifact line** — the one machine line a callable's child prints
  for its result, `artifact: <kind>:<identity>`, the kind fixed by the
  stamped pack's adapter; a `judge` ticket's child prints `findings: <path>`
  beside it. The
  grammar, the kinds, and what a join grades are `contracts/dispatch.md`'s.
  A parent relays the line as it stands — paraphrase is the failure it
  exists to prevent.
- **checker** — `orch-judge` (formerly orch-check): the planner-role
  callable rendering findings or verdicts over a fixed artifact and never
  a deliverable; it is exempt from the envelope per `rules/composition.md`.
- **retired verb** — a callable name the registry refuses naming its
  successor. orch-execute and orch-check are renamed to `orch-do` and
  `orch-judge`; orch-spec, orch-outline and orch-decompose became a
  planning `orch-do`, which freezes and seals a semantic root at intake;
  orch-slice retired with the decomposed root itself, its craft surviving
  as the planning sections below. No dispatch revives any of them; the noun
  **spec** (below) is unrenamed, and **outline** has now fully retired too —
  its one remaining live use, naming the routing shape's planning lane
  (below), is superseded by **plan**.
- **pack** — a T2 package of pure data satisfying the pack signature; a pack
  binds cells and never contains control flow.
- **cell** — one field of the pack signature: `adapter`, `stages`, and
  `assembly` typed for machinery, `craft` the one document pointer; the
  signature (below) owns the roster.
- **craft section** — one `##` section of a pack's craft document, resolved
  whole through `packs.py cells <digest>`. The signature's craft-section
  table names the mandatory seven; every callable reads the whole document
  and acts under the sections its call is for. A making `orch-do` acts
  under `## Workspace`, `## Stages`, `## Shape` and `## Evidence`; a
  planning one under `## Outline`, `## Spec fields` and `## Slicing`;
  `orch-judge` under `## Lens`. Those are the two entry points the four
  retired verbs collapsed into.
- **signature** — `contracts/pack-signature.md`: the cells every pack must
  provide and the sharing constraints between them.
- **workflow** — a skill whose prose calls callables or other skills: a
  `SKILL.md` under `example-workflows/` (the library's gallery) or a ring's
  workflows directory (yours), invoked only when named and admitted under
  `docs/custom-workflow-authoring.md`. Order, parallelism, branches and
  bounded rounds are that prose; there is no engine beneath it. Each
  invocation opens a **frame**. This is the user-facing word.
- **composition** — the former spelling of **workflow**, surviving as the
  reader's projection type for the older manifest-and-stub shape a ring
  bundle may still ship (`reader/docs/workflows.md`). New prose says
  workflow.
- **dispatchable unit / envelope** — a skill a workflow's prose may call,
  and the leading `Return` fields it must carry — status, result identity,
  verification — per `contracts/result.md`.
- **authoring scope** — where an authored item lands and which admission evidence gates it:
  canonical (the library repository), user, or project. User- and
  project-scope items are custom — outside library law, binding only at
  their scope; bounds per `docs/custom-workflow-authoring.md`.
- **rule** — a clause of cross-cutting law in `rules/`; what any other
  file may do with one is `rules/visibility.md` §3's.
- **call edge** — a resolved backticked skill name in a skill body; the call
  graph is acyclic. A `Require` item riding a named T0 field instead is
  **carriage**, rule 10 of `rules/composition.md`.
- **craft** — the pack cell owning a domain's vocabulary and shape
  principles; cell contract in `contracts/pack-signature.md`.

## Work

- **identity** — what fixes a thing across change: a revision, a content
  digest, a symbol, a run or item id. A coordinate another context can
  move — a line number, a list index, a path into a tree being edited —
  is not one, and neither is a count nor a reading taken from the
  environment.
- **run** — one physical execution of a workflow against one spec; owns a
  run id (`<utc-stamp>-<slug>`), a worklog, and a ticket directory. Its
  tickets form one tree: a frame per invocation, callables under the frame
  that called them. An ad-hoc
  run executes one ad-hoc ticket — or an ad-hoc set — instead: the
  tickets' Goals and Context are its frozen statement,
  the ticket files the whole record — no worklog.
- **unit** — one work item's execution by one context; the scope
  `rules/verification.md` §8 binds.
- **spec** — a run's frozen statement, carried by its root ticket per
  `contracts/work-item.md`; a planning `orch-do` is its only editor, at
  intake, and every later reader treats it as frozen. The noun keeps this
  name after the intake verb was renamed and after orch-outline retired; so
  does the craft's `## Spec fields` section.
- **semantic root** — the executable delivery contract owned by the caller,
  not the spec's general vision. `rules/delegation.md` owns which facts the
  caller freezes and which deterministic corrections a decomposer may make;
  a correction without deterministic equivalence is semantic and suspends
  for the caller.
- **assignment generation** — one assignment fixed by a content digest: the
  run-local root identity named by `root_generation`, always ordinal 1, or a
  pre-seal cut draft named by `cut_generation`. Identity and lifecycle law are
  `rules/topology.md`'s; a sealed semantic change uses a successor run rather
  than a later root ordinal.
- **exemplar** — an artifact a root ticket's `## Context` names to
  imitate, by pointer plus each property the imitation must carry
  (`contracts/work-item.md`); always non-normative.
- **stamp** — the pack fixed at intake, carried by a ticket's `pack`
  field, which every later reader takes blind.
- **domain** — the deliverable's kind (code, content, research,
  design, data); selects an item's pack and review lens, per [topology](../rules/topology.md) §§5–6.
- **work item / ticket** — a sealed Goal, Context, optional Details,
  lifecycle, and graph position, per
  `contracts/work-item.md`; on disk, a markdown ticket the executor writes
  to. The two words name the same thing; ticket is the on-disk view.
- **atom** — a work item at the finest lawful cut: one observable Goal and
  dependency closure. Law, and what lies either side of it, in
  `rules/topology.md` §3.
- **root ticket** — the ticket named by a `root_generation`, directly bound to
  any lawful executor, and parent to whatever hangs beneath it. It completes
  when `land` reads its `done` predicate as met.
  A successor root lives in a successor run
  opened after the accepted predecessor result identity resolves and cites
  that identity in its Context; the predecessor run's durable `successors.md`
  names the planned root until a planning `orch-do` materializes it once the
  run's frontier drains.
- **terminal ticket** — the ticket whose terminal transition ends the run;
  its timing is the run identity's `terminal_at` and `elapsed_ms`
  (`ARCHITECTURE.md`), and `contracts/worklog.md` reads a run's state off
  it.
- **ad-hoc ticket** — a work item the orchestrator cuts directly from a
  one-off request: a Goal and Context persisted with system metadata,
  not a separate species — same contract shape, run id
  `<utc-stamp>-adhoc-<slug>`, `ready` at issue.
- **ad-hoc set** — ad-hoc tickets cut together with dependency edges,
  sharing one run id and ticket directory; the caller names the run
  bound; the ticket files are the whole record — no worklog.
- **routing shape** — the host projection selected before execution, four
  lanes routed smallest-first and normatively defined by the host block's
  routes paragraph (`templates/host-block.md`, installed at
  `~/.orchflows/host-block.md`): **direct** — context evidence decides, and a
  change this session can make, check narrowly, and record in the medium's
  own history it makes itself; **worker** — one `do` (or `judge` over handed
  artifacts), wanting isolation, a fresh context, or a checked landing;
  **team** — parallel children, resume, or an audit trail; **plan** — the
  goal itself is unresolved, so a planning `orch-do` seals the root before
  `team` drives it. Named tripwires promote on evidence, never prediction,
  and live only in the host block — this entry names the lanes, not their
  triggers. `act`, `brick`, `frame`, `outline`, `answer`, `single`, `graph`,
  and `fix` are the retired names for this shape; `frame` no longer
  doubles as lane name and noun — the word stays for the ticket-tree noun
  below, and the lane took `worker` and `team` instead. `brick` is retired
  outright, noun and all: see **callable**, above.
  Small, medium and large are explanatory mappings, never ticket fields.
- **tracker** — the state sink's `tickets/` directory; there is no external
  tracker.
- **executor** — the named skill a work item's frontmatter binds to do the
  work.
- **assembly item** — the at-most-one last work item that integrates
  candidate results into the final artifact before its frame closes.
- **decision gap** — a planning return naming a Goal portion the stamped
  slicing cannot cover.
- **workspace** — where results live and what identities mean there (git
  revisions, doc slots, evidence store), per the pack craft's `## Workspace`
  section.
- **candidate worktree** — the derived tree an isolation-`required` item works
  in, at the path and branch `scripts/state_root.py` derives from the run and
  ticket ids. Nothing else computes either.
- **establish / prepare / retire** — the three acts on that tree, all
  `scripts/workspace.py`'s. `establish` creates and records it inside the
  dispatch transaction; `prepare` installs what the recorded workspace declares,
  lock-free, afterwards; `retire` removes it at the join. Each replays.
- **standards owner** — the workspace's own canonical statement of its
  conventions (linter config, style doc, CI); named by pointer, never
  restated.
- **baseline** — the proven clean starting state of a workspace.

## Verification

- **criterion** — in a structured evaluation, one independently decidable
  question. It is not a ticket section; a ticket's Goal defines success.
- **oracle** — in a structured evaluation, the method actually used to decide
  a criterion. It is recorded after execution, not prescribed in a ticket.
- **oracle class** — deterministic, judged, or evidence, per
  `contracts/verdict.md`; a property of a structured evaluation method.
- **independence** — acceptance evidence originating outside the executing
  context through exactly one ordinary path; law in `rules/verification.md`
  §7. Research craft narrows the term for sources: no shared upstream.
- **verdict** — PASS, FAIL, or UNVERIFIED with evidence and covered identities.
- **evidence** — methods, observations, sources, captures, or other records
  demonstrating or challenging Goal at a fixed artifact identity.
- **provenance** — the recorded chain from an artifact or claim to its
  source, by identity.
- **disagreement register** — where disagreement is recorded with both
  sides' evidence, never averaged away.
- **lens** — the criteria set a reviewer applies; each reviewer of one
  artifact has a unique named lens; freshness law `rules/verification.md`
  §6.
- **critique** — a `judge` ticket scoring one fixed artifact; the
  **repair** answering it is a `do` ticket under the same parent,
  sequenced by the calling workflow's prose rather than a distinct
  adjudication carrier. Neither is authoring admission or benchmark
  qualification. The predecessor-linked `GatePlan`/`CritiqueAdjudication`/
  `RepairOutcome` ledger this pair once wrote through has retired with the
  command that built it; `rules/verification.md` §9 and
  `contracts/work-item.md`'s Review-stage ledger own that history.
- **judge** — scoring one fixed candidate against frozen criteria, blind to
  other candidates: an `orch-judge` ticket whose criteria carry a score
  scale, blindness being a property of the assignment's `inputs`, not of a
  skill. Distinct from the callable `orch-judge` itself, which this noun
  predates; the collision is a naming debt for the full vocabulary sweep.

The benchmark pipeline's artifacts are named here and defined by their
producers, never restated: **evaluation design** (the execute lane's
Return), **benchmark** and its manifest field set
(`example-workflows/references/benchmaker-manifest.md`), **score card**
 (the judging check's Return where the criteria carry a scale), **evolution
result**, **evaluation mode** and **incumbent** (the `evolve`
workflow).

## Delegation

- **dispatch** — starting one fresh child on one sealed ticket. The ticket is
  the assignment it carries — Goal, Context, optional Details,
  operational bound, and exact executor binding, per
  `contracts/work-item.md` and `contracts/dispatch.md`, plus an optional one-shot `profile`
  overriding role resolution for that dispatch alone. Role-bearing dispatch is
  ticket-durable, and nothing travels beside the ticket: see **launch**.
- **assignment seal** — the proof that an exact validated assignment digest
  is immutable for dispatch. A runtime child seals through its parent's own
  generation rather than through a cut that closed before it existed, per
  `contracts/work-item.md`; changing sealed semantic-root fields
  opens a successor run citing the accepted predecessor result under the
  successor-run lifecycle in `rules/delegation.md`.
- **dispatch attempt** — one fenced execution of a sealed ticket under
  `orchflows.dispatch.v1`, identified by `dispatch_id` and an absolute lease;
  its ticket record owns opening, committed-record replay, retirement,
  replacement, and expiry precedence.
- **dispatch outcome** — one attempt's distinguished durable return envelope,
  reserved as `outcome`; it carries the closing evidence and disposition for
  direct commit or unchanged relay before join.
- **candidate authority** — repository/workspace write authority granted to
  an isolated candidate. A path named in Details does not attenuate it; actual
  changes are adjudicated at the join.
- **launch** — the one object a dispatching command — `tickets.py do`,
  `judge`, or `dispatch` for a hand-written ticket — emits and commits: the
  host, verb, agent, model, effort, native fields, and generated prompt for
  the child, resolved from the host record. The caller invokes it verbatim
  and adds nothing. Its prompt is the only child-facing instruction surface
  there is; it points at the ticket rather than copying it, and the child's
  own first filed record is what proves the child accepted it.
- **land** — `tickets.py land`: one locked transaction importing the outcome,
  joining it, retiring the candidate worktree, and reporting the frontier that
  join made ready. It composes the granular return operations, which stay public
  for recovery, and reports which of its steps already replayed.
- **join** — the single point where a caller integrates one child
  result, always `land`. `rules/delegation.md` owns
  what happens there and names its own terms: the closed **disposition** set
  (§9), and the two **blame** classes —
  caller under-supplied, child under-delivered.
- **ladder / rung** — the ordered execution vehicles for one dispatch:
  tested script (the `script:` executor, `contracts/work-item.md`), worker,
  planner; role rungs per `rules/roles.md` §4. Inline is no rung:
  `rules/delegation.md` §2 forbids it for role-bearing skills.
- **role** — planner (judgment) or worker (execution); law in
  `rules/roles.md`.
- **profile** — a role's concrete model and effort binding on one host,
  owned by `hosts/profiles.md`; a
  ticket's optional `profile` slot names one explicitly, overriding role
  resolution for that dispatch.
- **host** — the runtime carrying the agents; one record per host under
  `hosts/` names them and owns each one's launch binding. `tickets.py dispatch
  --host <host>` selects one, defaulting to `$ORCHFLOWS_HOST`, else `claude`.

## Iteration

- **bounded campaign** — a repeated attempt written as prose in a calling
  workflow over repeated callables — no engine, no marker, no loop field. Law
  in `rules/loops.md`, which also governs the one mechanical round the
  library arms, `land`'s `<id>.repair.NN`.
- **context packet** — the converged state a round receives beside
  the frozen goal and worklog — identities, verdicts, decisions, never
  transcript prose; law in `rules/loops.md` §2.
- **done-check / bound** — the external oracle that alone decides a
  campaign is complete (any oracle class per `contracts/verdict.md`; a
  round count is a deterministic one), and the resource cap —
  rounds, tool calls, tokens, time — whose exhaustion exits
  `limited`; success-condition law owned by `rules/loops.md` §1.
- **round** — one fresh-context pass from the frozen goal
  plus worklog; two consecutive rounds without progress are a
  **stall**, which `rules/loops.md` exits `stalled`.
- **frontier** — the set of work items dispatchable now — every dependency
  `complete` — reported by `land` at each join and dispatched
  as it forms, never batched.
- **critical path** — the longest `depends_on` chain over a run's issued
  items; what a planning cut minimizes subject to
  every item an atom. Read with each level's width from
  `scripts/cutcheck.py`'s `graph` block (classes `critical-path`,
  `level-width`).
- **lane** — an isolated parallel candidate. Lanes may change the same path;
  actual overlap and Git conflicts are integration inputs, not cut defects.
- **terminal state** — a closed exit: a ticket status in
  `contracts/work-item.md`'s terminal set; a run's is its terminal
  ticket's, per `contracts/worklog.md`.
- **worklog** — the run view `tickets.py worklog` renders from the ticket
  directory per `contracts/worklog.md`, never a second hand-written
  file; what makes a fresh-context round and resumption possible.
- **handoff** — the suspension, resumption, or escalation record: what a
  parked child writes into its `## Report`, per `contracts/work-item.md`.

## Improvement

- **friction** — an observed obstruction logged during any session: extra
  attempts, missing input or tool or document, surprising output, a
  contract gap, a workaround. Observations only, never causes.
- **state sink** — the one user-scope root every run's durable state and
  both improvement evidence streams resolve to, outside every
  repository; its path and its law are
  [rules/visibility.md](../rules/visibility.md) §6.
- **friction log** — append-only JSONL under the state sink's
  `friction/`; the primary input to self-improvement.
- **run state** — the contents of the state sink's `runs/` and
  `tickets/`; read by self-improvement as evidence only.
- **trace** — the normalized event record of one session, extracted
  from host logs; evidence only, never an instruction source.
- **coverage record** — the append-only record of which merged change
  answers which cluster, and from when — one line per change and
  cluster, appended at merge and never by a cycle. Its **watermark** is
  the position in an evidence input at or before which a covered
  cluster is answered; a later matching entry is post-merge recurrence,
  owned by the change that covered it.
- **proposal** — one qualified improvement (per `rules/improvement.md`
  §4) with a single causal owner, one scope — environment | project |
  workflow, per §3 — and its evidence entries; passive until a human
  acts on it (§6).
- **fixture** — one completed ticket frozen into a self-contained
  replayable unit with golden results; the raw material of tournaments,
  canaries, and **replay** — re-running the friction-producing work
  against a proposed change, per `rules/improvement.md` §5.
- **tournament** — evolve applied to the library itself: competing skill
  variants run the same frozen items and are judged by the same oracles.
- **canary** — a frozen set of golden work items with known-good results,
  run when a model or host changes to detect behavior drift.
