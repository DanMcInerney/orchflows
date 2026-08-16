---
id: 00-audit
executor: orch-critique
depends_on: []
write_scope: []
bound: {{audit_bound}}
excluded_actions:
  - start the audit or a brief without its bound already fixed
  - repair a finding instead of returning it
independence: checker
isolation: none
profile: orch-worker
---

## Objective

Ranked findings over {{workspace}}, each naming the evidence it stands
on, under {{priorities}} as the lens.

## Fixed inputs

- {{workspace}} — the tree to audit, at its current revision.
- {{priorities}} — the maintainer's stated priorities, verbatim, as the
  critique lens.
- {{audit_bound}} — this audit's budget, fixed before it starts.

## Completion test

- every finding cites evidence in {{workspace}} by identity | oracle: the finding set read against the tree | oracle_class: deterministic | provenance: pre-existing
- the findings are ranked and none is a repair | oracle: the finding set against {{priorities}} | oracle_class: judged | provenance: authored-here

## Return fields

status; result — the ranked findings with cited evidence and the
revision audited; verification; feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
