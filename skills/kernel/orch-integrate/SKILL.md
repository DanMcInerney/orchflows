---
name: orch-integrate
description: Adjudicate one returned child result at the join before anything downstream trusts it. Every child result crosses this once.
role: none
---

Require: one child return: its completed
[ticket](../../../contracts/work-item.md), or a bare packet's contracted fields
and originating dispatch.

Grade tickets against Goal and factual Context at the fixed artifact identity
through one outside-independence path per
[verification.md](../../../rules/verification.md) §7. `independence: gate`
defers review; `checker` requires
[work-item.md](../../../contracts/work-item.md)'s `checked_by`; uncovered
Goal claims yield needs-verify. Grade bare returns by their contract. Suspension resumes
from `## Handoff`.

The returning name must match `claimed_by`, `checked_by`, or the re-verifier
named by `tickets.py packet --executor`; reject mismatches and expired claims.
Reject a non-root carrying both `independence: gate` and `checked_by`. But
on a root, `checked_by` is cut reader bookkeeping, never final checker
acceptance: the composite gate decides acceptance. Inspect actual candidate
diffs and Git conflicts, resolve overlaps, regenerate shared derived artifacts
once, and, for required isolation, run `workspace.py check` from
the integrating checkout (exit 6 is caller-vantage failure).

Record blame on the run-state channel; only this join calls `tickets.py set-status`.
An accepted defect set of `[]` from every critique feeding
`<root>.gate.repair` completes that repair here without dispatch through
`tickets.py join-noop-repair <run> <root>.gate.repair --by <join-name>`, the
atomic attributed join-owned transition. Accepted non-blocking findings go to the run's
improvement or successor candidates, never that repair.

Never: treat Suggested files as authority, accept unresolved Git conflicts, or repair here.

Return: the disposition (accepted, rejected(blame), suspended, or needs-verify),
invalidated evidence, and integrated state.
