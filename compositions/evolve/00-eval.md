---
id: 00-eval
executor: orch-spec
depends_on: []
bound: <= 40 tool calls
independence: checker
isolation: none
profile: orch-worker
---

## Goal

One candidate-blind evaluation for {{target}}, frozen before any
candidate exists: its identity, mode, scoring criteria, required
admission and regression criteria, artifact-evidence adapter, promotion
rule, margin, and search policy.

Write the design into this ticket's `## Result` and nowhere inside
{{mutation_scope}}. In judged mode the accepted design identity also owns
the Judge brief, criteria, aggregation and adapter; in benchmark mode the
qualified benchmark and its runner own them.

## Context

- input: {"name":"evaluation","type":"literal","value":"{{evaluation}}"}
- input: {"name":"incumbent","type":"literal","value":"{{incumbent}}"}
- input: {"name":"target","type":"literal","value":"{{target}}"}
- input: {"name":"mutation-scope","type":"literal","value":"{{mutation_scope}}"}

Exceptional constraints:

- mutating {{target}} or anything in {{mutation_scope}}
- letting a candidate, variant or score enter the design

## Result


## Verification


## Feedback

[]

## Risks

[]
