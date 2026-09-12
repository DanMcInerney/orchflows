---
name: social-search
description: Research bounded public source scopes, then return one independent ranked assessment.
---

Reuse or establish [library context](../../references/library-context.md). Stay in the caller's context.

Choose only source assignments likely to contribute useful evidence, preserving requested sources, dates and bounds. Closely related sources may share an assignment when that reduces agent overhead. Share the question and output requirements, divide caller bounds across assignments, and give each a separate evidence directory.

Invoke [search-site](../search-site/SKILL.md) here once per assignment with deferred gathering. Launch independent assignments before gathering, within capacity and shared provider limits.

Gather actual outcomes from every assignment. Await or stop unfinished workers at the caller's deadline; retain missing or failed assignments as gaps.

Invoke [rank-evidence](../rank-evidence/SKILL.md) once with the question, all returned evidence and gaps, and the desired report location.

Return the assessment. For N assignments, the workflow uses N workers and one reviewer.
