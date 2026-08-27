---
id: 01-cause
executor: orch-loop
depends_on: [00-reproduce]
bound: <= 8 iterations
independence: checker
isolation: none
profile: orch-worker
---

## Goal

One proven cause of {{failure}}: the single change that, toggled,
toggles the reproduction between FAIL and PASS.

## Context

- input: {"name":"workspace","type":"literal","value":"{{workspace}}"}
- input: {"name":"failure","type":"literal","value":"{{failure}}"}

Exceptional constraints:

- repairing the cause once it is proven
- changing any artifact in {{workspace}} (the toggle is shown in a throwaway clone beside it)

## Result


## Verification


## Feedback

[]

## Risks

[]
