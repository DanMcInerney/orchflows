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
  iteration dispatches is its **loop body** (`rules/loops.md`), named in
  plain text by the caller and never a call edge.
- **kernel** — the primitive skills under `skills/kernel/`; a kernel
  skill calls no skill.
- **engine** — a control-flow skill: declarative shape,
  validator-linted bounds, no domain judgment.
- **workflow** — an assembled skill calling engines, primitives, or
  other workflows; always domain-blind. A T3 composition is a **named
  workflow**.
- **instance** — a concrete domain executor or lens: the one binding a
  pack cell names for a capability. A composition instantiated into a
  run is a **composition instance**.
- **utility** — a leaf generic skill; with the evaluators, exempt from
  the envelope per `rules/composition.md`.
- **evaluator** — `orch-critique` or `orch-verify`: a skill rendering
  findings or verdicts over a fixed artifact and never a deliverable;
  exempt from the envelope per `rules/composition.md`.
- **pack** — a T2 package of pure data satisfying the pack signature; a pack
  binds cells and never contains control flow.
- **cell** — one field of the pack signature (slicing, executor, assembly,
  lens, oracle policy, workspace, required spec fields, craft).
- **signature** — `contracts/pack-signature.md`: the cells every pack must
  provide and the sharing constraints between them.
- **composition** — a T3 named workflow: a template (below) under
  `compositions/` (canonical) or `<repo>/.orchflows/compositions/`
  (custom); entry `routed | named`; admitted through `orch-build`.
- **combinator** — one of the three ways a template composes its stubs:
  a `depends_on` edge, disjoint parallel stubs (no dependency path
  between them, so the frontier may run them together), and a loop stub
  (`executor: orch-loop`). There is no fourth, and none of them is a
  field: each is a shape the ticket graph already carries.
- **dispatchable unit / envelope** — a skill or composition another may
  bind as a step or loop body, and the leading `Return` fields it must
  carry — status, result identity, verification — per
  `contracts/result.md`.
- **build scope** — where a built item lands and which oracles gate it:
  canonical (the library repository), user, or project. User- and
  project-scope items are custom — outside library law, binding only at
  their scope; bounds per `orch-build`'s scopes reference.
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
  tickets' objectives and completion tests are its frozen statement,
  the ticket files the whole record — no worklog.
- **unit** — one work item's execution by one context; the scope
  `rules/verification.md` §10 binds.
- **spec** — a run's frozen statement, carried by its root ticket per
  `contracts/work-item.md`; input to decomposition; `orch-spec` is its
  only editor, at intake — every other reader, `orch-decompose`
  included while cutting, treats it as frozen.
- **exemplar** — an artifact a root ticket's `## Fixed inputs` names to
  imitate, by pointer plus each property the imitation must carry
  (`contracts/work-item.md`); always non-normative.
- **stamp** — the pack fixed at intake, carried by a ticket's `pack`
  field, which engines thereafter read blind.
- **domain** — the deliverable's kind (code, content, research,
  design); selects exactly one pack per run.
- **work item / ticket** — a delegation packet made durable: packet parts
  ⊕ completion test ⊕ lifecycle ⊕ graph position, per
  `contracts/work-item.md`; on disk, a markdown ticket the executor writes
  to. The two words name the same thing; ticket is the on-disk view.
- **atom** — a work item at the finest lawful cut: one observable end
  state, a completion test discriminating it alone, a closed write
  scope, oracles reading nothing a sibling writes, an instruction
  inside the stub ceiling. Law, and what lies either side of it, in
  `rules/topology.md` §3.
- **root ticket** — a ticket whose executor is `orch-decompose`; its
  subtree is `<id>.NN` unit tickets plus `<id>.gate.*`, checked before
  its first unit is promoted; it completes when
  `<id>.gate.verify` completes. A successor root lives in a successor run
  opened after this root's result identity resolves and cites that identity
  among its own fixed inputs.
- **template** — a directory of ticket stubs plus its `template.md`
  manifest, instantiated into a run's ticket directory by `tickets.py
  instantiate` and run by `orch-frontier`; the one form a composition
  takes. Shape per `contracts/work-item.md`.
- **stub** — a template's unit: a ticket missing only `run`, `status`,
  `claimed_*` and any `{{placeholder}}`.
- **terminal ticket** — the stub no other stub depends on; its
  completion test is the template's done check.
- **ad-hoc ticket** — a work item the orchestrator cuts directly from a
  one-off request: a delegation packet persisted with a completion test,
  not a separate species — same contract shape, run id
  `<utc-stamp>-adhoc-<slug>`, `ready` at issue.
- **ad-hoc set** — ad-hoc tickets cut together with dependency edges,
  sharing one run id and ticket directory; the caller names the run
  bound; the ticket files are the whole record — no worklog.
- **tracker** — the state sink's `tickets/` directory; there is no external
  tracker.
- **executor** — the named skill a work item's frontmatter binds to do the
  work.
- **assembly item** — the at-most-one terminal work item that rewrites its
  inputs into the final artifact (edit, synthesize); its completion test
  carries the final gate.
- **decision gap** — a decomposition return naming the acceptance
  criteria the stamped slicing cannot cover.
- **workspace** — where results live and what identities mean there (git
  revisions, doc slots, evidence store), per the pack's workspace cell.
- **standards owner** — the workspace's own canonical statement of its
  conventions (linter config, style doc, CI); named by pointer, never
  restated.
- **baseline** — the proven clean starting state of a workspace.

## Verification

- **criterion** — one enumerated acceptance check, singly decidable by a
  named oracle.
- **oracle** — the exact external check that decides a criterion; never the
  executor's own claim.
- **oracle class** — deterministic, judged, or evidence, per
  `contracts/verdict.md`; fixes the loop and gate policy for a criterion.
- **oracle provenance** — whether a criterion's oracle pre-exists the
  unit's work or is created by the executing context; values owned by
  `contracts/work-item.md`, independence law by `rules/verification.md`
  §10.
- **independence** — acceptance evidence originating outside the
  executing context through exactly one ordinary path; sources and law in
  `rules/verification.md` §10.
  Research craft narrows the term for sources: no shared upstream.
- **checker** — the fresh reviewer-corrector context (`orch-critique`
  dispatched with the ticket's write scope as its packet `authority`)
  through which independence enters a unit whose checks were authored
  in-unit; corrects but never renders verdicts; law in
  `rules/verification.md` §10.
- **verdict** — PASS, FAIL, or UNVERIFIED for one criterion, with oracle,
  class, evidence, and covered identities.
- **evidence** — what an oracle actually produced, cited by identity; the
  only currency verification accepts.
- **provenance** — the recorded chain from an artifact or claim to its
  source, by identity.
- **disagreement register** — where disagreement is recorded with both
  sides' evidence, never averaged away.
- **lens** — the criteria set a reviewer applies; every additional root-gate
  reviewer has a unique named lens; freshness law `rules/verification.md`
  §6.
- **gate** — the one composite critique-fix-verify path a run crosses: one
  or more uniquely named critiques feed one repair and one verification;
  `orch-build`'s admission and a benchmark's
  qualification are not gates.
- **judge** — scoring one fixed candidate against frozen criteria, blind to
  other candidates: `orch-verify` where the criteria carry a score scale,
  blindness being a property of the packet's `inputs`, not of a skill.

The benchmark pipeline's artifacts are named here and defined by their
producers, never restated: **evaluation design** (`orch-eval-design`'s
Return), **benchmark** and its manifest field set
(`compositions/references/benchmaker-manifest.md`), **score card**
(`orch-verify`'s Return where the criteria carry a scale), **evolution
result**, **evaluation mode** and **incumbent** (the `evolve`
composition).

## Delegation

- **dispatch / delegation packet** — sending one packet to one fresh
  child, and the packet itself: a ticket's own dispatch fields —
  objective, inputs, authority, bounds, return contract, reply_to, per
  `contracts/work-item.md`, plus an optional one-shot `profile`
  overriding role resolution for that dispatch alone. A packet-only
  dispatch is a ticket the dispatcher does not persist.
- **authority** — the write scope plus named excluded actions a dispatch
  grants; per `contracts/work-item.md`.
- **write scope** — the capability naming exactly what a child may change,
  expressed in the pack's workspace semantics.
- **join** — the single point where a caller integrates one child
  result, always `orch-integrate`. `rules/delegation.md` owns what
  happens there and names its own terms: the closed **disposition** set
  (§9, and `orch-triage` for its own), and the two **blame** classes —
  caller under-supplied, child under-delivered.
- **ladder / rung** — the ordered execution vehicles for one dispatch:
  tested script, inline, worker, planner; per `rules/delegation.md` §2.
- **role** — planner (judgment) or worker (execution); law in
  `rules/roles.md`.
- **profile** — a role's concrete model and effort binding on one host,
  owned by `skills/engines/orch-frontier/references/profiles.md`; a
  packet's optional `profile` slot names one explicitly, overriding role
  resolution for that dispatch.
- **host** — the runtime carrying the agents: Claude Code or Codex.

## Iteration

- **context packet** — the converged state an iteration receives beside
  the frozen goal and worklog; design owned by `orch-loop`'s packet
  reference.
- **done-check / bound** — the external oracle that alone decides a
  loop is complete (any oracle class per `contracts/verdict.md`; an
  iteration count is a deterministic one), and the resource cap —
  iterations, tool calls, tokens, time — whose exhaustion exits
  `limited`; success-condition law owned by `rules/loops.md` §1.
- **iteration** — one fresh-context pass of a loop from the frozen goal
  plus worklog; two consecutive iterations without progress are a
  **stall**, which `rules/loops.md` exits `stalled`.
- **frontier** — the set of work items dispatchable now — every dependency
  `complete` — recomputed by `orch-frontier` on every event and dispatched
  as it forms, never batched.
- **critical path** — the longest `depends_on` chain over a run's issued
  items, gate stubs excluded; what decomposition minimizes subject to
  every item an atom. Read with each level's width from
  `scripts/cutcheck.py`'s `graph` block (classes `critical-path`,
  `level-width`).
- **lane** — any independent parallel branch whose write scope and
  whose workspace are both disjoint from every other's (sharing =
  writing the same artifact or slot, not returning same-named fields).
  Two lanes in one workspace are one lane with two authors: neither
  one's oracle output is attributable to its own change. Distinct from
  independence, a property of acceptance evidence.
- **terminal state** — a closed exit: a ticket status in
  `contracts/work-item.md`'s terminal set; a run's is its root (or loop)
  ticket's, per `contracts/worklog.md`.
- **worklog** — the run view `tickets.py worklog` renders from the ticket
  directory per `contracts/worklog.md`, never a second hand-written
  file; what makes fresh-context iteration and resumption possible.
- **handoff** — the suspension, resumption, or escalation record: a
  ticket's `## Handoff` section, per `contracts/work-item.md`; a
  packet-only dispatch has none, and stops instead.

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
