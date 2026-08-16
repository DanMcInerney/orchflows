---
id: 00-acquire
run: cutcheck-f5-template
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

An instantiated template's first top-level stub, and one of this run's three
cuts. Its own subtree is `00-acquire.NN`; the stubs beside it are the
template's graph and belong to no root's decomposition.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

- `python install.py --dry-run` exits 0 | oracle: that command | oracle_class: deterministic | provenance: pre-existing

## Result

[]
