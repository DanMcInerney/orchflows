---
id: 01-mention
run: cutcheck-mention
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - install.py
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture ticket for scope closure: naming a path is not writing to it. The item
writes its verdict to `.orch/evidence/mention/verdict.txt`, an evidence sink
this grant does not name. The map a real run keeps is written to
`.orch/runs/<run>/coverage.md` by the decomposer, never by this item. This item
never writes `scripts/cutcheck.py`, which item 03 finished. The path stays
outside this write scope (`rules/topology.md` states that observing is not
naming).

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **The installer still lists its scripts.** `grep -n "SCRIPT_NAMES"
   install.py` returns the tuple line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
