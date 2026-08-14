---
id: 03-alien
run: cutcheck-f6-executor
status: issued
executor: orch-render
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - AGENTS.md
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture item for executor legality: its executor is no engine, and no cell of the stamped pack names it either.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **The installer lists the script.** `grep -n "cutcheck.py" install.py`
   returns the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
