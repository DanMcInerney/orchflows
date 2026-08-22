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
| lens | `orch-critique` with [references/craft.md#lens](references/craft.md#lens) |
| oracle_policy | [references/oracles.md](references/oracles.md) |
| workspace | git plus render: identities: [view identity](references/craft.md); authority: paths; mutation-plan field: `mutations`; scope-edge manifest: `.orchflows/scope-edges.json`; missing-manifest mode: direct-only; golden captures: spec-frozen paths; run captures: outside write scope; conflict binding: `orch-resolve-conflicts`; ticket adapter: `git-plus-render`; v2 lifecycle fields: root_generation, cut_generation, assignment_seal, ownership_regions; ownership_regions: `symbol` or `json-pointer` within a pinned view identity; fallback: dependency order or one sole owner; merge oracle: the git-plus-render adapter proves stable non-overlap at a pinned identity for same-artifact parallelism |
| required_spec_fields | target repository; render, capture, and diff commands; view set with breakpoints and states; design language; accessibility bar; golden captures by identity (absent for greenfield); standards owner by pointer |
| craft | [references/craft.md](references/craft.md) |
