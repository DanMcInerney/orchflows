---
id: 02-carried
run: cutcheck-scope-open
status: issued
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
---
## Objective

The same removal with the pins carried: the item deletes the engine skill
directory `skills/engines/orch-compose` and renames the role profile
`orch-planner`. Every file that pins either name is inside the write scope
above, so the cut closes over what it takes away.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **Nothing in the tree still spells the two names.** A reviewer reads the
   tree and finds each name gone from every file that held it. oracle_class:
   judged. provenance: authored-here.

## Result

[]
