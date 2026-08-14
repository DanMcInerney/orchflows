---
id: 02-contradiction
run: cutcheck-f3-scope
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - install.py
  - scripts/cutcheck.py
excluded_actions:
  - editing scripts/cutcheck.py
---
## Objective

Fixture ticket for a scope that contradicts itself: the grant above and the
exclusion above name the same path, so the item cannot be executed as issued.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **The family is named in the script.** `grep -n "family 1" scripts/cutcheck.py`
   returns at least one line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
