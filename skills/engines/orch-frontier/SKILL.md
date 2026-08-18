---
name: orch-frontier
description: Execute a ticket dependency graph by rolling frontier dispatch — every ready ticket in flight. Use whenever items have dependency edges.
role: none
---

Require: a run's ticket directory — tickets issued through `tickets.py`
— forming a finite acyclic dependency graph, and the run's bound, from
the root ticket or the caller.

Open by dispatching the ready frontier — every ticket whose
`depends_on` are all `complete` — one lane each. Per lane: claim
through `tickets.py claim`; take the packet `tickets.py packet` emits — a refusal is the
cut's defect; spawn one fresh child on it per
[rules/delegation.md](../../../rules/delegation.md) §1–§2, role per
[rules/roles.md](../../../rules/roles.md) §4, the ticket's executor as
the applied skill; host depth per
[references/profiles.md](references/profiles.md). Each ticket takes one
outside-independence path. Only where its `independence` reads `checker`,
an oracle is `authored-here`, and the ticket is not already checked, dispatch
`orch-critique` as one fresh child on the same claimed ticket, on
`tickets.py packet`'s `--executor orch-critique` checker packet form.
For a gate-deferred or pre-existing-only ticket, never
emit that checker packet. Then, where its pass invalidates an entry whose oracle is judged, dispatch
that packet's `--executor orch-verify` form; else re-run the
invalidated deterministic oracles at the checked identity here, the
rest covered ([rules/verification.md](../../../rules/verification.md) §10).
A root cut reader is the exception: the root's cut takes that checker where it has three or more `<id>.NN` or
`cutcheck.py` reported an advisory; the `<id>.NN` stay `pending` until
`checked_by` is set and this engine's own `cutcheck.py` re-run — the
re-verification — reads exit 0, which below the threshold accepts the
cut alone.
Accept every return once through `orch-integrate` under this engine's
write scope: `suspended` parks the item for the next claim to resume
from; any other grades the declared isolation and
integrates into the run workspace per the pack's workspace cell — a
conflict routes to its conflict binding. After each merge batch run the
standards owner's required checks on the integrated tip, the run's notes
carrying the tip's revision: a lane runs its ticket's own oracles,
nothing wider, its green provisional until the tip's, and a red
tip blocks the next dispatch but its repair's.

Watch each lane per [references/profiles.md](references/profiles.md).
Recompute on every event — a result landing, a new ticket file, a
suspension, a stale claim. Promote each newly ready `pending` ticket
through `tickets.py ready` and dispatch it at once, reading its
`skipped` list as state to report, never nothing
ready; set each `pending` ticket depending on
any other terminal status to `blocked`, naming its blocker — a
failure blocks exactly its dependents. A parked item's claim never goes
stale, its dependents wait, and a caller that cannot satisfy the
excluded action exits with the parked remainder. Exit when no
ticket is `ready` or `pending` and no dispatch is live; `limited` when
the bound is spent with tickets open.

Never: hold a ready ticket back to batch it; hide a blocked
subtree in a summary of successes; re-order the graph to dodge a
failure.

Return: status; per-ticket results by identity; the graph's terminal
state as verification; the open remainder with what blocks it.
