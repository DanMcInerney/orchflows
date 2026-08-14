---
id: 02-stamped
run: cutcheck-provenance-mention
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: [01-mentioned]
bound: 20 tool calls
write_scope:
  - docs/vocabulary.md
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture ticket for the paired positive: the same oracle under a stamp the
criterion makes is the invariant the stamp says it is, and stays exempt.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **A stamp made rather than mentioned.** `grep -n "SCRIPT_NAMES" install.py`
   returns the tuple line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
