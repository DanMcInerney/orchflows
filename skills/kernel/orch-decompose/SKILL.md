---
name: orch-decompose
description: Cut a stamped root ticket into work-item tickets under the pack's slicing. The one decomposer for every domain.
role: planner
---

Require: root [ticket](../../../contracts/work-item.md#roots-decomposition-and-integration),
stamped pack slicing and evidence. Reject missing parts by name.

Goal: minimize critical path; every item an atom under
[topology](../../../rules/topology.md) §3.

Emit [work items](../../../contracts/work-item.md) as `<root>.NN` from candidate
files through `tickets.py new <run> --file <candidate>`. Each candidate carries
the root's exact inherited `root_generation`, the stamped pack's `executor`,
and `independence: gate`. When the pack's `assembly` cell names a skill, emit
one terminal assembly item with that binding; when it says none, emit no
assembly item. The completed cut gets one new validated cut generation and
assignment seal while retaining its one root generation.

Give every member an observable Goal, relevant Context, optional non-binding
Suggested files, isolation, bound, and dependency edges. What an executor then
decides is [work-item.md](../../../contracts/work-item.md)'s. Suggested files
may overlap and never grant authority. Declared `isolation: required`, a cut
takes no workspace.

Write the sole composite gate through `tickets.py gate`: one critique per
unique lens, feeding one repair and one verification over the integrated result.
Then run `cutcheck.py` on that complete gate-bearing assignment draft; correct
structural defects and re-run to 0. The [cut lens](references/cut-lens.md)
judges advisories and undecidable matters. Follow
[topology](../../../rules/topology.md) §§8–§10 through
`tickets.py draft-validate` and `tickets.py seal` over the exact same complete
cut.

Never: edit the root ticket's frozen statement.

Return: status; ticket directory; cutcheck; item ids and edges; graph critical
path and level widths; decision_gap
(`[]` when coverable).
