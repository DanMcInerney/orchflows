# Case-set seals

One entry per seal, newest first. The recipe is owned by
`tools/seal_set.py`: the sealed scope is every file under
`benchmarks/benchmaker/` except `benchmark.lock`, `SEALS.md`, and the
`FINDINGS-*.md` campaign histories; `benchmark.lock` carries one
`<sha256>  <posix-path>` line per file, in byte order of the posix
paths, over exact working-tree bytes (`.gitattributes` pins LF); the
set digest is the sha256 of `benchmark.lock`'s exact bytes. Verify any entry with:

    uv run --no-project python benchmarks/benchmaker/tools/seal_set.py --verify

## 2026-08-07 — sixteen-case successor (benchmaker-built)

    set digest sha256:a263e8094c52ab37885ff13112f0bdea58ae240e9868c35c9c82edb8825dcbd8
    benchmark_identity sha256:1d8e6a24db8f883e23d3776d2508a59c76be912e5ba0ed9fcdba5ffe95c7a118

1006 files. Produced end to end by the `benchmaker` composition
(run 20260807T060439Z-benchmaker-recursion) against the fixed
benchmaker identity @ e66f3b6 per docs/benchmaker.md
§Self-benchmarking. `manifest.json` is the package's sealed
manifest; QC-3 (seal reproducibility) verified here:
`seal_set.py --verify` green over the shipped tree at this digest,
and `benchmark_identity` recomputes from the canonical manifest
payload. Qualification: 10/10 required criteria PASS
(qualification/index.md; weakest oracle_class judged).

Two pre-commit re-mints are on record, neither committed nor
consumed. Draft `2f63e093…`: superseded when the assembly's
whitespace check rejected the bad-seal-drift seed's newline-based
desync and the drift was re-authored as a content amendment. Draft
`6bccca6b…`: the composition's done-check ruled its qualification
verdicts covered the pre-amendment tree, not the sealed bytes — the
late-qualification defect this suite's own cases burn — so a fresh
disjoint context (Q3) re-qualified over the sealed bytes with a
one-file scope proof (qualification/q3-delta-verdicts.md, anchored
to component identities), and this identity seals that verdict set.
Post-re-mint QC-3 record: `seal_set.py --verify` green at the set
digest above; `benchmark_identity` recomputes from the canonical
manifest payload.

Supersedes `sha256:ff7d9aad…6de675d0` — the thirteen-case
hand-authored set (entry below), which remains addressable at
e66f3b6. Adoption of this successor is the commit that ships it;
retirement of adapt-marked hand-authored cases is deferred to the
queued settlement round (owner decision, 2026-08-07). No campaign
consumes this seal until it does so by this identity.

## 2026-08-07 — thirteen-case set

    sha256:ff7d9aada981e76248e96d6284ab7b5e09551e19d6e18eea7a968a536de675d0

179 files. Adds the `ranking` → `candidate-ranking` matrix row
(FINDINGS-EVOLVE next-step 4) and the seal tooling itself; first
entry sealed under this recipe and the first to carry a durable
`benchmark.lock`.

Supersedes `sha256:fb7cd69d…f42b9d15` — the B(0) seal over the
twelve-case set @ 966d8de (see FINDINGS-EVOLVE.md). That identity
stopped describing the tree when the fourteen-key schema supersession
changed the case bytes; no campaign may cite it against this tree. A
campaign consuming the set cites the digest above; any later change
to a sealed byte mints a successor entry here.
