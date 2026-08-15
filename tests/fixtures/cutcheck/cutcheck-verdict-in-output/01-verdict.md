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

Fixture ticket for commands whose verdict is in what they print: a text count
and a revision count both exit 0 whatever they counted.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **A count is read, not exited on.** `grep -c "SCRIPT_NAMES" install.py`
   reports 0. oracle_class: deterministic. provenance: authored-here.
2. **A revision count is printed, not exited on.** `git rev-list --count HEAD`
   reports 0. oracle_class: deterministic. provenance: authored-here.

## Result

[]
