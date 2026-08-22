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
canonical JSON `--input` records. Use the stamped workspace cell; carry its
`mutations` via `--mutation`. Objective states the routed observable end
state. Give every item scope (siblings overlap only when dependency-ordered),
required isolation when available, bound, edges, and completion criteria with
pack oracles and provenance. Stamp `independence: gate` exactly when the gate
covers all authored-here criteria, otherwise `independence: checker`,
regardless of oracle class. Apply §3 edges and sole ownership; emit §4
assembly when named.

Run `cutcheck.py` on the cut revision; amend defects and re-run to 0. The
[cut lens](references/cut-lens.md) judges advisories and undecidable matters.
Then write one composite gate: one critique per unique lens, all feeding one
repair and one verification over run scope.

Map every acceptance criterion to an item, the gate, or uncovered
remainder at `<state-root>/runs/<run>/<root>.coverage.md`.

For v2, complete one `draft` before eligibility: all assignments, edges,
coverage, `ownership_regions`, and merge-oracle identities. Every assignment
names one `root_generation`; the cut names its content-addressed
`cut_generation` and `assignment_seal` over exact validated worker fields.
Grade one exact snapshot, persist its validation receipt, then compare-and-swap
only that digest to sealed after cutcheck and lens pass. Post-seal assignment
changes create and validate a new generation; repeated normalized validation
failure suspends at the correction bound. The absence of v2 fields means v1;
never reinterpret legacy membership, receipts, cohorts, readiness, claims, or
packets.

Never: edit the root ticket's frozen statement.

Return: status; ticket directory; cutcheck; item ids and edges; graph critical
path and level widths; uncovered remainder (`[]` when none); decision_gap
(`[]` when coverable).
