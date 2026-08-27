---
id: 01-mentioned
run: cutcheck-provenance-mention
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
root_generation: root:01-mentioned:1:sha256:f2f0707eac480ab7ee7b5014c925f47d9ac28bc820ff86bedb2320fa8a5f8797
cut_generation: cut:01-mentioned:1:sha256:5262d4401c141689028c0eab4bec44769bd8ebf240f74167507f0c52ff32351d
assignment_seal: sha256:078718c2dcc6952e9e5ff257e5cc468448b3a10c500599bf76463d854cf052b0
---
## Objective

Fixture ticket for a mention of the provenance stamp rather than a stamp: a
criterion that quotes the phrase, and one that denies carrying it, are graded
exactly as they would be with the phrase absent.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **A quoted mention is discussion.** `grep -n "SCRIPT_NAMES" install.py`
   returns the tuple line, and the stamp this criterion quotes,
   `provenance: pre-existing`, is the one it talks about rather than one it
   makes. oracle_class: deterministic. provenance: authored-here.
2. **A denied mention is discussion too.** `grep -n "friction.py" install.py`
   returns that same line, and the stamp this criterion does not carry is
   provenance: pre-existing. oracle_class: deterministic. provenance:
   authored-here.

## Result

[]
