---
name: orch-dynamic-workflow
description: Use when the user does not specify a workflow or skill to use. Deliver the request through coordinated making and one final independent review.
---

State the intended result and its checks; investigate missing information. Select relevant [guidance](../../docs/architecture.md#guidance-selection) and resolve dependencies once. Use [orch-work](../orch-work/SKILL.md) for shared prerequisites and independent deliverables, giving each maker clear ownership and running them concurrently once their inputs are ready.

Join and verify the result. Use [orch-review](../orch-review/SKILL.md) once over the join. Return findings to the responsible makers for one repair pass, then verify the revision. Report what was made, checked, and remains unresolved.
