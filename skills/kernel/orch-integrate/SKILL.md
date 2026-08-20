---
name: orch-integrate
description: Adjudicate one returned child result at the join before anything downstream trusts it. Every child result crosses this once.
role: none
---

Require: one child return — its completed ticket per
[work-item.md](../../../contracts/work-item.md), or a bare packet's
contracted return fields with the originating
[delegation packet](../../../contracts/work-item.md#dispatch) — plus the
caller write scope.

Grade a work item by its ticket: verification covers every frozen criterion
at its identities through one outside-independence path per
[rules/verification.md](../../../rules/verification.md) §10
(`authored-here` coverage rides `independence`: `gate` defers to the
gate, `checker` requires `checked_by`), needs-verify reachable. `suspended`
resumes from `## Handoff`. Grade a bare packet by its contract; after
exclusion-stop, use a ticket only when resume matters.

Require the returning name to match `claimed_by`, `checked_by`, or the
re-verifier your `tickets.py packet --executor` named; reject mismatch(child)
and a lapsed claim outside its bound;
reject a non-root ticket carrying both `independence: gate` and `checked_by`;
on a root, `checked_by` is cut reader bookkeeping, never final checker
acceptance — authored-here acceptance rides the composite gate;
`changed_artifacts` per
[work-item.md](../../../contracts/work-item.md#dispatch); nothing a
verification entry covers has changed since it was produced. For
`isolation: required`, run `workspace.py check <run> <id> --base <rev>`
from the integrating checkout; exit 6 is a caller-vantage error, not a verdict.
Apply [result.md](../../../contracts/result.md)'s `return-size` crossing:
`tickets.py result-grade <run> <id>`; attribute each finding through the
work-item blame rule. Malformed caller-authored clauses and unavailable
caller/host resolver inputs are `reject(caller)`; an invalid, unresolved, or
oversized result the executor filed is `reject(child)`.

Classify blame per
[work-item contract](../../../contracts/work-item.md#dispatch), recording
writes through `tickets.py run-state --note`. The join alone
writes terminal status (`tickets.py set-status`). At a critique join,
an accepted defect set of `[]` across every critique the
`<root>.gate.repair` depends on completes that repair here — empty
disposition filed through `tickets.py result`, then
`set-status complete` — with no dispatch.

Never: trust out-of-scope output; re-run a covered oracle; repair it.

Return: disposition — accepted, rejected(blame), suspended (route to
resume), or ticket-grade-only needs-verify with uncovered
criteria — plus invalidated evidence and the integrated state.
