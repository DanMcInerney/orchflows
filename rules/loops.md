# Loops

The generated [terminal lifecycle cells](../docs/lifecycle.md#ticket-lifecycle)
connect bounded round outcomes to their run-visible states. There is no loop
engine and no loop marker: a bounded campaign is prose in the calling
workflow over repeated bricks, and the one mechanical round the library still
arms is the `<id>.repair.NN` round a refused
[`done` predicate](../contracts/work-item.md) leaves behind at `land`. The
law below governs both.

1. A bounded campaign carries a frozen goal, an external done-check, and a
   bound. The done-check alone decides success; the bound alone caps cost and
   is never a success condition. A declared round count is a
   done-check, never a bound. A time-shaped bound is script-enforced;
   an effort-shaped bound is the dispatching caller's to enforce.
2. Every round starts fresh from the frozen goal plus the
   [worklog](../contracts/worklog.md), never from a prior round's
   transcript. Its context carries identities, verdicts, and decisions —
   never transcript prose — and converges to the state that matters
   rather than accreting history.
3. Failed approaches are recorded with the evidence that killed them; an
   identical retry is a defect. Two consecutive rounds without a
   newly verified increment or a newly killed approach exit `stalled`;
   exhausting the bound exits `limited`. Discovered scope is queued in
   the worklog, never merged into the live goal.
4. A judged done-check's mid-campaign reading is provisional;
   `complete` requires the fresh final judgment
   [verification.md](verification.md) §6 requires — the advance reads it
   off a fresh check ticket's own joined disposition, never off a
   round's claim.
5. Work with no terminal done (queue health, upkeep) runs as scheduled
   bounded snapshots, never as an unconverging campaign; a host scheduler
   chains bounded campaigns.
