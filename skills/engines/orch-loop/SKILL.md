---
name: orch-loop
description: Iterate fresh-context passes against an external done-check within a bound. Use when done is a condition, not a task list.
role: none
---

Require: a frozen goal; the body per
[rules/loops.md](../../../rules/loops.md) §9; a done-check naming its
oracle and oracle_class per
[contracts/verdict.md](../../../contracts/verdict.md); a bound; and the
context packet the iterations carry — design it once via
[references/context-packet.md](references/context-packet.md).

Each iteration: issue `<id>.iter.NN` through `tickets.py new`
([contracts/work-item.md](../../../contracts/work-item.md#admission-and-migration),
Admission and migration) and claim it through `tickets.py claim` in the dispatched
child's name; start fresh from the frozen goal plus the worklog
`tickets.py worklog` renders; dispatch the body with the packet as
delegation inputs, per
[rules/delegation.md](../../../rules/delegation.md);
adjudicate the return through `orch-integrate`; let the done-check
decide per the contract's class policy.

Exit `complete` on [rules/loops.md](../../../rules/loops.md) §1's
done-check and `stalled` or `limited` per §5, plus `blocked` on an
unresolvable dependency and `failed` on an unrecoverable execution
error.

Never: count an iteration's own claim as the done-check; end a
judged-class run on iteration-time green.

Return: status, results by identity, final verification, iterations
run, queued scope, and bounds spent.
