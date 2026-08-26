---
name: orch-decompose
description: Cut a stamped root ticket into work-item tickets under the pack's slicing. The one decomposer for every domain.
role: planner
---

Require: root [ticket](../../../contracts/work-item.md#root-ticket), stamped
pack slicing and oracle_policy. Reject missing parts by name.

Goal: minimize critical path; every item an atom under
[topology](../../../rules/topology.md) §3.

Emit [work items](../../../contracts/work-item.md) as `<root>.NN` from candidate
files through `tickets.py new <run> --file <candidate>`. Each candidate carries
the root's exact inherited `root_generation`; the completed cut gets one new
validated cut generation and assignment seal.

Carry exact parameters as canonical JSON `--input`, the stamped workspace cell, and `mutations` via
`--mutation`. Give each item an observable objective, write scope (siblings
overlap only when dependency-ordered), isolation, bound, edges, and criteria
with pack oracles and provenance. Stamp `independence: gate` when the gate
covers all authored-here criteria; otherwise `independence: checker`,
regardless of oracle class. Apply topology §3 edges and sole ownership; emit
named §4 assembly. Declared `isolation: required`, a cut takes no workspace.

Run `cutcheck.py` on the cut revision; amend defects and re-run to 0. The
[cut lens](references/cut-lens.md) judges advisories and undecidable matters.
Map every acceptance criterion to an item, the gate, or uncovered
remainder at `<state-root>/runs/<run>/<root>.coverage.md`.

Then write one composite gate through `tickets.py gate`: one critique per
unique lens, feeding one repair and one verification over run scope. Follow
[topology](../../../rules/topology.md) §§8–§10 through `tickets.py
draft-validate` and `tickets.py seal` over the complete cut.

Never: edit the root ticket's frozen statement.

Return: status; ticket directory; cutcheck; item ids and edges; graph critical
path and level widths; uncovered remainder (`[]` when none); decision_gap
(`[]` when coverable).
