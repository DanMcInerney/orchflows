---
id: 03-qualify
executor: orch-decompose
pack: {{pack}}
depends_on: [02-materialize]
bound: <= 80 tool calls
independence: gate
isolation: required
profile: orch-worker
---

## Goal

The assembled benchmark qualified at a fixed identity in a delivery
disjoint from every builder: oracle failability, coverage,
discrimination, reproducibility, redundancy, provenance and execution
cost each checked independently, with a verdict per required criterion.

## Context

- input: {"name":"protocol-contract","type":"literal","value":"the protocol contract at compositions/references/benchmaker-protocol.md in the orchflows library"}
- input: {"name":"package","type":"literal","value":"{{package}}"}
- input: {"name":"pack","type":"literal","value":"{{pack}}"}

## Suggested files

- {{package}}

Exceptional constraints:

- return a self-qualified verdict set where the builder-disjoint context is unreachable

## Result


## Verification


## Feedback

[]

## Risks

[]
