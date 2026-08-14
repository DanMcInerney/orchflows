---
id: 03-baseline-quote
run: cutcheck-carveouts
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: [01-reads-only]
bound: 20 tool calls
write_scope:
  - install.py
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture ticket quoting text that is present at the baseline and absent at the
workspace revision. Citations resolve in the baseline scratch copy, so this
ticket is clean; resolving them at the workspace revision would report it.

## Fixed inputs

- Baseline: `ac8791a`, where `install.py:101` opens the script tuple
  `SCRIPT_NAMES = ("friction.py"`.

## Completion test

1. **The installer lists the script.** `grep -n "cutcheck.py" install.py`
   returns the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
