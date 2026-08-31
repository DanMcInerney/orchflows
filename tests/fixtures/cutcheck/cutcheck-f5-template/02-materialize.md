---
id: 02-materialize
run: cutcheck-f5-template
status: pending
executor: orch-slice
pack: orch-code-pack
depends_on: [01-design]
bound: 20 tool calls
write_scope:
  - README.md
excluded_actions:
  - editing scripts/tickets.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:00-acquire:1:sha256:9651df3fa891fc2a64f5977e7204e2b7e5c5cc45472a54d590bbfa256be751f7
cut_generation: cut:00-acquire:1:sha256:7ef0be0d72b6e7daa6a598e55c414eb4fb73ae07553c7c6c71b687519e611697
assignment_seal: sha256:6685bf37394053eb1d2ee9a47f9744f02b996f9c7ffb3c95099ca15dad27c561
---
## Objective

The run's second cut, which has issued nothing yet and carries no map. Its
absent map is reported against this root by name, not against the run.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

- the readme names the install command | oracle: `grep -n "install.py" README.md` | oracle_class: deterministic | provenance: pre-existing

## Result

[]
