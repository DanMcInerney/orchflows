---
id: 01-covered
run: cutcheck-f5-coverage
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - docs/vocabulary.md
excluded_actions:
  - editing scripts/tickets.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-covered:1:sha256:e680da7efe8fd2b1b6fecda586bc6cfc183fb4a3045fb8341497f0d141d94672
cut_generation: cut:01-covered:1:sha256:f8473ed080d100debce75dcd6913cfd1db26be8aeac14e0011b8e99d31882b3e
assignment_seal: sha256:2616efd482f8c79b32aeaaf7c1f7e9df3cd1ea8c16787bad2d75d122f6a62e2d
---
## Objective

Fixture item for acceptance coverage: the map beside these tickets names this item at criterion 1.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **The installer lists the script.** `grep -n "cutcheck.py" install.py`
   returns the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
