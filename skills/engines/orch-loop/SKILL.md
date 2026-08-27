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
([contracts/work-item.md](../../../contracts/work-item.md#semantic-assignment),
Semantic assignment) and claim it through `tickets.py claim` in the dispatched
child's name; start fresh from the frozen goal plus the worklog
`tickets.py worklog` renders; dispatch the body per
[rules/delegation.md](../../../rules/delegation.md), each packet field
emitted as a canonical JSON `--input` record — sorted keys, no spaces,
no duplicate key — because a record the sink cannot round-trip is
refused as `input-json-noncanonical` at the door rather than at the
oracle; adjudicate the return through `orch-integrate`; let the
done-check decide per the contract's class policy.

Exit `complete` on [rules/loops.md](../../../rules/loops.md) §1's
done-check and `stalled` or `limited` per §5, plus `blocked` on an
unresolvable dependency and `failed` on an unrecoverable execution
error. Where a predecessor — a nested loop, or a cited earlier run —
closed `limited`, name that limitation and the evidence that decided it
in this run's own result, and carry it into the packet's failed-approaches
digest: §7 forbids promoting a limited exit into `complete`, and a
limitation nobody restates is one the next iteration re-walks.

Never: count an iteration's own claim as the done-check; end a judged-class
run on iteration-time green; accept an iteration solely on its executor's
claim — it takes one outside evidence path under
[rules/verification.md](../../../rules/verification.md) §7 before counting
as progress, and where no such path is available the dispatch is refused.

Return: status, results by identity, final verification, iterations
run, queued scope, and bounds spent.
