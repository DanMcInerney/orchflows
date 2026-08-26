---
name: orch-decompose
description: Cut a stamped root ticket into work-item tickets under the pack's slicing. The one decomposer for every domain.
role: planner
---

Require: root [ticket](../../../contracts/work-item.md#root-ticket), stamped
pack slicing and oracle_policy. Reject missing parts by name.

Goal: minimize critical path; every item an atom under §3.

Cut [work items](../../../contracts/work-item.md) as `<root>.NN` by frozen root
version. Mandatory-v2 roots: candidate files carrying the
exact inherited `root_generation` and no `cohort`, via
`tickets.py new <run> --file <candidate>`. Legacy-v1 roots:
`tickets.py new <run> <id> --cohort v1:root:<root>`. Carry exact parameters as
canonical JSON `--input`, the stamped workspace cell, and `mutations` via
`--mutation`. Give each item an observable objective, write scope (siblings
overlap only when dependency-ordered), isolation, bound, edges, and criteria
with pack oracles and provenance. Stamp `independence: gate` when the gate
covers all authored-here criteria; otherwise `independence: checker`,
regardless of oracle class. Apply §3 edges and sole ownership; emit named §4
assembly. Declared `isolation: required`, a cut takes no workspace.

Run `cutcheck.py` on the cut revision; amend defects and re-run to 0. The
[cut lens](references/cut-lens.md) judges advisories and undecidable matters.
Then write one composite gate through `tickets.py gate`: one critique per
unique lens, feeding one repair and one verification over run scope.

Map every acceptance criterion to an item, the gate, or uncovered
remainder at `<state-root>/runs/<run>/<root>.coverage.md`.

For v2, complete one `draft` before eligibility with assignments, edges,
coverage, `ownership_regions`, and merge-oracle identities. Every assignment
names one `root_generation`; the cut names its content-addressed
`cut_generation` and `assignment_seal` over validated worker fields. Persist
one exact-snapshot receipt through `tickets.py draft-validate`; after cutcheck
and lens pass, compare-and-swap only its digest through `tickets.py seal`.
Post-seal changes require a new validated generation; repeated normalized
validation failure suspends at the correction bound. Absent v2 fields mean
v1; never reinterpret legacy membership, receipts, cohorts, readiness,
claims, or packets.

Never: edit the root ticket's frozen statement.

Return: status; ticket directory; cutcheck; item ids and edges; graph critical
path and level widths; uncovered remainder (`[]` when none); decision_gap
(`[]` when coverable).
