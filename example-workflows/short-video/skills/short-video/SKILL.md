---
name: short-video
description: Create short videos, then independently review their actual exports.
disable-model-invocation: true
---

The coordinator applies [library context](../../references/library-context.md). Choose assignments for the requested films/placements under core execution rules.

Apply [make-short-video](../make-short-video/SKILL.md) once per film with its brief and separate outputs. Run independent work concurrently and gather actual results. As each film completes, apply [review-short-video](../review-short-video/SKILL.md) once to all its exact exports and gaps, preserving the original brief and guidance.

Return editable projects, playable exports, independent findings and gaps. Add no research stage or outline review. Further work requires a caller request.
