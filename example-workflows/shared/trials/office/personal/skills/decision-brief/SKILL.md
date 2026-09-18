---
name: decision-brief
description: Compare supplied proposals and produce one independently reviewed, once-revised internal recommendation.
disable-model-invocation: true
---

Run in the caller. Require core `orchflows` 0.10.0+ and `shared` 0.3.0+; resolve package roots through the supplied home. Select `writing` and this personal library's `decision-brief` guidance, preserving caller library order. Apply core execution rules. No external action is part of this workflow.

Invoke `shared:compare-candidates` on the actual proposals and common requirements. Preserve uncertainty and no eligible choice. Use an existing draft when supplied; otherwise draft from the returned evidence, directly when settings permit or through `orchflows:orch-work`.

Invoke `shared:review-revise-once` on that draft, original sources, criteria, comparison evidence and selected guidance. Preserve scoped settings and the caller's repair arrangement, keeping the original draft before revision. Return the comparison, original review, delivered recommendation, verification and gaps. Stop after the single repair pass; no extra final review or adoption is implied.
