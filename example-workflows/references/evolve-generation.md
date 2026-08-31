# Evolve generation mapping

The loop body `02-campaign` dispatches, one generation per iteration. One
trusted controller maps each iteration without transferring its promotion
judgment.

1. For a search-policy/v1 campaign — a scalar campaign performs step 4
   alone — derive the closed search policy, prior projection, settled
   wrapper, and remaining bound from the frozen spec and latest Worklog
   entry. Before the
   first plan, score the fixed incumbent under the frozen scoring criteria: its
   score card identity and complete numeric dimension vector form the admitted
   origin. If the mapping is incomplete, do not call the planner; return the
   blocked evaluation-design gap.
2. Accept only the planner's canonical response — its request and response
   shapes are [the search-plan protocol](../../docs/search-plan-protocol.md)'s.
   Append it to the current iteration through the Worklog owner. A scoring
   lane scores and dispatches nothing: the children applying a candidate are
   dispatched by the loop's driver at the depth
   [profiles.md](../../hosts/profiles.md)
   allows. The latest
   Worklog entry persists the accepted
   response's complete projection, including every archive member.
3. For each ordered slot, map focus and public feedback or complementary parents
   to the frozen writer. Record slot, handoff, reservation, and `in_flight` in
   the same Worklog entry before delegation; pass every return through the join
   owner. Execute each slot in the mode 00-eval froze — that stub owns the mode
   dispatch — and freeze what it returns as the result/evidence. Submit that
   fixed evidence to the eligibility checker.
4. Score the incumbent and the eligible candidates as one fixed set under the
   frozen evaluation, then apply the frozen promotion rule and margin;
   a `pending` response launches nothing.

The projection carries complete candidate records, archive identities, and the
zero/one/two-parent DAG. It never carries transcript prose, evaluation mode, or
protected evidence.

On restart, reuse an accepted response. Reconcile or block an ambiguous
`in_flight` handoff; never redispatch a live slot. Active controller and planner
revisions remain outside candidate mutation authority. A self-target candidate
remains non-control and cannot become the active campaign controller or planner.
