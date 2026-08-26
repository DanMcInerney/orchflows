---
id: 01-reader
run: cutcheck-f4-ordered
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - tests/test_cutcheck.py
excluded_actions:
  - editing scripts/tickets.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-reader:1:sha256:09412c869a32ae3bee37583087fece57fe050c8a57f89943390d0d21c908c6ab
cut_generation: cut:01-reader:1:sha256:3ec656bddcefe42612362be918d0bb3755cdd1f39c5195899c3f2fc38b0126b8
assignment_seal: sha256:afd2629d9a6207a088110a5cb887478b9a06cb068eb2fd9d513d2a8cd1f83dcc
---
## Objective

Fixture item for pairwise safety: its oracle reads `install.py`, a path the sibling item `02-rewriter` alone may change. The edge below orders them, so the pair is no defect.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **The installer lists the script.** `grep -n "cutcheck.py" install.py`
   returns the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
