---
name: orch-eval-design
description: Design one frozen candidate-blind evaluation from fixed evidence. Use when benchmark semantics must be defined before construction.
role: none
---

Require: one complete
[delegation packet](../../../contracts/delegation.md). Its `objective`
carries the target identity and intended observable outcome;
`inputs` carry fixed evidence, source identities, source policy, and
applicable pack craft, lens, and oracle references plus judgment
permission; `authority` restricts artifact write scope and exclusions;
`bounds` cap design effort and expected execution cost; `return_contract`
names the evaluation-design identity, assumptions, gaps, and changed
artifacts; `reply_to` names the closing recipient.

Remain candidate-comparison-blind: inspect no candidate, variant, score,
or winner identity. Work only from `inputs`.

Fix the target boundary and observable outcome. Unsupported semantics or
an unavailable observable oracle become explicit gaps, never invented
domain truth. Record every bounded inference as a stated assumption.

Choose the smallest evaluation that maximizes valid discrimination and
intended coverage within the bound and expected execution cost. Record
case specifications; required criteria with named oracles, `oracle_class`,
required status, and judged anchors per
[contracts/verdict.md](../../../contracts/verdict.md); scoring and
aggregation; intended coverage; source identities and provenance; and
expected execution cost. Freeze the result at one package-owned
evaluation-design identity before benchmark construction or candidate
scoring.

Never: gather research; materialize or execute cases; inspect or compare
candidates; generate or promote variants; revise the design from scores;
prescribe a generation procedure where outcome semantics suffice.

Return: one frozen package-owned evaluation-design identity, stated
assumptions, explicit gaps, and changed artifacts; the closing result
addresses `reply_to`.
