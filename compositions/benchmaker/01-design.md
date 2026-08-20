---
id: 01-design
executor: orch-eval-design
depends_on: [00-acquire]
write_scope: [{{package}}]
bound: <= 60 tool calls
excluded_actions:
  - move the declared coverage floor with the target's execution cost
  - buy speed from the coverage floor, the oracle, or the horizon the outcome needs
independence: checker
isolation: none
profile: orch-worker
---

## Objective

One evaluation for {{target}}, frozen at one package-owned identity:
case specifications with their execution tiers and anchors, required
criteria with named oracles and `oracle_class`, scoring and aggregation,
intended coverage, and expected execution cost.

## Fixed inputs

- input: {"name":"target","type":"literal","value":"{{target}}"}
- input: {"name":"outcome","type":"literal","value":"{{outcome}}"}
- input: {"name":"sources","type":"literal","value":"{{sources}}"}
- input: {"identity":{"kind":"artifact","locator":"project:compositions/references/benchmaker-protocol.md","sha256":"cbe548149efd0ce3184e5f805a91173bd85a6c8a354f8d6e083a1781e4331f8d"},"name":"protocol-contract","type":"identity"}
- input: {"name":"package","type":"literal","value":"{{package}}"}

## Completion test

- the design is frozen at one package-owned identity before any case is materialized | oracle: the design identity against the package | oracle_class: deterministic | provenance: pre-existing
- every required criterion names an oracle and an `oracle_class`, and every case names its execution tier and its anchor or `none` with a reason | oracle: the design read against contracts/verdict.md | oracle_class: deterministic | provenance: pre-existing
- a missing field or gap that leaves {{outcome}} or its materialization unobservable is returned as partial evidence and stops materialization; every other declared gap is carried forward | oracle: the design's gap list | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — everything orch-eval-design's Return names: the frozen
design identity, the case specifications with their tiers and anchors,
the required criteria with their oracles and `oracle_class`, scoring and
aggregation, intended coverage, expected execution cost, and the gaps
carried forward; verification; feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
