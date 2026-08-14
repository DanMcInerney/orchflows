---
id: 01-shape
run: cutcheck-f1-shape
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - install.py
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture set for family 1 shape: one oracle whose exit status is swallowed by a
pipeline, and one per-item scope check written against a cumulative range.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **The suite still passes.**
   `python3 -m unittest discover -s tests | tail -5` ends OK. oracle_class:
   deterministic. provenance: pre-existing.
2. **Nothing outside this item's scope changed.**
   `git diff --name-only ac8791a..HEAD` lists only this item's paths.
   oracle_class: deterministic. provenance: pre-existing.

## Result

[]
