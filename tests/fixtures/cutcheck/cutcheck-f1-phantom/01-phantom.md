---
id: 01-phantom
run: cutcheck-f1-phantom
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

Fixture set for a criterion whose wrapped line opens with a digit and a period:
the wrap continues the criterion it is indented under, and opens no item of its
own.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **A criterion whose oracle discriminates.** `grep -n "cutcheck.py"
   install.py` returns the SCRIPT_NAMES line. oracle_class: deterministic.
   provenance: pre-existing.
2. **A criterion whose own wrap opens with a number.** The installer names
   every script it copies, and `grep -n "SCRIPT_NAMES" install.py` exits
   0. oracle_class: deterministic. provenance: pre-existing.
3. **A criterion after the wrap opens on its own.** `grep -n "friction.py"
   install.py` returns that same tuple line. oracle_class: deterministic.
   provenance: pre-existing.

## Result

[]
