---
name: orch-review-revise-once
description: Independently review an existing candidate, revise it at most once, and return the original review separately from the delivered result and checks.
disable-model-invocation: true
---

Apply [composition](../../docs/architecture.md#composition). Inputs: stable candidate, requirements, relevant sources/evidence, selected guidance, repair scope, required checks and output location. Preserve enough reviewed state to identify later changes.

Use [orch-review](../orch-review/SKILL.md) once on the whole candidate. Unavailable or incomplete independent review blocks repairs: preserve the candidate and report the gap. Repair requests within this workflow do not waive review. After review completes, make at most one coordinated repair pass for actionable findings within scope, honoring fixer settings and ownership. Run affected checks and caller-required verification even without repairs; report missing verification.

Return the original review and inspected state separately from delivered state, changes, checks and unresolved findings. Repairs do not inherit the verdict. This process adds no second review, release or external decision pause.
