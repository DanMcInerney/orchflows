---
id: 01-cause
executor: orch-loop
depends_on: [00-reproduce]
write_scope: []
bound: <= 8 iterations
excluded_actions:
  - repairing the cause once it is proven
  - changing any artifact in {{workspace}} (the toggle is shown in a throwaway clone beside it)
independence: checker
isolation: none
profile: orch-worker
---

## Objective

One proven cause of {{failure}}: the single change that, toggled,
toggles the reproduction between FAIL and PASS.

## Fixed inputs

- input: {"name":"workspace","type":"literal","value":"{{workspace}}"}
- input: {"name":"failure","type":"literal","value":"{{failure}}"}

## Completion test

- done-check: the candidate cause toggled toggles the failure — the reproduction FAILs with it present and PASSes with it toggled, at the same revision | oracle: the reproduction command from 00-reproduce's Result, run at both toggle states | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the proven cause by identity, the toggle that
demonstrates it, and the killed-hypothesis digest; verification;
feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
