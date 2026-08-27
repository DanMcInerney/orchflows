---
id: 01-barenoun
run: cutcheck-barenoun
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
root_generation: root:01-barenoun:1:sha256:625e63246c712b6fd272c06cb28a9df5609328306684214a35bcdfc9eeab2631
cut_generation: cut:01-barenoun:1:sha256:2a3efd5d65d5dad92dd0f157300754889a665a9c75031273953ab6c9348038aa
assignment_seal: sha256:212a6ecaad1088db3ce9ec5d2b677050d48caaf293a38f640be0db250529d1cc
---
## Objective

Fixture ticket for the command name a ticket states as English: a backticked
span holding nothing but a command head names the tool, and no bare name is a
decidable oracle. Criterion 1 states such a mention beside a real oracle, which
still has to decide the criterion; criterion 2 states one with no oracle beside
it, which has to surface as an extraction gap.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

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
