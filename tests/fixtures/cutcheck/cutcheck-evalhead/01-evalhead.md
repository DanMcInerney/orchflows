---
id: 01-evalhead
run: cutcheck-evalhead
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - scripts/cutcheck.py
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture ticket for untrusted ticket content: the criterion below states its
oracle as a backticked interpreter span whose argument is the program. An
interpreter head is a head an extractor accepts, and evaluating a ticket's own
text is what a shell head is refused for.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **An interpreter evaluating its argument is never executed.** `python3 -c
   "import pathlib;pathlib.Path('/tmp/cutcheck-evalhead-ran').touch()"` is the
   span; evaluated, it touches that file, which is how the test tells running
   from reporting. oracle_class: deterministic. provenance: authored-here.

## Result

[]
