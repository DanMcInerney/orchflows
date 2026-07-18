---
id: canary-delegate
run: canary
status: ready
executor: orch-trivial
depends_on: []
write_scope: .orch/canary/scratch/delegate/output.json
bound: 5 tool calls
---
## Objective
Write the transformed JSON, per the fixed rule below, to output.json.
## Fixed inputs
Source JSON: {"a": 1, "b": 2, "c": 3}
Rule: multiply every value by 10; keep keys ascending alphabetical;
emit compact JSON (no spaces after `:` or `,`); end with one `\n`.
## Completion test
1. output.json byte-equals `{"a":10,"b":20,"c":30}\n` exactly. Oracle:
   byte comparison against the literal string above. oracle_class:
   deterministic.
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
