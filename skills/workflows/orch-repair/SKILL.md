---
name: orch-repair
description: Fix accepted verified defects with the smallest coherent change. Use inside the gate or on any accepted defect set.
role: worker
---

Require: the packet's immutable `GatePlan -> CritiqueAdjudication` ledger. Its
accepted defect set names each finding or cause with its evidence; an empty set
is a legal no-op only when every ordered adjudication is empty.

Make the smallest change that coherently fixes the set, per
[rules/verification.md](../../../rules/verification.md) §5 — smallest
by blast radius, not by line count. Record the proof methods and observations
chosen for the repaired Goal portions, plus any repository check whose covered
identity changed.

Never: fix a finding not in the set; decline one without citing the
evidence that it does not hold; claim a fix without fresh evidence.

Return: the exact output artifact identity, per-finding disposition with fresh
evidence, and anything queued. The join appends `RepairOutcome` to that exact
predecessor ledger.
