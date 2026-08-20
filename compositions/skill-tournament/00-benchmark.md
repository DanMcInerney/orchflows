---
id: 00-benchmark
executor: orch-frontier
pack: orch-code-pack
depends_on: []
write_scope: [benchmarks/{{skill}}/]
bound: <= 200 tool calls
excluded_actions:
  - mutating {{skill}} — the benchmark is built for it, never by changing it
  - generating, scoring or comparing a candidate; this stub builds and qualifies, and nothing else
  - restate or call evolve's verification, search, or selection internals
  - letting a benchmaker run targeting benchmaker call evolve
independence: checker
isolation: required
profile: orch-worker
---

## Objective

The terminal nested run formed by this ticket's `run` plus `.00-benchmark`
is an instantiation of `compositions/benchmaker` for `target={{skill}}`, the
skill's declared observable outcome, `sources={{sources}}`, `rigor={{rigor}}`,
`pack={{pack}}`, and this ticket's benchmark write scope as `package`. Its
qualified result is recorded in the package manifest at the one Git revision
that versions the benchmark and remains fixed for the campaign.

## Fixed inputs

- input: {"name":"skill","type":"literal","value":"{{skill}}"}

## Completion test

- the nested run met benchmaker's done check, which [its terminal stub](../benchmaker/05-measure.md) states | oracle: the manifest read against the package's component set | oracle_class: deterministic | provenance: pre-existing
- the benchmark revision is named by identity and the package is clean at it | oracle: git status over the benchmark package at the revision the manifest names | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the qualified benchmark revision by identity;
verification — the manifest's qualification; feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
