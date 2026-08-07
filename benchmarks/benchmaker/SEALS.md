# Case-set seals

One entry per seal, newest first. The recipe is owned by
`tools/seal_set.py`: the sealed scope is every file under
`benchmarks/benchmaker/` except `benchmark.lock`, `SEALS.md`, and the
`FINDINGS-*.md` campaign histories; `benchmark.lock` carries one
`<sha256>  <posix-path>` line per file, in byte order of the posix
paths, over exact working-tree bytes (`.gitattributes` pins LF); the
set digest is the sha256 of `benchmark.lock`'s exact bytes. Verify any entry with:

    uv run --no-project python benchmarks/benchmaker/tools/seal_set.py --verify

## 2026-08-07 — shape-licensing supersession

    set digest sha256:75eb992563ba6f3258695ae7e06e8cff086daf74bfd4d01c8ad50b695aff4fcc
    benchmark_identity sha256:0509fe444edad0f29e3ad5bdd5cf4aacf35dae6228c17d73fb6064014a660787

1022 files. Supersedes `sha256:a263e809…825dcbd8` /
`1d8e6a24…95c7a118` (entry below). Content: every probe-demanded
interchange shape is now licensed by its case's exhibited evidence
(78 audited clusters, 15 new evidence files + 6 extensions across
all 16 cases); ~49 probe crash loci converted to clean named FAILs
(0 tracebacks across Q4's 160-run sweep); protected store relocated
to `BENCH_PROTECTED_DIR` default `%LOCALAPPDATA%\bs-bmk-prot`,
migration proven byte-identical; the manifest schema gained the
construction-complete-qualification-pending marker (GD4 closed at
law level); settlement round closed with no revivals. Q4
re-qualification: 10/10 required criteria PASS over current bytes
(qualification/q4-supersession-verdicts.md), QC-6 inherited under a
git scope proof — no seed, expected.md, or target byte changed.
Post-re-mint QC-3 record: `seal_set.py --verify` green at the set
digest above; `benchmark_identity` recomputes from the canonical
manifest payload. Known-and-declared: fleet interchange
heterogeneity is a recorded gap; uniformity belongs to the
bench-stack adapter or a successor.

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
