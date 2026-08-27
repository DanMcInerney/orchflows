---
id: 01-design
run: cutcheck-f5-template
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: [00-acquire]
bound: 20 tool calls
write_scope:
  - docs/vocabulary.md
excluded_actions:
  - editing scripts/tickets.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:00-acquire:1:sha256:9651df3fa891fc2a64f5977e7204e2b7e5c5cc45472a54d590bbfa256be751f7
cut_generation: cut:00-acquire:1:sha256:7ef0be0d72b6e7daa6a598e55c414eb4fb73ae07553c7c6c71b687519e611697
assignment_seal: sha256:712de92eba690aabd4f3423655cfdfbb9570d2d6372a936952786e9d1c90124c
---
## Objective

A top-level stub of the template, issued by no root. It is named by no root's
coverage map and is not an orphan for that.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

- the vocabulary carries the term | oracle: `grep -n "terminal ticket" docs/vocabulary.md` | oracle_class: deterministic | provenance: authored-here

## Result

[]
