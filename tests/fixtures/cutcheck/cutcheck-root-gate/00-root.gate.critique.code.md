---
id: 00-root.gate.critique.code
run: cutcheck-root-gate
status: issued
executor: orch-critique
pack: orch-code-pack
depends_on: [00-root.01]
bound: 60m
write_scope: []
---
## Objective

Every defect in `00-root`'s delivered result that the `code` lens finds is
reported by identity and severity: an open search over what the subtree
produced, not a re-run of the criteria it already states.

## Fixed inputs

- lens: `code`
- the `## Result` of each of the following, by identity:
  - `00-root.01`
- `00-root`'s `## Completion test`, the acceptance this gate closes over:

- `python install.py --dry-run` exits 0 | oracle: that command | oracle_class: deterministic | provenance: pre-existing

## Completion test

- every finding names the artifact identity it was found at and the evidence that shows it | oracle: this ticket's `## Result` read under the `code` lens | oracle_class: judged | provenance: authored-here
- every `## Result` named in the fixed inputs was read | oracle: this ticket's `## Result` against that list | oracle_class: deterministic | provenance: authored-here

## Result

[]
