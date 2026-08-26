---
id: 01-pre-existing
run: cutcheck-provenance
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - install.py
excluded_actions:
  - editing scripts/tickets.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-pre-existing:1:sha256:46447722b3db35a0defb7451fd0414c52484a1f5ba6baa98067eb1998742202b
cut_generation: cut:01-pre-existing:1:sha256:9408cbd3ae1257bdb417fc2c3b4c89c42bc6196d1016fbe95248374ed746b68a
assignment_seal: sha256:ce4d2cd07baec449220db81eefcf360a6b2a063e71f45502c135b4140d11c343
---
## Objective

Fixture ticket for provenance: an invariant is stated as an oracle that passes
at the baseline and keeps passing, and a pre-existing stamp exempts it from
discrimination alone.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

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
