---
name: review-short-video
description: Independently examine the exact exported short video without repairs.
disable-model-invocation: true
---

Reuse or establish [library context](../../references/library-context.md). Accept an existing film's exports, editable project and original brief; prior use of make-short-video is unnecessary. Identify exports by absolute path and SHA-256 and keep them stable for review.

Use `orchflows:orch-review` once with a reviewer who made none of the film, covering every export and overall coherence. Pass the actual exports, source, brief, supporting facts and the same resolved guidance paths:

> Review every supplied export against the brief and guidance, using the actual encoded media. Report findings at useful timestamps, identify the exact files examined, and distinguish technical checks, frame inspection, motion viewing and listening with their coverage and gaps. Do not change source or exports.

Return the review findings, including unresolved criteria and absent or corrupt exports. This leaf makes no repairs or additional review.
