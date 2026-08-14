---
id: 01-lonely
run: cutcheck-f5-nomap
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - docs/vocabulary.md
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture item for the absent-map path: this set carries no map, so family 5 reports the map itself and no orphan in either direction.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **The installer lists the script.** `grep -n "cutcheck.py" install.py`
   returns the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
