# Vocabulary

The library's nouns. Each term is defined once, here, and used with exactly
this meaning everywhere — skills, rules, contracts, tickets, logs. A document
that needs a different meaning needs a different word.

## Structure

- **tier** — one of four layers: T0 contracts, T1 skills, T2 packs, T3
  compositions. T0 is the only data interface between them; a higher
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
  `SKILL.md`, budgeted by `rules/token-economy.md`. What a loop
  iteration dispatches is its **loop body**: the loop stub's own
  `executor` verb (`rules/loops.md`), never a call edge.
- **kernel** — the primitive skills under `skills/kernel/`; a kernel
  skill calls no skill.
- **workflow** — an assembled skill calling primitives or other
  workflows; always domain-blind. A T3 composition is a **named
  workflow**.
- **checker** — `orch-check`: the planner-role callable rendering findings
  or verdicts over a fixed artifact and never a deliverable; it is exempt
  from the envelope per `rules/composition.md`.
- **outline** — `orch-outline`: the planner-role callable that freezes and
  seals a semantic root at intake, reading the stamped pack craft's
  `## Outline` and `## Spec fields` sections to do it. It supersedes the
  earlier intake-verb name, which no
  dispatch revives; the noun **spec** (below) is unrenamed. As a routing shape it is
  the shape (below) that reaches this verb.
- **pack** — a T2 package of pure data satisfying the pack signature; a pack
  binds cells and never contains control flow.
- **cell** — one field of the pack signature: `adapter`, `stages`, and
  `assembly` typed for machinery, `craft` the one document pointer; the
  signature (below) owns the roster.
- **craft section** — one `##` section of a pack's craft document, resolved
  whole through `packs.py cells <digest>`. The signature's craft-section
  table names the mandatory seven; every verb reads the whole document and
  acts under the sections its skill names.
- **signature** — `contracts/pack-signature.md`: the cells every pack must
  provide and the sharing constraints between them.
- **composition** — a T3 named workflow: a template (below) under
  `compositions/` (canonical) or `<repo>/.orchflows/compositions/`
  (custom); entry `routed | named`; admitted under
  `docs/custom-workflow-authoring.md`. One instantiated into a run is a
  **composition instance**.
- **combinator** — one of the three ways a template composes its stubs:
  a `depends_on` edge, disjoint parallel stubs (no dependency path
  between them, so the frontier may run them together), and a loop stub
  (the `loop` field of `contracts/work-item.md`). There is no fourth.
- **dispatchable unit / envelope** — a skill or composition another may
  bind as a step or loop body, and the leading `Return` fields it must
  carry — status, result identity, verification — per
  `contracts/result.md`.
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
  run id (`<utc-stamp>-<slug>`), a worklog, and a ticket directory. When
  decomposed it has one root ticket and one composite gate. An ad-hoc
  run executes one ad-hoc ticket — or an ad-hoc set — instead: the
  tickets' Goals and Context are its frozen statement,
  the ticket files the whole record — no worklog.
- **unit** — one work item's execution by one context; the scope
  `rules/verification.md` §8 binds.
- **spec** — a run's frozen statement, carried by its root ticket per
  `contracts/work-item.md`; input to decomposition; `orch-outline` is its
  only editor, at intake — every other reader, `orch-decompose`
  included while cutting, treats it as frozen. The noun keeps this name
  after the intake verb was renamed; so does the craft's `## Spec fields`
  section.
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
  design, data); selects an item's pack and gate lens, per [topology](../rules/topology.md) §§5–6.
- **work item / ticket** — a sealed Goal, Context, optional Details,
  lifecycle, and graph position, per
  `contracts/work-item.md`; on disk, a markdown ticket the executor writes
  to. The two words name the same thing; ticket is the on-disk view.
- **atom** — a work item at the finest lawful cut: one observable Goal and
  dependency closure. Law, and what lies either side of it, in
  `rules/topology.md` §3.
- **root ticket** — the ticket named by a `root_generation`, directly bound to
  any lawful executor. A decomposed root uses `orch-decompose`; its subtree is
  any `<id>.NN` unit tickets plus `<id>.gate.*`, and it completes when
  `land` reads its `done` predicate as met. A successor root lives in a successor run
  opened after the accepted predecessor result identity resolves and cites
  that identity in its Context; the predecessor run's durable `successors.md`
  names the planned root until `orch-outline` materializes it once the run's
  frontier drains.
- **template** — a directory of ticket stubs plus its `template.md`
  manifest, instantiated into a run's ticket directory by `tickets.py
  instantiate` and drained by the driver two commands at a time; the one
  form a composition takes. Shape per `contracts/work-item.md`.
- **stub** — a template's unit: a ticket missing only `run`, `status`,
  `claimed_*` and any `{{placeholder}}`.
- **terminal ticket** — the stub no other stub depends on; its Goal is the
  template's final observable result.
- **ad-hoc ticket** — a work item the orchestrator cuts directly from a
  one-off request: a Goal and Context persisted with system metadata,
  not a separate species — same contract shape, run id
  `<utc-stamp>-adhoc-<slug>`, `ready` at issue.
- **ad-hoc set** — ad-hoc tickets cut together with dependency edges,
  sharing one run id and ticket directory; the caller names the run
  bound; the ticket files are the whole record — no worklog.
- **routing shape** — the host projection selected before execution:
  `answer` when available evidence decides; `single` for one ordinary ticket;
  `graph` for a frozen root that needs decomposition; `outline` when a planner
  must first freeze that root, preserve its claim lifecycle, then decompose it.
  `fix` is no fifth shape: it disambiguates a known cause into `single` and an
  unknown or unverified one into `outline`.
  Small, medium and large are explanatory mappings, never ticket fields.
- **tracker** — the state sink's `tickets/` directory; there is no external
  tracker.
- **executor** — the named skill a work item's frontmatter binds to do the
  work.
- **assembly item** — the at-most-one terminal work item that integrates
  candidate results into the final artifact before the final gate.
- **decision gap** — a decomposition return naming a Goal portion the stamped
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
  §9. Research craft narrows the term for sources: no shared upstream.
- **checker** — the durable adjudication carrier for the ordinary
  outside-independence path: an explicit derived review-stage ticket whose
  fresh read-only `orch-check` accepts the exact assignment, challenges one
  fixed artifact and its evidence, and joins its accepted set before the
  target can record `checked_by`.
- **verdict** — PASS, FAIL, or UNVERIFIED with evidence and covered identities.
- **evidence** — methods, observations, sources, captures, or other records
  demonstrating or challenging Goal at a fixed artifact identity.
- **provenance** — the recorded chain from an artifact or claim to its
  source, by identity.
- **disagreement register** — where disagreement is recorded with both
  sides' evidence, never averaged away.
- **lens** — the criteria set a reviewer applies; every additional root-gate
  reviewer has a unique named lens; freshness law `rules/verification.md`
  §6.
- **ordered lens bundle** — an opt-in stable adjudication order of unique lens
  identities. Their independent critique tickets remain parallel; the order
  does not add execution dependencies.
- **gate** — a decomposed run's immutable predecessor-linked `GatePlan` →
  `CritiqueAdjudication` → `RepairOutcome` path. It fixes
  reviewed and repaired artifact identities, accepted blockers, root pack,
  established workspace, and normalized isolation `none`; authoring admission
  and benchmark qualification are not gates.
- **judge** — scoring one fixed candidate against frozen criteria, blind to
  other candidates: an `orch-check` ticket whose criteria carry a score scale,
  blindness being a property of the assignment's `inputs`, not of a skill.

The benchmark pipeline's artifacts are named here and defined by their
producers, never restated: **evaluation design** (the execute lane's
Return), **benchmark** and its manifest field set
(`compositions/references/benchmaker-manifest.md`), **score card**
 (the judging check's Return where the criteria carry a scale), **evolution
result**, **evaluation mode** and **incumbent** (the `evolve`
composition).

## Delegation

- **dispatch** — starting one fresh child on one sealed ticket. The ticket is
  the assignment it carries — Goal, Context, optional Details,
  operational bound, and exact executor binding, per
  `contracts/work-item.md` and `contracts/dispatch.md`, plus an optional one-shot `profile`
  overriding role resolution for that dispatch alone. Role-bearing dispatch is
  ticket-durable, and nothing travels beside the ticket: see **launch**.
- **assignment seal** — the proof that an exact validated assignment digest
  is immutable for dispatch. A later cut generation may add or change members
  under the same immutable root semantics; changing sealed semantic-root fields
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
- **launch** — the one object `tickets.py dispatch` emits and commits: the
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

- **context packet** — the converged state an iteration receives beside
  the frozen goal and worklog — identities, verdicts, decisions, never
  transcript prose; law in `rules/loops.md` §2.
- **done-check / bound** — the external oracle that alone decides a
  loop is complete (any oracle class per `contracts/verdict.md`; an
  iteration count is a deterministic one), and the resource cap —
  iterations, tool calls, tokens, time — whose exhaustion exits
  `limited`; success-condition law owned by `rules/loops.md` §1.
- **iteration** — one fresh-context pass of a loop from the frozen goal
  plus worklog; two consecutive iterations without progress are a
  **stall**, which `rules/loops.md` exits `stalled`.
- **frontier** — the set of work items dispatchable now — every dependency
  `complete` — reported by `land` at each join and dispatched
  as it forms, never batched.
- **critical path** — the longest `depends_on` chain over a run's issued
  items, gate stubs excluded; what decomposition minimizes subject to
  every item an atom. Read with each level's width from
  `scripts/cutcheck.py`'s `graph` block (classes `critical-path`,
  `level-width`).
- **lane** — an isolated parallel candidate. Lanes may change the same path;
  actual overlap and Git conflicts are integration inputs, not cut defects.
- **terminal state** — a closed exit: a ticket status in
  `contracts/work-item.md`'s terminal set; a run's is its root (or loop)
  ticket's, per `contracts/worklog.md`.
- **worklog** — the run view `tickets.py worklog` renders from the ticket
  directory per `contracts/worklog.md`, never a second hand-written
  file; what makes fresh-context iteration and resumption possible.
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
