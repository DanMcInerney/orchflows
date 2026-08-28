---
id: 01-evidence
executor: orch-investigate
pack: orch-research-pack
depends_on: [00-record]
bound: <= 120 tool calls
independence: checker
isolation: required
profile: orch-worker
---

## Goal

One fixed evidence packet for the empirical fields in 00-record that can
affect its next material transition. Each experiment predeclares the decision,
frozen candidates, workload or cohort, environment, metrics, stopping rule,
falsifiable oracle, and transfer boundary; negative, null, and inconclusive
results remain visible.

## Context

- input: {"identity":{"kind":"ticket-section","run":"{{run}}","section":"Result","ticket":"00-record"},"name":"program-record","type":"identity"}
- input: {"name":"evidence-store-root","type":"literal","value":"the run-scoped evidence store recorded by workspace_path"}
- input: {"name":"question","type":"literal","value":"Which independently schedulable empirical gaps in the current program record need evidence before its next transition?"}
- input: {"name":"source-policy","type":"literal","value":"current primary specifications, vendor terms, release records, repositories, and inspectable measurements; secondary sources only for discovery"}
- input: {"name":"rigor-bar","type":"literal","value":"each load-bearing claim requires dated, target-matched evidence with mechanism, workload, population, and outcome transfer stated"}

Exceptional constraints:

- answer or reclassify a `kind: user-only` field
- promote a renderer, engine, backend, topology, performance number, fallback, QA ladder, release model, AI policy, or transport to a universal default
- authorize a time-sensitive choice without its observation date and revalidation trigger

## Result


## Verification


## Feedback

[]

## Risks

[]
