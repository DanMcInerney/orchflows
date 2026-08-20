---
id: 01-triage
executor: orch-triage
depends_on: [00-audit]
write_scope: []
bound: <= 30 tool calls
excluded_actions:
  - investigate a finding past the cheap checks triage licenses
independence: checker
isolation: none
profile: orch-worker
---

## Objective

Every finding carries one disposition, and every ready-for-agent finding
carries a compacted brief a fresh context can execute from.

## Fixed inputs

- input: {"name":"none","type":"literal","value":null}

## Completion test

- every finding from 00-audit's Result carries exactly one disposition | oracle: the disposition set against that finding set | oracle_class: deterministic | provenance: pre-existing
- every ready-for-agent brief names objective, known evidence, and entrypoint skill | oracle: the brief set | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the dispositions by finding, the compacted briefs, and
which are ready-for-human; verification; feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
