---
id: 01-campaign
executor: orch-frontier
pack: orch-code-pack
depends_on: [00-benchmark]
write_scope: [{{surface}}]
bound: {{bound}}
excluded_actions:
  - change the benchmark or policy inside the campaign
  - restate or call evolve's verification, search, or selection internals
  - activating a selected result here — a selected result requires a separate authorized integration before activation
independence: checker
isolation: required
profile: orch-worker
---

## Objective

The terminal nested run formed by this ticket's `run` plus `.01-campaign`
is an instantiation of `compositions/evolve` with `target={{skill}}`, the
skill's current fixed result/evidence as `incumbent`, 00-benchmark's qualified
revision plus {{policy}} as `evaluation`, `writer=orch-build`,
`mutation_scope={{surface}}`, and `bound={{bound}}`. Its final score card
names the final incumbent and the one benchmark revision every candidate
was scored against.

## Fixed inputs

- input: {"name":"policy","type":"literal","value":"{{policy}}"}
- input: {"name":"surface","type":"literal","value":"{{surface}}"}
- input: {"name":"bound","type":"literal","value":"{{bound}}"}
- input: {"name":"skill","type":"literal","value":"{{skill}}"}

## Completion test

- the final score card covers the one benchmark revision every candidate was scored against | oracle: the score card's benchmark revision compared with 00-benchmark's Result | oracle_class: deterministic | provenance: pre-existing
- the benchmark package is byte-identical at close to the revision 00-benchmark qualified, and {{policy}} is the identity the packet froze | oracle: git diff over the benchmark package plus the policy identity comparison | oracle_class: deterministic | provenance: pre-existing
- every changed path lies inside {{surface}} | oracle: the run's changed artifacts read against {{surface}} | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the evolution result by identity; verification — the
final score card; then the benchmark revision, the candidate set, bounds
spent and cumulative changed artifacts; feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
