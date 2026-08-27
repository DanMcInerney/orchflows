---
id: 02-carried
run: cutcheck-scope-open
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on:
  - 01-open
bound: 20 tool calls
write_scope:
  - skills/engines/orch-compose
  - scripts/tickets.py
  - tests/test_contracts.py
  - tests/test_roles.py
  - tests/test_installer.py
  - tests/test_live_profiles.py
  - tests/fixtures/transcripts
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-open:1:sha256:d39b4d5ef00ab804133cde8a2d57987cfba245d8d76462e526a8bc1d9bcbcb22
cut_generation: cut:01-open:1:sha256:f918beffafa55d179973e9bea48c1e310f69d0b7a6dc9996f98703d08ae29a58
assignment_seal: sha256:2e1552b0ea2d8a6a93f662220f8f6f1b2e68848208a76b3cbf70bc1182ad9511
---
## Objective

The same removal with the pins carried: the item deletes the engine skill
directory `skills/engines/orch-compose` and renames the role profile
`orch-planner`. Every file that pins either name is inside the write scope
above, so the cut closes over what it takes away.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **Nothing in the tree still spells the two names.** A reviewer reads the
   tree and finds each name gone from every file that held it. oracle_class:
   judged. provenance: authored-here.

## Result

[]
