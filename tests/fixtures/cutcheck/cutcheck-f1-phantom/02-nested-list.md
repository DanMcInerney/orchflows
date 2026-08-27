---
id: 02-nested-list
run: cutcheck-f1-phantom
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: [01-phantom]
bound: 20 tool calls
write_scope:
  - docs/vocabulary.md
excluded_actions:
  - editing scripts/tickets.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-phantom:1:sha256:be8de52e3108b224cbb5507608db911b79d26d091f8beb119e37f079bb224069
cut_generation: cut:01-phantom:1:sha256:7331573c35e97e0cc857dddac72f983e451fb5b71f2fe941a26092e2090b2ba8
assignment_seal: sha256:c5dd94d4fa91c49cbbffee53952a954de8965237126404d736dcb0f5a0d2b5b7
---
## Objective

Fixture ticket for the control the wrap rule must not break: a numbered list
nested under a criterion is that criterion's own text, and the criterion after
the list still opens.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **A criterion holding a nested enumeration.** `grep -n "SCRIPT_NAMES"
   install.py` returns the tuple line, which carries
   1. the tuple the installer opens, and
   2. every script name it lists.
   oracle_class: deterministic. provenance: pre-existing.
2. **The criterion after the nested list opens on its own.** `grep -n
   "friction.py" install.py` returns that same line. oracle_class:
   deterministic. provenance: pre-existing.

## Result

[]
