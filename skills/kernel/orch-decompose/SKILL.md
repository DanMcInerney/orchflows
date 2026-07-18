---
name: orch-decompose
description: Cut a stamped spec into work-item tickets under the pack's slicing. The one decomposer for every domain.
role: planner
---

Require: a frozen [spec](../../../contracts/spec.md) whose routing stamp
names a pack, carrying every field the pack's `required_spec_fields`
cell demands — reject otherwise, naming the missing fields — and the
pack's slicing reference.

Cut the spec into [work items](../../../contracts/work-item.md) under
the slicing — cut count per
[rules/topology.md](../../../rules/topology.md) §3: each item gets its
executor from the pack's binding, the spec's `pack` stamp,
`independence: gate` when the gate re-verifies it, a disjoint write
scope strictly inside the run's scope, a bound, and a completion test
whose criteria name oracles from the pack's oracle policy, each with
its oracle provenance. A spec defect surfaced while cutting is
repaired in place, the correction recorded in the worklog. Add
dependency edges; issue `status: pending` for a non-empty `depends_on`,
`ready` otherwise. Emit at most one terminal assembly item when the
slicing declares one, depending on every unit item, its completion
test carrying the final gate's criteria.

Map every acceptance criterion to an item, to the gate when the pack's
lens owns it, or to uncovered remainder in the worklog. When the
slicing cannot cover most criteria, return a decision gap naming them
(§3) — never a forced slicing.

Never: branch on the domain in this body; widen the run's scope; repair
a spec silently.

Return: item ids with edges, the ticket directory, uncovered remainder
(`[]` when none), and decision_gap (`[]` when coverable).
