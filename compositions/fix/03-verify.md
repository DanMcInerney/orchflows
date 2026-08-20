---
id: 03-verify
executor: orch-verify
depends_on: [02-repair]
write_scope: []
bound: <= 30 tool calls
excluded_actions:
  - skip the regression guard because the fix looks obvious
  - accept a guard that passes at the pre-repair revision
independence: checker
isolation: none
---

## Objective

Verdicts over the repaired {{workspace}}: every oracle the failure was
already gated by, plus the regression guard that keeps {{failure}} from
returning unobserved.

## Fixed inputs

- input: {"name":"workspace","type":"literal","value":"{{workspace}}"}
- input: {"name":"failure","type":"literal","value":"{{failure}}"}

## Completion test

- every original oracle PASSes at the repaired revision | oracle: the workspace's own check commands, rerun at that revision | oracle_class: deterministic | provenance: pre-existing
- 02-repair's regression check FAILs at the pre-repair revision (in a clone) and PASSes at the repaired revision | oracle: the regression check named in 02-repair's Result, run at both revisions | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the verdict per criterion with evidence cited by
identity, and the regression check by identity; verification; feedback;
risks

## Result

## Verification

## Feedback

[]

## Risks

[]
