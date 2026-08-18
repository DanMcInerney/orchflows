---
name: orch-decompose
description: Cut a stamped root ticket into work-item tickets under the pack's slicing. The one decomposer for every domain.
role: planner
---

Require: a root
[ticket](../../../contracts/work-item.md#root-ticket) plus the stamped
pack's slicing reference and oracle_policy. Reject a root missing any
part that contract names, naming it.

Goal: minimize the run's critical path subject to every item an atom.
The atom test, and where a cut's count and its width are settled, are
[rules/topology.md](../../../rules/topology.md) §3's; read it before
the first item.

Cut the root ticket into [work items](../../../contracts/work-item.md)
under the slicing, issued as `<root>.NN` into the root's own run
directory through `tickets.py new`. Each item takes a write scope
overlapping only siblings it is dependency-ordered with,
`isolation: required` when the pack's workspace cell names a mechanism
covering that scope, a bound, its edges, and a completion test whose
criteria name oracles from the pack's oracle policy, each with its
provenance. Select `independence: gate` when the final gate covers all
authored-here criteria on that item, regardless of oracle class; select
`independence: checker` when any authored-here criterion is not covered
there. Draw each edge under §3's edge rule and place each
artifact two items would write under its sole-owner rule, at the point
you decide one.
Emit the assembly item the pack's cell names, on §4's terms.

Then run `cutcheck.py` against the revision the set was cut from,
repair every cut defect it reports through `tickets.py amend` and re-run
it to exit 0; its advisories and what it cannot decide are
[references/cut-lens.md](references/cut-lens.md)'s to judge. Only then
write the run's one composite gate through `tickets.py gate`: one critique
per unique lens name, all feeding one repair and one verification over the
run's scope.

Map every acceptance criterion to an item, the gate, or uncovered
remainder at `<state-root>/runs/<run>/<root>.coverage.md`.

Never: edit the root ticket's frozen statement.

Return: status; result — the ticket directory; verification — the
cutcheck result; then item ids with edges, the critical-path length
and per-level width from cutcheck's `graph` block, uncovered
remainder (`[]` when none), and decision_gap (`[]` when coverable).
