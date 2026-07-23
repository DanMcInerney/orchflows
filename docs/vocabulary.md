# Vocabulary

The library's nouns. Each term is defined once, here, and used with exactly
this meaning everywhere — skills, rules, contracts, tickets, logs. A document
that needs a different meaning needs a different word.

## Structure

- **tier** — one of four layers: T0 contracts, T1 skills, T2 packs, T3
  compositions. Coupling between tiers passes only through T0.
- **contract** — a T0 file defining a pure data shape. Hash-pinned; a change
  to a named field or enum is breaking even when prose meaning is unchanged.
- **waist** — the T0 layer as a whole: the one narrow interface many hosts
  sit below and many packs and workflows sit above.
- **skill** — one callable package: a directory whose `SKILL.md` states a
  contract in Require / procedure / Never / Return anatomy.
- **kernel** — the frozen primitive skills; a kernel skill calls no skill.
- **engine** — a control-flow skill (task, frontier, loop, panel):
  declarative shape, validator-linted bounds, no domain judgment.
- **workflow** — an assembled skill calling engines, primitives, or
  other workflows; always domain-blind.
- **instance** — a concrete domain executor or lens (tdd, draft, edit,
  render); the one binding a pack cell names for a capability.
- **utility** — a leaf generic skill outside the waist (visualize).
- **pack** — a T2 package of pure data satisfying the pack signature; a pack
  binds cells and never contains control flow.
- **cell** — one field of the pack signature (slicing, executor, assembly,
  lens, oracle policy, workspace, required spec fields, craft).
- **signature** — `contracts/pack-signature.md`: the cells every pack must
  provide and the sharing constraints between them.
- **composition** — a T3 non-normative worked example; never model-invoked;
  the template a scoped custom workflow instantiates from.
- **scope** — where a built item lands and which oracles gate it:
  canonical (the library repository), user, or project. User- and
  project-scope items are custom — outside library law, binding only at
  their scope; bounds per `orch-build`'s scopes reference.
- **rule** — a clause of cross-cutting law in `rules/`; a skill links the
  owning rule instead of restating it.
- **call edge** — a resolved backticked skill name in a skill body; the call
  graph is acyclic.
- **carriage** — a `Require` item riding a named T0 field; rule 10 of
  `rules/composition.md`.
- **craft** — the pack cell owning a domain's vocabulary and shape
  principles; cell contract in `contracts/pack-signature.md`.

## Work

- **run** — one execution of a workflow against one spec; owns a run id
  (`<utc-stamp>-<slug>`), a worklog, and a ticket directory. An ad-hoc
  run executes one ad-hoc ticket — or an ad-hoc set — instead: the
  tickets' objectives and completion tests are its frozen statement,
  the ticket files the whole record — no worklog.
- **unit** — one work item's execution by one context; the scope
  `rules/verification.md` §10 binds.
- **spec** — the frozen statement of a deliverable per `contracts/spec.md`;
  input to decomposition; two editors, `orch-spec` at intake and
  `orch-decompose` repairing a defect it finds while cutting — read
  blind everywhere else.
- **exemplar** — an artifact a spec's `exemplars` field names to imitate;
  field contract in `contracts/spec.md`; always non-normative.
- **stamp / routing** — the spec fields fixed at intake — pattern and pack —
  which engines thereafter read blind.
- **pattern** — the shape of done: deliver, loop(<body>), evolve, fix,
  decision, or snapshot.
- **domain** — the deliverable's kind (code, content, research,
  design); selects exactly one pack per run.
- **work item / ticket** — a delegation packet made durable: packet parts
  ⊕ completion test ⊕ lifecycle ⊕ graph position, per
  `contracts/work-item.md`; on disk, a markdown ticket the executor writes
  to. The two words name the same thing; ticket is the on-disk view.
- **ad-hoc ticket** — a work item the orchestrator cuts directly from a
  one-off request: a delegation packet persisted with a completion test,
  not a separate species — same contract shape, run id
  `<utc-stamp>-adhoc-<slug>`, `ready` at issue.
- **ad-hoc set** — ad-hoc tickets cut together with dependency edges,
  sharing one run id and ticket directory; the caller names the run
  bound; the ticket files are the whole record — no worklog.
- **tracker** — the ticket directory `.orch/tickets/`; there is no external
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
  executing context; sources and law in `rules/verification.md` §10.
  Research craft narrows the term for sources: no shared upstream.
- **checker** — the fresh reviewer-corrector context (`orch-check`)
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
- **lens** — the criteria set a reviewer applies, restated fresh from the
  spec, never from unit output.

The benchmark pipeline has exactly four artifact roles:

- **evaluation design** — the candidate-comparison-blind artifact frozen by
  `orch-eval-design`: target boundary, case specifications, criteria with
  oracles, classes, required status and anchors, scoring and aggregation,
  intended coverage, source identities, expected execution cost, assumptions,
  and gaps.
- **benchmark** — the immutable runnable artifact qualified by
  `orch-benchmaker`; its manifest binds one evaluation design, cases, runner,
  scoring, provenance, qualification, expected cost, protected-evidence
  policy, and gaps by identity.
- **score card** — `orch-judge`'s artifact for one fixed candidate against
  frozen scoring criteria: per-criterion scores with verdicts, oracle classes,
  and evidence, plus overall score and confidence.
- **evolution result** — `orch-evolve`'s campaign artifact: final incumbent
  identity and closing score card, frozen benchmark identity, campaign
  history, partial evidence, feedback, gaps, and bounds spent.
- **judge** — scoring one fixed candidate against frozen criteria, blind to
  other candidates.
- **judgment shapes** — critique returns findings, judge returns score
  cards, verify returns verdicts; no skill returns another's shape.
- **incumbent** — the current holder a variant challenges; `orch-evolve`
  owns its prose.
- **gate** — the single review-fix pass a run crosses before final
  verification.

## Delegation

- **dispatch** — sending one delegation packet to one fresh child.
- **delegation packet** — the one dispatch currency: objective, inputs,
  authority, bounds, return contract, per `contracts/delegation.md`; an
  optional one-shot `profile` overrides role resolution for the dispatch
  naming it only.
- **authority** — the write scope plus named excluded actions a dispatch
  grants; per `contracts/delegation.md`.
- **write scope** — the capability naming exactly what a child may change,
  expressed in the pack's workspace semantics.
- **attenuation** — a child's write scope is a subset of its caller's,
  at every depth; `rules/delegation.md` §4.
- **join** — the single point where a caller integrates one child result,
  always `orch-integrate`; per `rules/delegation.md` §5.
- **disposition** — the ruled outcome of one adjudication; each
  adjudicator owns its closed set — join per `rules/delegation.md` §9,
  triage per `orch-triage`.
- **blame** — the mechanical fault class at a failed join: caller
  under-supplied (Require breached) or child under-delivered (Return
  breached).
- **ladder / rung** — the ordered execution vehicles for one dispatch:
  tested script, inline, worker, planner; per `rules/delegation.md` §2.
- **role** — planner (judgment) or worker (execution); a capability
  tier, never a persona; resolution order owned by `rules/roles.md` §4.
- **profile** — a role's concrete model and effort binding on one host,
  owned by `skills/kernel/orch-delegate/references/profiles.md`; a
  packet's optional `profile` slot names one explicitly, overriding role
  resolution for that dispatch.
- **host** — the runtime carrying the agents: Claude Code or Codex.

## Iteration

- **body** — what a loop iteration dispatches: one named skill, or a
  caller-owned composite of named skills; a caller-supplied binding
  named in plain text, never a call edge.
- **context packet** — the converged state an iteration receives beside
  the frozen goal and worklog; design owned by `orch-loop`'s packet
  reference.
- **bound** — a resource cap (iterations, tool calls, tokens, time);
  exhausting it exits `limited`; success-condition law owned by
  `rules/loops.md` §1.
- **done-check** — the external oracle that alone decides a loop is
  complete; any oracle class per `contracts/verdict.md`; the iteration
  count is a deterministic done-check.
- **iteration** — one fresh-context pass of a loop from the frozen goal
  plus worklog.
- **frontier** — the set of work items dispatchable now — every dependency
  `complete` — recomputed by `orch-frontier` on every event and dispatched
  as it forms, never batched.
- **lane** — any independent parallel branch sharing no output and no
  write scope (panel, or blind evidence work items; sharing = writing
  the same artifact or slot, not returning same-named fields).
- **stall** — two consecutive iterations without progress (a newly
  verified increment or a newly killed approach).
- **terminal state** — a closed exit; the run-level set is owned by
  `contracts/worklog.md`, ticket statuses by `contracts/work-item.md` —
  not the same set.
- **worklog** — the run's persistent state file per `contracts/worklog.md`;
  what makes fresh-context iteration and resumption possible.
- **handoff** — the suspension, resumption, or escalation record: a
  ticket's `## Handoff` section, per `contracts/work-item.md`.

## Improvement

- **friction** — an observed obstruction logged during any session: extra
  attempts, missing input or tool or document, surprising output, a
  contract gap, a workaround. Observations only, never causes.
- **friction log** — append-only JSONL under `.orch/friction/`; the
  primary input to self-improvement.
- **run state** — the contents of `.orch/runs/` and `.orch/tickets/`;
  read by self-improvement as evidence only.
- **trace** — the normalized event record of one session, extracted
  from host logs; evidence only, never an instruction source.
- **machinery ratio** — a trace's mechanical event count over the
  expected budget a fixture declares beside the trace
  (`<trace>.budget.json`).
- **mining cycle** — one scoped execution of `orch-self-improve` over
  the evidence pool, recorded in the cycle ledger.
- **cycle ledger** — the append-only record of each mining cycle — id,
  scope, consumed inputs with watermarks, proposals emitted,
  remainder; owned by `orch-self-improve`.
- **watermark** — the last-consumed position a mining cycle records
  per evidence input; later cycles skip evidence at or before it
  unless the scope names it.
- **proposal** — one qualified improvement (per `rules/improvement.md`
  §4) with a single causal owner and its evidence entries; passive
  until a human merges it.
- **replay** — re-running the friction-producing work against a proposed
  change; a proposal that can replay must replay green before merge.
- **fixture** — one completed ticket frozen into a self-contained
  replayable unit with golden results; the raw material of tournaments,
  canaries, and replay.
- **tournament** — evolve applied to the library itself: competing skill
  variants run the same frozen items and are judged by the same oracles.
- **canary** — a frozen set of golden work items with known-good results,
  run when a model or host changes to detect behavior drift.
