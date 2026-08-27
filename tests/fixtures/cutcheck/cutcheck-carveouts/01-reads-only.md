---
id: 01-reads-only
run: cutcheck-carveouts
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
root_generation: root:01-reads-only:1:sha256:28837ee2df2b8fe5c704d42a82975a2b7c8224341b224a99df8d787d13244f2b
cut_generation: cut:01-reads-only:1:sha256:3ce87e62cb68ed5358655faa6705891a1c766cdb4ee2856ef66397e926e83c15
assignment_seal: sha256:c2c058ac67ecc79b77cd7488e283a9e8c126345eacd2175694369fd987f4229e
---
## Objective

Fixture ticket whose oracle reads a path it does not write. Observing is not
naming: a path the test only reads stays outside the write scope, so family 3
reports nothing here.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **The installer lists the script.** `grep -n "cutcheck.py" install.py`
   returns the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
