---
id: 04-audit
executor: orch-critique
depends_on: [03-qualify]
write_scope: [{{package}}]
bound: <= 80 tool calls
excluded_actions:
  - render a pass/fail verdict on the benchmark
  - enter an attack artifact into the case set
  - audit only the hard cases
  - leave a hole undeclared
independence: gate
isolation: required
profile: orch-worker
---

## Objective

The triage measurement pass, then the two questions qualification does
not ask, answered in a context disjoint from every builder and from the
qualifier: is each case's stated expectation right, and is its probe
passable without the work.
Each finding repaired within the remaining allocation or declared as a
gap naming the case and its class.

## Fixed inputs

- input: {"name":"protocol-contract","type":"literal","value":"the protocol contract at compositions/references/benchmaker-protocol.md in the orchflows library"}
- input: {"name":"package","type":"literal","value":"{{package}}"}

## Completion test

- every case §Reference audit sends to the solve-it-yourself pass was audited that way, and the re-read sample over the rest is declared | oracle: the triage measurement record and the reference audit record | oracle_class: deterministic | provenance: authored-here
- the audit's output carries the shape §Reference audit requires of it | oracle: the reference audit record | oracle_class: deterministic | provenance: pre-existing
- every attack outcome is one of §Attack pass's three, taken from the candidate's own scope for that case, and every unrepaired hole is declared | oracle: the attack pass record | oracle_class: deterministic | provenance: authored-here

## Return fields

status; result — the reference audit and attack pass records by
identity, the auditing and attacking contexts' model id, effort and host
binding, and what was repaired; verification; feedback; risks — every
declared gap

## Result

## Verification

## Feedback

[]

## Risks

[]
