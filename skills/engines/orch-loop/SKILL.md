---
name: orch-loop
description: Iterate fresh-context passes against an external done-check within a bound. Use when done is a condition, not a task list.
role: none
---

Require: a frozen goal; the body — what each iteration dispatches, one
named skill or a caller-owned composite of named skills, bound as
plain text and never backticked, a binding rather than a call edge; a
done-check naming its oracle and oracle_class per
[contracts/verdict.md](../../../contracts/verdict.md) — the iteration
count is a deterministic done-check; a bound; and the context packet the
iterations carry — design it once via
[references/context-packet.md](references/context-packet.md).

Create the worklog through `orch-worklog`. Each iteration: start fresh
from the frozen goal plus the worklog — never a prior transcript; take
one work item; dispatch the body with the packet as delegation inputs
through `orch-delegate`; adjudicate the return at the join through
`orch-integrate`; let the done-check decide, per the contract's class
policy. Commit verified increments; record failed approaches; queue
discovered scope.

Judged exits follow [rules/loops.md](../../../rules/loops.md)'s
provisional-exit clause: an iteration-time judged PASS never closes the
run on its own.

Exit on the first of: done-check PASS (`complete`); two consecutive
no-progress iterations (`stalled`); bound spent (`limited`); an
unresolvable dependency (`blocked`); an unrecoverable execution error
(`failed`). Loops per [rules/loops.md](../../../rules/loops.md).

Never: hardcode a body; carry a step plan; widen the goal; count an
iteration's own claim as the done-check; end a judged-class run on
iteration-time green.

Return: status, iterations run, results by identity, final verification,
queued scope, and bounds spent.
