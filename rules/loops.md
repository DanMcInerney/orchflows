# Loops

1. A loop carries a frozen goal, an external done-check, and a bound. The
   done-check alone decides success; the bound alone caps cost. A bound
   is never a success condition, and a loop never carries a step plan —
   prescribed steps encode one model generation's pace and rot; the
   done-condition does not.
2. Every iteration starts fresh from the frozen goal plus the
   [worklog](../contracts/worklog.md), never from a prior iteration's
   transcript.
3. One work item per iteration. Verified increments commit; unverified
   work never carries forward as fact.
4. Failed approaches are recorded with the evidence that killed them; an
   iteration never re-walks one.
5. Progress is exactly a newly verified increment or a newly killed
   approach; two consecutive iterations without either exit `stalled`.
   Exhausting the bound exits `limited`. The terminal set is closed:
   complete, blocked, stalled, limited, failed.
6. Discovered scope is queued in the worklog, never merged into the live
   goal.
7. Nested loops inherit bounds and cannot promote a stalled or limited
   exit into complete. A child whose internal loop stalls returns
   `limited` in its result, with the stall evidence.
8. Work with no terminal done (queue health, upkeep) runs as scheduled
   bounded snapshots, never as an unconverging loop.
9. A loop's body is a caller-supplied binding: what one iteration
   dispatches — one named skill, or a caller-owned composite of named
   skills. A routing stamp's `loop(<body>)` names one skill
   ([contracts/spec.md](../contracts/spec.md)); a composite body is
   bound only by a calling workflow. The engine owns iteration and
   exit; the body carries no judgment over either.
10. A done-check may be the iteration count itself (`iterations_run ==
    N`; deterministic; evidence: the worklog's iteration entries). The
    declared count is then the goal; the bound remains a separate cost
    cap, and §1 is unchanged by this.
11. A judged done-check's iteration-time PASS exits iteration
    provisionally; `complete` requires a fresh final re-judgment from
    the frozen goal. On that re-judgment's FAIL, findings enter the
    context packet and iteration resumes while bound remains; bound
    spent exits `limited`.
