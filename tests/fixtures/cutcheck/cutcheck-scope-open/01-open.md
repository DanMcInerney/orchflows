---
id: 01-open
run: cutcheck-scope-open
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - skills/engines/orch-compose
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-open:1:sha256:d39b4d5ef00ab804133cde8a2d57987cfba245d8d76462e526a8bc1d9bcbcb22
cut_generation: cut:01-open:1:sha256:f918beffafa55d179973e9bea48c1e310f69d0b7a6dc9996f98703d08ae29a58
assignment_seal: sha256:a3a4e0e9337950417a82018b7c4a37b26ebd4421d535bb5fc1454789b8e597db
---
## Objective

Fixture ticket for a cut that opens the tree: the item deletes the engine
skill directory `skills/engines/orch-compose` and renames the role profile
`orch-planner`. Neither the constant that holds the engine name nor the
fixture that holds the role name is inside the write scope above.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **Nothing in the tree still spells the two names.** A reviewer reads the
   tree and finds each name gone from every file that held it. oracle_class:
   judged. provenance: authored-here.

## Result

[]
