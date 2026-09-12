---
name: social-search
description: Research sites, the web and feed sets in parallel, then return one independent ranked assessment.
---

Reuse or establish [library context](../../references/library-context.md). Stay in the caller's context.

Choose bounded source assignments for the question, preserving requested sources, dates and constraints. [search-site](../search-site/SKILL.md) accepts a named site, web discovery across selected domains or the open web, or a supplied feed URL set. Share the question and output requirements, divide caller bounds across assignments, and give each assignment a separate evidence directory.

Invoke search-site here per assignment with deferred gathering; each invocation launches one worker, including a feed set. Launch every available assignment before awaiting any; when capacity or shared provider limits require waves, fill available slots as work finishes.

Gather actual outcomes from every assignment. Await or stop unfinished workers at the caller's deadline; retain missing or failed assignments as gaps.

Invoke [rank-evidence](../rank-evidence/SKILL.md) once with the question, all returned evidence and gaps, and the desired report location.

Return the assessment. For N assignments, the workflow uses N workers and one reviewer.
