# 3D browser-game lineage repair

The gate consumer now has a small, pure provenance seam for the two confirmed
acceptance failures. `example-workflows/3d-browser-game/scripts/gate_lineage.mjs` accepts typed run-record,
traceability, evidence-index, and gate-verdict objects. It returns a compact
valid result or a `LineageError` with a stable code, JSON pointer, expected
shape, and observed value. `sourceObservation(ancestor, descendant)` remains
caller owned: a hash identifies bytes, while the consumer must observe git
ancestry.

Final acceptance requires an accepted typed core verdict, post-core concept
records, typed production asset manifests, and an ancestry observation from
the core artifact to each descendant. A changed mechanic requires an accepted
core reproof made after the changed source and bound to the final revision.
The original brief and amendments are bound by identity and SHA-256, while
the audited promise inventory must equal the traceability row set. The helper
does not parse natural language or claim that a hash proves an audit was
complete.

Successor run records bind the predecessor record bytes. Prior complaint IDs,
seams, kinds, and causes are retained; deletion, rewriting, or reopening a
closed complaint is rejected. A status transition to fixed, rejected, or
superseded requires a closure reason and evidence identities. The helper does
not launch workers or mutate run state.

The standalone `references/lineage.schema.json` defines the reusable lineage,
complaint-closure, and core-reproof shapes. Run-record and traceability
schemas expose those fields while preserving their existing common header and
closed-object contracts. The package validator registers the lineage schema
and invokes the helper after rehashing indexed evidence.

The deterministic test module covers accepted core and core-to-art-to-final
fixtures, missing core, pre-core art, unrelated source ancestry, omitted
brief promises, deleted and reopened complaints, and stale changed-mechanic
reproof. It labels fixture evidence as controlled evidence; it makes no claim
of actual browser play or performance.
