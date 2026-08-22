---
name: orch-decompose
description: Cut a stamped root ticket into work-item tickets under the pack's slicing. The one decomposer for every domain.
role: planner
---

Require: root [ticket](../../../contracts/work-item.md#root-ticket), stamped
pack slicing and oracle_policy. Reject missing parts by name.

Goal: minimize critical path; every item an atom; obey §3's test/count/width law.

Cut [work items](../../../contracts/work-item.md) as `<root>.NN` through
`tickets.py new --cohort v1:root:<root>`. Pass exact parameters/evidence as
canonical JSON `--input` records. Reach planned nodes only through the
stamped workspace cell: when it names `mutations`, carry each through
`tickets.py new --mutation`. Put routing in
Objective as the observable routed end state.
Each item takes a write scope
overlapping only siblings it is dependency-ordered with,
`isolation: required` when the pack's workspace cell names a mechanism
covering that scope, a bound, its edges, and a completion test whose
criteria name oracles from the pack's oracle policy, each with its
provenance. Oracle class does not choose the field: stamp
`independence: gate` if the final gate covers all authored-here criteria;
otherwise stamp `independence: checker`. This holds regardless of oracle
class. Draw each edge under §3's rule and place each artifact two
items would write under its sole-owner rule.
Emit the assembly item the pack's cell names, on §4's terms.

Run `cutcheck.py` against the cut revision; repair every defect through
`tickets.py amend` and re-run to exit 0.
[The cut lens](references/cut-lens.md) judges advisories and whatever the
script cannot decide. Only then
write the run's one composite gate through `tickets.py gate`: one critique
per unique lens name, all feeding one repair and one verification over the
run's scope.

Map every acceptance criterion to an item, the gate, or uncovered
remainder at `<state-root>/runs/<run>/<root>.coverage.md`.

For a v2 root, produce one complete `draft` before any unit becomes eligible:
all unit and gate assignments, dependency edges, the coverage map,
`ownership_regions`, and merge-oracle identities. Every assignment names the
same `root_generation`; the cut names a content-addressed `cut_generation` of
the form `v2:cut:<root-id>:<ordinal>:sha256:<digest>` and carries an
`assignment_seal` over its exact validated worker fields. Grade one exact
draft snapshot, persist its validation receipt, and compare-and-swap only that
digest to sealed after cutcheck and the cut lens pass. Any post-seal assignment
change creates and validates a new generation; a repeated normalized
validation failure suspends immediately under the correction bound.
The absence of v2 fields means v1. Never reinterpret or rewrite legacy cut
membership, receipts, cohorts, readiness, claims, or packets.

Never: edit the root ticket's frozen statement.

Return: status; result — the ticket directory; verification — the
cutcheck result; then item ids with edges, the critical-path length
and per-level width from cutcheck's `graph` block, uncovered
remainder (`[]` when none), and decision_gap (`[]` when coverable).
