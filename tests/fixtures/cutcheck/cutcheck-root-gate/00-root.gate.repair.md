---
id: 00-root.gate.repair
run: cutcheck-root-gate
status: pending
executor: orch-repair
pack: orch-code-pack
depends_on: [00-root.gate.critique.code]
bound: 60m
write_scope:
  - install.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:00-root:1:sha256:da7c8359bf9ef3ab73b37663ba424dedb450d3fe3ed5461568de8607d62c6aac
cut_generation: cut:00-root:1:sha256:27b8ef3c56be7957567ab6c334da59d9138635200308a45d304ffe7db15f80be
assignment_seal: sha256:fdba625350644b800c82949b908c98258075453adaad2c0e09f15bfcf901dd10
---
## Objective

Every accepted blocking finding against `00-root` is repaired inside this
ticket's own write scope, or declined with a stated reason; every accepted
non-blocking finding is queued as candidate scope per verification §9, and
nothing outside that scope changes.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}
- input: {"name":"fixture-context","type":"literal","value":"- the `## Result` of each critique stub of `00-root`, by identity\n- write scope:\n  - `install.py`"}

## Completion test

- every accepted blocking finding is repaired or declined with a stated reason, and every accepted non-blocking finding is queued as candidate scope | oracle: the critique tickets' findings against this ticket's `## Result` | oracle_class: deterministic | provenance: pre-existing
- nothing outside the write scope changed | oracle: `git status --porcelain` in the run's workspace | oracle_class: deterministic | provenance: pre-existing

## Result

[]
