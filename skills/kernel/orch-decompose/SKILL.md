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
state. Give every item a write scope (siblings overlap only when dependency-ordered),
isolation, bound, edges, and completion criteria with
pack oracles and provenance. Stamp `independence: gate` exactly when the gate
covers all authored-here criteria, otherwise `checker`,
regardless of oracle class. Apply §3 edges and sole ownership; emit §4
assembly when named. Declared `isolation: required`, a cut still takes no
workspace: it writes tickets.

Run `cutcheck.py` on the cut revision; amend defects and re-run to 0. The
[cut lens](references/cut-lens.md) judges advisories and undecidable matters.
Then write one composite gate through `tickets.py gate`: one critique per
unique lens, feeding one repair and one verification over run scope.

Map every acceptance criterion to an item, the gate, or uncovered
remainder at `<state-root>/runs/<run>/<root>.coverage.md`.

For v2, complete one `draft` before eligibility: all assignments, edges,
coverage, `ownership_regions`, and merge-oracle identities. Every assignment
names one `root_generation`; the cut names its content-addressed
`cut_generation` and `assignment_seal` over exact validated worker fields.
Grade one exact snapshot and persist its receipt through
`tickets.py draft-validate`, then compare-and-swap only that digest to sealed
with `tickets.py seal` after cutcheck and lens pass. Post-seal
changes create and validate a new generation; repeated normalized validation
failure suspends at the correction bound. Absent v2 fields mean v1;
never reinterpret legacy membership, receipts, cohorts, readiness, claims, or
packets.

Never: edit the root ticket's frozen statement.

Return: status; ticket directory; cutcheck; item ids and edges; graph critical
path and level widths; uncovered remainder (`[]` when none); decision_gap
(`[]` when coverable).
