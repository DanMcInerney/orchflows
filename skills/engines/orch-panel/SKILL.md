---
name: orch-panel
description: Adjudicate a fixed candidate set through blind independent judge lanes. Use for evolve, ranking, and consequential decisions.
role: none
---

Require: a fixed candidate set by identity; frozen scoring criteria; a
declared aggregation method — rank, vote, or score — chosen before any
lane runs; and the lane count.

Dispatch each `orch-judge` lane in parallel through `orch-delegate`,
the candidate set and frozen criteria as the packet, blind: no sight
of other lanes; every result crosses `orch-integrate`. Aggregate
exactly by the declared method. Report the disagreement between lanes
as part of the result — high disagreement is information about the
criteria, not noise to average away.

Never: let lanes see each other; change the aggregation method after
seeing scores; drop a dissenting lane.

Return: the aggregate order or verdict, per-lane score cards, and the
disagreement register.
