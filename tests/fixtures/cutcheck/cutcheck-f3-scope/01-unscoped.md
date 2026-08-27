---
id: 01-unscoped
run: cutcheck-f3-scope
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - install.py
excluded_actions:
  - editing scripts/tickets.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-unscoped:1:sha256:526c70009670b400741c861a70771368e337303d4193fb3a520bcb233d765c1a
cut_generation: cut:01-unscoped:1:sha256:22faf28185b3709c49bef5c89c27b4b3c0ec10e6613d3d5d04718a951dc56c48
assignment_seal: sha256:d3b132dabcaf671e5001bd10249fccbf5fe3e1c3dd3bae59a95ffd3278b59053
---
## Objective

Fixture ticket for scope coverage: the item writes its verdict to
`.orch/evidence/f3-scope/verdict.txt`, an evidence sink the write scope above
does not name.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **The installer lists the script.** `grep -n "cutcheck.py" install.py`
   returns the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
