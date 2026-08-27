---
id: 05-epsilon
run: cutcheck-graph
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on:
  - 04-delta
  - 02-beta
bound: 20 tool calls
write_scope:
  - AGENTS.md
excluded_actions:
  - editing scripts/tickets.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-alpha:1:sha256:f9ef9281cc7785d56e804d0887c9dcbf434193fedf97166ff55390475f79fd10
cut_generation: cut:01-alpha:1:sha256:afea98ae440c5321ca92804593595b5c398ccb04ae3bd5ea94e7e81407832aec
assignment_seal: sha256:e988f4bda31241762692b24ca5bae1b5428a642b5b5126c3257783d8d761a5a9
---
## Objective

Fixture set for the shape reading: two items stand behind this one, one on each
of the levels below, so the greater of them decides the level and the chain.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **Installed under its bare name.** `grep -n "cutcheck.py" install.py` returns
   the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
