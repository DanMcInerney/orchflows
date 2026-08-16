---
id: 01-open
run: cutcheck-scope-open
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - skills/engines/orch-compose
---
## Objective

Fixture ticket for a cut that opens the tree: the item deletes the engine
skill directory `skills/engines/orch-compose` and renames the role profile
`orch-planner`. Neither the constant that holds the engine name nor the
fixture that holds the role name is inside the write scope above.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **Nothing in the tree still spells the two names.** A reviewer reads the
   tree and finds each name gone from every file that held it. oracle_class:
   judged. provenance: authored-here.

## Result

[]
