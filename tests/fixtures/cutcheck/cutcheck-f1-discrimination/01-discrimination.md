---
id: 01-discrimination
run: cutcheck-f1-discrimination
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

Fixture set for family 1 discrimination: three oracles that read the same at the
baseline as they will when the work has landed, one per reported case.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **Already reads PASS at the baseline.**
   `grep -n "SCRIPT_NAMES" install.py` returns the tuple line. oracle_class:
   deterministic. provenance: authored-here.
2. **Zero hits at the baseline and zero hits at HEAD.**
   `grep -rn "zzqq-token-never-written" install.py` returns at least one line.
   oracle_class: deterministic. provenance: authored-here.
3. **A node id naming a class that does not exist.**
   `python3 -m pytest tests/test_installer.py::NoSuchClass::test_absent` exits 0.
   oracle_class: deterministic. provenance: authored-here.

## Result

[]
