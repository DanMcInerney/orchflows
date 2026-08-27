---
id: 01-evalhead
run: cutcheck-evalhead
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
root_generation: root:01-evalhead:1:sha256:29ffd0506dec525878f51cc1ece3a00569f81ac7942525489141045ee1f5111b
cut_generation: cut:01-evalhead:1:sha256:624397718ae2a0df1c872a88001560cd326217e2deaf3c6e35328ffe619c04f0
assignment_seal: sha256:e4f2e7596dbab58ab99492ab88dd887209eaa3966372c03249d7a1216ef875ed
---
## Objective

Fixture ticket for untrusted ticket content: the criterion below states its
oracle as a backticked interpreter span whose argument is the program. An
interpreter head is a head an extractor accepts, and evaluating a ticket's own
text is what a shell head is refused for.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **An interpreter evaluating its argument is never executed.** `python3 -c
   "import pathlib;pathlib.Path('/tmp/cutcheck-evalhead-ran').touch()"` is the
   span; evaluated, it touches that file, which is how the test tells running
   from reporting. oracle_class: deterministic. provenance: authored-here.

## Result

[]
