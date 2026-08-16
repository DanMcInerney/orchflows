---
id: 00-run
executor: orch-frontier
depends_on: []
write_scope: []
bound: <= 60 tool calls
excluded_actions:
  - instantiating a template — every canary item is already a ticket
  - adding, removing, or reordering a canary item to make the set run
independence: checker
isolation: none
profile: orch-worker
---

## Objective

Every canary item in {{canary_set}} ran under `orch-frontier`, each
carrying its own result, at one recorded binding — model id, effort
level, and host.

## Fixed inputs

- {{canary_set}} — the frozen golden work items under `.orch/canary/`,
  each already a ticket, spanning the kernel boundaries its README
  declares. Read only: the run never writes into it.
- The items are placed, each a copy carrying this ticket's `run` plus
  `.00-run` as its `run`, through `tickets.py new --file`, before the
  drain, so a claim or a result lands on the issued copy and the golden
  set is still byte-clean at close.

## Completion test

- every item in {{canary_set}} carries a terminal status and a result | oracle: `tickets.py worklog` over the run | oracle_class: deterministic | provenance: pre-existing
- no item's golden result changed during the run | oracle: git status over {{canary_set}} | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the run id, each item's result identity, and the
binding recorded as model id, effort level and host; verification;
feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
