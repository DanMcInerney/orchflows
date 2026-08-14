---
id: 02-orphan-item
run: cutcheck-f5-coverage
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - ARCHITECTURE.md
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture item for acceptance coverage: no row of the map beside these tickets names this item, so it answers to no criterion.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **The installer lists the script.** `grep -n "cutcheck.py" install.py`
   returns the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
