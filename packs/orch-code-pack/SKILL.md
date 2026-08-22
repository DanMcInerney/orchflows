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
| workspace | git: identities: revisions; authority: paths; mutation-plan field: `mutations`; scope-edge manifest: `.orchflows/scope-edges.json`; missing-manifest mode: direct-only; isolation: branch or worktree; conflict binding: `orch-resolve-conflicts`; ticket adapter: `git`; v2 lifecycle fields: root_generation, cut_generation, assignment_seal, ownership_regions; ownership_regions: `symbol` or `json-pointer` at a pinned revision; fallback: dependency order or one sole owner; merge oracle: the git adapter proves stable non-overlap at a pinned identity for same-artifact parallelism |
| required_spec_fields | target repository; standards owner by pointer; acceptance as runnable checks |
| craft | [references/craft.md](references/craft.md) |
