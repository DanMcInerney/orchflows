---
id: 02-beta
run: cutcheck-graph
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - rules/topology.md
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture set for the shape reading: a second item on the first level, and one
the last level's item depends on without lengthening the chain.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **Installed under its bare name.** `grep -n "cutcheck.py" install.py` returns
   the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
