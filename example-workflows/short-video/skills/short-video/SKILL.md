---
name: short-video
description: Create short videos for any genre or placement, then independently review the actual exports.
disable-model-invocation: true
---

Reuse or establish [library context](../../references/library-context.md). Coordinate production and independent review in the caller. Choose staffing for the requested films and placements under core execution rules.

Invoke [make-short-video](../make-short-video/SKILL.md) once per film with its brief and separate output location. Run independent work concurrently and gather actual outcomes. As each film is ready, invoke [review-short-video](../review-short-video/SKILL.md) once over all its exact exports and any gaps, carrying the original brief and resolved guidance.

Return the editable projects, playable exports, independent findings and remaining gaps. No research stage, outline review, additional coordinator or repair loop is implied. Further work occurs only when requested.
