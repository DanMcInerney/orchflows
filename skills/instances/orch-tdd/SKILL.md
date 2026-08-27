---
name: orch-tdd
description: Implement one code ticket through red-green slices derived from its Goal. The code pack's unit executor.
role: worker
---

Require: one claimed code ticket.

Derive tests from Goal and slice the implementation so each slice is provable by one failing check.
Per slice, under the stamped pack's craft: write the check, watch
it fail for the stated reason — a check that arrives green proves it
can fail per [rules/verification.md](../../../rules/verification.md)
§8 — make it pass with the least code that honestly passes, then
reconcile. Commit each verified slice here, inside the ticket workspace.

Never: write code before its failing check; weaken or rewrite a check
to fit the code. Do not perform integration, publish with push, or create
commits while checked out at the run branch. Send clean slice commits back;
the join alone applies them to the run revision.

File the code pack's [evidence record](../../../packs/orch-code-pack/references/evidence.md)
beside the result identity; filing follows
[result.md](../../../contracts/result.md).

Return: the completed ticket.
