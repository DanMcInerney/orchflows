---
id: 01-evidence
executor: orch-outline
pack: orch-research-pack
depends_on: [00-record]
bound: <= 120 tool calls
independence: checker
profile: orch-worker
---

<!-- BGW-TRACE[implementation:experiment-validity|PJ-16,PJ-17] -->
<!-- BGW-TRACE[implementation:conditional-fidelity|PJ-23] -->
<!-- BGW-TRACE[implementation:revalidation|PJ-25] -->

## Goal

One fixed evidence packet for the independently schedulable empirical fields
in 00-record that can affect its next material transition. Each experiment
matches its source field's open `decision_id` under the intake-authority
policy, predeclares every required experiment field, and settles only its
matched cells. Negative, null, and inconclusive results remain visible.
Conditional controls and experiments without the policy's complete recorded
trigger identity remain `inactive`.

## Context

- input: {"name":"program-record","type":"literal","value":"the accepted 00-record Result identity in this composition instance"}
- input: {"name":"intake-authority-policy","type":"literal","value":"compositions/references/browser-game-intake-policy.json"}
- input: {"name":"evidence-store-root","type":"literal","value":"the run-scoped evidence store recorded by workspace_path"}
- input: {"name":"question","type":"literal","value":"Which independently schedulable empirical gaps in the current program record need evidence before its next transition?"}
- input: {"name":"source-policy","type":"literal","value":"current primary specifications, vendor terms, release records, repositories, and inspectable measurements; secondary sources only for discovery"}
- input: {"name":"rigor-bar","type":"literal","value":"each load-bearing claim requires dated, target-matched evidence with mechanism, workload, population, and outcome transfer stated"}

Exceptional constraints:

- settle or change the authority of a user-only field
- settle an empirical field whose `decision_id` or transfer cell does not match the experiment
- activate a CR or EX control without its recorded trigger identity
- promote a renderer, engine, backend, topology, performance number, fallback, QA ladder, release model, AI policy, or transport to a universal default
- authorize a time-sensitive choice without its observation date and revalidation trigger

## Result


## Verification


## Feedback

[]

## Risks

[]
