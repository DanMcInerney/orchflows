---
id: 01-truncated
run: cutcheck-f1-truncated
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

Fixture set for a numbered completion list interrupted by prose: the criterion
after the interruption must stay visible, as an extraction gap at minimum.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **A criterion whose oracle discriminates.**
   `grep -n "cutcheck.py" install.py` returns the SCRIPT_NAMES line.
   oracle_class: deterministic. provenance: pre-existing.

An unindented prose line interrupts the numbered list here.

  2. **The criterion after the interruption.** A reviewer names, from the module
     docstring alone, every family cutcheck decides. oracle_class: judgment.
     provenance: authored-here.

## Result

[]
