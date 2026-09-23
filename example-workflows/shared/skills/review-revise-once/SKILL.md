---
name: review-revise-once
description: Independently review an existing candidate, revise it at most once, and return the original review separately from the delivered result and checks. Use when a workflow names it or the user selects it; ordinary requests use orch-dynamic-workflow. Top-level coordinators only.
disable-model-invocation: false
---

Establish [library context](../../references/library-context.md). Inputs: stable candidate, requirements, relevant sources/evidence, selected guidance, repair scope, required checks and output location. Preserve enough reviewed state to identify later changes.

Use `orchflows:orch-review` once on the whole candidate. Repair requests within this workflow do not waive review. After review completes, make at most one coordinated repair pass for actionable findings within scope.

Return the original review and inspected state separately from delivered state, changes, checks and unresolved findings. This process adds no release or external decision pause.
