---
name: evolve
description: Evolve one target through bounded candidate generations against one frozen evaluation. Manual-only campaign.
entry: named
---

Require: one complete [delegation packet](../contracts/work-item.md#dispatch)
whose `inputs` carry one frozen evolve spec governed by the
[root-ticket contract](../contracts/work-item.md#root-ticket). Its `evidence` identifies the incumbent
identity and fixed result/evidence identity for the artifact; a supplied frozen evaluation adds
the frozen evaluation identity, mode, scoring contract, and covered incumbent
verdict and score card.
`affected_surfaces` and packet `authority` name candidate scope; their
intersection is mutation authority. `acceptance` freezes evaluation setup,
search policy, candidate-accessible dimensions and feedback, writer, lane count per candidate,
promotion done-check and rule, required margin, and regression criteria;
`bound` and packet `bounds` cap the campaign.
When no evaluation is supplied, the packet also carries the inputs, disjoint
evaluation-design write scope, and reserved bound mapped by the
[evaluation-open protocol](references/evolve-evaluation.md).

Steps:
- evaluation — use the supplied frozen evaluation. When no frozen evaluation is
  supplied, `orch-eval-design` creates one candidate-blind Judge brief under the
  evaluation-open protocol before generation; this is judged mode. A qualified
  benchmark plus runner is benchmark mode.
- eligibility — `orch-verify` checks fixed incumbent evidence against the
  evaluation's required admission and regression criteria. Only covered PASS
  permits generation direction; expose no protected item-level evidence.
- campaign — `orch-loop` over the body mapped by the
  [generation protocol](references/evolve-generation.md). It uses one frozen
  `orch-panel` binding before the first plan and after each candidate set, then
  calls `orch-search-plan` and `orch-integrate` around the frozen writer and
  evaluation, dispatched per rules/delegation.md, its run state rendered by
  `tickets.py worklog`, reusing the eligibility Verify binding.

Edges: seq evaluation → eligibility → campaign; loop campaign — generation body,
frozen bound, and a fresh `orch-verify` done-check — blind: inputs carry only
this candidate — over the final incumbent and its admitted result/evidence.

Invariants:
- Freeze the evaluation identity, evaluation mode, scoring, criteria, evidence
  adapter, optional runner, protected evidence policy, controller and planner
  revisions, mutation authority, search policy, promotion rule, margin, and
  bound. A changed constant starts a new campaign and reevaluates every retained
  candidate; benchmark mode also freezes its benchmark revision.
- Benchmark mode runs the qualified runner. Judged mode scores each fixed
  artifact snapshot through the same candidate-blind Judge brief and Panel.
- Kill any candidate lacking PASS on every required admission criterion; judged
  score cannot compensate. Every Panel score card cites admitted evidence.
- The archive supplies exploration parents only; Evolve alone applies the
  promotion rule and margin. Promotion alone never completes.
- A missing public numeric mapping returns a blocked partial result with an
  evaluation-design gap.
- Never: change evaluation after campaign open; rank an ineligible candidate;
  re-execute or substitute admitted evidence; expose protected evidence; call
  Benchmaker; activate a selected candidate; add a closing wrapper.

Done check: Loop's final score card cites the final incumbent identity and its
admitted result/evidence and satisfies the frozen promotion done-check.

Return: status, result — the final incumbent identity, verification — the final
score card and admission verdicts; then frozen evaluation identity and mode,
benchmark revision when used, accepted projection and plan identities,
generation count, promotion/kill log, disagreement, partial evidence, feedback
and gaps, bounds spent, and cumulative changed artifacts including Worklog and
accepted descendant changes.
