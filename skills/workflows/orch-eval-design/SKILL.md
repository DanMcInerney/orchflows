---
name: orch-eval-design
description: Design one frozen candidate-blind evaluation from fixed evidence. Use before benchmark construction or direct judged scoring.
role: planner
---

Require: one complete
[semantic assignment](../../../contracts/work-item.md#semantic-assignment)
whose Goal names the target identity and intended observable outcome;
whose Context carries fixed evidence, source identities, source policy,
applicable pack craft, lens, and oracle references, judgment permission,
and expected execution cost; and whose system-owned
[`bound`](../../../contracts/work-item.md#system-owned-metadata) caps design
effort.

Remain candidate-blind: inspect no candidate, variant, score, or winner
identity.

Fix the target boundary and observable outcome. Unsupported semantics or
an unavailable observable oracle become explicit gaps, never invented
domain truth. Record every bounded inference as a stated assumption.

Choose the smallest evaluation that maximizes valid discrimination and
intended coverage within the bound and expected execution cost. The
coverage floor is not tradable against that cost: where the target's
execution is cheap, every case sits in the smallest tier its outcome can
be observed in; where it is expensive, the ceiling rises and the cost is
declared. Buy difficulty from horizon length, outcome specificity, and a
stricter oracle that stays correct — never from a looser check, and
never from a candidate's scores.

Freeze the result at one package-owned identity before benchmark
construction or candidate scoring.

Never: gather research; materialize or execute cases; inspect or compare
candidates; generate or promote variants; revise the design from scores;
select, retain or remove a case by a candidate's success or failure;
prescribe a generation procedure where outcome semantics suffice.

Return: one frozen package-owned evaluation-design identity carrying
case specifications with execution tier and anchor (or `none` with a
reason); required criteria with oracle, `oracle_class` and required
status per
[contracts/verdict.md](../../../contracts/verdict.md) and judged
anchors; scoring and aggregation, the per-angle vector primary;
intended coverage; source identities and provenance; expected execution
cost; where a campaign will consume it, promotion rule, margin and
search policy (`none` or a
[search-policy/v1](../../../docs/search-plan-protocol.md) object); for
judged evaluation one candidate-blind Judge brief — target, outcome,
criteria, scale, anchors, exclusions, aggregation; stated assumptions;
explicit gaps; changed artifacts.
