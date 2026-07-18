---
name: orch-integrate
description: Adjudicate one returned child result at the join before anything downstream trusts it. Every child result crosses this once.
role: none
---

Require: one child return — the completed ticket per
[work-item.md](../../../contracts/work-item.md), or a bare packet's
contracted return fields with the originating
[delegation packet](../../../contracts/delegation.md) — plus the
caller's own write scope.

Grade by dispatch type: a work item takes the ticket grade — verification must cover every
frozen criterion at its stated identities, with independence per [rules/verification.md](../../../rules/verification.md) §10
(`authored-here` coverage rides `independence`: `gate` defers to the downstream gate, `checker` requires `checked_by`),
needs-verify reachable; `suspended` is ticket-grade only, routing to resume from the ticket's `## Handoff`. A bare packet
takes the packet grade — no completion test, so disposition stays accepted or rejected(blame) only; an exclusion-stop is
adjudicated on its contracted return per [delegation.md](../../../contracts/delegation.md) — the caller re-dispatches with a ticket when resume matters.

Check always: `changed_artifacts` lie inside the write scope, else
rejection regardless of verdicts; nothing a verification entry covers has
changed since it was produced; a non-empty write scope's return must name
its changed artifacts, any unattributed change is rejected(child). Reuse
covered, uninvalidated evidence; re-verify nothing it already proves.

Classify any failure by blame per the
[delegation contract](../../../contracts/delegation.md) and record the class
in the worklog — the ticket when the run keeps none. The join alone writes terminal status.

Never: trust out-of-scope output; re-run a covered oracle; repair the
result yourself; reach needs-verify on a packet-graded return; treat
`suspended` as a failure or let the child write terminal status.

Return: disposition — accepted, rejected(blame), suspended (route to
resume), or ticket-grade-only needs-verify with the exact uncovered
criteria — plus invalidated evidence and the integrated state.
