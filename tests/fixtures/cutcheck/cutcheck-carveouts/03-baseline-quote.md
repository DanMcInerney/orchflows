---
id: 03-baseline-quote
run: cutcheck-carveouts
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: [01-reads-only]
bound: 20 tool calls
write_scope:
  - install.py
excluded_actions:
  - editing scripts/tickets.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-reads-only:1:sha256:28837ee2df2b8fe5c704d42a82975a2b7c8224341b224a99df8d787d13244f2b
cut_generation: cut:01-reads-only:1:sha256:3ce87e62cb68ed5358655faa6705891a1c766cdb4ee2856ef66397e926e83c15
assignment_seal: sha256:6c1a6d0e478642ab76bb33d9db4cd4a63900605345b37a8780416c626426edd3
---
## Objective

Fixture ticket quoting text that is present at the baseline and absent at the
workspace revision. Citations resolve in the baseline scratch copy, so this
ticket is clean; resolving them at the workspace revision would report it.
At `install.py:101`, the baseline opens the script tuple
`SCRIPT_NAMES = ("friction.py"`.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

## Completion test

1. **The installer lists the script.** `grep -n "cutcheck.py" install.py`
   returns the SCRIPT_NAMES line. oracle_class: deterministic. provenance:
   pre-existing.

## Result

[]
