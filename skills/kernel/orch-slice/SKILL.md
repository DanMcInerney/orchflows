---
name: orch-slice
description: Cut a stamped root ticket into work-item tickets under the pack's slicing. The one decomposer for every domain.
role: planner
---

Require: root [ticket](../../../contracts/work-item.md#roots-decomposition-and-integration),
the stamped pack's craft — the cut works under its `## Slicing` and
`## Evidence` sections. Reject missing parts by name.

Goal: minimize critical path; every item an atom under
[topology](../../../rules/topology.md) §3.

Emit [work items](../../../contracts/work-item.md) as `<root>.NN` from candidate
files through `tickets.py new <run> --file <candidate>`. Each candidate carries
the root's exact inherited `root_generation`, the stamped pack's `executor`,
and `independence: gate`. When the pack's `assembly` cell names a stage, emit
one terminal assembly item at that stage; when it says none, emit no
assembly item. The completed cut gets one new validated cut generation and
assignment seal while retaining its one root generation.

Write each member as the brief a fresh child needs, with isolation, bound,
edges. Open on its role and authority boundary. Goal: one observable end
result with the evidence behind it. Context: pointers by identity, the root
ticket path required reading, never a dump. Details: prescribe as hard as your
investigation earned and no harder — read-lists, anchors, steps, non-scope,
done commands whose exit codes it captures, and what its report must cover.
Every prescription carries its evidence and an escape hatch: deviate where it
would miss Goal, reporting that. Where you did not investigate, leave the
choice. Details may overlap and never grant
authority. Declared `isolation: required`, a cut takes no workspace.

Write no gate family: a critique is one `tickets.py judge` brick over the
delivered members and the repair answering it one `tickets.py do` brick, both
sequenced by the caller's prose.
Run `cutcheck.py` on the complete assignment draft; correct
structural defects and re-run to 0. The [cut lens](references/cut-lens.md)
judges advisories and undecidable matters. Follow
[topology](../../../rules/topology.md) §§8–§10 over that exact cut.

Never: edit the root ticket's frozen statement.

Return: status; ticket directory; cutcheck; item ids and edges; graph critical
path and level widths; decision_gap
(`[]` when coverable).
