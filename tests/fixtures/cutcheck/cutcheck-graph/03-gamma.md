---
id: 03-gamma
run: cutcheck-graph
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - packs/orch-code-pack/SKILL.md
excluded_actions:
  - editing scripts/tickets.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-alpha:1:sha256:f9ef9281cc7785d56e804d0887c9dcbf434193fedf97166ff55390475f79fd10
cut_generation: cut:01-alpha:1:sha256:afea98ae440c5321ca92804593595b5c398ccb04ae3bd5ea94e7e81407832aec
assignment_seal: sha256:ef9f54d204d60be81d08fbe8dfffaa37ff8fe5ab5070c45c2e9ac14b7c2a2e0c
---
## Objective

Fixture set for the shape reading: a third item on the first level, on no
chain at all, so the first level's width is three where the chain is one.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **Installed under its bare name.** `grep -n "cutcheck.py" install.py` returns
   the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
