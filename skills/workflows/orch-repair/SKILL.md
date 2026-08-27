---
name: orch-repair
description: Fix accepted verified defects with the smallest coherent change. Use inside the gate or on any accepted defect set.
role: worker
---

Require: the accepted defect set the ticket Context names — each
finding or cause with its evidence; an empty set is a legal dispatch
whose result is no change.

Make the smallest change that coherently fixes the set, per
[rules/verification.md](../../../rules/verification.md) §9 — smallest
by blast radius, not by line count. Rerun exactly the oracles that
failed, plus any oracle whose covered identities the change touched.

Never: fix a finding not in the set; decline one without citing the
evidence that it does not hold; claim a fix whose oracle was not rerun.

Return: changed artifacts, per-finding disposition with rerun evidence,
and anything queued.
