---
id: 01-reader
run: cutcheck-f4-ordered
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - tests/test_cutcheck.py
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture item for pairwise safety: its oracle reads `install.py`, a path the sibling item `02-rewriter` alone may change. The edge below orders them, so the pair is no defect.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **The installer lists the script.** `grep -n "cutcheck.py" install.py`
   returns the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
