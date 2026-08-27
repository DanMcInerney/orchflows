---
id: 01-truncated
run: cutcheck-f1-truncated
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - install.py
excluded_actions:
  - editing scripts/tickets.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-truncated:1:sha256:f3a10a0b63c9276ffd74cece704b19b0b0ea38ee12ad042c1a89fc639cb7115c
cut_generation: cut:01-truncated:1:sha256:899df67686a769502161ab2d1bef9bc505c935d3deb982994cc316bc5d304b6d
assignment_seal: sha256:84d74b815bfac37c3f8caea3cbb6cbcd23c1f31efddf7b5e784e7c8fc90eebd9
---
## Objective

Fixture set for a numbered completion list interrupted by prose: the criterion
after the interruption must stay visible, as an extraction gap at minimum.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **A criterion whose oracle discriminates.**
   `grep -n "cutcheck.py" install.py` returns the SCRIPT_NAMES line.
   oracle_class: deterministic. provenance: pre-existing.

An unindented prose line interrupts the numbered list here.

  2. **The criterion after the interruption.** A reviewer names, from the module
     docstring alone, every family cutcheck decides. oracle_class: judgment.
     provenance: authored-here.

## Result

[]
