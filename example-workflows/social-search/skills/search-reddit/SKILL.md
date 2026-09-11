---
name: search-reddit
description: Search Reddit for relevant threads and comments, inspect selected discussion context, and return locally ranked evidence. Use for a Reddit research request or a scoped Reddit source assignment.
---

# Search Reddit

Load [search-site](../search-site/SKILL.md) and apply its scope, access, bounds and evidence contract with Reddit as the source. Run in the current worker context; launch no children. Accept an ordinary research prompt or a caller's scoped assignment and write locally ranked evidence to the assigned `results.md`.

## Discover and select depth

Search relevant communities and topic vocabulary, using named subreddits or authors when supplied. Within the allotted reads, consider both recent and relevance-oriented discovery when each can answer the question. A platform time bucket or search order does not establish an item's date or complete coverage.

Select threads from their actual topic and community context. A generic daily-discussion title can merit a comment read when the community and available text connect it to the question; the title or a large comment count alone is insufficient. Inspect selected submissions and relevant comment branches, including parent text needed to interpret replies. Top comments are a ranked sample, not the community's consensus.

Rank firsthand accounts, concrete details and substantive disagreements by their value to the question. Distinguish independent experiences from replies repeating one claim. Scores and thread activity can help choose depth but cannot establish truth or representativeness.

## Preserve discussion evidence

- Attribute each submission and comment to its own author, permalink, date and observed counts when available. Keep a comment's score separate from the submission's score and total comment count; missing counts remain unknown.
- Keep the older parent submission and an in-window comment's dates distinct. The comment may qualify for a comment-focused window; it does not make the parent a newly published post. Label older context and uncertain relative timestamps.
- Retain enough parent/reply context to distinguish the author's claim, a quotation, a correction and sarcasm. Cite the specific comment for a comment claim, with its thread linked for context.
- Name an archive's operator and preserve snapshot provenance. Archived bodies and counts are observations through that archive; any current Reddit read is separately attributed and timed. Do not present an archived score as today's score.
- Deleted, removed, collapsed, unavailable or unreturned comments remain gaps. A displayed total is not proof that those comments were read; do not reconstruct missing text or call a partial branch the full discussion.

## Optional bundled acquisition

Use permitted public native reads by default, as search-site directs. If its optional acquisition method is selected, read the [Reddit route guidance](../research-acquire/references/selection-routes.md#reddit). The retained backend supports scoped archive post discovery, Shreddit discovery and selected comments, and RSS discovery; archive post hydration does not fetch comments. Read the documented operation and its losses before planning it. Route presence does not establish current availability, and more-comments continuation is not supported by this backend.
