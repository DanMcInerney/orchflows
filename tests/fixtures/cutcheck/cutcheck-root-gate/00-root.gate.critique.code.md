---
id: 00-root.gate.critique.code
run: cutcheck-root-gate
status: pending
executor: orch-critique
pack: orch-code-pack
depends_on: [00-root.01]
bound: 60m
write_scope: []
admission: pending
mutations: []
ownership_regions: []
root_generation: root:00-root:1:sha256:da7c8359bf9ef3ab73b37663ba424dedb450d3fe3ed5461568de8607d62c6aac
cut_generation: cut:00-root:1:sha256:27b8ef3c56be7957567ab6c334da59d9138635200308a45d304ffe7db15f80be
assignment_seal: sha256:26ea590ec670c238ed25c342be93843a16f1d97d58d7dbe9f87e2591f7e57ef2
---
## Objective

Every defect in `00-root`'s delivered result that the `code` lens finds is
reported by identity with its evidence: an open search over what the subtree
produced, not a re-run of the criteria it already states.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}
- input: {"name":"fixture-context","type":"literal","value":"- lens: `code`\n- the `## Result` of each of the following, by identity:\n  - `00-root.01`\n- `00-root`'s `## Completion test`, the acceptance this gate closes over:\n\n- `python install.py --dry-run` exits 0 | oracle: that command | oracle_class: deterministic | provenance: pre-existing"}

## Completion test

- every finding names the artifact identity it was found at and the evidence that shows it | oracle: this ticket's `## Result` read under the `code` lens | oracle_class: judged | provenance: authored-here
- every `## Result` named in the fixed inputs was read | oracle: this ticket's `## Result` against that list | oracle_class: deterministic | provenance: authored-here

## Result

[]
