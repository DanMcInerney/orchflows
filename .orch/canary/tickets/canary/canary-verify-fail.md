---
id: canary-verify-fail
run: canary
status: ready
executor: orch-trivial
depends_on: []
write_scope: .orch/canary/scratch/verify-fail/note.txt
bound: 5 tool calls
---
## Objective
Create note.txt containing exactly one line: `canary marker: present`.
## Fixed inputs
None.
## Completion test
1. note.txt contains `canary marker: present`. Oracle: grep -F "canary
   marker: present" note.txt. oracle_class: deterministic.
2. note.txt contains `canary marker: absent-xyz` (never written;
   designed to fail). Oracle: grep -F "canary marker: absent-xyz"
   note.txt. oracle_class: deterministic.
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
