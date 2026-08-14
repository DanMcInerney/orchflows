---
id: 01-barenoun
run: cutcheck-barenoun
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - scripts/cutcheck.py
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture ticket for the command name a ticket states as English: a backticked
span holding nothing but a command head names the tool, and no bare name is a
decidable oracle. Criterion 1 states such a mention beside a real oracle, which
still has to decide the criterion; criterion 2 states one with no oracle beside
it, which has to surface as an extraction gap.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **A mention beside a real oracle leaves that oracle deciding.** Whatever a
   `pytest` invocation would say is not the subject here; the oracle is
   `grep -rn "unrunnable-oracle" scripts/`, which finds nothing at the baseline
   and finds it once the work has landed. oracle_class: deterministic.
   provenance: authored-here.
2. **A mention standing alone is an extraction gap.** The only command head this
   criterion states is `pytest`, so no extractor recognizes an oracle here and
   the gap line is the honest report. oracle_class: deterministic. provenance:
   authored-here.

## Result

[]
