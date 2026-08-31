---
id: 00-acquire
run: cutcheck-f5-template
status: pending
executor: orch-slice
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
root_generation: root:00-acquire:1:sha256:9651df3fa891fc2a64f5977e7204e2b7e5c5cc45472a54d590bbfa256be751f7
cut_generation: cut:00-acquire:1:sha256:7ef0be0d72b6e7daa6a598e55c414eb4fb73ae07553c7c6c71b687519e611697
assignment_seal: sha256:d61a1879bb944776842b4878013577825d883bc0c01d04f3ce34f3dab75be5f9
---
## Objective

An instantiated template's first top-level stub, and one of this run's three
cuts. Its own subtree is `00-acquire.NN`; the stubs beside it are the
template's graph and belong to no root's decomposition.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

- `python install.py --dry-run` exits 0 | oracle: that command | oracle_class: deterministic | provenance: pre-existing

## Result

[]
