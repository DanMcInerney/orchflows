---
name: orch-code-pack
description: Domain pack for executable artifacts — code evidence, git workspace. Stamp when the deliverable is code.
---

Cells per [contracts/pack-signature.md](../../contracts/pack-signature.md):

| cell | binding |
| --- | --- |
| slicing | [references/slicing.md](references/slicing.md) |
| workspace | git: identities are commits; isolation is a branch or worktree per candidate; changes are ordinary diffs; Git conflicts and shared derived artifacts resolve once at the join through the conflict owner |
| required_spec_fields | target repository; standards owner by pointer; observable result |
| craft | [references/craft.md](references/craft.md) |
| adapter | git |
| stages | [implement] |
| assembly | none |
| evidence | [references/evidence.md](references/evidence.md) |
| outline | [references/outline.md](references/outline.md) |
