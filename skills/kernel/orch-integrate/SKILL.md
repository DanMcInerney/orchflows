---
name: orch-integrate
description: Adjudicate one returned child result at the join before anything downstream trusts it. Every child result crosses this once.
role: none
---

Require: one child return: its completed
[ticket](../../../contracts/work-item.md), or a bare packet's contracted fields
and originating [dispatch](../../../contracts/work-item.md#dispatch); also the
caller write scope.

Grade tickets against every frozen criterion and identity through one
outside-independence path per
[verification.md](../../../rules/verification.md) §10. `independence: gate`
defers authored checks; `checker` requires
[work-item.md](../../../contracts/work-item.md)'s `checked_by`; uncovered
criteria yield needs-verify. Grade bare returns by their contract. Suspension resumes
from `## Handoff`.

The returning name must match `claimed_by`, `checked_by`, or the re-verifier
named by `tickets.py packet --executor`; reject mismatches and expired claims.
Reject a non-root carrying both `independence: gate` and `checked_by`. But
on a root, `checked_by` is cut reader bookkeeping, never final checker
acceptance: the composite gate decides authored acceptance. Confirm `changed_artifacts`,
unchanged evidence, and, for required isolation, run `workspace.py check` from
the integrating checkout (exit 6 is caller-vantage failure).

Apply [result.md](../../../contracts/result.md)'s `return-size` crossing once:
`tickets.py result-grade <run> <id>`. Caller-authored malformed clauses or
missing resolver inputs are `reject(caller)`; executor-authored invalid,
unresolved, or oversized results are `reject(child)`. Record blame on the
run-state channel; only this join calls `tickets.py set-status`. An accepted
`orch-decompose` Result is `cut-accepted`: retain the root's live status.
Accepting `<root>.gate.verify` performs the root's terminal status transition
only from the required-check event identity in its Verification.
An accepted defect set of `[]` from every critique feeding
`<root>.gate.repair` completes that repair here by filing the empty result and
status, without dispatch. Accepted non-blocking findings go to the run's
improvement or successor candidates, never that repair.

For v2, validate exactly one
`- amendment-request: <canonical JSON record>` in a parked worker's Handoff,
including all fields required by [delegation.md](../../../rules/delegation.md).
Route it once per dispatch; neither worker nor join edits its parent. The
caller applies [delegation.md](../../../rules/delegation.md) §14 through
`tickets.py resume-generation`; resume only from its sealed generation or
unchanged packet. The absence of v2 fields means v1; old free-form Handoffs and
claimed or terminal v1 history retain their path.

Never: trust out-of-scope output, rerun covered oracles, or repair here.

Return: the disposition (accepted, rejected(blame), suspended, or needs-verify),
invalidated evidence, and integrated state.
