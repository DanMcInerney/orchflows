---
name: review-revise-once
description: Independently review a stable candidate, make at most one repair pass, and return the reviewed and delivered states with distinct evidence.
disable-model-invocation: true
---

Establish [library context](../../references/library-context.md). Accept an existing candidate, requirements, evidence, guidance, permitted repair scope, required checks and output location. Preserve the original.

Apply resolved core architecture's standard review and repair, honoring any supplied maker handles and fixer settings. Verify even when no repair is needed; a missing review is a gap, not a clean verdict.

Return the original identity and review separately from the delivered identity, changes, verification and gaps. Stop without adoption, external release or an additional independent trial.
