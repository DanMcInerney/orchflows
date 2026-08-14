---
id: 01-clean-oracles
run: cutcheck-clean
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
  - editing scripts/tickets.py
---
## Objective

Fixture set for a clean cut: every completion-test oracle below discriminates,
so family 1 reports nothing and cutcheck exits 0 over this set.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **Installed under its bare name.** `grep -n "cutcheck.py" install.py` returns
   the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.
2. **The family is named in the script.**
   `grep -n "family 1" scripts/cutcheck.py` returns at least one line.
   oracle_class: deterministic. provenance: pre-existing.

## Result

[]
