---
id: 02-materialize
run: cutcheck-f5-template
status: issued
executor: orch-decompose
pack: orch-code-pack
depends_on: [01-design]
bound: 20 tool calls
write_scope:
  - README.md
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

The run's second cut, which has issued nothing yet and carries no map. Its
absent map is reported against this root by name, not against the run.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

- the readme names the install command | oracle: `grep -n "install.py" README.md` | oracle_class: deterministic | provenance: pre-existing

## Result

[]
