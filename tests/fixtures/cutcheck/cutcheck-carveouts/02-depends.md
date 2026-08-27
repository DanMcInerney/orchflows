---
id: 02-depends
run: cutcheck-carveouts
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: [01-reads-only]
bound: 20 tool calls
write_scope:
  - tests/test_cutcheck.py
excluded_actions:
  - editing scripts/tickets.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-reads-only:1:sha256:28837ee2df2b8fe5c704d42a82975a2b7c8224341b224a99df8d787d13244f2b
cut_generation: cut:01-reads-only:1:sha256:3ce87e62cb68ed5358655faa6705891a1c766cdb4ee2856ef66397e926e83c15
assignment_seal: sha256:775ce6c78be8c9a903d5923f87b05f709c8c1007276908e989d8e86da48875de
---
## Objective

Fixture ticket whose oracle names a path its `depends_on` ancestor makes. The
oracle runs at this item's revision, which contains the ancestor's work, so the
path is present for family 2 and absent from this item's own write scope.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **The family the ancestor added is named.**
   `grep -n "family 1" scripts/cutcheck.py` returns at least one line.
   oracle_class: deterministic. provenance: pre-existing.

## Result

[]
