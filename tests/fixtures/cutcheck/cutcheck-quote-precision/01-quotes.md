---
id: 01-quotes
run: cutcheck-quote-precision
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
root_generation: root:01-quotes:1:sha256:2ce2829f63a5de5e9e9db29872593b583c3afc8e5a43dfff558a6e1521606753
cut_generation: cut:01-quotes:1:sha256:b159321381778f8723da0e27fa71754f261d15c8fdcb40c30bfd1ce3779f3bc4
assignment_seal: sha256:1981ec392e535ee4175b2943d97e4c6871ad21e366d11b28094c2ffdd57c031c
---
## Objective

Fixture ticket for quotation precision: a quotation is text the ticket asserts
appears at the citation, and nothing else in the sentence around it is.
A citation and the symbol it points at: `install.py:1 SCRIPT_NAMES`.
The module head at `install.py:1` opens with "a docstring that wraps
across this line" and the word "it" refers to the file.
The line at `install.py:1` reads "no line of this file reads this way",
which the file does not carry.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **The installer still lists its scripts.** `grep -n "SCRIPT_NAMES"
   install.py` returns the tuple line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
