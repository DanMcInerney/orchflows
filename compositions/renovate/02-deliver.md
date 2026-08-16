---
id: 02-deliver
executor: orch-decompose
pack: {{pack}}
depends_on: [01-triage]
write_scope: [{{workspace}}]
bound: {{brief_bound}} per ready-for-agent brief
excluded_actions:
  - deliver a brief 01-triage did not disposition ready-for-agent
  - answer a ready-for-human brief on the maintainer's behalf
independence: gate
isolation: required
profile: orch-worker
---

## Objective

Every ready-for-agent brief delivered into {{workspace}} with its own
final verification, and every ready-for-human brief returned to the
maintainer unanswered. One root ticket over every brief, not one per
brief: this cut yields a unit per brief, so the gate runs once over the
whole delivery.

## Fixed inputs

- 01-triage's `## Result` — the dispositions and compacted briefs by
  identity.
- {{pack}} — this run's stamp, which every cut unit takes.
- {{workspace}} — the target repository: the tree the delivered changes
  land in.
- The standards owner, by pointer: the workspace's own owner file —
  AGENTS.md or its equivalent.
- Acceptance as runnable checks: the workspace's required checks as
  that owner names them.
- {{brief_bound}} — each brief's budget, fixed before that brief starts.

## Completion test

- every disposition landed — each agent brief delivered with its final verification, each human brief returned | oracle: the disposition set from 01-triage's Result against the delivered result identities | oracle_class: judged | provenance: pre-existing
- every changed path lies inside {{workspace}} | oracle: the workspace diff against the recorded baseline | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the delivered change identities per brief;
verification — each brief's final verdicts; feedback — the dispositions
returned to the maintainer; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
