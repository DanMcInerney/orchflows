---
id: 00-root
run: cutcheck-root-gate
status: pending
executor: orch-decompose
pack: orch-code-pack
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
assignment_seal: sha256:e2eda0a8434d4fba11fbdc75de3c11bd5e7ab17a779050c28070231e407b46e8
---
## Objective

Fixture root ticket in the layout the work-item contract states: a root, one
`<root>.NN` unit, and the three gate stubs the gate step adds. The set is
honest, so the cut's own verdict is repeatable over it -- before the gate step
and again after it.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

- `python install.py --dry-run` exits 0 | oracle: that command | oracle_class: deterministic | provenance: pre-existing

## Result

[]
