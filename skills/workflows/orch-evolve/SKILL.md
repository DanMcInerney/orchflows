---
name: orch-evolve
description: Evolve one target through bounded candidate generations against one frozen qualified benchmark. Manual-only campaign.
disable-model-invocation: true
role: none
---

Require: one complete [delegation packet](../../../contracts/delegation.md)
whose `inputs` carry one frozen evolve spec governed by the [spec contract](../../../contracts/spec.md).
The spec's `evidence` identifies the incumbent identity, its fixed benchmark result/evidence, covered eligibility verdict and Judge-owned score card, plus one qualified benchmark identity and covered-PASS qualification verdict.
`affected_surfaces` names candidate-mutable target surfaces; packet `authority` names write scope and exclusions. Mutation authority is their intersection.
Spec `acceptance` fixes generation width, lane count per candidate, promotion done-check and rule, required margin, and regression criteria; spec `bound` and packet `bounds` cap the campaign.

Freeze the benchmark identity, runner, scoring, protected evidence policy, mutation authority, promotion rule, required margin, and bound.
A changed benchmark starts a new campaign in which every retained candidate is evaluated again.

Submit the incumbent's fixed result/evidence identity and frozen required eligibility and regression criteria, with named oracles and `oracle_class`, to `orch-verify`.
Only covered PASS permits the Judge-owned incumbent score card to supply generation direction; expose no protected item-level evidence.

Run `orch-loop` with the frozen goal, one generation as caller-owned composite body, the done-check, bound, and a context packet carrying campaign constants, incumbent identity and score card, promotion/kill log, disagreement, and failed approaches.

Each generation dispatches independent variants through `orch-delegate` within mutation authority; every child return crosses `orch-integrate` with caller write scope.
Run the frozen runner against each integrated candidate to produce one fixed result/evidence identity, then submit it and the same frozen criteria to `orch-verify`.
Kill any candidate lacking PASS on every required deterministic criterion; deterministic failure blocks eligibility and judged score cannot compensate.

Send only verified survivors, including the incumbent, as a fixed set binding each candidate to its covered-PASS result/evidence identity and frozen benchmark/scoring identities.
Submit that set, frozen criteria, predeclared aggregation, and lane count to `orch-panel`.
Promote only a survivor whose score card cites the admitted evidence and satisfies the frozen rule and margin; promotion alone never completes.

A judged done-check PASS is provisional. Submit the final incumbent, its admitted result/evidence identity, and frozen scoring criteria to a fresh `orch-judge`.
Only a closing score card citing that evidence can satisfy the done-check.

An ambiguous or non-discriminating benchmark returns a blocked partial result, evidence, and feedback for a separate BenchMaker run.
Terminal states and partial-result law follow [rules/loops.md](../../../rules/loops.md).

Never: change campaign constants; rank an ineligible candidate; re-execute or substitute admitted evidence for judging; expose protected evidence; call evaluation design or BenchMaker; treat a changed benchmark as continuity.

Return: status, final incumbent identity and closing score card, frozen benchmark identity, generation count, promotion/kill log, disagreement, partial evidence, feedback and gaps, and bounds spent.
