---
id: 01-shellhead
run: cutcheck-shellhead
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - scripts/cutcheck.py
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture ticket for untrusted ticket content: the criterion below states its
oracle as a backticked shell span. A ticket is input, so no span of one may
reach a shell.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **A shell span is never executed.** `bash -lc 'touch /tmp/cutcheck-shellhead-ran'`
   is the span; through a shell it touches that file, which is how the test
   tells running from reporting. oracle_class: deterministic. provenance:
   authored-here.

## Result

[]
