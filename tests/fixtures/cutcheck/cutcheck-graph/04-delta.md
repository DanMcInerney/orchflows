---
id: 04-delta
run: cutcheck-graph
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on:
  - 01-alpha
bound: 20 tool calls
write_scope:
  - README.md
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture set for the shape reading: one first-level item stands behind this one,
so it is the second level and the second link of the chain.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **Installed under its bare name.** `grep -n "cutcheck.py" install.py` returns
   the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
