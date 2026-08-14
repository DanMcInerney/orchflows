---
id: 02-middle
run: cutcheck-f4-transitive
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: [01-first]
bound: 20 tool calls
write_scope:
  - install.py
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture item for pairwise safety: the middle of the chain, depending on `01-first` and depended on by `03-third`.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **The installer lists the script.** `grep -n "cutcheck.py" install.py`
   returns the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
