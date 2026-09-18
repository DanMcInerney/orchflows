---
name: orch-dynamic-workflow
description: Coordinate a top-level task with one final independent review when requested, or as an explicitly enabled fallback when no specific workflow fits.
disable-model-invocation: true
---

This fallback is for the top-level orchestrator only; child assignments must not invoke it. Apply core [execution](../../docs/architecture.md#execution), resolve guidance and dependencies, and preserve the caller's model and effort choices.

State the intended result and checks; investigate missing information. Make clear changes directly when settings permit or assign work through [orch-work](../orch-work/SKILL.md). Join and verify the result, then apply [orch-review-revise-once](../orch-review-revise-once/SKILL.md). Report what was made, checked and remains unresolved.
