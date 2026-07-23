---
name: orch-panel
description: Adjudicate a fixed candidate set through blind independent judge lanes. Use for evolve, ranking, and consequential decisions.
role: none
---

Require: a fixed candidate set whose every entry binds one candidate
identity to its covered-PASS benchmark result/evidence identity; the frozen
benchmark and scoring identities; frozen scoring criteria, each naming its
oracle and `oracle_class`; a declared aggregation method — rank, vote, or
score — chosen before any lane runs; and the lane count per candidate.

For each candidate, form the declared number of complete delegation
packets. Each packet's objective asks `orch-judge` to score exactly one fixed
candidate identity from its admitted evidence; inputs contain only that candidate
identity, its exact result/evidence identity, the frozen benchmark and scoring
identities, and frozen scoring criteria bound to that evidence; authority grants no target
write; bounds cap the lane; return_contract requests one score card citing
the exact evidence identity; reply_to names the dispatcher.

Dispatch the packets in parallel through `orch-delegate`. Keep every lane
blind to all other candidates, provenance, lanes, and scores; every child
return crosses `orch-integrate` with the caller's write scope.

Aggregate exactly by the declared method from the per-lane score cards.
Report every dissent and its evidence in the disagreement register; high
disagreement remains information about the criteria.

Never: let a judge packet carry multiple candidates; re-execute or substitute
admitted evidence; let lanes see each other; change the aggregation method
after seeing scores; drop a dissenting lane.

Return: the aggregate order or verdict, per-lane score cards citing their
admitted result/evidence identities, and the disagreement register.
