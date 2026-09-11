---
name: social-search
description: Search relevant sites in parallel, gather their evidence, and return one independent ranked assessment.
---

Reuse or establish [library context](../../references/library-context.md). Stay in the caller's context.

Choose relevant [source profiles](references/source-workflows.md), preserving requested sources, dates and constraints; use [search-site](../search-site/SKILL.md) for other domains. Share the question and output requirements, divide caller bounds across assignments, and give each source a separate evidence directory.

Invoke each selected workflow here with deferred gathering. Each invocation launches one source worker through search-site. Launch every available assignment before awaiting any; when capacity or shared provider limits require waves, fill available slots as work finishes.

Gather actual outcomes from every selected source. Settle unfinished workers; retain missing or failed assignments as gaps.

Invoke [rank-evidence](../rank-evidence/SKILL.md) once with the question, all returned evidence and gaps, and the desired report location. This launches the only reviewer, after collection. There are no source reviewers or review-to-acquisition loops.

Return the assessment. For N selected sources, the workflow uses N workers and one reviewer.
