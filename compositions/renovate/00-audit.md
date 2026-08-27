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

An `orch-critique` report over {{workspace}} under {{priorities}}.

## Context

- input: {"name":"workspace","type":"literal","value":"{{workspace}}"}
- input: {"name":"priorities","type":"literal","value":"{{priorities}}"}
- input: {"name":"audit-bound","type":"literal","value":"{{audit_bound}}"}

- Apply the evaluator contract in `skills/kernel/orch-critique/SKILL.md`.

## Result


## Verification


## Feedback

[]

## Risks

[]
