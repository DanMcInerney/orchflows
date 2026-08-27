---
id: 03-verify
executor: orch-verify
depends_on: [02-repair]
bound: <= 30 tool calls
independence: checker
isolation: none
---

## Goal

An independent verdict on whether the repaired {{workspace}} achieves the
fix Goal, with fresh evidence capable of exposing {{failure}} and any
material regression in the affected behavior.

## Context

- input: {"name":"workspace","type":"literal","value":"{{workspace}}"}
- input: {"name":"failure","type":"literal","value":"{{failure}}"}

Exceptional constraints:

- The verifier is read-only over the repaired artifact.
- Executor claims are evidence inputs, not the verdict.

## Result


## Verification


## Feedback

[]

## Risks

[]
