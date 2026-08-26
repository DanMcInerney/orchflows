---
id: 01-lonely
run: cutcheck-f5-nomap
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
root_generation: root:01-lonely:1:sha256:c768ddbe7f7332ca1bd3a748210c0653cc9cf5dba50afe6eae6015081e885b2b
cut_generation: cut:01-lonely:1:sha256:1d8f711e90e2ca5b1ec55998690bf140acd02d45580672c1f58effd7de7da753
assignment_seal: sha256:b625da17f3b4ac037b08b036972be036b49411c958c4672952ef6be31a6baffb
---
## Objective

Fixture item for the absent-map path: this set carries no map, so family 5 reports the map itself and no orphan in either direction.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **The installer lists the script.** `grep -n "cutcheck.py" install.py`
   returns the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
