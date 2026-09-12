---
name: social-search
description: Research bounded public source scopes, then return one independent ranked assessment.
---

Stay in the caller's context. Reuse or establish [library context](../../references/library-context.md).

Choose assignments by their contribution to the question, preserving requested sources and dates. Group overlapping scopes when separate workers would repeat the same investigation. Give shared original-source checks one owner; other assignments collect distinct evidence, passing canonical leads to that owner and reusing its support.

Divide caller bounds across assignments. A total time limit includes evidence writing, gathering and final review: reserve time for those when setting read and handoff deadlines. Share the question, output requirements, ownership and deadlines; give each assignment a separate evidence directory.

Invoke [search-site](../search-site/SKILL.md) here once per assignment with deferred gathering. Launch independent assignments before gathering, within capacity and shared provider limits.

Gather every assignment's actual outcome by its handoff deadline; stop unfinished workers and retain partial artifacts and missing or failed assignments as gaps.

Invoke [rank-evidence](../rank-evidence/SKILL.md) once with the question, all returned evidence and gaps, remaining bounds and report location.

Return the assessment. For N assignments, the workflow uses N workers and one reviewer.
