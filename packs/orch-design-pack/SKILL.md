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
| workspace | git plus render: identities: [view and capture artifact identities](references/craft.md#vocabulary); authority: paths; mutation-plan field: `mutations`; scope-edge manifest: `.orchflows/scope-edges.json`; missing-manifest mode: direct-only; golden captures: spec-frozen paths; run captures: outside write scope, as `capture-artifact` identities with `sink:` locators; conflict binding: `orch-resolve-conflicts`; ticket adapter: `git-plus-render`; ownership selectors: `symbol` or `json-pointer` within a pinned view identity; [rules/topology.md](../../rules/topology.md) §§8–§11 |
| required_spec_fields | repository; build command; typecheck command; standards-shape command; render command; capture command; diff command; views by breakpoint/state; design language; accessibility bar; golden identities; greenfield discriminator (`true` or `false`); standards owner pointer |
| craft | [references/craft.md](references/craft.md) |
