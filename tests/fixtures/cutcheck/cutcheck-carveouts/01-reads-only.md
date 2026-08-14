---
id: 01-reads-only
run: cutcheck-carveouts
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - scripts/cutcheck.py
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture ticket whose oracle reads a path it does not write. Observing is not
naming: a path the test only reads stays outside the write scope, so family 3
reports nothing here.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **The installer lists the script.** `grep -n "cutcheck.py" install.py`
   returns the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
