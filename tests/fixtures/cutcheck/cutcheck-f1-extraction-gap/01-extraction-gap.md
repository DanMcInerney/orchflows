---
id: 01-extraction-gap
run: cutcheck-f1-extraction-gap
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
root_generation: root:01-extraction-gap:1:sha256:6edf30765da7b36200bf717b61febba152e313a8473922f380b08b36ca2e378a
cut_generation: cut:01-extraction-gap:1:sha256:14c31190250f02534401c2f921e703ec47a2eb014a501491ccfc5b85eaf2f417
assignment_seal: sha256:d11e611db1b954187b240bcaf2ca7c9ee84cf6bc6b1931cfb191577ea37d02a3
---
## Objective

Fixture set for the extraction gap: a sole completion criterion stated in prose
that no extractor recognizes, so under-coverage is reported rather than read as
a fully checked set. The gap never sets the exit status.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **The boundary reads clearly to a first reader.** A reviewer who has not seen
   this ticket can name, from the module docstring alone, which defects family 1
   reports and which it only notes. oracle_class: judgment. provenance:
   authored-here.

## Result

[]
