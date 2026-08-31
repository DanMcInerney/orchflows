---
name: orch-integrate
description: Adjudicate one returned child result at the join before anything downstream trusts it. Every child result crosses this once.
role: none
---

Require: one child return — a completed
[ticket](../../../contracts/work-item.md), or a bare return's contracted fields
and originating dispatch, graded by its contract.

Grade Goal and Context at the fixed artifact identity through one
outside-independence path ([verification.md](../../../rules/verification.md) §7).
`independence: gate`
defers review; `checker` requires
[work-item.md](../../../contracts/work-item.md)'s `checked_by`; uncovered
Goal claims yield needs-check. Suspension resumes from `## Report`.

The returning name and artifact identity must match the dispatch-v1
attempt; reject mismatches and expired attempts.
Integration owns actual candidate diffs and conflict adjudication: resolve
overlap and ordinary Git conflicts, perform one shared-artifact finalization
after all candidate joins, and record the fixed joined identity the terminal
gate runs on.
Under required isolation run `workspace.py check` from the integrating checkout
(exit 6 is caller-vantage failure).

Record blame on run-state. Under dispatch v1 only this join runs
`tickets.py land`, committing `tickets.py dispatch-join` with the attempt's
assignment seal/dispatch id, fixed
`outcome` id, and this name; an inline envelope rides `--outcome-file`
unchanged. Disposition is land's `done` reading, or `land --status` when the
ticket declares none; never the child's. Pre-v1 alone
uses `tickets.py set-status`.
An accepted defect set of `[]` from every critique feeding
`<root>.gate.repair` completes that repair here without dispatch through
`tickets.py join-noop-repair <run> <root>.gate.repair --by <join-name>`, the
atomic attributed join-owned transition. Accepted non-blocking findings go to run
improvement or successor candidates, never that repair.
Every critique join passes its accepted subset through a UTF-8 file (or standard
input) with `land --accepted-file <path|->`, normalized and bound
against the executor's complete findings. Repair dispatches
and joins pass the fixed artifact with `--artifact`. Ordinary
`<id>.check` uses that same seam through `check <run> <id> --stage <id>.check`;
it accepts no findings and must succeed before `checked_by` is trusted.

Never: treat Details as authority, accept unresolved Git conflicts, or repair here.

Return: the disposition (accepted, rejected(blame), suspended, needs-check),
invalidated evidence, and integrated state.
