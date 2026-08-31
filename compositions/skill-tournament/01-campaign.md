---
id: 01-campaign
executor: orch-execute
pack: {{pack}}
depends_on: [00-benchmark]
bound: {{bound}}
independence: checker
isolation: required
profile: orch-worker
---

## Goal

The terminal nested run formed by this ticket's `run` plus `.01-campaign`
is an instantiation of `compositions/evolve` with `target={{skill}}`, the
skill's current fixed result/evidence as `incumbent`, 00-benchmark's qualified
revision plus {{policy}} as `evaluation`, `writer=orch-execute`,
`mutation_scope={{surface}}`, and `bound={{bound}}`. Its final score card
names the final incumbent and the one benchmark revision every candidate
was scored against.

## Context

- input: {"name":"policy","type":"literal","value":"{{policy}}"}
- input: {"name":"surface","type":"literal","value":"{{surface}}"}
- input: {"name":"bound","type":"literal","value":"{{bound}}"}
- input: {"name":"skill","type":"literal","value":"{{skill}}"}
- standards owner: docs/custom-workflow-authoring.md

## Details

- {{surface}}

Exceptional constraints:

- change the benchmark or policy inside the campaign
- restate or call evolve's verification, search, or selection internals
- activating a selected result here — a selected result requires a separate authorized integration before activation

## Report
