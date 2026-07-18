---
id: canary-tdd-micro
run: canary
status: ready
executor: orch-tdd
depends_on: []
write_scope: .orch/canary/scratch/tdd/
bound: 10 tool calls
---
## Objective
Add pure function `double(n)` returning `n * 2` to canary_math.py,
proven by named test `test_double_returns_twice_input` in
test_canary_math.py asserting `double(21) == 42`. Write the check
first, watch it fail, then pass it.
## Fixed inputs
None.
## Completion test
1. `python -m unittest discover -s .orch/canary/scratch/tdd -p
   "test_*.py" -v` exits 0 and reports test_double_returns_twice_input
   passing. Oracle: the test command above. oracle_class: deterministic.
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
