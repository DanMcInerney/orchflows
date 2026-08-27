---
id: 01-f2-paths
run: cutcheck-f2-paths
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
root_generation: root:01-f2-paths:1:sha256:65cce69cca875be147fa5b12501a84b70330240d5ca923826c2096254f64f95b
cut_generation: cut:01-f2-paths:1:sha256:c84426cf4e5ac2348674feb9bf56389a03aaa8b440a822afbc1cd4fa9ece2aab
assignment_seal: sha256:a145509bdc5f4f8732819c301ac0c67cdd34774ece4ca4d09e36ad1e78f14fc4
---
## Objective

Fixture set for family 2: an oracle argument naming an evidence directory that
is nowhere at the baseline, a `file:line` citation whose line is past the end of
its file, and a quoted string cited to a location that does not hold it.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

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
