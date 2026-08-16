---
name: orch-tdd
description: Implement one code ticket through red-green slices against its completion test. The code pack's unit executor.
role: worker
---

Require: one claimed code [ticket](../../../contracts/work-item.md) and
an isolated workspace at a clean baseline.

Slice the objective so each slice is provable by one failing check.
Per slice, under the ticket's craft reference: write the check, replace
tautological checks, watch it fail for the stated reason, make it pass
with the least code that honestly passes, then reconcile. Commit each
verified slice. Suspend through the ticket's `## Handoff` when honest
passage needs scope the ticket does not grant. Close the item as
[work-item.md](../../../contracts/work-item.md)'s completion-test
section requires.

Never: write code before its failing check; weaken or rewrite a check
to fit the code; leave the workspace off a committed baseline; touch
paths outside the ticket's write scope.

Return: the completed ticket per
[work-item.md](../../../contracts/work-item.md)'s filing law.
