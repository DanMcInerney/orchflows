---
id: 01-alpha
run: cutcheck-graph
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

Fixture set for the shape reading: this item depends on nothing in the set, so
it sits on the first level, and the chain the reading names starts here.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **Installed under its bare name.** `grep -n "cutcheck.py" install.py` returns
   the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
