---
id: 02-rewriter
run: cutcheck-f4-ordered
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: [01-reader]
bound: 20 tool calls
write_scope:
  - install.py
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture item for pairwise safety: `install.py` is this item's whole scope, and the oracle of item `01-reader` reads it. This item depends on that one, so the pair is ordered.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **The installer lists the script.** `grep -n "cutcheck.py" install.py`
   returns the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
