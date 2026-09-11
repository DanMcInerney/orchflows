---
name: prepare-evidence
description: Turn collected or saved research into a compact, inspectable evidence handoff in the current context.
---

Use existing material; launch no agents or source reads. Preserve supplied evidence and write a compact handoff, normally `results.md`:

- Question, source, relevant dates and constraints.
- Locally ranked items with stable IDs, original URLs, authors when relevant, dates or unknowns, and a reason for inclusion.
- Support the next reader can inspect: contextual excerpts, labeled paraphrases or accessible saved responses with precise locators. A URL or inaccessible tool handle alone is insufficient. Distinguish an index snippet from inspected source content.
- Coverage, missing context and required gaps; observed usage when relevant to caller bounds. Separate source origin, access provider and observation time where they affect interpretation.

Keep source assertions distinct from established facts. Retain the item's own dates and engagement; newer replies or reposts do not refresh their parents.

Report `complete` for the bounded assignment fulfilled, `partial` for useful unfinished evidence, `blocked` for unusable access or constraints, or `no_results` for a completed search with no matches. Failed or missing collection is not no-results evidence.

Check the handoff against the supplied support. Return its location and material gaps.
