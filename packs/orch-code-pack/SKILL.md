---
name: orch-code-pack
description: Domain pack for executable artifacts — code evidence, git workspace. Stamp when the deliverable is code.
---

Cells per [contracts/pack-signature.md](../../contracts/pack-signature.md):

| cell | binding |
| --- | --- |
| slicing | [references/slicing.md](references/slicing.md) |
| workspace | git: isolated branch or worktree candidates have repository write authority; Suggested files are non-binding; integration inspects actual diffs and ordinary Git conflicts, resolves overlaps through the conflict owner, regenerates shared derived artifacts once, then runs the final gate; assignment references: root_generation, cut_generation, assignment_seal; lifecycle metadata: workspace_path, workspace_branch, workspace_baseline |
| required_spec_fields | target repository; standards owner by pointer; observable result |
| craft | [references/craft.md](references/craft.md) |
| adapter | git |
| stages | [tdd] |
| assembly | none |
| lens | [references/craft.md#lens](references/craft.md#lens) |
| evidence | [references/evidence.md](references/evidence.md) |
