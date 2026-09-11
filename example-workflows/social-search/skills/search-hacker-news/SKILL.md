---
name: search-hacker-news
description: Find and locally rank Hacker News stories and participant comments for a research question or scoped source assignment.
---

# Search Hacker News

Load and follow [search-site](../search-site/SKILL.md) in the current worker context, without spawning agents. Apply this profile to an ordinary research question or a caller's Hacker News assignment. Use the shared scope, public read-only default, bounds and evidence contract, returning locally ranked evidence in the assigned `results.md`.

- Search relevant topic terms, product names and linked URLs. Include Ask HN or Show HN when they fit the question. A search bounded by story submission date can miss recent comments on older stories; choose the relevant date and report that coverage gap when it matters.
- Read the selected story's own text or linked material as needed, and actual participant comments when answering what people think. Distinguish the submitter, linked article's author and commenters. A story title, article body or comment count cannot establish participant opinion.
- Preserve a comment's permalink, author, date and enough parent/reply context to interpret it. Use its own published score only when available; never attach the story's points or total comment count to a comment. Keep unknown counts unknown.
- Prefer substantive firsthand reports, technical explanations and supported disagreement over short reactions. Distinguish what a commenter experienced from claims they repeat. Multiple discussions of the same article can add distinct reactions while still sharing the underlying reporting.
- State whether the evidence includes a full returned tree, selected branches, search excerpts or no accessible comments. Missing, deleted or truncated comments limit claims about the discussion; they do not imply agreement or an absence of opposing views.

If the shared workflow selects the optional bundled acquisition method, consult the `hacker_news` entry in its [adapter roster](../research-acquire/references/protocol.md#adapter-roster). It supports Algolia story/comment search, Firebase item reads and Algolia tree reads. Keep HN source identity distinct from Algolia access provenance, and judge the comments actually returned.
