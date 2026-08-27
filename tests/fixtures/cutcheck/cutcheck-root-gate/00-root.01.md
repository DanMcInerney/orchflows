---
id: 00-root.01
run: cutcheck-root-gate
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
root_generation: root:00-root:1:sha256:da7c8359bf9ef3ab73b37663ba424dedb450d3fe3ed5461568de8607d62c6aac
cut_generation: cut:00-root:1:sha256:27b8ef3c56be7957567ab6c334da59d9138635200308a45d304ffe7db15f80be
assignment_seal: sha256:67fedf50dea36ffd81c93365e471f5bd6c2416be0a1e50d77a1634ce786b218b
---
## Objective

The one unit ticket of this root's subtree: the installer names every script
it copies.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

- the installer's script list names the cutter | oracle: `grep -n "cutcheck.py" install.py` | oracle_class: deterministic | provenance: authored-here

## Result

[]
