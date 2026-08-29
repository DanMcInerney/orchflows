---
id: 00-audit
executor: orch-critique
depends_on: []
bound: {{audit_bound}}
independence: checker
isolation: none
profile: orch-planner
---

## Goal

An independent blocker report over {{workspace}} under {{priorities}}.

## Context

- input: {"name":"workspace","type":"literal","value":"{{workspace}}"}
- input: {"name":"priorities","type":"literal","value":"{{priorities}}"}
- input: {"name":"audit-bound","type":"literal","value":"{{audit_bound}}"}

- Apply the pack's check craft and report every evidence-backed blocker.

## Result


## Verification


## Feedback

[]

## Risks

[]
