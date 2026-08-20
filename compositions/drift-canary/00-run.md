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

The nested run formed by this ticket's `run` plus `.00-run` is terminal and
contains one `tickets.py new --file` copy of every item in the read-only
`{{canary_set}}` golden set under `.orch/canary/`. Each copy carries its own
result from `orch-frontier` at one recorded model-id, effort-level, and host
binding; the golden set is byte-identical to its input identity.

## Fixed inputs

- input: {"name":"canary-set","type":"literal","value":"{{canary_set}}"}

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
