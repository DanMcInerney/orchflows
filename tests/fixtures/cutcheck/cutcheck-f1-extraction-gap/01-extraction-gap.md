---
id: 01-extraction-gap
run: cutcheck-f1-extraction-gap
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

Fixture set for the extraction gap: a sole completion criterion stated in prose
that no extractor recognizes, so under-coverage is reported rather than read as
a fully checked set. The gap never sets the exit status.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **The boundary reads clearly to a first reader.** A reviewer who has not seen
   this ticket can name, from the module docstring alone, which defects family 1
   reports and which it only notes. oracle_class: judgment. provenance:
   authored-here.

## Result

[]
