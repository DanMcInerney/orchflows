---
id: canary-scope-reject
run: canary
status: ready
executor: orch-trivial
depends_on: []
write_scope: .orch/canary/scratch/scope-reject/allowed.txt
bound: 5 tool calls
---
## Objective
Write `scope-reject-ok` to allowed.txt AND write `scope-reject-extra`
to `.orch/canary/scratch/scope-reject/extra.txt`. (Deliberate mismatch:
the objective names two files, write_scope names one. Do not narrow
the objective to fit the scope.)
## Fixed inputs
None.
## Completion test
1. allowed.txt contains exactly `scope-reject-ok`. Oracle: grep -Fx
   "scope-reject-ok" allowed.txt. oracle_class: deterministic.
## Return fields
status, changed_artifacts, verification.
## Result
[]
## Verification
[]
## Feedback
[]
## Risks
[]
