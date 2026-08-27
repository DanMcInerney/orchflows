---
id: 01-discrimination
run: cutcheck-f1-discrimination
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - install.py
excluded_actions:
  - editing scripts/tickets.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-discrimination:1:sha256:dde470b41a3bebf1ce5784bcd1f7ee6f5f383570777686cb3eb0fe2c9936a387
cut_generation: cut:01-discrimination:1:sha256:3f5e965d8a655cbecfb332e1583d6ab755da433fbd8d1785e56b510f8c1e310d
assignment_seal: sha256:ea1cba5734bc469cb796e2d5d45f49521dfacc079b56410251e2aeef3aae970e
---
## Objective

Fixture set for family 1 discrimination: three oracles that read the same at the
baseline as they will when the work has landed, one per reported case.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **Already reads PASS at the baseline.**
   `grep -n "SCRIPT_NAMES" install.py` returns the tuple line. oracle_class:
   deterministic. provenance: authored-here.
2. **Zero hits at the baseline and zero hits at HEAD.**
   `grep -rn "zzqq-token-never-written" install.py` returns at least one line.
   oracle_class: deterministic. provenance: authored-here.
3. **A node id naming a class that does not exist.**
   `python3 -B -m unittest tests.test_installer.NoSuchClass.test_absent` exits 0.
   oracle_class: deterministic. provenance: authored-here.

## Result

[]
