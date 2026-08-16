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
| workspace | evidence store: identities are [evidence packets](references/craft.md), isolation is a run-scoped directory, write scopes are lane stores |
| required_spec_fields | evidence store root; the question; source policy; rigor bar — the confidence each load-bearing claim must reach, stated as the evidence that must exist for it |
| craft | [references/craft.md](references/craft.md) |
