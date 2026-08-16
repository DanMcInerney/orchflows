---
name: orch-decompose
description: Cut a stamped root ticket into work-item tickets under the pack's slicing. The one decomposer for every domain.
role: planner
---

Require: a root [ticket](../../../contracts/work-item.md#root-ticket) — `executor: orch-decompose`, a `pack` stamp, a
`## Completion test` whose every criterion names its oracle, and the stamped pack's `required_spec_fields` among its
`## Fixed inputs` — plus that pack's slicing reference and oracle_policy. Reject otherwise, naming what is missing.

Cut the root ticket into [work items](../../../contracts/work-item.md) under the slicing — cut count per
[rules/topology.md](../../../rules/topology.md) §3 — issued as `<root>.NN` into the root's own run directory through
`tickets.py new` (`pending` with a non-empty `depends_on`, else `ready`). Each item takes its executor from the pack's
executor cell, the root's `pack` stamp, `isolation` per the pack's workspace cell and
[references/isolation.md](references/isolation.md), a write scope overlapping only siblings it is dependency-ordered
with, a bound, its edges, and a completion test whose criteria name oracles from the pack's oracle policy, each with its
provenance; `independence: gate` when a `judged` criterion there rides the final gate. Resolve every deterministic
oracle against the workspace before freezing the item. Emit the terminal assembly item when the pack's `assembly`
cell names a skill, on [rules/topology.md](../../../rules/topology.md) §4's terms.

Then run `cutcheck.py <run> --baseline <the revision the set was cut from>`, repair every cut defect it reports with
`tickets.py amend <run> <id> --section '<name>' --file <path>` on the still-unclaimed ticket and re-run it to exit 0, and
read its advisory lines; what it cannot decide is [references/cut-lens.md](references/cut-lens.md)'s to judge. Only after that
repair write the gate stubs — `tickets.py gate <run> <root> --lens <a label per stamped lens, the pack's domain by
default> --write-scope <the run's scope>` — behind the assembly item where the pack named one, so the gate depends on it.

Map every acceptance criterion to an item, to the gate when the pack's lens owns it, or to uncovered remainder; that
map's durable home is `<state-root>/runs/<run>/coverage.md`. A criterion no slicing covers returns a decision gap naming
them; the rest is still cut, never a forced slicing (§3). When the caller asked for a plan, the cut ends in the root
ticket's `## Handoff` as a `plan_gate` suspension, resumed on approval.

Never: branch on the domain here; widen the run's scope; edit the root ticket.

Return: item ids with edges, the ticket directory, uncovered remainder (`[]` when none), decision_gap (`[]` when
coverable), and the cutcheck result.
