---
name: orch-content-pack
description: Domain pack for prose read by humans — judged oracles, document workspace. Stamp when the deliverable is a document.
---

Cells per [contracts/pack-signature.md](../../contracts/pack-signature.md):

| cell | binding |
| --- | --- |
| slicing | [references/slicing.md](references/slicing.md) |
| executor | `orch-draft` |
| assembly | `orch-edit` |
| lens | `orch-critique` with [references/craft.md#lens](references/craft.md#lens) |
| oracle_policy | [references/oracles.md](references/oracles.md) |
| workspace | document tree: `workspace.py start` returns a ticket-owned run directory and durable region receipt; `workspace.py check` re-derives that proof and the document revision; write scopes are outline slots; ticket adapter: `document-tree`; ownership selector: `heading` outline slots at a pinned document revision; [rules/topology.md](../../rules/topology.md) §§8–§11 |
| required_spec_fields | target directory; audience; voice contract; length budget; citation policy |
| craft | [references/craft.md](references/craft.md) |
