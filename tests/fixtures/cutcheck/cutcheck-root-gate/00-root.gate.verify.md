---
id: 00-root.gate.verify
run: cutcheck-root-gate
status: issued
executor: orch-verify
pack: orch-code-pack
depends_on: [00-root.gate.repair]
bound: 60m
write_scope: []
---
## Objective

`00-root`'s acceptance is decided at the revision `00-root.gate.repair` left:
one verdict per criterion, from the oracle that criterion names.

## Fixed inputs

- `00-root`'s `## Completion test`, the criteria this ticket decides, carried verbatim below
- the revision `00-root.gate.repair` left

## Completion test

- `python install.py --dry-run` exits 0 | oracle: that command | oracle_class: deterministic | provenance: pre-existing

## Result

[]
