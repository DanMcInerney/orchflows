---
name: orch-repair
description: Fix accepted verified defects with the smallest coherent change. Use inside the gate or on any accepted defect set.
role: none
---

Require: the findings to repair — from the critique `## Result`s the
packet names, each with its evidence and the oracle that showed it —
and the write scope the repair may touch; an empty set is a legal
dispatch whose result is no change.

Make the smallest change that coherently fixes the set, per
[rules/verification.md](../../../rules/verification.md) §9 — smallest
by blast radius, not by line count. Rerun exactly the oracles that
failed, plus any oracle whose covered identities the change touched.

Never: fix a finding not in the set, or widen a fix past the frozen
spec's license (queue either); decline a finding without citing the
evidence that it does not hold; refactor opportunistically; claim a fix
whose oracle was not rerun.

Return: changed artifacts, per-finding disposition with rerun evidence,
and anything queued.
