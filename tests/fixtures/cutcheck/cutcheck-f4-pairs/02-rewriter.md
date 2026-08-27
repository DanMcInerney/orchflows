---
id: 02-rewriter
run: cutcheck-f4-pairs
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
root_generation: root:01-reader:1:sha256:3cc15c0565a48ad15676b9fcf0d353443407f22de85ef04d55d867aba880efab
cut_generation: cut:01-reader:1:sha256:2d70cc95218a9e707754ec4b36335836c38bac332dfe26d6ed80ae4b8b487ca4
assignment_seal: sha256:594d360f04376e4e7c51da1bbbe03285983c69ffb574753587b22f877a472f02
---
## Objective

Fixture item for pairwise safety: `install.py` is this item's whole scope, and the oracle of item `01-reader` reads it. No edge joins the two.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **The installer lists the script.** `grep -n "cutcheck.py" install.py`
   returns the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
