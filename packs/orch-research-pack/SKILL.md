---
name: orch-research-pack
description: Domain pack for knowledge claims — evidence oracles, evidence store. Stamp when the deliverable answers a question.
---

Cells per [contracts/pack-signature.md](../../contracts/pack-signature.md):

| cell | binding |
| --- | --- |
| slicing | [references/slicing.md](references/slicing.md) |
| executor | `orch-investigate` |
| assembly | `orch-synthesize` |
| lens | `orch-critique` with [references/craft.md#lens](references/craft.md#lens) |
| oracle_policy | [references/oracles.md](references/oracles.md) |
| workspace | evidence store: identities are [evidence packets](references/craft.md), isolation is a run-scoped directory, write scopes are lane stores; ticket adapter: `evidence-store`; ownership selectors: adapter-equivalent lane-store slices at a pinned evidence-packet identity; [rules/topology.md](../../rules/topology.md) §§8–§11 |
| required_spec_fields | evidence-store-root — direct default sink:evidence/{run}/{ticket}/; question — direct default {objective}; source-policy — direct default primary evidence only; rigor-bar — direct default each load-bearing claim has primary evidence or is an explicit gap |
| craft | [references/craft.md](references/craft.md) |
