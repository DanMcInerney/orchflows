# Loops

1. A loop carries a frozen goal, an external done-check, and a bound.
   The done-check alone decides success; the bound alone caps cost and
   is never a success condition. A declared iteration count is a
   done-check (`iterations_run == N`, evidenced by the worklog's
   iteration entries), never a bound. A loop carries no step plan — the
   done-condition does not.
2. Every iteration starts fresh from the frozen goal plus the
   [worklog](../contracts/worklog.md), never from a prior iteration's
   transcript.
3. One work item per iteration. Verified increments commit; unverified
   work never carries forward as fact.
4. Failed approaches are recorded with the evidence that killed them; a
   later attempt changes cause, input, or method, and an identical retry
   is a defect.
5. Progress is exactly a newly verified increment or a newly killed
   approach; two consecutive iterations without either exit `stalled`,
   and exhausting the bound exits `limited`. The terminal set is
   [work-item.md](../contracts/work-item.md)'s.
6. Discovered scope is queued in the worklog, never merged into the live
   goal.
7. Nested loops inherit bounds and cannot promote a stalled or limited
   exit into complete. A child whose internal loop stalls returns
   `limited` in its result, with the stall evidence.
8. Work with no terminal done (queue health, upkeep) runs as scheduled
   bounded snapshots, never as an unconverging loop.
9. A loop's body is a caller-supplied binding: what one iteration
   dispatches — one named skill, a composition, or a caller-owned
   composite of named skills. The engine owns iteration and exit; the
   body carries no judgment over either.
10. A judged done-check's iteration-time PASS exits iteration
    provisionally; `complete` requires the fresh final re-judgment
    [verification.md](verification.md) §6 requires. On its FAIL,
    findings enter the context packet and iteration resumes while bound
    remains; bound spent exits `limited`.
