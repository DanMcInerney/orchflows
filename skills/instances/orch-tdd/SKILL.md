---
name: orch-tdd
description: Implement one code ticket through red-green slices against its completion test. The code pack's unit executor.
role: worker
---

Require: one claimed code [ticket](../../../contracts/work-item.md)
(its `isolation` established as the first act, at a clean baseline).

Slice the objective so each slice is provable by one failing check.
Per slice, under the ticket's craft reference: write the check, watch
it fail for the stated reason — a check that arrives green proves it
can fail per [rules/verification.md](../../../rules/verification.md)
§8 — make it pass with the least code that honestly passes, then
reconcile. Commit each verified slice.

Never: write code before its failing check; weaken or rewrite a check
to fit the code; leave the workspace off a committed baseline.

Return: the completed ticket per
[work-item.md](../../../contracts/work-item.md)'s filing law.
