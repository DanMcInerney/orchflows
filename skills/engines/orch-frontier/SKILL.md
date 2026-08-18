---
name: orch-frontier
description: Execute a ticket dependency graph by rolling frontier dispatch — every ready ticket in flight. Use whenever items have dependency edges.
role: none
---

Require: one finite acyclic run ticket graph issued through `tickets.py`,
plus its bound from the root ticket or caller.

Dispatch the ready frontier — tickets whose `depends_on` are all
`complete` — one lane each. Claim through `tickets.py claim`; take the
`tickets.py packet` (refusal is a cut defect); spawn one fresh child per
[rules/delegation.md](../../../rules/delegation.md) §1–§2, role per
[rules/roles.md](../../../rules/roles.md) §4, applying its executor;
host depth per
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
A root cut reader is the exception: the cut takes that checker with three or more `<id>.NN` or when
`cutcheck.py` reported an advisory; the `<id>.NN` stay `pending` until
`checked_by` is set and this engine's own `cutcheck.py` re-run — the
re-verification — reads exit 0, which below the threshold accepts the
cut alone.
Accept every return once through `orch-integrate` under this engine's
write scope: `suspended` parks it for resumption; any other grades isolation and
integrates into the run workspace per the pack's workspace cell — a
conflict routes to its conflict binding. After each merge batch run the
standards owner's required checks on the integrated tip, the run's notes
carrying the tip's revision: a lane runs its ticket's own oracles,
nothing wider, its green provisional until the tip's, and a red
tip blocks the next dispatch but its repair's.

Watch each lane per [references/profiles.md](references/profiles.md).
Recompute after results, new tickets, suspension, or stale claims. Promote
each ready `pending` ticket through `tickets.py ready`; dispatch it at once,
reporting its `skipped` list, never nothing ready; set each `pending` ticket depending on
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
