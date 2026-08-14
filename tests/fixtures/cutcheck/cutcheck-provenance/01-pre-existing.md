---
id: 01-pre-existing
run: cutcheck-provenance
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

Fixture ticket for provenance: an invariant is stated as an oracle that passes
at the baseline and keeps passing, and a pre-existing stamp exempts it from
discrimination alone.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **The installer still lists its scripts.** `grep -n "SCRIPT_NAMES"
   install.py` returns the tuple line. oracle_class: deterministic. provenance:
   pre-existing.
2. **Shape is judged whatever the provenance.** `python3 -m unittest discover -s
   tests | tail -5` reports OK. oracle_class: deterministic. provenance:
   pre-existing.
3. **An undecidable oracle is told whatever the provenance.** `grep -c
   "SCRIPT_NAMES" install.py` reports 1, which its exit status does not carry.
   oracle_class: deterministic. provenance: pre-existing.

## Result

[]
