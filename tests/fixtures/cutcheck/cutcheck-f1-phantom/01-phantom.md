---
id: 01-phantom
run: cutcheck-f1-phantom
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
root_generation: root:01-phantom:1:sha256:be8de52e3108b224cbb5507608db911b79d26d091f8beb119e37f079bb224069
cut_generation: cut:01-phantom:1:sha256:7331573c35e97e0cc857dddac72f983e451fb5b71f2fe941a26092e2090b2ba8
assignment_seal: sha256:d0915695955f2a07a956ce50a41630ed57029e511d8332a57deace7b50a423d7
---
## Objective

Fixture set for a criterion whose wrapped line opens with a digit and a period:
the wrap continues the criterion it is indented under, and opens no item of its
own.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **A criterion whose oracle discriminates.** `grep -n "cutcheck.py"
   install.py` returns the SCRIPT_NAMES line. oracle_class: deterministic.
   provenance: pre-existing.
2. **A criterion whose own wrap opens with a number.** The installer names
   every script it copies, and `grep -n "SCRIPT_NAMES" install.py` exits
   0. oracle_class: deterministic. provenance: pre-existing.
3. **A criterion after the wrap opens on its own.** `grep -n "friction.py"
   install.py` returns that same tuple line. oracle_class: deterministic.
   provenance: pre-existing.

## Result

[]
