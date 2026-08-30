---
name: orch-data-pack
description: Domain pack for data analysis — reproducible computation over pinned datasets. Stamp when the deliverable is an analysis.
---

Cells per [contracts/pack-signature.md](../../contracts/pack-signature.md):

| cell | binding |
| --- | --- |
| slicing | [references/slicing.md](references/slicing.md) |
| workspace | git: identities are commits whose committed manifests pin dataset bytes by digest and carry the sealed assignment (root_generation, cut_generation, assignment_seal), raw data living outside the repository; per-item worktree isolation; candidate changes are ordinary diffs; contested derived outputs are re-materialized once at the join, through the conflict owner; Suggested files are non-binding |
| required_spec_fields | target repository; dataset identities or the pinning policy; the question; rerun policy; claim bar — the robustness checks every load-bearing number must survive |
| craft | [references/craft.md](references/craft.md) |
| adapter | git |
| stages | [analyze, reproduce] |
| assembly | reproduce |
| lens | [references/craft.md#lens](references/craft.md#lens) |
| evidence | [references/evidence.md](references/evidence.md) |
| outline | [references/outline.md](references/outline.md) |
