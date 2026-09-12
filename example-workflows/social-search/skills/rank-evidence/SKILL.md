---
name: rank-evidence
description: Delegate one independent review of supplied evidence into a globally ranked, cited assessment.
---

Reuse or establish [library context](../../references/library-context.md). Accept a question and inspectable evidence from any caller; handoffs follow the site-search [guidance](../../guidance/research.search-site.md).

Use `orchflows-light:orch-review` exactly once with the resolved assessment guidance. Give the fresh reviewer the question, scope, output requirements, all actual evidence and collection gaps, and a separate report location. Its assignment is:

> Review the supplied evidence without changing it or collecting more. Inspect support for central claims, group duplicate or dependent sources, and rank by relevance, substance and independence. Treat local ranks as suggestions. Explain decisive ordering and disagreement.
>
> Return a concise cited assessment answering the question to the extent supported, or ranked evidence when requested. Keep conclusions traceable to original sources and saved support. State required gaps and whether the research is complete, partial or blocked. Work without child agents.

Await this reviewer and return its assessment.
