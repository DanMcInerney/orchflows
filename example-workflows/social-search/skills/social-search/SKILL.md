---
name: social-search
description: Search relevant sites in parallel, gather their evidence, and return one independent ranked assessment.
---

Reuse or establish [library context](../../references/library-context.md). Stay in the caller's context.

Choose sites for the question, preserving requested sources, dates and constraints; this library's [guidance](../../guidance/) names the sites with source knowledge, and [search-site](../search-site/SKILL.md) accepts any domain. Share the question and output requirements, divide caller bounds across assignments, and give each site a separate evidence directory.

Invoke search-site here per site with deferred gathering; each invocation launches one worker. Launch every available assignment before awaiting any; when capacity or shared provider limits require waves, fill available slots as work finishes.

Gather actual outcomes from every site. Await or stop unfinished workers at the caller's deadline; retain missing or failed assignments as gaps.

Invoke [rank-evidence](../rank-evidence/SKILL.md) once with the question, all returned evidence and gaps, and the desired report location.

Return the assessment. For N selected sites, the workflow uses N workers and one reviewer.
