---
name: orch-frontier
description: Execute a ticket dependency graph by rolling frontier dispatch — every ready ticket in flight. Use whenever items have dependency edges.
role: none
---

Require: a run's ticket directory — tickets issued through `tickets.py
new` or `tickets.py instantiate` — forming a finite acyclic dependency
graph, and the run's bound, from the root ticket or named by the caller
for an ad-hoc set.

Open by dispatching the whole ready frontier — every ticket whose
`depends_on` are all `complete` — one lane per ticket. Per lane: claim
through `tickets.py claim`; take the packet `tickets.py packet` emits — a refusal is the
cut's defect; spawn one fresh child on it per
[rules/delegation.md](../../../rules/delegation.md) §1–§2, role per
[rules/roles.md](../../../rules/roles.md) §4, the ticket's executor as
the applied skill; host depth per
[references/profiles.md](references/profiles.md). Where the ticket's
`independence` reads `checker` and a criterion's oracle is
`authored-here`, dispatch `orch-critique` as one further fresh child on
the same claimed ticket, on the packet `tickets.py packet <run> <id>
--reply-to <name> --executor orch-critique` emits; then, where the
checker's pass names an invalidated entry, re-run the completion test
at the checked identity through `orch-verify` on that packet's
`--executor orch-verify` form, else the join reads the entries as
covered ([rules/verification.md](../../../rules/verification.md) §10).
Accept every return once through `orch-integrate` under this engine's
write scope: `suspended` parks the item, claim kept, for the next claim
to resume from; any other disposition grades the declared isolation and
integrates into the run workspace per the pack's workspace cell — a
conflict routes to its conflict binding.

Watch each lane per [references/profiles.md](references/profiles.md).
Recompute on every event — a result landing, a new ticket file in the
run's directory, a suspension, a claim going stale. A parked item's
claim never goes stale. Promote each `pending` ticket
whose `depends_on` are all `complete` to `ready` through `tickets.py
ready` and dispatch it at once; set each `pending` ticket depending on a
ticket in any other terminal status to `blocked`, naming its blocker — a
failure blocks exactly its dependents. A parked item's dependents wait
for the caller to satisfy the excluded action and re-ready it; a caller
that cannot exits with the parked remainder. Exit when no
ticket is `ready` or `pending` and no dispatch is live; `limited` when
the run bound is spent with tickets open.

Never: hold a ready ticket back to batch it with others; hide a blocked
subtree in a summary of the successes; re-order the graph to dodge a
failure.

Return: status; per-ticket results by identity; the graph's terminal
state as verification; and the open remainder with what blocks it.
