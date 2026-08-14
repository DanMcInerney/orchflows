---
id: 01-mentioned
run: cutcheck-provenance-mention
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

Fixture ticket for a mention of the provenance stamp rather than a stamp: a
criterion that quotes the phrase, and one that denies carrying it, are graded
exactly as they would be with the phrase absent.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **A quoted mention is discussion.** `grep -n "SCRIPT_NAMES" install.py`
   returns the tuple line, and the stamp this criterion quotes,
   `provenance: pre-existing`, is the one it talks about rather than one it
   makes. oracle_class: deterministic. provenance: authored-here.
2. **A denied mention is discussion too.** `grep -n "friction.py" install.py`
   returns that same line, and the stamp this criterion does not carry is
   provenance: pre-existing. oracle_class: deterministic. provenance:
   authored-here.

## Result

[]
