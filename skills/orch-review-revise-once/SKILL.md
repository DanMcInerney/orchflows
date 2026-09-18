---
name: orch-review-revise-once
description: Independently review an existing candidate, revise it at most once, and return the original review separately from the delivered result and checks.
disable-model-invocation: true
---

Apply [composition](../../docs/architecture.md#composition). Inputs are a stable candidate, requirements, relevant sources/evidence, selected guidance, permitted repair scope, required checks and output location. Preserve the reviewed state sufficiently to identify later changes.

Use [orch-review](../orch-review/SKILL.md) once on the whole candidate. After the reviewer finishes, make at most one coordinated repair pass for actionable findings within scope, honoring fixer settings and ownership. Run affected checks and caller-required verification even when no repair is needed. Missing review or verification remains a gap.

Return the original review and inspected state separately from the delivered state, changes, checks and unresolved findings. A repair does not inherit the original verdict. This process adds no second review, release or external decision pause.
