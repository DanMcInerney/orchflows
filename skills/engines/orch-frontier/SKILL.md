---
name: orch-frontier
description: Execute a ticket dependency graph by rolling frontier dispatch — every ready ticket in flight. Use whenever items have dependency edges.
role: none
---

Require: a run's ticket directory forming a finite acyclic dependency
graph, and the run's bound — from the spec, or named by the caller
for an ad-hoc set.

Open by dispatching the whole ready frontier — every ticket whose
`depends_on` are all `complete` — in parallel through `orch-task`, one
dispatch per ticket, no two sharing a write scope; a ticket waiting on
a dependency stays `pending`. Then recompute on every event — a result
landing, a suspension parking its item, a claim's lease expiring —
never on a schedule of rounds: record what landed in the worklog —
the tickets alone are the record when the run keeps none; reclaim
stale claims per [rules/delegation.md](../../../rules/delegation.md)
§11 (a parked item's claim never goes stale); promote
each `pending` ticket whose `depends_on` are now all `complete` to
`ready`; set each `pending` ticket depending on a `failed`, `blocked`,
or `limited` ticket to `blocked`, naming its blocker — a failure
blocks exactly its dependents, the rest of the graph rolls on;
dispatch everything newly `ready` immediately. A suspension parks its
item at the event step — neither complete nor failed, its dependents
wait: the caller satisfies the excluded action at that step and
re-readies the ticket; a caller that cannot satisfy it exits with the
parked remainder — resume is its own caller's re-dispatch, never this
engine's. The engine exits when no ticket is `ready` or `pending` and
no live dispatch remains — parked items return in the open remainder —
and exits `limited` when the run bound is spent with tickets still
open; bounds inherit downward.

Never: start a dependent before its dependencies are complete; hold a
ready ticket back to batch it with others; hide a blocked subtree in a
summary of the successes; re-order the graph to dodge a failure.

Return: per-ticket results, the graph's terminal state, and the open
remainder with what blocks it.
