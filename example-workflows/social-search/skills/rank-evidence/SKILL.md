---
name: rank-evidence
description: Delegate one independent review of supplied evidence into a globally ranked, cited assessment.
---

Reuse or establish [library context](../../references/library-context.md). Accept a question and inspectable evidence from any caller; handoffs follow the collection [guidance](../../guidance/research.search-site.md).

Use `orchflows-light:orch-review` exactly once with the resolved assessment guidance. Give the fresh reviewer the question, scope, output requirements, all actual evidence and collection gaps, and a separate report location. Its assignment is:

> Review the supplied evidence without changing it or collecting more. Apply the resolved Review guidance and write the requested assessment in the report location. Work without child agents.

Await this reviewer and return its assessment.
