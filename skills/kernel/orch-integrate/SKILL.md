---
name: orch-integrate
description: Adjudicate one returned child result at the join before anything downstream trusts it. Every child result crosses this once.
role: none
---

Require: one child return — the completed ticket per
[work-item.md](../../../contracts/work-item.md), or a bare packet's
contracted return fields with the originating
[delegation packet](../../../contracts/work-item.md#dispatch) — plus the
caller's own write scope.

Grade by dispatch type: a work item takes the ticket grade —
verification must cover every frozen criterion at its stated
identities, with independence per
[rules/verification.md](../../../rules/verification.md) §10
(`authored-here` coverage rides `independence`: `gate` defers to the
downstream gate, `checker` requires `checked_by`), needs-verify
reachable; `suspended` is ticket-grade only, routing to resume from the
ticket's `## Handoff`. A bare packet takes the packet grade — no
completion test, so disposition stays accepted or rejected(blame) only;
an exclusion-stop is adjudicated on its contracted return per
[work-item.md](../../../contracts/work-item.md#dispatch) — the caller
re-dispatches with a ticket when resume matters.

Check always: the returning child's name matches the ticket's
`claimed_by`, its `checked_by`, or the re-verifier your own
`tickets.py packet --executor` named — a mismatch is rejected(child), a
lapsed claim returning outside its bound, never a caller under-supply;
`changed_artifacts` per
[work-item.md](../../../contracts/work-item.md#dispatch); nothing a
verification entry covers has changed since it was produced. For
`isolation: required`, run `workspace.py check <run> <id> --base <rev>`
from the integrating checkout before accepting; exit 6 is a caller
vantage error, not a verdict.

Classify by blame per the
[work-item contract](../../../contracts/work-item.md#dispatch) and
record the class through `tickets.py run-state --note`. The join alone
writes terminal status (`tickets.py set-status`). At a critique join,
an accepted defect set of `[]` across every critique the
`<root>.gate.repair` depends on completes that repair here — empty
disposition filed through `tickets.py result`, then
`set-status complete` — with no dispatch.

Never: trust out-of-scope output; re-run a covered oracle; repair the
result yourself.

Return: disposition — accepted, rejected(blame), suspended (route to
resume), or ticket-grade-only needs-verify with the exact uncovered
criteria — plus invalidated evidence and the integrated state.
