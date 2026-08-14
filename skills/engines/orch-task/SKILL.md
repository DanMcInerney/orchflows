---
name: orch-task
description: Run one ready ticket through its named executor to one accepted result. The unit engine every larger shape composes.
role: none
---

Require: one `ready` [ticket](../../../contracts/work-item.md) —
issued by decomposition, or an
[ad-hoc ticket](../../../docs/vocabulary.md) the orchestrator writes
before claim. Refuse a ticket whose completion test lacks a named
oracle with its oracle_class on any criterion, naming the missing
part — a request that cannot name one belongs to orch-spec.

Claim the ticket (set `claimed_by`, `claimed_at`, status `claimed`).
Isolate the item's workspace per the workspace cell of the pack the
ticket names — a ticket naming none works at its plain-path write
scope — asking for it at dispatch and establishing it from inside —
the child's first act there, per orch-workspace — with its identity,
provenance and baseline evidence riding the result. Dispatch exactly
one fresh child through `orch-delegate` — or execute inline under
[rules/delegation.md](../../../rules/delegation.md) §2's independence
condition; the ladder's cheaper rungs apply inside the child — naming
the ticket's executor as the applied skill, with the ticket path as
the packet. `tickets.py packet` emits that packet or names the part
the ticket is missing; a refusal here is the cut's defect, never read
the body to repair it yourself.

When a criterion's oracle carries `authored-here` provenance and the
ticket's `independence` reads `checker`, dispatch `orch-check` as one
further fresh child on the same packet shape, then re-run the
completion test through `orch-verify` at the checked result — its
entries supersede what they cover, per
[rules/verification.md](../../../rules/verification.md) §10.

Accept the result once through `orch-integrate`. On `suspended` — the
executor has written its `## Handoff` — set status `suspended`, claim
fields kept, for the next claim to resume from it; never the join's
reject path. On any other disposition, integrate the result into the
run workspace per the ticket's pack workspace cell when one is named —
a conflict during integration routes to the cell's conflict binding;
derived evidence the cell defines is refreshed at the fixed revision
before any lens runs — on needs-verify run `orch-verify` for exactly
the uncovered criteria; on rejected record the blame class. Record
the join's terminal status in the ticket.

Never: run two executors for one ticket; accept a result that skipped
the join; re-verify evidence the join already accepted; call a
workspace established on a result carrying no such evidence.

Return: the completed ticket per
[work-item.md](../../../contracts/work-item.md).
