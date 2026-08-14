---
id: 01-quotes
run: cutcheck-quote-precision
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - install.py
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture ticket for quotation precision: a quotation is text the ticket asserts
appears at the citation, and nothing else in the sentence around it is.

## Fixed inputs

- A citation and the symbol it points at: `install.py:1 SCRIPT_NAMES`.
- The module head at `install.py:1` opens with "a docstring that wraps
  across this line" and the word "it" refers to the file.
- The line at `install.py:1` reads "no line of this file reads this way",
  which the file does not carry.

## Completion test

1. **The installer still lists its scripts.** `grep -n "SCRIPT_NAMES"
   install.py` returns the tuple line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
