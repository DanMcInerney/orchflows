---
id: 01-mention
run: cutcheck-mention
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
root_generation: root:01-mention:1:sha256:e540258a7c702d22a9587dfa10a5ec116a5e66598a1d0967e656d4c77dbd9698
cut_generation: cut:01-mention:1:sha256:78484b1e5399507b5fbed66ed4b65ba4487826ab1f54cb3956fde3b5af82ef5a
assignment_seal: sha256:69f7b73319aa20b7a5768bc903cd3bad498e9ac6e28786a623a5c0f537926bbf
---
## Objective

Fixture ticket for scope closure: naming a path is not writing to it. The item
writes its verdict to `.orch/evidence/mention/verdict.txt`, an evidence sink
this grant does not name. The map a real run keeps is written to
`.orch/runs/<run>/coverage.md` by the decomposer, never by this item. This item
never writes `scripts/cutcheck.py`, which item 03 finished. The path stays
outside this write scope (`rules/topology.md` states that observing is not
naming).

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **The installer still lists its scripts.** `grep -n "SCRIPT_NAMES"
   install.py` returns the tuple line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
