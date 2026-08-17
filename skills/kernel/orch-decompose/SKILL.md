---
name: orch-decompose
description: Cut a stamped root ticket into work-item tickets under the pack's slicing. The one decomposer for every domain.
role: planner
---

Require: a root
[ticket](../../../contracts/work-item.md#root-ticket) plus the stamped
pack's slicing reference and oracle_policy. Reject a root missing any
part that contract names, naming it.

Goal: minimize the run's critical path subject to every item an atom
([rules/topology.md](../../../rules/topology.md) §3). Count is
unbounded above; width beyond the host profile is the frontier's
queue, not the cut's.

Cut the root ticket into [work items](../../../contracts/work-item.md)
under the slicing, issued as `<root>.NN` into the root's own run
directory through `tickets.py new`. Each item takes a write scope
overlapping only siblings it is dependency-ordered with,
`isolation: required` when the pack's workspace cell names a mechanism
covering that scope, a bound, its edges, and a completion test whose
criteria name oracles from the pack's oracle policy, each with its
provenance; `independence: gate` when a `judged` criterion there rides
the final gate. Per §3: draw an edge only where the dependent's oracle
reads what the predecessor writes or its fixed inputs cite the
predecessor's result identity; and give an artifact more than one item
would write to exactly one of them, never shared.
Emit the assembly item the pack's cell names, on §4's terms.

Then run `cutcheck.py` against the revision the set was cut from,
repair every cut defect it reports through `tickets.py amend` and re-run
it to exit 0; its advisories and what it cannot decide are
[references/cut-lens.md](references/cut-lens.md)'s to judge. Only then
write the gate stubs through `tickets.py gate`, one lens per stamped
lens over the run's scope.

Map every acceptance criterion to an item, the gate, or uncovered
remainder at `<state-root>/runs/<run>/<root>.coverage.md`.

Never: edit the root ticket's frozen statement.

Return: status; result — the ticket directory; verification — the
cutcheck result; then item ids with edges, the critical-path length and
per-level width from cutcheck's `graph` block, uncovered remainder (`[]` when
none), and decision_gap (`[]` when coverable).
