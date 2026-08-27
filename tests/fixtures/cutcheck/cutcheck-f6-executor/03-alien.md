---
id: 03-alien
run: cutcheck-f6-executor
status: pending
executor: orch-render
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - AGENTS.md
excluded_actions:
  - editing scripts/tickets.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:02-legal:1:sha256:cabccf1eb80b22fa0fcf12c7dcfc2904e07e3cfa57156ea4eefbfea515dfc27a
cut_generation: cut:02-legal:1:sha256:ea9e9d817e6d903fea9afa2d82d5eb0ff55bf8fce4d158106674d03176b49758
assignment_seal: sha256:796afce215c3b3652bd43f5004f66dad162fa04e93d45a39f5f8ba48c3c60edd
---
## Objective

Fixture item for executor legality: its executor is no engine, and no cell of the stamped pack names it either.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **The installer lists the script.** `grep -n "cutcheck.py" install.py`
   returns the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
