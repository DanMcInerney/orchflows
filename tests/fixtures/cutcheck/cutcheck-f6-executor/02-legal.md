---
id: 02-legal
run: cutcheck-f6-executor
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - ARCHITECTURE.md
excluded_actions:
  - editing scripts/tickets.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:02-legal:1:sha256:cabccf1eb80b22fa0fcf12c7dcfc2904e07e3cfa57156ea4eefbfea515dfc27a
cut_generation: cut:02-legal:1:sha256:ea9e9d817e6d903fea9afa2d82d5eb0ff55bf8fce4d158106674d03176b49758
assignment_seal: sha256:4d3c46c0f200644773601c82e663d45bc5931df88e6b70e705903056d54e2554
---
## Objective

Fixture item for executor legality: its executor is the stamped pack's own executor cell, so nothing is reported for it.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **The installer lists the script.** `grep -n "cutcheck.py" install.py`
   returns the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
