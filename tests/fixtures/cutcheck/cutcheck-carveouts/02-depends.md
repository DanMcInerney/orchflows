---
id: 02-depends
run: cutcheck-carveouts
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: [01-reads-only]
bound: 20 tool calls
write_scope:
  - tests/test_cutcheck.py
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture ticket whose oracle names a path its `depends_on` ancestor makes. The
oracle runs at this item's revision, which contains the ancestor's work, so the
path is present for family 2 and absent from this item's own write scope.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **The family the ancestor added is named.**
   `grep -n "family 1" scripts/cutcheck.py` returns at least one line.
   oracle_class: deterministic. provenance: pre-existing.

## Result

[]
