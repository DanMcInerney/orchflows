---
id: 01-design
run: cutcheck-f5-template
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: [00-acquire]
bound: 20 tool calls
write_scope:
  - docs/vocabulary.md
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

A top-level stub of the template, issued by no root. It is named by no root's
coverage map and is not an orphan for that.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

- the vocabulary carries the term | oracle: `grep -n "terminal ticket" docs/vocabulary.md` | oracle_class: deterministic | provenance: authored-here

## Result

[]
