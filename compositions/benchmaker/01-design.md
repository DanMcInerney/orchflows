---
id: 01-design
executor: orch-eval-design
depends_on: [00-acquire]
write_scope: [{{package}}]
bound: <= 60 tool calls
excluded_actions:
  - move the declared coverage floor with the target's execution cost
  - buy speed from the coverage floor, the oracle, or the horizon the outcome needs
  - buy difficulty from filtering on a candidate's scores
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

- 00-acquire's `## Result` — the frozen synthesis identity and its
  source identities; the design works from these and gathers nothing.
- {{target}} and {{outcome}} — the identity and intended observable
  outcome, still opaque.
- [the protocol](../references/benchmaker-protocol.md#licensed-oracle-material) —
  what the frozen evidence licenses as oracle material, and what is not
  a reason to decline casing it.

## Completion test

- the design is frozen at one package-owned identity before any case is materialized | oracle: the design identity against the package | oracle_class: deterministic | provenance: pre-existing
- every required criterion names an oracle and an `oracle_class`, and every case names its execution tier and its anchor or `none` with a reason | oracle: the design read against contracts/verdict.md | oracle_class: deterministic | provenance: pre-existing
- a missing field or gap that leaves {{outcome}} or its materialization unobservable is returned as partial evidence and stops materialization; every other declared gap is carried forward | oracle: the design's gap list | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the frozen evaluation-design identity, stated
assumptions and explicit gaps; verification; feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
