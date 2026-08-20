---
id: 00-mine
executor: orch-self-improve
pack: orch-code-pack
depends_on: []
write_scope: []
bound: <= 60 tool calls
independence: checker
isolation: none
profile: orch-planner
---

## Objective

Ranked improvement proposals for {{window}}, each written to the state
sink's `improvement/` through `tickets.py improvement --proposal` with
one causal owner, its scope, the exact change, and every evidence entry
verbatim — and the top-ranked proposal named as this run's delivery
target, or the finding that nothing qualified.

## Fixed inputs

- input: {"name":"window","type":"literal","value":"{{window}}"}
- input: {"identity":{"kind":"artifact","locator":"project:rules/improvement.md","sha256":"5855133149c60da7eea97a3ae8430affdc0cc5e0f1fde0c5355d1ecf4c0e616c"},"name":"improvement-law","type":"identity"}

## Completion test

- every proposal names exactly one causal owner as a repository-relative path and cites its evidence entries verbatim | oracle: each proposal file under the sink's `improvement/` | oracle_class: deterministic | provenance: pre-existing
- no proposal rests on an entry at or before a covered cluster's watermark | oracle: the proposals' evidence against `improvement/covered.jsonl` | oracle_class: deterministic | provenance: pre-existing
- the ranking follows evidence strength — checked contradiction or probe, then recurrence | oracle: each proposal's qualification basis against rules/improvement.md §4 | oracle_class: judged | provenance: pre-existing

## Return fields

status; result — everything orch-self-improve's Return names, and the
top-ranked proposal by path with the evidence entries it cites;
verification; feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
