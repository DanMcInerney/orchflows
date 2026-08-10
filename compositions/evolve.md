---
name: evolve
description: Evolve one target through bounded candidate generations against one frozen qualified benchmark. Manual-only campaign.
entry: named
---

Require: one complete [delegation packet](../contracts/delegation.md)
whose `inputs` carry one frozen evolve spec governed by the
[spec contract](../contracts/spec.md). Its `evidence` identifies the
incumbent identity, fixed result/evidence, covered eligibility verdict,
Judge-owned incumbent score card, and qualified benchmark revision and
scoring identity. `affected_surfaces` and packet `authority` name candidate
scope; their intersection is mutation authority. `acceptance` freezes optimizer activation, search policy,
candidate-accessible dimension and feedback mappings, runner, writer, lane
count per candidate, promotion done-check and rule, required margin, and
regression criteria; `bound` and packet `bounds` cap the campaign.

Steps:
- eligibility — `orch-verify` the incumbent's fixed evidence against required
  eligibility and regression criteria. Only covered PASS permits generation
  direction from its score card; expose no protected item-level evidence.
- campaign — `orch-loop` over the generation body mapped by the
  [generation protocol](references/evolve-generation.md), which calls
  `orch-search-plan`, `orch-worklog`, `orch-delegate`, `orch-integrate`,
  `orch-verify`, and `orch-panel` around the frozen writer and runner.

Edges:
- seq eligibility → campaign.
- loop campaign — generation body, frozen bound, and a fresh `orch-judge`
  done-check over the final incumbent and its admitted result/evidence.

Invariants:
- Freeze the benchmark revision, runner, scoring, protected evidence policy,
  active controller and planner revisions, mutation authority, search policy,
  promotion rule, required margin, and bound. A changed constant starts a new
  campaign and projection in which every retained candidate is evaluated again.
- Kill any candidate lacking PASS on every required deterministic criterion;
  judged score cannot compensate. Verified survivors each carry a covered-PASS
  result/evidence identity, and every Panel score card cites the admitted evidence.
- The archive supplies exploration parents only; Evolve alone applies the
  promotion rule and margin. Promotion alone never completes.
- A missing candidate-accessible numeric mapping returns a blocked partial
  result with a Benchmaker gap for a separate Benchmaker run.
- Never: change campaign constants; rank an ineligible candidate; re-execute or
  substitute admitted evidence; expose protected evidence; call evaluation
  design or Benchmaker; activate a selected candidate; add a closing wrapper.

Done check: Loop's final score card cites the final incumbent identity and its
admitted result/evidence and satisfies the frozen promotion done-check.

Return: status, result — the final incumbent identity, verification — the final
score card and eligibility verdicts; then frozen benchmark revision, accepted
projection and plan identities, generation count, promotion/kill log,
disagreement, partial evidence, feedback and gaps, bounds spent, and cumulative
changed artifacts including Worklog and accepted descendant changes.
