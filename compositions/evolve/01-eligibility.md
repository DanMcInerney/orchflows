---
id: 01-eligibility
executor: orch-verify
pack: orch-code-pack
depends_on: [00-eval]
write_scope: []
bound: <= 30 tool calls
excluded_actions:
  - expose protected evidence
  - rank an ineligible candidate
  - generating or scoring a candidate — this stub grades the incumbent
independence: checker
isolation: none
profile: orch-worker
---

## Objective

Verdicts over {{incumbent}}'s fixed evidence against the frozen
evaluation's required admission and regression criteria: covered PASS is
what permits generation to open, and nothing else does.

## Fixed inputs

- 00-eval's `## Result` — the evaluation identity, mode and criteria, by
  identity; {{evaluation}} itself where that is not `none`.
- {{incumbent}} — the fixed incumbent result/evidence identity for
  {{target}}, read as admitted and never re-executed.

## Completion test

- every required admission and regression criterion of the frozen evaluation carries a verdict over {{incumbent}}'s fixed evidence | oracle: the criterion set from 00-eval's Result, checked for coverage against the verdict set | oracle_class: deterministic | provenance: pre-existing
- generation opens on covered PASS alone; one required criterion short of PASS closes the campaign here | oracle: the verdict set read against the required criteria | oracle_class: deterministic | provenance: pre-existing
- no protected item-level evidence appears in this ticket's Result | oracle: the Result read against the frozen evaluation's protected evidence policy | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the admission verdicts and the evaluation identity they
were taken under; verification; feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
