---
id: 04-audit
executor: orch-critique
depends_on: [03-qualify]
bound: <= 80 tool calls
independence: gate
isolation: required
profile: orch-worker
---

## Goal

The triage measurement pass, then the two questions qualification does
not ask, answered in a context disjoint from every builder and from the
qualifier: is each case's stated expectation right, and is its probe
passable without the work.
Each finding repaired within the remaining allocation or declared as a
gap naming the case and its class.

## Context

- input: {"name":"protocol-contract","type":"literal","value":"the protocol contract at compositions/references/benchmaker-protocol.md in the orchflows library"}
- input: {"name":"package","type":"literal","value":"{{package}}"}

## Suggested files

- {{package}}

Exceptional constraints:

- render a pass/fail verdict on the benchmark
- enter an attack artifact into the case set
- audit only the hard cases
- leave a hole undeclared

## Result


## Verification


## Feedback

[]

## Risks

[]
