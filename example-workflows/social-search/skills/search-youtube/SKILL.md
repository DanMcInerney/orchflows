---
name: search-youtube
description: Search YouTube for relevant videos, inspect selected transcripts or accessible video content and comments, and return locally ranked evidence. Use for a YouTube research request or a scoped YouTube source assignment.
---

# Search YouTube

Load [search-site](../search-site/SKILL.md) and apply its scope, access, bounds and evidence contract with YouTube as the source. Run in the current worker context; launch no children. Accept an ordinary research prompt or a caller's scoped assignment and write locally ranked evidence to the assigned `results.md`.

## Discover and select depth

Search topic variants and named channels, speakers or videos as relevant to the request. Search cards, channel feeds, titles and descriptions can identify candidates; inspect the selected watch-page metadata to establish the video's identity and publication date. Keep upload/publication time distinct from the date of a recorded event or a later comment.

Choose depth for the claim being investigated. A firsthand demonstration, original interview or detailed explanation may be more useful than a popular summary. Prefer original material over reuploads or clips when accessible, and identify when multiple videos reuse the same recording. Views, likes and channel size measure attention, not credibility.

For spoken claims, read the relevant transcript cues with surrounding context or inspect accessible video/audio through a supported tool. Titles and descriptions alone cannot verify what was said. Comments are useful depth when the question concerns audience experience, corrections or reception; do not fetch them automatically for every video.

## Preserve video evidence

- Cite the video and timestamps for supported passages. Preserve cue ranges and adjacent context needed for qualifications, speaker changes or an answer that depends on the preceding question. A transcript does not itself verify a visual demonstration.
- Record the transcript's language and whether captions are manual, automatic or translated when known. Distinguish the uploader/channel from the speaker when identifiable. Mark uncertain transcription and translated paraphrases; do not silently turn a translation into a verbatim original-language quote.
- If captions, media or the relevant passage are unavailable, report that limit. Never invent a transcript, infer a spoken claim from the title, or treat an accessible description as full video content.
- Attribute comments to their own authors, dates, permalinks or available identifiers and counts. A new comment does not refresh the video's publication date; a commenter's claim is not the creator's statement. Comment sorting and missing replies limit any conclusion about audience consensus.

## Optional bundled acquisition

Use permitted public native reads by default, as search-site directs. If its optional acquisition method is selected, consult [supported depth](../research-acquire/references/selection-routes.md#other-existing-sources) and the YouTube entry in the [adapter roster](../research-acquire/references/protocol.md#adapter-roster). The retained `youtube_innertube` route has search, `player` metadata, `next` comments and `transcript` operations. Transcript depth needs capacity for both the track list and cue page (`max_items >= 2`). Availability and language depend on the returned track, and refusals or missing captions remain gaps; route presence is not a promise of access.
