---
id: 00-audit
executor: orch-critique
depends_on: []
bound: {{audit_bound}}
independence: checker
isolation: none
profile: orch-worker
---

## Goal

Ranked findings over {{workspace}}, each naming the evidence it stands
on, under {{priorities}} as the lens.

## Context

- input: {"name":"workspace","type":"literal","value":"{{workspace}}"}
- input: {"name":"priorities","type":"literal","value":"{{priorities}}"}
- input: {"name":"audit-bound","type":"literal","value":"{{audit_bound}}"}

Exceptional constraints:

- repair a finding instead of returning it

## Result


## Verification


## Feedback

[]

## Risks

[]
