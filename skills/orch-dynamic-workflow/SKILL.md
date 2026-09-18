---
name: orch-dynamic-workflow
description: Use for top-level requests when no more specific workflow or skill fits. Coordinate work and one final independent review.
disable-model-invocation: false
---

This fallback is for the top-level orchestrator only; child assignments must not invoke it. Apply core [execution](../../docs/architecture.md#execution), resolve guidance and dependencies, and preserve the caller's model and effort choices.

State the intended result and checks; investigate missing information. Make clear changes directly when settings permit or assign work through [orch-work](../orch-work/SKILL.md). Join and verify the result, then apply [standard review and repair](../../docs/architecture.md#standard-review-and-repair). Report what was made, checked and remains unresolved.
