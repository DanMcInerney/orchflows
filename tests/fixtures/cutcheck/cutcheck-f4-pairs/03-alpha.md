---
id: 03-alpha
run: cutcheck-f4-pairs
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - scripts/cutcheck.py
excluded_actions:
  - editing scripts/tickets.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-reader:1:sha256:3cc15c0565a48ad15676b9fcf0d353443407f22de85ef04d55d867aba880efab
cut_generation: cut:01-reader:1:sha256:2d70cc95218a9e707754ec4b36335836c38bac332dfe26d6ed80ae4b8b487ca4
assignment_seal: sha256:f3dccd08632fb95d15ee89e22d88fb3418df2f0b5ef02a8adac28048f9c4eba0
---
## Objective

Fixture item for pairwise safety: this item and `04-beta` hold the same scope with no edge between them.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **The shared scope is the whole defect.** The two scopes intersect, which
   the report names without running anything. oracle_class: deterministic.
   provenance: authored-here.

## Result

[]
