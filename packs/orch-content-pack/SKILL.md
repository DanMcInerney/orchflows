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
| workspace | document tree: identities are document revisions, isolation is a run-scoped directory, write scopes are a whole document for one direct owner or outline slots for a genuine cut; ticket adapter: `document-tree`; assignment metadata: root_generation plus cut_generation, assignment_seal, and ownership_regions; ownership_regions: `heading` outline slots at a pinned document revision; without region proof, serialize by dependency or give one owner full control; merge oracle: the document-tree adapter proves stable non-overlap at a pinned identity for same-artifact parallelism |
| required_spec_fields | target directory; audience; voice contract; length budget; citation policy |
| craft | [references/craft.md](references/craft.md) |
