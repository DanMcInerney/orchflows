---
name: evolve
description: Evolve one target through bounded candidate generations against one frozen qualified benchmark. Manual-only campaign.
entry: named
---

Require: one complete [delegation packet](../contracts/delegation.md)
whose `inputs` carry one frozen evolve spec governed by the
[spec contract](../contracts/spec.md). The spec's `evidence`
identifies the incumbent identity, its fixed benchmark
result/evidence, covered eligibility verdict and Judge-owned score
card, plus one qualified benchmark identity and covered-PASS
qualification verdict. `affected_surfaces` names candidate-mutable
target surfaces; packet `authority` names write scope and exclusions.
Mutation authority is their intersection. Spec `acceptance` fixes
generation width, lane count per candidate, promotion done-check and
rule, required margin, and regression criteria; spec `bound` and
packet `bounds` cap the campaign.

Steps:
- eligibility — `orch-verify`: the incumbent's fixed result/evidence
  identity and frozen required eligibility and regression criteria,
  with named oracles and `oracle_class`. Only covered PASS permits the
  Judge-owned incumbent score card to supply generation direction;
  expose no protected item-level evidence.
- generation — the loop body, a caller-owned composite: independent
  variants through `orch-delegate` within mutation authority; every
  child return crosses `orch-integrate` with caller write scope; the
  frozen runner produces one fixed result/evidence identity per
  integrated candidate, submitted with the same frozen criteria to
  `orch-verify`; verified survivors, including the incumbent, go as a
  fixed set — each candidate bound to its covered-PASS result/evidence
  identity and frozen benchmark/scoring identities — with frozen
  criteria, predeclared aggregation, and lane count to `orch-panel`.
  Promote only a survivor whose score card cites the admitted evidence
  and satisfies the frozen rule and margin; promotion alone never
  completes.
- closing — a fresh `orch-judge` over the final incumbent, its
  admitted result/evidence identity, and frozen scoring criteria.

Edges:
- seq eligibility → campaign → closing.
- loop campaign — body `generation`, the promotion done-check, the
  frozen bound, dispatched through `orch-loop` with the frozen goal
  and a context packet carrying campaign constants, incumbent identity
  and score card, promotion/kill log, disagreement, and failed
  approaches.

Invariants:
- Freeze the benchmark identity, runner, scoring, protected evidence
  policy, mutation authority, promotion rule, required margin, and
  bound.
- A changed benchmark starts a new campaign in which every retained
  candidate is evaluated again.
- Kill any candidate lacking PASS on every required deterministic
  criterion; deterministic failure blocks eligibility and judged score
  cannot compensate.
- Judge lanes are blind per `orch-panel`; they cite the admitted
  evidence without re-execution or substitution.
- A judged done-check PASS is provisional; only a closing score card
  citing the final incumbent's admitted evidence can satisfy the
  done-check.
- An ambiguous or non-discriminating benchmark returns a blocked
  partial result, evidence, and feedback for a separate BenchMaker
  run. Terminal states and partial-result law follow
  [rules/loops.md](../rules/loops.md).
- Never: change campaign constants; rank an ineligible candidate;
  re-execute or substitute admitted evidence for judging; expose
  protected evidence; call evaluation design or BenchMaker; treat a
  changed benchmark as continuity.

Done check: the closing `orch-judge` score card, citing the final
incumbent's admitted result/evidence identity, satisfies the frozen
promotion done-check.

Return: status, result — the final incumbent identity, verification —
the closing score card and eligibility verdicts; then frozen benchmark
identity, generation count, promotion/kill log, disagreement, partial
evidence, feedback and gaps, and bounds spent.
