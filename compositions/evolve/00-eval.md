---
id: 00-eval
executor: orch-eval-design
pack: orch-code-pack
depends_on: []
write_scope: []
bound: <= 40 tool calls
excluded_actions:
  - mutating {{target}} or anything in {{mutation_scope}}
  - letting a candidate, variant or score enter the design
independence: checker
isolation: none
profile: orch-worker
---

## Objective

One candidate-blind evaluation for {{target}}, frozen before any
candidate exists: its identity, mode, scoring criteria, required
admission and regression criteria, artifact-evidence adapter, promotion
rule, margin, and search policy.

Write the design into this ticket's `## Result` and nowhere inside
{{mutation_scope}}. In judged mode the accepted design identity also owns
the Judge brief, criteria, aggregation and adapter; in benchmark mode the
qualified benchmark and its runner own them.

## Fixed inputs

- input: {"name":"evaluation","type":"literal","value":"{{evaluation}}"}
- input: {"name":"incumbent","type":"literal","value":"{{incumbent}}"}
- input: {"name":"target","type":"literal","value":"{{target}}"}
- input: {"name":"mutation-scope","type":"literal","value":"{{mutation_scope}}"}

## Completion test

- the evaluation identity in force is frozen before generation — {{evaluation}} where that is not `none`, otherwise the identity this ticket's `## Result` names | oracle: the identity cited in `## Result` | oracle_class: deterministic | provenance: pre-existing
- the design names its mode, scoring criteria, required admission and regression criteria, evidence adapter, promotion rule, margin, and search policy (`none` or a search-policy/v1 object), or returns a blocked partial result naming the evaluation-design gap | oracle: the design read against that field list | oracle_class: deterministic | provenance: authored-here

## Return fields

status; result — the evaluation identity, its mode, and the criteria,
promotion rule, margin and search policy it freezes; verification;
feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
