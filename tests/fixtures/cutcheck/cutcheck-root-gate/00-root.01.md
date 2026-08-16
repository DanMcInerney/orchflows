---
id: 00-root.01
run: cutcheck-root-gate
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

The one unit ticket of this root's subtree: the installer names every script
it copies.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

- the installer's script list names the cutter | oracle: `grep -n "cutcheck.py" install.py` | oracle_class: deterministic | provenance: authored-here

## Result

[]
