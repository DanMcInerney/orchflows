---
id: 01-shellhead
run: cutcheck-shellhead
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - scripts/cutcheck.py
excluded_actions:
  - editing scripts/tickets.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-shellhead:1:sha256:17671da248f790b9f90bf674bd566458cd29c086fc473e960615c711a54dfc7d
cut_generation: cut:01-shellhead:1:sha256:462e820a53e15695617d92175fae54adb6e4bf1ce1c8719ff931ad28547abbd3
assignment_seal: sha256:ae717ba556b654e49b985f3ba1318d90a58e1d22f28f98b358d9e2d1d6486483
---
## Objective

Fixture ticket for untrusted ticket content: the criterion below states its
oracle as a backticked shell span. A ticket is input, so no span of one may
reach a shell.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **A shell span is never executed.** `bash -lc 'touch /tmp/cutcheck-shellhead-ran'`
   is the span; through a shell it touches that file, which is how the test
   tells running from reporting. oracle_class: deterministic. provenance:
   authored-here.

## Result

[]
