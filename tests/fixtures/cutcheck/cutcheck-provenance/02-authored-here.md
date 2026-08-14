---
id: 02-authored-here
run: cutcheck-provenance
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: [01-pre-existing]
bound: 20 tool calls
write_scope:
  - docs/vocabulary.md
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture ticket for provenance: the same oracle, stamped as authored here, still
has to discriminate.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **An oracle this item authored.** `grep -n "SCRIPT_NAMES" install.py`
   returns the tuple line. oracle_class: deterministic. provenance:
   authored-here.

## Result

[]
