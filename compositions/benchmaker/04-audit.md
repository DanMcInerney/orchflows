---
id: 04-audit
executor: orch-critique
depends_on: [03-qualify]
write_scope: [{{package}}]
bound: <= 80 tool calls
excluded_actions:
  - render a pass/fail verdict on the benchmark
  - audit only the hard cases — the re-read sample is declared, so difficulty filtering cannot enter by the back door
  - leave a hole undeclared, which is the failure a declared one is not
independence: gate
isolation: required
profile: orch-worker
---

## Objective

The two questions qualification does not ask, answered in a context
disjoint from every builder and from the qualifier: is each case's
stated expectation right, and is its probe passable without the work.
Each finding repaired within the remaining allocation or declared as a
gap naming the case and its class.

## Fixed inputs

- 03-qualify's `## Result` — the qualified assembly at its fixed
  identity, and its verdict set.
- [the protocol](../references/benchmaker-protocol.md)'s audit and
  measurement stages — the stage order, the reference audit's three
  defect classes, the attack pass's three outcomes, and the triage
  measurement pass that precedes the audit it targets.
- The dated attack checklist this package carries, appended to with its
  date where this pass adds a class.

## Completion test

- every case recorded `inversion` or `both-fail` by the triage pass was audited by solving it from the prompt and licensed evidence alone, and the re-read sample over the rest is declared | oracle: the reference audit record | oracle_class: deterministic | provenance: authored-here
- the audit reports a defect count and each defect's class, never a rate | oracle: the reference audit record | oracle_class: deterministic | provenance: pre-existing
- every attack outcome is `SUCCEEDED`, `FAILED` or `BLOCKED` from the candidate's own scope for that case, and every unrepaired hole is declared with the attack that works | oracle: the attack pass record | oracle_class: deterministic | provenance: authored-here

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
