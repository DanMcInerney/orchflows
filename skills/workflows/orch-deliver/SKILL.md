---
name: orch-deliver
description: Take one stamped spec to a verified deliverable through plan, rolling frontier, one gate, and a final verification. Any pack, one body.
role: none
---

Require: a frozen, routing-stamped [spec](../../../contracts/spec.md).
This body never names a domain; every domain fact comes from the
stamped pack's cells.

Open the run: `orch-worklog`, then `orch-workspace` for the run's
target per the pack's workspace cell. Decompose through
`orch-decompose`; a returned decision_gap rides this body's own Return
and routes to the caller.

Plan gate: when the caller asked for a plan, or the spec sets
`plan_gate`, stop here and return the plan — items, edges, budgets,
risks, uncovered remainder. Execution resumes only on approval, against
the frozen plan.

Execute the graph through `orch-frontier`. When the frontier exits
carrying a failed, blocked, or unparked-open item, set the worklog
terminal state through `orch-worklog` and return per
[rules/composition.md](../../../rules/composition.md) rule 8 without
crossing the gate. A parked-only remainder returns the same way but
leaves `terminal` empty — the run stays open; re-invoked on an open
run, this body skips decomposition and re-enters the frontier over
the existing tickets; the gate crosses only once every unit item is
complete. Otherwise the terminal assembly item, if the pack declares
one, runs last and invalidates unit verification it rewrites, per
[rules/topology.md](../../../rules/topology.md) rule 4 — the gate
re-verifies the assembled artifact. Cross one `orch-review-fix` gate,
supplying its Require by name: the fixed result identity (the
assembled artifact), the pack's stamped lens, the pack's oracle
policy, the spec, the standards owner by pointer where the workspace
names one, the pack's craft reference, and the write scope; record
anything it queues into the worklog's `queued_scope`.
Finish with `orch-verify` over the spec's acceptance under the pack's
oracle policy, reusing the gate's covered verdicts and verifying only
uncovered criteria per
[rules/verification.md](../../../rules/verification.md) §7; a judged or
evidence overall verdict is reported as such, never laundered into a
deterministic green. Set the worklog terminal state through
`orch-worklog` at close.

Never: edit the spec; run a second gate; end a judged run on its own
claimed green; cross the gate with an open unit item.

Return: status, result identity, changed artifacts, final verification,
uncovered remainder, decision_gap, anything the gate queued, and
feedback.
