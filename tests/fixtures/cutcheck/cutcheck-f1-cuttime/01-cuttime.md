---
id: 01-cuttime
run: cutcheck-f1-cuttime
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
root_generation: root:01-cuttime:1:sha256:3e8769679150c6b4d6d6556d75176d4eb9f203c49fb247fac9c5ab6e4981a944
cut_generation: cut:01-cuttime:1:sha256:78641d8701854254d1bb0048aced46f46137abf1c07214b2e4dfb173336936d8
assignment_seal: sha256:da51428e924f7e9004b4120cca69eb62ee59cd132a5565d8fec1a1fdef29a893
---
## Objective

Fixture set for cut time: one oracle that discriminates correctly for work that
has not landed, so it matches nothing in the tree it is cut from.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **The token the work will add.**
   `grep -rn "zzqq-cuttime-token" install.py` returns at least one line.
   oracle_class: deterministic. provenance: authored-here.

## Result

[]
