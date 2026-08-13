---
name: orch-decompose
description: Cut a stamped spec into work-item tickets under the pack's slicing. The one decomposer for every domain.
role: planner
---

Require: a frozen [spec](../../../contracts/spec.md) whose routing stamp
names a pack, carrying every field the pack's `required_spec_fields`
cell demands — reject otherwise, naming what's missing — and the pack's
slicing reference and oracle_policy.

Cut the spec into [work items](../../../contracts/work-item.md) under
the slicing — cut count per
[rules/topology.md](../../../rules/topology.md) §3: each item gets its
executor from the pack's binding, the spec's `pack` stamp, a write
scope overlapping only siblings it is dependency-ordered with, a bound,
and a completion test whose criteria name oracles from the pack's
oracle policy, each with its oracle provenance; `independence: gate`
when a `judged` criterion there rides the final gate. Add dependency
edges; issue `status: pending` for a non-empty `depends_on`, `ready`
otherwise. Emit at most one terminal assembly item when the pack's
`assembly` cell names a skill, depending on every unit item, its
completion test carrying the final gate's criteria.

Map every acceptance criterion to an item, to the gate when the pack's
lens owns it, or to uncovered remainder in the worklog. A criterion no
slicing covers returns a decision gap naming exactly those criteria;
the covered remainder is still cut into items, never a forced slicing
(§3).

Never: branch on the domain in this body; widen the run's scope; edit
the spec.

Return: item ids with edges, the ticket directory, uncovered remainder
(`[]` when none), and decision_gap (`[]` when coverable).
