---
name: orch-tdd
description: Implement one code ticket through red-green slices against its completion test. The code pack's unit executor.
role: worker
---

Require: one claimed code [ticket](../../../contracts/work-item.md) and
an isolated workspace at a clean baseline.

Slice the objective so each slice is provable by one failing check.
Per slice: write the check, watch it fail for the stated reason, make
it pass with the least code that honestly passes, then reconcile with
the workspace's idiom and shape per the ticket's craft reference. Test
at public seams; rewrite any tautological check. Commit each verified
slice. Close by running the ticket's full completion test through
`orch-verify` against the result's fixed identity.

Never: write code before its failing check; weaken a check to pass it;
leave the workspace off a committed baseline; touch paths outside the
ticket's write scope.

Return: the completed ticket per
[work-item.md](../../../contracts/work-item.md)'s filing law.
