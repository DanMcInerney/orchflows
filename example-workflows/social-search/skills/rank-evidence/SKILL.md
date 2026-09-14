---
name: rank-evidence
description: Delegate one independent review of supplied evidence into a globally ranked, cited assessment.
disable-model-invocation: true
---

Reuse or establish [library context](../../references/library-context.md). Accept a question and inspectable evidence from any caller under the [evidence contract](../../references/evidence.md).

Use `orchflows:orch-review` once with the resolved assessment guidance and evidence contract. Supply the question, scope, output requirements, remaining bounds, evidence, every collection outcome and a separate report location:

> Apply the Review guidance to the supplied evidence without changing it or collecting more. Write the requested assessment in the report location. Work without child agents.

Await this reviewer and return its assessment.
