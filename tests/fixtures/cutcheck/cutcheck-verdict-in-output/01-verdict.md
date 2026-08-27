---
id: 01-verdict
run: cutcheck-verdict-in-output
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
root_generation: root:01-verdict:1:sha256:f2d1f9521e05e75a062eb75f3116ccc0c0f633e5633ee079a34a5515e5f96acc
cut_generation: cut:01-verdict:1:sha256:02e2a94c0f42320aab9065c88ad9d6fc3dbc0e891f2abce64b5ba537d6991aac
assignment_seal: sha256:b5186cb074f122874b5ccdf87ce097166c6eb1940500e0b6a2b7d43292b63a85
---
## Objective

Fixture ticket for commands whose verdict is in what they print: a text count
and a revision count both exit 0 whatever they counted.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **A count is read, not exited on.** `grep -c "SCRIPT_NAMES" install.py`
   reports 0. oracle_class: deterministic. provenance: authored-here.
2. **A revision count is printed, not exited on.** `git rev-list --count HEAD`
   reports 0. oracle_class: deterministic. provenance: authored-here.

## Result

[]
