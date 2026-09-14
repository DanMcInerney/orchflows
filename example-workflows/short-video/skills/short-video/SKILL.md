---
name: short-video
description: Create short videos for any genre or placement, then independently review the actual exports.
disable-model-invocation: true
---

Reuse or establish [library context](../../references/library-context.md). For N requested films, declare N makers and N fresh reviewers, 2N agents total. Placement versions of one film share its pair. Run this coordination in the current context.

Invoke [make-short-video](../make-short-video/SKILL.md) once per film with its brief and separate output location. Independent films may run concurrently using returned handles; gather their actual outcomes. For each outcome, invoke [review-short-video](../review-short-video/SKILL.md) once over all its exact exports and any gaps, carrying the original brief and resolved guidance.

Return the editable projects, playable exports, independent findings and remaining gaps. No research stage, outline review, additional coordinator or repair loop is implied. Further work occurs only when requested.
