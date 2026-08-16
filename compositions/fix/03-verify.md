---
id: 03-verify
executor: orch-verify
pack: orch-code-pack
depends_on: [02-repair]
write_scope: []
bound: <= 30 tool calls
excluded_actions:
  - skip the regression guard because the fix looks obvious
  - accept a guard that passes at the pre-repair revision
independence: checker
isolation: none
profile: orch-worker
---

## Objective

Verdicts over the repaired {{workspace}}: every oracle the failure was
already gated by, plus the regression guard that keeps {{failure}} from
returning unobserved.

## Fixed inputs

- 02-repair's `## Result` — the changed artifacts, the repaired
  revision, and the regression check, by identity.
- 00-reproduce's `## Result` — the reproduction command and the failure
  identity.
- The oracles {{workspace}} already gates on, named by its standards
  owner.

## Completion test

- every original oracle PASSes at the repaired revision | oracle: the workspace's own check commands, rerun at that revision | oracle_class: deterministic | provenance: pre-existing
- 02-repair's regression check FAILs at the pre-repair revision (in a clone) and PASSes at the repaired revision — a fix without such a check is `limited`, never `complete` | oracle: the regression check named in 02-repair's Result, run at both revisions | oracle_class: deterministic | provenance: pre-existing

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
