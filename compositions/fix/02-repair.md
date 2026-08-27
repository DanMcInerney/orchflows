---
id: 02-repair
executor: orch-repair
depends_on: [01-cause]
bound: <= 60 tool calls
independence: checker
isolation: required
profile: orch-worker
---

## Goal

The smallest coherent change to {{workspace}} that removes the proven
cause of {{failure}}, leaving the reproduction PASSing, plus one new
regression check that FAILs on the old behaviour and PASSes on the new.

## Context

- input: {"name":"none","type":"literal","value":null}
- input: {"name":"workspace","type":"literal","value":"{{workspace}}"}
- input: {"name":"failure","type":"literal","value":"{{failure}}"}

## Suggested files

- {{workspace}}

Exceptional constraints:

- repair an unproven cause
- widen into adjacent cleanup

## Result


## Verification


## Feedback

[]

## Risks

[]
