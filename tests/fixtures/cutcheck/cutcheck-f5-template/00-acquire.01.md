---
id: 00-acquire.01
run: cutcheck-f5-template
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

The one unit of the first cut's subtree, and the only id its map may name.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

- the installer's script list names the cutter | oracle: `grep -n "cutcheck.py" install.py` | oracle_class: deterministic | provenance: authored-here

## Result

[]
