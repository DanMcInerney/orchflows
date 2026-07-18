---
name: orch-design-pack
description: Domain pack for rendered interfaces — oracles run on captures, git-plus-render workspace. Stamp when the deliverable is judged as rendered.
---

Cells per [contracts/pack-signature.md](../../contracts/pack-signature.md):

| cell | binding |
| --- | --- |
| slicing | [references/slicing.md](references/slicing.md) |
| executor | `orch-render` |
| assembly | none — the merged revision's rendered views are the assembly |
| lens | `orch-critique` with [references/lens.md](references/lens.md) |
| oracle_policy | [references/oracles.md](references/oracles.md) |
| workspace | git plus render: identities are view × breakpoint × state at a revision; write scopes are path sets; golden captures are spec-frozen paths; run captures are evidence outside write scope; each frontier item gets its own worktree branched from the run's current revision at dispatch, merged at the join; conflict binding `orch-resolve-conflicts` |
| required_spec_fields | target repository; render, capture, and diff commands; view set with breakpoints and states; design language; accessibility bar; golden captures by identity (absent for greenfield); standards owner by pointer |
| craft | [references/craft.md](references/craft.md) |
