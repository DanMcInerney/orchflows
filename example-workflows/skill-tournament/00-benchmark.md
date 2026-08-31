---
id: 00-benchmark
executor: orch-execute
pack: {{pack}}
depends_on: []
bound: <= 200 tool calls
independence: checker
isolation: required
profile: orch-worker
---

## Goal

The terminal nested run formed by this ticket's `run` plus `.00-benchmark`
is an instantiation of `example-workflows/benchmaker` for `target={{skill}}`, the
skill's declared observable outcome, `sources={{sources}}`, `rigor={{rigor}}`,
`pack={{pack}}`, and this ticket's benchmark starting location as `package`. Its
qualified result is recorded in the package manifest at the one Git revision
that versions the benchmark and remains fixed for the campaign.

## Context

- input: {"name":"skill","type":"literal","value":"{{skill}}"}

## Details

- benchmarks/{{skill}}/

Exceptional constraints:

- mutating {{skill}} — the benchmark is built for it, never by changing it
- generating, scoring or comparing a candidate; this stub builds and qualifies, and nothing else
- restate or call evolve's verification, search, or selection internals
- letting a benchmaker run targeting benchmaker call evolve

## Report
