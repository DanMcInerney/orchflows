---
id: 01-quoted
run: cutcheck-command-mention
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - scripts/cutcheck.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-quoted:1:sha256:ef676b1783e3d19fcba8a621c4dbc01d70c300e97c3db8d8e02189e8c247bbd7
cut_generation: cut:01-quoted:1:sha256:1b3251e02670365d2bbe25b9d16787e084631f58073df5780740af1fcf2aa79c
assignment_seal: sha256:d5ee6fefd3854180e563e8593d212894a4ae6384f43fa321604a307e823c0020
---
## Objective

Fixture ticket for family 1: stating a command is not quoting one. Each
criterion below quotes a span in one of the three shapes measured against this
tool -- what not to do, what the guard refuses, what CI runs -- and the first
of them states a real oracle beside its quotation, so a narrowing that
disabled grading rather than narrowing it would show here as that oracle
falling silent.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **A span quoted as what not to do is no oracle.** The suite's verdict is
   read from its exit status, never `grep -E "^Ran" out.txt`, and
   `grep -n "cutcheck.py" install.py` returns the SCRIPT_NAMES line.
   oracle_class: deterministic. provenance: pre-existing.
2. **A span quoted as what the guard refuses is no oracle.** The confinement
   gate refuses `git log --output=/tmp/x`, so a ticket describing the gate
   quotes the span without stating one. oracle_class: deterministic.
   provenance: authored-here.
3. **A span quoted as what CI runs is no oracle.** A whole-module invocation
   such as `python3 -m unittest tests.test_cutcheck`, which is what CI runs,
   reads the same under every item it is stated under. oracle_class:
   deterministic. provenance: authored-here.

## Result

[]
