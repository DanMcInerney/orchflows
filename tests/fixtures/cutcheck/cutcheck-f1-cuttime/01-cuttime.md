---
id: 01-cuttime
run: cutcheck-f1-cuttime
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - install.py
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture set for cut time: one oracle that discriminates correctly for work that
has not landed, so it matches nothing in the tree it is cut from.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **The token the work will add.**
   `grep -rn "zzqq-cuttime-token" install.py` returns at least one line.
   oracle_class: deterministic. provenance: authored-here.

## Result

[]
