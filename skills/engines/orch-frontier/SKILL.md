---
name: orch-frontier
description: Execute a ticket dependency graph by rolling frontier dispatch — every ready ticket in flight. Use whenever items have dependency edges.
role: none
---

Require: a run's ticket directory — tickets issued through `tickets.py new` or `tickets.py instantiate` — forming a finite acyclic
dependency graph, and the run's bound, from the root ticket or named by the caller for an ad-hoc set. Refuse a ticket whose completion
test leaves a criterion without a named oracle and its oracle_class, naming the missing part.

Open by dispatching the whole ready frontier — every ticket whose `depends_on` are all `complete` — in parallel, one lane per ticket;
a ticket waiting on a dependency stays `pending`. Each lane runs its one ticket to one accepted result. Claim it through `tickets.py
claim` (`claimed_by`, `claimed_at`, status `claimed`). Isolate the item per the workspace cell of the pack the ticket names — a ticket
naming none works at its plain-path write scope — the child establishing the isolation the ticket declares as its own first act and
recording what it derives from and that its baseline is clean, so a later failure is attributable to the run and not to the starting
state; only an instance inside can prove what it got, which `workspace.py check` grades against the dispatch revision before the
merge. Establishment rides the complete delegation packet `tickets.py packet` emits: a packet refusal names the part the ticket lacks
and is the cut's defect, never read the body to repair it yourself. Spawn exactly one fresh child on that packet, dispatched per
[rules/delegation.md](../../../rules/delegation.md) §1-§2 with its role resolved per [rules/roles.md](../../../rules/roles.md) §4,
the ticket's executor as the applied skill — an `executor: script:<path>` runs the named script and spawns nothing — or execute
inline under that same §2's independence condition. Where a criterion's oracle
carries `authored-here` provenance and the ticket's `independence` reads `checker`, dispatch `orch-critique` as one further fresh
child on that same claimed ticket — the ticket's own write scope as that packet's `authority`, which is what makes the critic the
corrector — whose result and authored checks await the coverage, then re-run the completion test through
`orch-verify` at the checked result identity — its entries supersede what they cover, per
[rules/verification.md](../../../rules/verification.md) §10. Accept the child return once through `orch-integrate` under this engine's
write scope: on `suspended` — the executor has written its `## Handoff` — the item parks, claim fields kept, for the next claim to
resume from, never the join's reject path; on any other disposition grade the declared isolation, integrate into the run workspace per
that same pack cell where one is named — a conflict routes to the cell's conflict binding — and record the join's terminal status.

Arm the caller's own re-check of every open ticket's durable file at dispatch, per §11 of that same rules/delegation.md, whose watch mechanics
and this host's role bindings are [references/profiles.md](references/profiles.md) — a child's closing message is a courtesy, never the signal
this engine waits on. Then recompute on every event — a result landing (by message or by that re-check reading a ticket `complete`), a new ticket
file appearing in the run's directory, a suspension parking its item, a claim going stale — never on a schedule of rounds: the tickets are the
record and `tickets.py worklog <run>` renders the run view from them. Reclaim a stale claim per
[contracts/work-item.md](../../../contracts/work-item.md): nothing written to the ticket's own sections or to an artifact its `## Result` names
for longer than its bound, and a parked item's claim never goes stale. Promote each `pending` ticket whose `depends_on` are now all `complete` to
`ready` through `tickets.py ready`; set each `pending` ticket depending on a `failed`, `blocked`, or `limited` ticket to `blocked`, naming its
blocker — a failure blocks exactly its dependents, the rest of the graph rolls on; dispatch everything newly `ready` immediately. The join sets a
root ticket `complete` when its `<id>.gate.verify` completes; a dependent of the root waits for that. A named template is instantiated by
`tickets.py instantiate <template> --run <run> --set k=v`, then run by this engine over the resulting directory. A parked item is neither
complete nor failed and its dependents wait: the caller satisfies the excluded action and re-readies the ticket; a caller that cannot exits with
the parked remainder — resume is its own caller's re-dispatch, never this engine's. The engine exits when no ticket is `ready` or `pending` and
no live dispatch remains, and exits `limited` when the run bound is spent with tickets still open; bounds inherit downward.

Never: start a dependent before its dependencies are complete; run two executors for one ticket; hold a ready ticket back to batch it
with others; accept a result that skipped the join; hide a blocked subtree in a summary of the successes; re-order the graph to dodge
a failure.

Return: status; per-ticket results by identity; the graph's terminal state as verification; and the open remainder with what blocks it.
