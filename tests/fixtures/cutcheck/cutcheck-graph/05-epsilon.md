---
id: 05-epsilon
run: cutcheck-graph
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on:
  - 04-delta
  - 02-beta
bound: 20 tool calls
write_scope:
  - AGENTS.md
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture set for the shape reading: two items stand behind this one, one on each
of the levels below, so the greater of them decides the level and the chain.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **Installed under its bare name.** `grep -n "cutcheck.py" install.py` returns
   the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
