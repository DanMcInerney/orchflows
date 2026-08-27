---
id: 01-first
run: cutcheck-f4-transitive
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - scripts/cutcheck.py
excluded_actions:
  - editing scripts/tickets.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-first:1:sha256:4f79c1364c06f871141f8725975b5e1e4abaadb2c9c4116f1a9cbaa0f6c78fec
cut_generation: cut:01-first:1:sha256:8042fe5c2fd7275fd66468e66fd7f35bd399ab250b5bba2f2bde9177b3918a8f
assignment_seal: sha256:116cd22d5f3badc988208275233ffb1536fc14974dcbe5af75b9f3bd6de21fb1
---
## Objective

Fixture item for pairwise safety: this item shares its scope with `03-third` and its oracle reads that shared path. Only `02-middle` joins them.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **The pairwise class is named in the script.**
   `grep -n "staged-invalidation" scripts/cutcheck.py` returns at least one
   line. oracle_class: deterministic. provenance: pre-existing.

## Result

[]
