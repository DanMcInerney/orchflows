---
id: 01-alpha
run: cutcheck-graph
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - docs/vocabulary.md
excluded_actions:
  - editing scripts/tickets.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-alpha:1:sha256:f9ef9281cc7785d56e804d0887c9dcbf434193fedf97166ff55390475f79fd10
cut_generation: cut:01-alpha:1:sha256:afea98ae440c5321ca92804593595b5c398ccb04ae3bd5ea94e7e81407832aec
assignment_seal: sha256:4f50b5ed08eaeec47fd7a9436a7c4ed8e4ea62606dfa9351b2baba85bec2b850
---
## Objective

Fixture set for the shape reading: this item depends on nothing in the set, so
it sits on the first level, and the chain the reading names starts here.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **Installed under its bare name.** `grep -n "cutcheck.py" install.py` returns
   the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
