---
id: 00-run
executor: orch-frontier
depends_on: []
bound: <= 60 tool calls
independence: checker
isolation: none
profile: orch-worker
---

## Goal

The nested run formed by this ticket's `run` plus `.00-run` is terminal and
contains one `tickets.py new --file` copy of every item in the read-only
`{{canary_set}}` golden set under `.orch/canary/`. Each copy carries its own
result from `orch-frontier` at one recorded model-id, effort-level, and host
binding; the golden set is byte-identical to its input identity.

## Context

- input: {"name":"canary-set","type":"literal","value":"{{canary_set}}"}

Exceptional constraints:

- instantiating a template — every canary item is already a ticket
- adding, removing, or reordering a canary item to make the set run

## Report
