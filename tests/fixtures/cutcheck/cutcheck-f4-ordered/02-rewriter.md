---
id: 02-rewriter
run: cutcheck-f4-ordered
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: [01-reader]
bound: 20 tool calls
write_scope:
  - install.py
excluded_actions:
  - editing scripts/tickets.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-reader:1:sha256:09412c869a32ae3bee37583087fece57fe050c8a57f89943390d0d21c908c6ab
cut_generation: cut:01-reader:1:sha256:3ec656bddcefe42612362be918d0bb3755cdd1f39c5195899c3f2fc38b0126b8
assignment_seal: sha256:2ad0df8570a0bb79b7ce5fc40fab3ac0d3a7173537aed60d4123de4c09c5e2f4
---
## Objective

Fixture item for pairwise safety: `install.py` is this item's whole scope, and the oracle of item `01-reader` reads it. This item depends on that one, so the pair is ordered.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **The installer lists the script.** `grep -n "cutcheck.py" install.py`
   returns the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
