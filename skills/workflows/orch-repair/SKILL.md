---
name: orch-repair
description: Fix accepted verified defects with the smallest coherent change. Use inside the gate or on any accepted defect set.
role: none
---

Require: the accepted defect set, each defect with its evidence and the
oracle that showed it; the write scope the repair may touch.

Make the smallest change that coherently fixes the set, per
[rules/verification.md](../../../rules/verification.md) §9 — smallest
by blast radius, not by line count. Rerun exactly the oracles that
failed, plus any oracle whose covered identities the change touched.

Never: fix a defect not in the accepted set, or widen a fix past the
frozen spec's license (queue either); refactor opportunistically; claim
a fix whose oracle was not rerun.

Return: changed artifacts, per-defect disposition with rerun evidence,
and anything queued.
