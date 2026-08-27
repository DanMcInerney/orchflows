---
id: 01-triage
executor: orch-triage
depends_on: [00-audit]
bound: <= 30 tool calls
independence: checker
isolation: none
profile: orch-worker
---

## Goal

Every finding carries one disposition, and every ready-for-agent finding
carries a compacted brief a fresh context can execute from.

## Context

- input: {"name":"none","type":"literal","value":null}

Exceptional constraints:

- investigate a finding past the cheap checks triage licenses

## Result


## Verification


## Feedback

[]

## Risks

[]
