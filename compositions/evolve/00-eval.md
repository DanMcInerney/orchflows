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
admission and regression criteria, and artifact-evidence adapter.

## Fixed inputs

- {{evaluation}} — the frozen evaluation identity, or `none`. Skip when
  a frozen evaluation identity is supplied: the terminal reads it
  instead.
- {{incumbent}} — the fixed incumbent result/evidence identity for
  {{target}}, with its source identities, source policy, judgment
  permission, and the applicable pack craft, lens and oracle references.
- The design is written into this ticket's `## Result` and nowhere else,
  so the evaluation-design scope stays disjoint from {{mutation_scope}}:
  no evaluation is designed inside the scope its candidates mutate.
- In judged mode the accepted design identity is both evaluation and
  scoring identity, covering the Judge brief, criteria, aggregation and
  adapter; a qualified benchmark plus its runner is benchmark mode.

## Completion test

- the evaluation identity in force is frozen before generation — {{evaluation}} where that is not `none`, otherwise the identity this ticket's `## Result` names | oracle: the identity cited in `## Result` | oracle_class: deterministic | provenance: pre-existing
- the design names its mode, scoring criteria, required admission and regression criteria, and evidence adapter, or returns a blocked partial result naming the evaluation-design gap | oracle: the design read against that field list | oracle_class: deterministic | provenance: authored-here

## Return fields

status; result — the evaluation identity, its mode, and the criteria it
freezes; verification; feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
