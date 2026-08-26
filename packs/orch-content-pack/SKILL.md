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
| workspace | document tree: `workspace.py start` returns a ticket-owned run directory and durable region receipt; `workspace.py check` re-derives that proof and the document revision; write scopes are outline slots; ticket adapter: `document-tree`; v2 assignment metadata: root_generation plus cut_generation, assignment_seal, and ownership_regions; ownership_regions: `heading` outline slots at a pinned document revision; without region proof, serialize by dependency or give one owner full control; merge oracle: the document-tree adapter reads the pinned document and proves stable non-overlap for same-artifact parallelism |
| required_spec_fields | target directory; audience; voice contract; length budget; citation policy |
| craft | [references/craft.md](references/craft.md) |
