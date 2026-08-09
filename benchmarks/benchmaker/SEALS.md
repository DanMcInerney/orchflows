# Case-set seals

One entry per seal, newest first. The recipe is owned by
`tools/seal_set.py`: the sealed scope is every file under
`benchmarks/benchmaker/` except `benchmark.lock`, `SEALS.md`, and the
`FINDINGS-*.md` campaign histories; `benchmark.lock` carries one
`<sha256>  <posix-path>` line per file, in byte order of the posix
paths, over exact working-tree bytes (`.gitattributes` pins LF); the
set digest is the sha256 of `benchmark.lock`'s exact bytes. Verify any entry with:

    uv run --no-project python benchmarks/benchmaker/tools/seal_set.py --verify

## 2026-08-09 — redesign law: exec_bound split, pre-seal manifest fields, and a bound manifest

    set digest sha256:b236f61477dfb810ee12d730ea3e521b5fa2c45e979a63519f8f7467ee8c5712
    benchmark_identity sha256:cb06f65657c82a4ecbf5b57431764605c27aeeea37cd776283e2e9a70b839088
    supersedes sha256:ec343b64…2f19ddce61 / benchmark_identity sha256:0509fe44…4a660787

1023 files, one added. Three changes, all landed for named correctness
defects and none for a score.

**The manifest is bound to its tree.** `tools/component_identity.py` is
new: it defines the recompute recipe the manifest asserted and no tool
could execute — a file component's identity is the sha256 of its bytes, a
directory component's is the sha256 of its component lock under
`seal_set.py`'s own line format, relative to the component root. The
three directory components (`cases/`, `provenance/`, `qualification/`)
reproduced under no recipe and are re-derived here, which is why
`benchmark_identity` moves for the first time since 2026-08-07. A
`cases/` change now moves `benchmark_identity` and `--verify` reports it.
This closes the hole the entry below records. `protected_evidence` is
exempt and printed as exempt: its bytes are off-tree by policy, and a
tool that could recompute it would have to read what the policy
withholds. 22 tests in `tests/test_component_identity.py`, each mutating
one thing — an edited case file, a rename at identical bytes, two cases
with their contents swapped — and proving the tool reports it.

**`case.toml`'s `bound` became `exec_bound` and shed its construction
half.** `bound = "one BC1 share; probe within small tier"` conflated the
construction run's builder-context allocation with the candidate-facing
execution bound, so a candidate-visible key told a candidate how its case
was authored, and only the tier half was ever measurable. The allocation
lives in `evaluation-design.md` section 8's capacity plan, where it
already was. `validate_cases.py` now refuses a `BC<n>` token in
`exec_bound` and refuses a tier that disagrees with `size`. Fourteen
frozen keys, still fourteen. The 2026-08-08 measurement record quotes the
predecessor string verbatim and is not rewritten: `validate_measures.py`
strips the construction clause before comparing, and a predecessor row
naming the wrong tier still fails.

**The manifest gained the redesign's eight pre-seal fields** — `anchors`,
`builders`, `reference_audit`, `attack_audit`, `seal_measurement`,
`resolution`, `retirement_trigger`, `incomparability`
(`compositions/references/benchmaker-manifest.md`). Every value is
measured, quoted from an existing package artifact, or a declared
absence; nothing is inferred. Four are declared absences and each is also
a manifest gap: the reference audit and the attack pass have not run,
`builders` records the allocated context but no model id, effort or host
binding, because the construction run recorded none, and three of sixteen
anchors are `none` with a reason because their angles are new at this set.
The sixteen cases were cut against the predecessor manifest law and case
none of these fields; a candidate that omits every one of them still
passes every case probe. That is a gap, not a pass.

Consumers of the 2026-08-08 measurement record: its three rows were
measured at set digest `sha256:75eb9925…5aff4fcc`, two seals below this
one.

## 2026-08-08 — declared runner invocation (cs-antigoodhart-2)

    set digest sha256:ec343b64016e1c295433b5d1cbf494d3af8df19dd46acace4f41ff2f19ddce61
    benchmark_identity sha256:0509fe444edad0f29e3ad5bdd5cf4aacf35dae6228c17d73fb6064014a660787 (unchanged)

1022 files. One file changed:
`cases/cs-antigoodhart-2/evidence/interchange.md` gains a **Runner
invocation** section. Repaired for a named correctness defect, not for
a score: `probe/check.py` executes the runner as
`python <runner> <impl-dir>` with a scratch working directory and
treats exit status as the verdict, and no candidate-visible evidence
stated any of it. Found by the 2026-08-08 measurement pass, where both
rungs invented different signatures and both failed P0.d in
consequence; reproduced outside the probe. The declaration is read off
the probe and adds no requirement the probe does not already enforce.

`benchmark_identity` is unchanged because `manifest.json` is
unchanged — and that is the entry's second finding. The manifest's
directory-component identities (`runnable_cases` at `cases/`, and the
`provenance/` and `qualification/` locators) are **not reproducible by
any tool in this package**: `seal_set.py` computes only the whole-set
lock, and the lock recipe applied to `cases/` reproduces the stated
`sha256:5ae08ffa…` under no path convention tried, including over the
pre-edit bytes. So a `cases/` change does not move `benchmark_identity`
and nothing detects the divergence. QC-3 as recorded proves
manifest-internal consistency and tree-lock consistency, never
manifest-to-tree agreement. Logged as friction; the recompute tool is
owed.

Consumers of the 2026-08-08 measurement record: its three rows were
measured against the predecessor digest below, not this one.

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
