---
id: 03-verify
executor: orch-verify
depends_on: [02-repair]
bound: <= 30 tool calls
independence: checker
isolation: none
---

## Goal

Verdicts over the repaired {{workspace}}: every oracle the failure was
already gated by, plus the regression guard that keeps {{failure}} from
returning unobserved.

## Context

- input: {"name":"workspace","type":"literal","value":"{{workspace}}"}
- input: {"name":"failure","type":"literal","value":"{{failure}}"}

Exceptional constraints:

- skip the regression guard because the fix looks obvious
- accept a guard that passes at the pre-repair revision

## Result


## Verification


## Feedback

[]

## Risks

[]
