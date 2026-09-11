---
name: search-x
description: Search X for relevant posts and conversations, inspect selected context, and return locally ranked evidence. Use for an X or Twitter research request or a scoped X source assignment.
---

# Search X

Load [search-site](../search-site/SKILL.md) and apply its scope, access, bounds and evidence contract with X as the source. Run in the current worker context; launch no children. Accept an ordinary research prompt or a caller's scoped assignment and write locally ranked evidence to the assigned `results.md`.

## Discover and select depth

Choose topical search, posts by a named account, or discussion about that account according to the question; these are different evidence sets. Search handles and topic variants where useful, without automatically spending the budget on every lane. Recent and relevance-ranked discovery may surface different material; neither proves complete window coverage.

Inspect actual selected posts and conversation context, including a parent or quoted post needed to understand the claim. A reply, cropped screenshot or search snippet can omit the statement being disputed. Follow a consequential claim's linked source within the assignment's allowed scope or preserve it as an unverified linked claim.

Rank direct observations, original announcements and specific, checkable arguments by relevance and substance. A principal's post can establish what they said; it does not independently prove their assertion. Distinguish corroboration from reposts and commentary on the same underlying post. Engagement can help choose depth but cannot establish accuracy or consensus.

## Preserve post evidence

- Retain each post's exact status URL, author/handle, publication time and available conversation relationship. Attribute quoted text to its original author and the added commentary to the quoting author.
- Keep original-post, repost and quote-post timing distinct when available. A fresh repost does not make the underlying claim newly published. An in-window quote or reply can qualify as new discussion while its older parent remains dated context.
- Attach observed engagement only to the post whose counts were returned. Missing likes, reposts, replies or quotes are unknown, not zero; do not transfer original-post counts to a reply or quote.
- Name the operator when a permitted archive or index provides the content, while retaining X as the source origin. Preserve snapshot and current observations separately. A missing parent, deleted post or unavailable conversation stays a context gap.
- Stop the refused read on an authentication, access, rate-limit or attestation boundary. Do not retry it through a different archive, instance, browser or API route. Preserve the refusal and available evidence for the caller; no route recipe authorizes such a fallback.

## Optional bundled acquisition

Use permitted public native reads by default, as search-site directs. If its optional acquisition method is selected, read the [X route guidance](../research-acquire/references/selection-routes.md#x). It documents explicit `x_xcancel` search/status and `x_fxtwitter` search/conversation operations, plus references for the retained guest and syndication routes. These routes are choices to scope before acquisition, not a fallback chain. Third-party attribution and reported losses remain attached, and installed code does not establish live access.
