---
id: 02-contradiction
run: cutcheck-f3-scope
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - install.py
  - scripts/cutcheck.py
excluded_actions:
  - editing scripts/cutcheck.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-unscoped:1:sha256:526c70009670b400741c861a70771368e337303d4193fb3a520bcb233d765c1a
cut_generation: cut:01-unscoped:1:sha256:22faf28185b3709c49bef5c89c27b4b3c0ec10e6613d3d5d04718a951dc56c48
assignment_seal: sha256:3dc5b30a2fd1417eda0ef33fa535c22977f63d20a65d297824a4ad03f669d44f
---
## Objective

Fixture ticket for a scope that contradicts itself: the grant above and the
exclusion above name the same path, so the item cannot be executed as issued.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **The family is named in the script.** `grep -n "family 1" scripts/cutcheck.py`
   returns at least one line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
