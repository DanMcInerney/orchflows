---
name: orch-loop
description: Iterate fresh-context passes against an external done-check within a bound. Use when done is a condition, not a task list.
role: none
---

Require: a frozen goal; the body per
[rules/loops.md](../../../rules/loops.md) §9, bound as plain text and
never a call edge; a done-check naming its oracle and oracle_class per
[contracts/verdict.md](../../../contracts/verdict.md); a bound; and the
context packet the iterations carry — design it once via
[references/context-packet.md](references/context-packet.md).

Freeze the goal into the run's state through `tickets.py run-state`.
Each iteration: issue `<id>.iter.NN` through `tickets.py new`
([contracts/work-item.md](../../../contracts/work-item.md), Root
ticket); start fresh from the frozen goal plus the worklog `tickets.py
worklog` renders — never a prior transcript; dispatch the body with the
packet as delegation inputs, per
[rules/delegation.md](../../../rules/delegation.md);
adjudicate the return through `orch-integrate`; let the done-check
decide per the contract's class policy. Commit verified increments;
record failed approaches; queue discovered scope.

Judged exits follow [rules/loops.md](../../../rules/loops.md)'s
provisional-exit clause: an iteration-time judged PASS never closes the
run on its own.

Exit on the first of: done-check PASS (`complete`); two consecutive
no-progress iterations (`stalled`); bound spent (`limited`); an
unresolvable dependency (`blocked`); an unrecoverable execution error
(`failed`).

Never: hardcode a body; carry a step plan; widen the goal; count an
iteration's own claim as the done-check; end a judged-class run on
iteration-time green.

Return: status, results by identity, final verification, iterations
run, queued scope, and bounds spent.
