---
id: 01-diff
executor: orch-verify
depends_on: [00-run]
write_scope: []
bound: <= 40 tool calls
excluded_actions:
  - edit a golden result inside a canary run
  - treat divergence as failure
independence: checker
isolation: none
---

## Objective

One verdict per canary item against its golden result, and one friction
entry per divergence, so the delta between the new binding and the
frozen one is recorded where `orch-self-improve` reads it.

## Fixed inputs

- input: {"identity":{"kind":"ticket-section","run":"{{run}}","section":"Result","ticket":"00-run"},"name":"canary-results","type":"identity"}
- input: {"name":"canary-set","type":"literal","value":"{{canary_set}}"}

## Completion test

- every canary item ran and every divergence is logged as friction | oracle: the friction log for this run beside 00-run's result identities, read against `golden.json` | oracle_class: deterministic | provenance: pre-existing
- every verdict cites the `golden.json` entry it was decided against | oracle: the verdict set | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the divergence log, one entry per diverging item, and
the binding it was observed under; verification — the verdicts against
`golden.json`; feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
