---
name: orch-integrate
description: Adjudicate one returned child result at the join before anything downstream trusts it. Every child result crosses this once.
role: none
---

Require: one child return: its completed
[ticket](../../../contracts/work-item.md), or a bare packet's contracted fields
and originating dispatch.

Grade Goal and Context at the fixed artifact identity through one
outside-independence path ([verification.md](../../../rules/verification.md) §7).
`independence: gate`
defers review; `checker` requires
[work-item.md](../../../contracts/work-item.md)'s `checked_by`; uncovered
Goal claims yield needs-verify. Grade bare returns by their contract. Suspension
resumes from `## Handoff`.

The returning name and artifact identity must match the committed dispatch-v1
packet and its accepted receipt; reject mismatches and expired attempts.
Inspect candidate Git state: integration owns actual candidate diffs and conflict
adjudication, resolves overlap and ordinary Git conflicts, and performs one
shared-artifact finalization after all candidate joins. It records the fixed
joined identity for the terminal gate. For required isolation, run
`workspace.py check` from the integrating checkout (exit 6 is caller-vantage
failure).

Record blame on run-state. For dispatch v1, only this join calls
`tickets.py dispatch-join` with packet assignment seal/dispatch id, fixed
`outcome` id, and this name. Disposition comes from the validated
outcome envelope, never transport or arbitrary section record. Relay an inline
envelope unchanged through `tickets.py dispatch-outcome` first. Pre-v1 alone
uses `tickets.py set-status`.
An accepted defect set of `[]` from every critique feeding
`<root>.gate.repair` completes that repair here without dispatch through
`tickets.py join-noop-repair <run> <root>.gate.repair --by <join-name>`, the
atomic attributed join-owned transition. Accepted non-blocking findings go to the run's
improvement or successor candidates, never that repair.
For each critique join, pass the accepted subset through a UTF-8 file (or
standard input) with `dispatch-join --accepted-file <path|->`; the protocol
normalizes and binds it against the executor's complete findings. For repair
and verification packet and join operations, pass the fixed artifact with
`--artifact`. For ordinary `<id>.check`, use the same accepted-file seam.
Apply it using
`check <run> <id> --stage <id>.check`; it accepts no findings, and must succeed
before `checked_by` is trusted.

Never: treat Suggested files as authority, accept unresolved Git conflicts, or repair here.

Return: the disposition (accepted, rejected(blame), suspended, or needs-verify),
invalidated evidence, and integrated state.
