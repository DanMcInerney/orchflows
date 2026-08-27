---
name: orch-code-pack
description: Domain pack for executable artifacts — deterministic oracles, git workspace. Stamp when the deliverable is code.
---

Cells per [contracts/pack-signature.md](../../contracts/pack-signature.md):

| cell | binding |
| --- | --- |
| slicing | [references/slicing.md](references/slicing.md) |
| executor | `orch-tdd` |
| assembly | none — the repository is the assembly |
| lens | `orch-critique` with [references/craft.md#lens](references/craft.md#lens) |
| oracle_policy | [references/oracles.md](references/oracles.md) |
| workspace | git: isolated branch or worktree candidates have repository write authority; Suggested files are non-binding; integration inspects actual diffs and ordinary Git conflicts, resolves overlaps through `orch-resolve-conflicts`, regenerates shared derived artifacts once, then runs the final gate; ticket adapter: `git`; assignment references: root_generation, cut_generation, assignment_seal |
| required_spec_fields | target repository; standards owner by pointer; acceptance as runnable checks |
| craft | [references/craft.md](references/craft.md) |
