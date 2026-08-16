---
id: 01-campaign
executor: orch-frontier
pack: orch-code-pack
depends_on: [00-benchmark]
write_scope: [{{surface}}]
bound: {{bound}}
excluded_actions:
  - change the benchmark or policy inside the campaign
  - restate or call evolve's verification, panel, search, or selection internals
  - activating a selected result here — a selected result requires a separate authorized integration before activation
independence: checker
isolation: required
profile: orch-worker
---

## Objective

One campaign over {{skill}} inside {{surface}}, scored against
00-benchmark's qualified revision and no other: a final score card
naming the final incumbent and the benchmark revision every candidate
was scored against.

## Fixed inputs

- 00-benchmark's `## Result` — the qualified benchmark revision, by
  identity. It is the campaign's evaluation and is read, never rebuilt.
- Instantiate compositions/evolve into a nested run of its own — this
  ticket's own `run` field plus `.01-campaign`, never the outer run —
  naming every placeholder that manifest declares: target={{skill}},
  incumbent={{skill}}'s fixed result/evidence at its current revision,
  evaluation=00-benchmark's qualified benchmark revision with {{policy}}
  as its search policy, writer=orch-build, mutation_scope={{surface}}, bound={{bound}}. Drain
  that ticket set here.
- {{policy}} — the frozen optimizer policy and candidate-accessible
  mappings, fixed for the whole campaign.

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
