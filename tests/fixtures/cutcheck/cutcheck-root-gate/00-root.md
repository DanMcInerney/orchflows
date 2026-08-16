---
id: 00-root
run: cutcheck-root-gate
status: issued
executor: orch-decompose
pack: orch-code-pack
depends_on: []
bound: 20 tool calls
write_scope:
  - install.py
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture root ticket in the layout the work-item contract states: a root, one
`<root>.NN` unit, and the three gate stubs the gate step adds. The set is
honest, so the cut's own verdict is repeatable over it -- before the gate step
and again after it.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

- `python install.py --dry-run` exits 0 | oracle: that command | oracle_class: deterministic | provenance: pre-existing

## Result

[]
