---
id: 00-root.gate.repair
run: cutcheck-root-gate
status: issued
executor: orch-repair
pack: orch-code-pack
depends_on: [00-root.gate.critique.code]
bound: 60m
write_scope:
  - install.py
---
## Objective

Every accepted finding against `00-root` is repaired inside this ticket's own
write scope, or declined with a stated reason; nothing outside that scope
changes.

## Fixed inputs

- the `## Result` of each critique stub of `00-root`, by identity
- write scope:
  - `install.py`

## Completion test

- every accepted finding is repaired or declined with a stated reason | oracle: the critique tickets' findings against this ticket's `## Result` | oracle_class: deterministic | provenance: authored-here
- nothing outside the write scope changed | oracle: `git status --porcelain` in the run's workspace | oracle_class: deterministic | provenance: pre-existing

## Result

[]
