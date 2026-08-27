---
id: 00-root.gate.verify
run: cutcheck-root-gate
status: pending
executor: orch-verify
pack: orch-code-pack
depends_on: [00-root.gate.repair]
bound: 60m
write_scope: []
admission: pending
mutations: []
ownership_regions: []
root_generation: root:00-root:1:sha256:da7c8359bf9ef3ab73b37663ba424dedb450d3fe3ed5461568de8607d62c6aac
cut_generation: cut:00-root:1:sha256:27b8ef3c56be7957567ab6c334da59d9138635200308a45d304ffe7db15f80be
assignment_seal: sha256:f561f9ccdc2396abf4e6cacbc2a407c35172495210bfef7306638bad34178a86
---
## Objective

`00-root`'s acceptance is decided at the revision `00-root.gate.repair` left:
one verdict per criterion, from the oracle that criterion names.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}
- input: {"name":"fixture-context","type":"literal","value":"- `00-root`'s `## Completion test`, the criteria this ticket decides, carried verbatim below\n- the revision `00-root.gate.repair` left"}

## Completion test

- `python install.py --dry-run` exits 0 | oracle: that command | oracle_class: deterministic | provenance: pre-existing

## Result

[]
