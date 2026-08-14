---
id: 03-third
run: cutcheck-f4-transitive
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: [02-middle]
bound: 20 tool calls
write_scope:
  - scripts/cutcheck.py
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture item for pairwise safety: this item shares its scope with `01-first`, reachable from here through `02-middle`.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **The pairwise class is named in the script.**
   `grep -n "staged-invalidation" scripts/cutcheck.py` returns at least one
   line. oracle_class: deterministic. provenance: pre-existing.

## Result

[]
