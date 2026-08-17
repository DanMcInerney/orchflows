---
id: 03-gamma
run: cutcheck-graph
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - packs/orch-code-pack/SKILL.md
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture set for the shape reading: a third item on the first level, on no
chain at all, so the first level's width is three where the chain is one.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **Installed under its bare name.** `grep -n "cutcheck.py" install.py` returns
   the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
