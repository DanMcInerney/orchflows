# Loops

The generated [terminal lifecycle cells](../docs/lifecycle.md#ticket-lifecycle)
connect bounded loop outcomes to their run-visible states. A loop is a
ticket carrying the `loop` object of
[work-item.md](../contracts/work-item.md); `scripts/tickets_loop.py` owns
arm, evaluate, and advance, and the worklog is the state.

1. A loop carries a frozen goal, an external done-check, and a bound.
   The done-check alone decides success; the bound alone caps cost and
   is never a success condition. A declared iteration count is a
   done-check, never a bound. A time-shaped bound is script-enforced;
   an effort-shaped bound is the dispatching caller's to enforce.
2. Every iteration starts fresh from the frozen goal plus the
   [worklog](../contracts/worklog.md), never from a prior iteration's
   transcript. Its context carries identities, verdicts, and decisions —
   never transcript prose — and converges to the state that matters
   rather than accreting history.
3. Failed approaches are recorded with the evidence that killed them; an
   identical retry is a defect. Two consecutive iterations without a
   newly verified increment or a newly killed approach exit `stalled`;
   exhausting the bound exits `limited`. Discovered scope is queued in
   the worklog, never merged into the live goal.
4. A judged done-check's iteration-time reading is provisional;
   `complete` requires the fresh final judgment
   [verification.md](verification.md) §6 requires — the advance reads it
   off a fresh check ticket's own joined disposition, never off an
   iteration's claim.
5. Work with no terminal done (queue health, upkeep) runs as scheduled
   bounded snapshots, never as an unconverging loop; a host scheduler
   chains bounded campaigns.
