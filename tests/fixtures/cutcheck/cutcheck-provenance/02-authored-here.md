---
id: 02-authored-here
run: cutcheck-provenance
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: [01-pre-existing]
bound: 20 tool calls
write_scope:
  - docs/vocabulary.md
excluded_actions:
  - editing scripts/tickets.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-pre-existing:1:sha256:46447722b3db35a0defb7451fd0414c52484a1f5ba6baa98067eb1998742202b
cut_generation: cut:01-pre-existing:1:sha256:9408cbd3ae1257bdb417fc2c3b4c89c42bc6196d1016fbe95248374ed746b68a
assignment_seal: sha256:ef139bd76b839bb8c312dbce8de56977048e21c7256c5cf6296ba28c9d86aa0c
---
## Objective

Fixture ticket for provenance: the same oracle, stamped as authored here, still
has to discriminate.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **An oracle this item authored.** `grep -n "SCRIPT_NAMES" install.py`
   returns the tuple line. oracle_class: deterministic. provenance:
   authored-here.

## Result

[]
