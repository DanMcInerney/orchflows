---
name: rank-evidence
description: Delegate one independent review of supplied evidence into a globally ranked, cited assessment.
disable-model-invocation: true
---

Establish [library context](../../references/library-context.md). Accept a question and inspectable evidence under the [evidence contract](../../references/evidence.md).

Use `orchflows:orch-review` once with assessment guidance and evidence contract. Supply question, scope, output requirements, remaining bounds, evidence, every collection outcome and a separate report location. Instruct the assessor to write the assessment without changing evidence or collecting more.

Return the complete independent assessment, disagreements and gaps. Do not rewrite substantive rankings, collect evidence or add review.
