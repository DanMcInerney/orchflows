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

Give every member an observable Goal, relevant Context, optional non-binding
Suggested files, isolation, bound, and dependency edges. The executor chooses
implementation and verification. Suggested files may overlap and never grant
authority. Declared `isolation: required`, a cut takes no workspace.

Run `cutcheck.py` on the cut revision; correct structural defects and re-run to 0. The
[cut lens](references/cut-lens.md) judges advisories and undecidable matters.
Then write one composite gate through `tickets.py gate`: one critique per
unique lens, feeding one repair and one verification over the integrated result. Follow
[topology](../../../rules/topology.md) §§8–§10 through `tickets.py
draft-validate` and `tickets.py seal` over the complete cut.

Never: edit the root ticket's frozen statement.

Return: status; ticket directory; cutcheck; item ids and edges; graph critical
path and level widths; decision_gap
(`[]` when coverable).
