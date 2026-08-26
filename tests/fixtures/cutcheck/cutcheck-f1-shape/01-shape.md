---
id: 01-shape
run: cutcheck-f1-shape
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
root_generation: root:01-shape:1:sha256:dea3553de9c77b535c31b31c1988aa6a6ece42252ec5474168b93203d48dc151
cut_generation: cut:01-shape:1:sha256:d1759fae287729d2b90c5a9e21d39ce7e3ba1de9ca0fd78c5b0e8121c480928b
assignment_seal: sha256:62c806746f3c734967764f478dd4cd3636d138251903f7e3c0de9e78bd15e3d2
---
## Objective

Fixture set for family 1 shape: one oracle whose exit status is swallowed by a
pipeline, and one per-item scope check written against a cumulative range.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **The suite still passes.**
   `python3 -m unittest discover -s tests | tail -5` ends OK. oracle_class:
   deterministic. provenance: pre-existing.
2. **Nothing outside this item's scope changed.**
   `git diff --name-only ac8791a..HEAD` lists only this item's paths.
   oracle_class: deterministic. provenance: pre-existing.

## Result

[]
