---
id: 01-f2-paths
run: cutcheck-f2-paths
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - install.py
  - scripts/cutcheck.py
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture set for family 2: an oracle argument naming an evidence directory that
is nowhere at the baseline, a `file:line` citation whose line is past the end of
its file, and a quoted string cited to a location that does not hold it.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **The recorded verdict is where the ticket says.**
   `grep -rn "verdict" .orch/evidence/f2-missing/` returns the recorded verdict.
   oracle_class: deterministic. provenance: authored-here.
2. **A citation whose line does not resolve.** The installer names its scripts
   at `install.py:99999`. `grep -n "family 1" scripts/cutcheck.py` returns at
   least one line. oracle_class: deterministic. provenance: pre-existing.
3. **A quoted string cited where it is not present.** `install.py:1` reads
   "no line reads this way". `grep -n "cutcheck.py" install.py` returns the
   SCRIPT_NAMES line. oracle_class: deterministic. provenance: pre-existing.

## Result

[]
