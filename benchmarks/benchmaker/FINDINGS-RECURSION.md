# Recursion findings — benchmaker rebuilt its own benchmark

Run 20260807T060439Z-benchmaker-recursion (runtime record in the
producing worktree's `.orch/runs/`; this file the durable summary).
One `benchmaker` composition run against the fixed benchmaker
identity @ e66f3b6, per docs/benchmaker.md §Self-benchmarking:
manual, acyclic, between campaigns. Result: the sixteen-case
successor sealed at `benchmark_identity sha256:1d8e6a24…95c7a118`,
set digest `sha256:a263e809…825dcbd8`, superseding the thirteen-case
hand-authored set (`sha256:ff7d9aad…6de675d0`, still addressable at
e66f3b6). Owner decisions elicited at run start: session+lanes
bound; successor replaces `benchmarks/benchmaker/`; adapt-case
retirement deferred to the settlement round; matched-model
median-of-3 trials on judged/nondeterministic cases.

## Successor vs the hand-authored set

| | hand-authored (13) | successor (16) |
| --- | --- | --- |
| provenance | expected.md (self-referential) | claims-traced: `synthesis@41ee9ea2 claims <ids>`, QC-4 machine-checked |
| claim coverage | implicit | 60 claims: 49 case-mapped, 7 gapped explicitly, 4 merged — arithmetic closes, zero silent omissions |
| artifact under test | inner tool implementations | the produced benchmark package itself (manifest identity, component digests, verdict contract, inner discrimination) |
| process angles | 2 negative rows | 4: intake-refusal, run-conduct, package-audit added; both prior negatives redesigned (their answers were transcribable from exhibited files) |
| seeds | 39 deviations, all exhibited/burned | 64 fresh bad seeds; 0 equivalent variants (QC-5); 0 burn violations (QC-6); one inert + one near-miss per case |
| qualification | validator only, builder-adjacent | 10 required criteria, two contexts disjoint from six builders; trial counts declared; judged variance recorded |
| seal | lock + SEALS entry (added at e66f3b6) | full manifest (ten fields, recomputable identity) + lock + SEALS entry |
| contamination | assumed, undetectable | two-GUID canary (detection only) |
| protected evidence | repo-local seeds | off-tree store, digests in manifest; resistance still UNVERIFIED |

Claims that remain uncased (explicit, from the design): wall
enforcement, bound arithmetic, cross-campaign acyclicity (not
observable by a case oracle under current host attestation);
unsolvable-as-written angle deferred (zero claim coverage lost).

## Findings

**R1 — the recursion works but the evidence-shape tax is real.**
Q2's matched-model liveness trial passed cs-cli-fresh only on
attempt 3: the failures were probe-dictated interchange shapes
(component key names, case-record fields, runner report keys) that
the case's evidence never licenses. This is E1's shape in a new
place: where law is checked at a boundary the builder cannot see,
builders fail on format, not semantics. First fix for any successor:
every probe-required shape must be licensed by exhibited evidence.

**R2 — probe robustness is a qualification blind spot.** The
cs-cli-fresh probe crashes on a string `"overall": "PASS"` — a shape
another case's own sealed target uses. Under scoring law a crash is
UNVERIFIED, not FAIL, so this cannot flip a verdict, but a fleet of
16 independently-authored probes has no shared shape law. The
bench-stack port's uniform adapter is the structural fix.

**R3 — builders converge on additive elaboration, not drift.** All
six builder contexts returned zero semantic deviations from the
frozen design; every disclosed elaboration was a check the design's
own seed set forced into existence (probe inversion is
self-correcting in exactly the way E5 predicted campaign scoring is
not). The design→materialize join held without a correction round.

**R4 — the exhibited/protected line now has a mechanism, not just a
law.** Off-tree store + BENCH_PROTECTED_DIR degradation + two-GUID
canary made D1 (protected constants leaked into exhibited files —
two instances in the hand-authored set) structurally checkable
(QC-9, ag.1 scans). Resistance remains UNVERIFIED until a
candidate-inaccessible check exists (bench-stack port).

**R6 — the recursion caught itself.** The run's own done-check
rejected the first sealed draft: after qualification, a one-file
whitespace repair (forced by a repo required check) changed the tree,
the assembly context claimed re-verification, and the done-check
ruled — correctly — that a builder-side claim is not qualification
coverage. That is byte-for-byte the late-qualification /
qualification-independence defect this suite's cs-package-audit and
cs-workflow-fresh seeds burn. A fresh disjoint context (Q3)
re-qualified over the sealed bytes with a one-file scope proof, and
the identity was re-minted. The machinery this set certifies was
enforced against the run that produced the set.

**R5 — cost.** Bound: one session + ~10-20 subagent lanes. Spent:
15 lanes (2 acquire, 1 synthesis, 1 design, 6 build, 2 qualify,
1 delta re-qualification, 2 done-check passes), ≈2.2M subagent
tokens, suite sweep measured at 173-186 s against an 8.9 h timeout
ceiling. Materialize (6 lanes) dominated; the R6 catch cost one
re-qualification lane and one extra done-check — the price of the
late-qualification law holding.

## Settlement (closed 2026-08-07)

Owner ruling, elicited: the round closes with NO revivals. Every
angle carries a fresh successor case; all 39 predecessor seed
deviations are burned as exhibited; the thirteen-case set remains
addressable at e66f3b6 and each successor case's `port` key names
its predecessor. Nothing returns to HEAD. Any future revival is a
new supersession decision, not a reopening of this round.

## Supersession 2026-08-07 (identity 0509fe44…, R1/R2 closed)

The first-successor fixes landed as one supersession: a fleet audit
found R1 was systemic — 78 unlicensed demanded-shape clusters and 49
crash loci across the 16 probes, including four incompatible
component-reference dialects, so no single package shape could pass
all probes even in principle. The fix licensed each probe's current
demands in its own case's exhibited evidence (15 new files, 6
extensions) and converted every crash to a clean named FAIL; Q4
re-qualified everything over current bytes with zero tracebacks in
160 runs. The cross-case dialect heterogeneity is now a declared
manifest gap — per-case licensing was this run's bound; a uniform
interchange convention belongs to the bench-stack adapter or a
successor. Also closed: GD4 (pending-qualification marker in the
manifest schema), protected-store relocation to the bench-stack
root role (byte-identical), settlement round (§Settlement).

## Next

Bench-stack port: resume draft PR #36 (uniform adapter per R2,
protected root now populated at its own role path; handoff on that
branch). Successor candidates: uniform interchange convention
(retiring the dialect gap), cs-package-audit locator-containment
check, unsolvable-as-written angle, MAST agent-class inner target.
