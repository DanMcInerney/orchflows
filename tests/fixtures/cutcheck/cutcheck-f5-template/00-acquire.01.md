---
id: 00-acquire.01
run: cutcheck-f5-template
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
root_generation: root:00-acquire:1:sha256:9651df3fa891fc2a64f5977e7204e2b7e5c5cc45472a54d590bbfa256be751f7
cut_generation: cut:00-acquire:1:sha256:7ef0be0d72b6e7daa6a598e55c414eb4fb73ae07553c7c6c71b687519e611697
assignment_seal: sha256:b66a89ae80d77991a92264bc4aaacaae9a07a7c38f9f00ecd402c44d6f34f840
---
## Objective

The one unit of the first cut's subtree, and the only id its map may name.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

- the installer's script list names the cutter | oracle: `grep -n "cutcheck.py" install.py` | oracle_class: deterministic | provenance: authored-here

## Result

[]
