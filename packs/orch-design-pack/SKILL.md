---
name: orch-design-pack
description: Domain pack for rendered interfaces — oracles run on captures, git-plus-render workspace. Stamp when the deliverable is judged as rendered.
---

Cells per [contracts/pack-signature.md](../../contracts/pack-signature.md):

| cell | binding |
| --- | --- |
| slicing | [references/slicing.md](references/slicing.md) |
| executor | `orch-render` |
| assembly | none — merged views form the assembly |
| lens | `orch-critique` with [references/craft.md#lens](references/craft.md#lens) |
| oracle_policy | [references/oracles.md](references/oracles.md) |
| workspace | git plus render: identities are [view identities](references/craft.md); isolated candidates have repository write authority; Suggested files are non-binding; integration resolves actual diff and render conflicts through `orch-resolve-conflicts`, regenerates shared captures once, then runs the final gate; ticket adapter: `git-plus-render`; generation metadata: root_generation, cut_generation, assignment_seal |
| required_spec_fields | repository; render/capture/diff commands; views by breakpoint/state; language; accessibility bar; golden identities (none greenfield); standards owner pointer |
| craft | [references/craft.md](references/craft.md) |
