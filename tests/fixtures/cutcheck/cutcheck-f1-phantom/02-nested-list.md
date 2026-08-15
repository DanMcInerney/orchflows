---
id: 02-nested-list
run: cutcheck-f1-phantom
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: [01-phantom]
bound: 20 tool calls
write_scope:
  - docs/vocabulary.md
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture ticket for the control the wrap rule must not break: a numbered list
nested under a criterion is that criterion's own text, and the criterion after
the list still opens.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **A criterion holding a nested enumeration.** `grep -n "SCRIPT_NAMES"
   install.py` returns the tuple line, which carries
   1. the tuple the installer opens, and
   2. every script name it lists.
   oracle_class: deterministic. provenance: pre-existing.
2. **The criterion after the nested list opens on its own.** `grep -n
   "friction.py" install.py` returns that same line. oracle_class:
   deterministic. provenance: pre-existing.

## Result

[]
