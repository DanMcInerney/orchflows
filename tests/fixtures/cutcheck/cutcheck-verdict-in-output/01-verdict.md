---
id: 01-verdict
run: cutcheck-verdict-in-output
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

Fixture ticket for commands whose verdict is in what they print: a count, an
archive, and a two-argument diff all exit 0 whatever they find.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **A count is read, not exited on.** `grep -c "SCRIPT_NAMES" install.py`
   reports 0. oracle_class: deterministic. provenance: authored-here.
2. **An archive exits 0 whenever it can archive.** `git archive ac8791a` is
   byte-identical to the baseline tree. oracle_class: deterministic.
   provenance: authored-here.
3. **A two-argument diff exits 0 almost always.** `git diff ac8791a --
   install.py` is empty. oracle_class: deterministic. provenance:
   authored-here.

## Result

[]
