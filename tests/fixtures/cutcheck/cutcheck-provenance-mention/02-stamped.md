---
id: 02-stamped
run: cutcheck-provenance-mention
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: [01-mentioned]
bound: 20 tool calls
write_scope:
  - docs/vocabulary.md
excluded_actions:
  - editing scripts/tickets.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-mentioned:1:sha256:f2f0707eac480ab7ee7b5014c925f47d9ac28bc820ff86bedb2320fa8a5f8797
cut_generation: cut:01-mentioned:1:sha256:5262d4401c141689028c0eab4bec44769bd8ebf240f74167507f0c52ff32351d
assignment_seal: sha256:9bb586e298d8be36438e6fd0f0cefe90a27a5bfe02b2d9b7e7149fff7d3246fc
---
## Objective

Fixture ticket for the paired positive: the same oracle under a stamp the
criterion makes is the invariant the stamp says it is, and stays exempt.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **A stamp made rather than mentioned.** `grep -n "SCRIPT_NAMES" install.py`
   returns the tuple line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
