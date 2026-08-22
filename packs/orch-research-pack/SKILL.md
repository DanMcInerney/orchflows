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
| workspace | evidence store: identities are [evidence packets](references/craft.md), isolation is a run-scoped directory, write scopes are lane stores; ticket adapter: `evidence-store`; v2 lifecycle fields: root_generation, cut_generation, assignment_seal, ownership_regions; ownership_regions: adapter-equivalent lane-store slices at a pinned evidence-packet identity; fallback: dependency order or one sole owner; merge oracle: the evidence-store adapter proves stable non-overlap at a pinned identity for same-artifact parallelism |
| required_spec_fields | evidence store root; the question; source policy; rigor bar — the confidence each load-bearing claim must reach, stated as the evidence that must exist for it |
| craft | [references/craft.md](references/craft.md) |
