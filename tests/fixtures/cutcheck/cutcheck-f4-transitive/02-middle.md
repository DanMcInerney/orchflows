---
id: 02-middle
run: cutcheck-f4-transitive
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: [01-first]
bound: 20 tool calls
write_scope:
  - install.py
excluded_actions:
  - editing scripts/tickets.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-first:1:sha256:4f79c1364c06f871141f8725975b5e1e4abaadb2c9c4116f1a9cbaa0f6c78fec
cut_generation: cut:01-first:1:sha256:8042fe5c2fd7275fd66468e66fd7f35bd399ab250b5bba2f2bde9177b3918a8f
assignment_seal: sha256:1d3850fdcf7f6bb6bc16e3ca5c66ae7538621c35426b8d6a36f0580a9dff7a1c
---
## Objective

Fixture item for pairwise safety: the middle of the chain, depending on `01-first` and depended on by `03-third`.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **The installer lists the script.** `grep -n "cutcheck.py" install.py`
   returns the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
