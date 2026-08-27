---
id: 01-clean-oracles
run: cutcheck-clean
status: pending
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
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-clean-oracles:1:sha256:34f909a41ede627b815be2bb2d310270957201a9271f7bc70ac772d4625daa67
cut_generation: cut:01-clean-oracles:1:sha256:64273ad6acfdbffa0db429fe4d9ac2778f874158908f8ab7620b05947be4b0ba
assignment_seal: sha256:ec60912cd18db1500240bc8107351725aadf958245ef3ed8dbebb7d2e37ed996
---
## Objective

Fixture set for a clean cut: every completion-test oracle below discriminates,
so family 1 reports nothing and cutcheck exits 0 over this set.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **Installed under its bare name.** `grep -n "cutcheck.py" install.py` returns
   the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.
2. **The family is named in the script.**
   `grep -n "family 1" scripts/cutcheck.py` returns at least one line.
   oracle_class: deterministic. provenance: pre-existing.

## Result

[]
