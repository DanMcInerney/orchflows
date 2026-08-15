---
id: 01-quoted
run: cutcheck-command-mention
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - scripts/cutcheck.py
---
## Objective

Fixture ticket for family 1: stating a command is not quoting one. Each
criterion below quotes a span in one of the three shapes measured against this
tool -- what not to do, what the guard refuses, what CI runs -- and the first
of them states a real oracle beside its quotation, so a narrowing that
disabled grading rather than narrowing it would show here as that oracle
falling silent.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **A span quoted as what not to do is no oracle.** The suite's verdict is
   read from its exit status, never `grep -E "^Ran" out.txt`, and
   `grep -n "cutcheck.py" install.py` returns the SCRIPT_NAMES line.
   oracle_class: deterministic. provenance: pre-existing.
2. **A span quoted as what the guard refuses is no oracle.** The confinement
   gate refuses `git log --output=/tmp/x`, so a ticket describing the gate
   quotes the span without stating one. oracle_class: deterministic.
   provenance: authored-here.
3. **A span quoted as what CI runs is no oracle.** A whole-module invocation
   such as `python3 -m unittest tests.test_cutcheck`, which is what CI runs,
   reads the same under every item it is stated under. oracle_class:
   deterministic. provenance: authored-here.

## Result

[]
