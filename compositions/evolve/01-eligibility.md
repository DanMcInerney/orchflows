---
id: 01-eligibility
executor: orch-check
pack: orch-code-pack
depends_on: [00-eval]
bound: <= 30 tool calls
independence: checker
isolation: required
---

## Goal

Verdicts over {{incumbent}}'s fixed evidence against the frozen
evaluation's required admission and regression criteria: covered PASS is
what permits generation to open, and nothing else does.

## Context

- input: {"name":"incumbent","type":"literal","value":"{{incumbent}}"}
- input: {"name":"target","type":"literal","value":"{{target}}"}

Exceptional constraints:

- expose protected evidence
- rank an ineligible candidate
- generating or scoring a candidate — this stub grades the incumbent

## Result


## Verification


## Feedback

[]

## Risks

[]
