---
name: orch-panel
description: Adjudicate a fixed candidate set through blind independent judge lanes. Use for evolve, ranking, and consequential decisions.
role: none
---

Require: a fixed candidate set whose every entry binds one candidate identity to
its covered-PASS evaluation result/evidence identity; frozen evaluation and
scoring identities; frozen evaluation mode; one frozen candidate-blind Judge
brief; frozen scoring criteria, each naming its oracle and `oracle_class`; a
declared aggregation method — rank, vote, or score — chosen before any lane
runs; and the lane count per candidate.

Carry the frozen candidate-blind Judge brief verbatim into every packet. For each candidate,
form the declared number of complete delegation packets. Each packet's objective
asks `orch-verify` to score exactly one fixed candidate identity from its admitted
evidence — blind: inputs carry only this candidate; inputs contain only that identity, its exact result/evidence identity,
the frozen evaluation mode, frozen evaluation and scoring identities, brief, and
frozen scoring criteria. Benchmark mode evidence names executed runner/oracle output; judged
mode evidence names the static artifact snapshot. Authority grants no target
write; bounds cap the lane; return_contract requests one score card citing the
exact evidence identity; reply_to names the dispatcher.

Dispatch packets in parallel per
[rules/delegation.md](../../../rules/delegation.md). Keep every lane blind to
all other candidates, provenance, lanes, and scores; every child return crosses
`orch-integrate` with the caller's write scope.

Aggregate exactly by the declared method from the per-lane score cards. Report
every dissent and its evidence in the disagreement register; high disagreement
remains information about the criteria.

Never: let one packet carry multiple candidates; replace or alter the frozen
brief; re-execute or substitute admitted evidence; let lanes see each other;
change the aggregation method after seeing scores; drop a dissenting lane.

Return: the aggregate order or verdict, per-lane score cards citing their
admitted result/evidence identities, and the disagreement register.
