---
id: 00-audit
executor: orch-critique
depends_on: []
write_scope: []
bound: {{audit_bound}}
excluded_actions:
  - repair a finding instead of returning it
independence: checker
isolation: none
profile: orch-worker
---

## Objective

Ranked findings over {{workspace}}, each naming the evidence it stands
on, under {{priorities}} as the lens.

## Fixed inputs

- input: {"name":"workspace","type":"literal","value":"{{workspace}}"}
- input: {"name":"priorities","type":"literal","value":"{{priorities}}"}
- input: {"name":"audit-bound","type":"literal","value":"{{audit_bound}}"}

## Completion test

- every finding cites evidence in {{workspace}} by identity | oracle: the finding set read against the tree | oracle_class: deterministic | provenance: pre-existing
- the findings are ranked and none is a repair | oracle: the finding set against {{priorities}} | oracle_class: judged | provenance: authored-here

## Return fields

status; result — everything orch-critique's Return names: the ranked
findings with the evidence each cites, by identity, and the revision
audited; verification; feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
