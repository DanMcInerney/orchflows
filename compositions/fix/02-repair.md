---
id: 02-repair
executor: orch-repair
pack: orch-code-pack
depends_on: [01-cause]
write_scope: [{{workspace}}]
bound: <= 60 tool calls
excluded_actions:
  - repair an unproven cause
  - widen into adjacent cleanup
independence: checker
isolation: required
profile: orch-worker
---

## Objective

The smallest coherent change to {{workspace}} that removes the proven
cause of {{failure}}, leaving the reproduction PASSing, plus one new
regression check that FAILs on the old behaviour and PASSes on the new.

## Fixed inputs

- 01-cause's `## Result` — the proven cause by identity and the toggle
  that demonstrated it.
- 00-reproduce's `## Result` — the reproduction command and the failure
  identity it produces.

## Completion test

- the reproduction command PASSes at the repaired revision | oracle: the reproduction command from 00-reproduce's Result | oracle_class: deterministic | provenance: pre-existing
- the changed paths lie inside {{workspace}} | oracle: the workspace diff against the recorded baseline | oracle_class: deterministic | provenance: pre-existing
- one new regression check exists that FAILs at the pre-repair revision and PASSes at the repaired revision | oracle: the new check run in a clone at both revisions | oracle_class: deterministic | provenance: authored-here

## Return fields

status; result — the changed artifacts by identity, the repaired
revision, and the regression check by identity; verification; feedback;
risks

## Result

## Verification

## Feedback

[]

## Risks

[]
