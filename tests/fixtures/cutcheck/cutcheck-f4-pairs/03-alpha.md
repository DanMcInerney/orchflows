---
id: 03-alpha
run: cutcheck-f4-pairs
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - scripts/cutcheck.py
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture item for pairwise safety: this item and `04-beta` hold the same scope with no edge between them.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **The shared scope is the whole defect.** The two scopes intersect, which
   the report names without running anything. oracle_class: deterministic.
   provenance: authored-here.

## Result

[]
