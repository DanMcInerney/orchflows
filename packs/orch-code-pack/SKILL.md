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
| lens | `orch-critique` with [references/lens.md](references/lens.md) |
| oracle_policy | [references/oracles.md](references/oracles.md) |
| workspace | git: identities are revisions, isolation is a branch or worktree, write scopes are path sets; each frontier item gets its own worktree branched from the run's current revision at dispatch, merged at the join; conflict binding `orch-resolve-conflicts` |
| required_spec_fields | target repository; standards owner by pointer; acceptance as runnable checks |
| craft | [references/craft.md](references/craft.md) |
