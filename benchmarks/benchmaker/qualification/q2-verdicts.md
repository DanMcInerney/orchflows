# Q2 verdicts — qualification context Q2 (independent evidence/judged)

run: 20260807T060439Z-benchmaker-recursion
context: q2 (disjoint from all builder contexts; every result below recomputed from bytes)
date: 2026-08-07
worktree HEAD: e66f3b6
successor set under audit: `.orch/runs/20260807T060439Z-benchmaker-recursion/successor/`
successor-tree identity (sha256 over sorted `relpath:sha256` lines, `__pycache__` excluded, 997 files):
`sha256:6c074734a53db691571b13011bf9587f451bf5298f14da3cca3f33587b755b42`

Method: every probe run executed from its case directory as
`uv run --no-project python probe/check.py <impl>` (the case.toml probe token
contract), Python 3.11 via uv. No case file was edited. Builder claims were not
consulted as evidence anywhere.

---

## QC-5 — equivalence bridge

```
verdict: PASS
oracle: full probe sweep, one run per implementation (plus 3x reruns on
  cs-nondet-fresh), capturing exit code and per-violation lines; a bad seed
  counts only if its probe run exits nonzero with a named failing check
oracle_class: evidence
evidence: 64/64 bad seeds across all 16 cases fail their case probe with at
  least one named check; all 16 targets and all 17 good seeds exit 0; the
  full table below is the proof record
covers: successor-tree sha256:6c074734a53db691571b13011bf9587f451bf5298f14da3cca3f33587b755b42 @ e66f3b6
required: true
```

Equivalent-variant count: **0**. Every case's INERT seed (bad-vacuous /
bad-silent-proceed / bad-proceeded / bad-flat-record / bad-vacuous-record)
fails its probe — no inert-shown-equivalent finding, no discrimination
UNVERIFIED gap under this check.

Reproducibility note: the two N=3 cases were exercised beyond one run —
cs-nondet-fresh's probe (which internally runs the package's declared 3-trial
law) was executed 3 times per implementation with identical verdicts each run;
cs-judged-fresh's scoring path was rerun 3x under QC-7 with byte-identical
results.

| case | seed | deviation | failing check(s) | behavior change |
|---|---|---|---|---|
| cs-antigoodhart-2 | bad-leaked-holdback | memorization @ manifest protected_evidence description (one held-back constant exhibited) | ag.1 | PROVEN |
| cs-antigoodhart-2 | bad-public-only | input-class-drop @ workload-class locus (held-back class undiscriminable, absence undeclared) | ag.2, ag.3 | PROVEN |
| cs-antigoodhart-2 | bad-vacuous (INERT) | oracle-vacuity @ planner scoring | P0.d | PROVEN |
| cs-cli-fresh | bad-crlf | boundary-shift @ CRLF line-terminator locus of the package oracle's output comparison | cli.1 | PROVEN |
| cs-cli-fresh | bad-self-qualified | self-reported-score-trusted @ inner qualification record | cli.3 | PROVEN |
| cs-cli-fresh | bad-vacuous (INERT) | oracle-vacuity @ csvmerge scoring script | P0.d | PROVEN |
| cs-contradiction-fresh | bad-register-dropped | binding-omission @ disagreement-register locus | cd.1 | PROVEN |
| cs-contradiction-fresh | bad-side-pick | value-substitution @ unsettled leap-second locus | cd.2 | PROVEN |
| cs-contradiction-fresh | bad-stale-settlement | input-ignored @ settlement-artifact locus | cd.3 | PROVEN |
| cs-contradiction-fresh | bad-vacuous (INERT) | oracle-vacuity @ parser scoring locus | P0.d | PROVEN |
| cs-cost-fresh | bad-classless | input-class-drop @ W3 witness-class locus | P0.d, cp.2, cp.3 | PROVEN |
| cs-cost-fresh | bad-over-budget | constraint-relaxation @ expected-cost locus | cp.1 | PROVEN |
| cs-cost-fresh | bad-vacuous (INERT) | oracle-vacuity @ query scoring | P0.d, cp.3 | PROVEN |
| cs-intake-refusal | bad-invented-outcome | reference-fabrication @ objective locus | ir.4 | PROVEN |
| cs-intake-refusal | bad-missing-field | binding-omission @ return-contract-fields locus | ir.3 | PROVEN |
| cs-intake-refusal | bad-proceeded (INERT) | guard-deletion @ packet-completeness gate | ir.1, ir.3 | PROVEN |
| cs-intake-refusal | bad-reuse-deficient | default-substitution @ synthesis-reuse gate | ir.2 | PROVEN |
| cs-judged-fresh | bad-compensating | rule-substitution @ judged/deterministic aggregation locus | jd.2 | PROVEN |
| cs-judged-fresh | bad-dangling-anchor | dangling-reference @ anchor-to-source citation locus | jd.3 | PROVEN |
| cs-judged-fresh | bad-no-variance | state-omission @ judge-rerun variance-record locus | jd.1 | PROVEN |
| cs-judged-fresh | bad-vacuous (INERT) | oracle-vacuity @ judged-rubric / condenser scoring locus | P0.d | PROVEN |
| cs-multidomain-fresh | bad-code-only | input-class-drop @ document-domain locus | P0.d, md.1 | PROVEN |
| cs-multidomain-fresh | bad-stale-join | dangling-reference @ cross-domain join locus | md.2 | PROVEN |
| cs-multidomain-fresh | bad-vacuous (INERT) | oracle-vacuity @ doc-domain checks | P0.d, md.1 | PROVEN |
| cs-nondet-fresh | bad-anchor-dropped | binding-omission @ exhibited-trace-anchor locus | nd.2 | PROVEN |
| cs-nondet-fresh | bad-best-of-n | rule-substitution @ trial-aggregation locus | nd.1 | PROVEN |
| cs-nondet-fresh | bad-offset | boundary-shift @ off-by-one stream-offset locus | P0.d, nd.2 | PROVEN |
| cs-nondet-fresh | bad-vacuous (INERT) | oracle-vacuity @ distribution check | P0.d | PROVEN |
| cs-package-audit | bad-axis-missing | binding-omission @ redundancy-axis locus | pa.1 | PROVEN |
| cs-package-audit | bad-seal-drift | artifact-desync @ manifest-tree seal locus | P0.b | PROVEN |
| cs-package-audit | bad-self-provenance | self-referential-provenance @ inner-case provenance | pa.4 | PROVEN |
| cs-package-audit | bad-self-qualified | self-reported-score-trusted @ qualification-independence locus | pa.2 | PROVEN |
| cs-package-audit | bad-unproven-exclusion | guard-deletion @ equivalence-bridge locus | pa.3 | PROVEN |
| cs-package-audit | bad-vacuous-record (INERT) | oracle-vacuity @ qualification record | P0.c, pa.2, pa.3 | PROVEN |
| cs-ranking-fresh | bad-default-tie | default-substitution @ tie-policy locus | rk.2 | PROVEN |
| cs-ranking-fresh | bad-judge-reexec | contract-substitution @ judge-scope locus | rk.4 | PROVEN |
| cs-ranking-fresh | bad-ranks-failure | rule-substitution @ required-eligibility locus | rk.1 | PROVEN |
| cs-ranking-fresh | bad-vacuous (INERT) | oracle-vacuity @ ranking oracle | P0.d, rk.1 | PROVEN |
| cs-ratelimit-fresh | bad-invented-surface | reference-fabrication @ limiter interface locus | rl.2 | PROVEN |
| cs-ratelimit-fresh | bad-margin | value-substitution @ refill-margin off-by-one locus | P0.d | PROVEN |
| cs-ratelimit-fresh | bad-vacuous (INERT) | oracle-vacuity @ limiter scoring | P0.d | PROVEN |
| cs-ratelimit-fresh | bad-wallclock | contract-substitution @ scoring-clock locus | rl.1 | PROVEN |
| cs-refusal-2 | bad-bare-status | early-exit @ return-fields locus | rf.2 | PROVEN |
| cs-refusal-2 | bad-missing-gaps | binding-omission @ gaps-field locus | rf.2 | PROVEN |
| cs-refusal-2 | bad-proxy | contract-substitution @ proxy-oracle locus | rf.3 | PROVEN |
| cs-refusal-2 | bad-silent-proceed (INERT) | guard-deletion @ observability gate | rf.1, rf.2, rf.3 | PROVEN |
| cs-run-conduct | bad-evolve-call | exclusion-breach @ never-clause gate | rc.5 | PROVEN |
| cs-run-conduct | bad-flat-record (INERT) | structure-omission @ record tree | rc.1-rc.8 (all) | PROVEN |
| cs-run-conduct | bad-gap-truncated | value-truncation @ gap-ledger locus | rc.6 | PROVEN |
| cs-run-conduct | bad-lane-collapse | input-class-drop @ charter-lane locus | rc.2 | PROVEN |
| cs-run-conduct | bad-promoted-exhibit | memorization @ protected-tier locus | rc.2 | PROVEN |
| cs-run-conduct | bad-stageless | state-omission @ stage-ledger locus | rc.1 | PROVEN |
| cs-sparse-fresh | bad-gapless | state-omission @ gap-register locus | sp.2 | PROVEN |
| cs-sparse-fresh | bad-invented-rule | reference-fabrication @ QML-lite undocumented-behavior locus | sp.3 | PROVEN |
| cs-sparse-fresh | bad-narrowed | quantifier-narrowing @ exhibited-key-range locus | P0.d | PROVEN |
| cs-sparse-fresh | bad-vacuous (INERT) | oracle-vacuity @ linter scoring locus | P0.d | PROVEN |
| cs-stateful-fresh | bad-construct-commit | side-channel-state @ commit-on-construct-only locus | st.1 | PROVEN |
| cs-stateful-fresh | bad-env-leak | guard-insertion @ env-var-leak locus | P0.d, st.2 | PROVEN |
| cs-stateful-fresh | bad-single-run | state-masking @ migration-journal locus | st.1 | PROVEN |
| cs-stateful-fresh | bad-vacuous (INERT) | oracle-vacuity @ migration scoring | P0.d, st.2 | PROVEN |
| cs-workflow-fresh | bad-edge-short | quantifier-narrowing @ per-edge gate-coverage locus | P0.d, wf.3 | PROVEN |
| cs-workflow-fresh | bad-late-qualification | late-operation @ seal-ordering locus | wf.4 | PROVEN |
| cs-workflow-fresh | bad-reverse-join | reverse-flow @ design-evidence join | wf.5 | PROVEN |
| cs-workflow-fresh | bad-vacuous (INERT) | oracle-vacuity @ package-level aggregate gate | P0.d, wf.1, wf.2, wf.3, wf.6 | PROVEN |

---

## QC-6 — burn-law compliance (Q-BURN)

```
verdict: PASS
oracle: census comparison — every successor `deviation:` line under
  successor/cases/*/seeds/bad-*/defect.md against every predecessor
  `deviation:` line under benchmarks/benchmaker/cases/*/seeds/bad-*/defect.md
  (13-case incumbent set, 40 predecessor lines), family-matched by the
  successor case's `port` key; loci established from defect bodies where the
  predecessor line carries the bare name
oracle_class: evidence
evidence: 0 same-name-same-locus reuses in any same case family; 5 new
  deviation names verified absent from the census; all 9 same-family
  name reuses proven locus-distinct (table below); 2 documentation
  deficiencies noted (no burn violation)
covers: successor-tree sha256:6c074734a53db691571b13011bf9587f451bf5298f14da3cca3f33587b755b42 @ e66f3b6;
  predecessor set at benchmarks/benchmaker/cases @ e66f3b6
required: true
```

Burn violations: **0**.

Predecessor census (26 distinct names over 40 seed lines): ordering-absent,
candidate-derived-reweighting, self-reported-score-trusted,
arrival-order-tie-break, input-class-drop, default-substitution,
value-substitution, boundary-shift, dangling-reference, oracle-vacuity,
binding-omission, contract-substitution, guard-deletion, state-omission,
value-truncation, early-exit, artifact-desync, input-ignored,
rule-substitution, memorization, reference-fabrication, constraint-relaxation,
quantifier-narrowing, state-masking, guard-insertion, side-channel-state.

NEW names (absent from census, verified): late-operation, reverse-flow
(cs-workflow-fresh), exclusion-breach, structure-omission (cs-run-conduct),
self-referential-provenance (cs-package-audit) — 5 seeds lawful by clause (a).

Census names reused in a DIFFERENT case family (no `port` match): 50 seeds —
lawful; the predecessor locus lives in a different case and different inner
target by construction. (cs-intake-refusal, cs-run-conduct, cs-package-audit
carry `port = new`: no predecessor family exists, so no family match is
possible for any of their census-name seeds.)

Same-name SAME-family reuses (the 9 that Q-BURN must prove locus-distinct):

| successor seed | deviation name | predecessor burn (family) | predecessor locus (from defect body) | successor locus | locus verdict | freshness arg in defect.md |
|---|---|---|---|---|---|---|
| cs-cli-fresh/bad-crlf | boundary-shift | cli-dedupe/bad-window-off-by-one | `--window N` eviction arithmetic (`len(recent) > window + 1`) | CRLF line-terminator form of the package oracle's output comparison | DISTINCT | yes |
| cs-ratelimit-fresh/bad-wallclock | contract-substitution | lib-rate-limiter/bad-wall-clock | inner limiter ignores the injected clock, reads `time.monotonic()` | package scoring path sleeps real time (scoring-clock locus; constitutionally unburnable before — predecessor design ran on the real clock) | DISTINCT | yes (burn note) |
| cs-antigoodhart-2/bad-leaked-holdback | memorization | overfit-trap/bad-hardcoded | inner impl answer table over the five exhibited worked examples | manifest protected_evidence description quoting one held-back member outward | DISTINCT | yes |
| cs-sparse-fresh/bad-narrowed | quantifier-narrowing | sparse-evidence/bad-first-only + bad-repeated-key | secret-masking checker witness loci (count=1; repeated-key), different inner target | QML-lite linter exhibited-key-range in cases/cases.json (new inner target) | DISTINCT | yes |
| cs-contradiction-fresh/bad-side-pick | value-substitution | contradictory-evidence/bad-empty-none | empty-input `None` vs `[]` boundary of the ports parser | leap-second acceptance of a fresh date-parsing target (fresh contested boundary) | DISTINCT | yes |
| cs-stateful-fresh/bad-single-run | state-masking | stateful-plugin/bad-delete-masks | KV-store delete tombstone masking membership | migration-journal single-run oracle (escaped second-run state unreachable), fresh inner target | DISTINCT | yes |
| cs-stateful-fresh/bad-construct-commit | side-channel-state | stateful-plugin/bad-state-leak | KV-store shadow file surviving teardown | harness-committed run-2 state directory (commit-on-construct-only) | DISTINCT | **no — deficiency** |
| cs-stateful-fresh/bad-env-leak | guard-insertion | stateful-plugin/bad-overwrite-empty | `if value:` truthiness guard dropping empty-string writes | harness exports MIGRATION_SAFE=1 into the inner env | DISTINCT | **no — deficiency** |
| cs-workflow-fresh/bad-vacuous | oracle-vacuity | composition-target/bad-status-done-check | done_check restating step status (workflow status oracle) | successor package-level aggregate gate accepting an empty run | DISTINCT | yes |

Deficiency (not a burn violation, recorded for the join): design §2 requires
the freshness argument recorded in the seed's defect.md when the predecessor
family matches. `cs-stateful-fresh/seeds/bad-construct-commit/defect.md` and
`cs-stateful-fresh/seeds/bad-env-leak/defect.md` describe their loci in full
but carry no explicit freshness paragraph. Locus distinctness is proven here
independently (different inner target, different mechanism), so QC-6 PASSes;
the two files fall short of the design's recording rule.

---

## QC-7 — judged rerun variance (cs-judged-fresh)

```
verdict: PASS
oracle: 3x rerun of the target package's own documented scoring path
  (`python runner/run.py <impl-dir>` per inner impl, then
  `python scoring/aggregate.py <results.json>`) over the full inner pool
  (reference, good-terse, bad-invented-cite, bad-nearmiss-drop, bad-overlong),
  scratch-copied; per-criterion verdict/score variance computed across runs
oracle_class: judged
evidence: variance 0 on every criterion for every implementation across the
  3 runs — raw runner output bytes identical per impl on all runs
  (sha-compared), aggregate verdicts stable
  (reference PASS/PASS/PASS, good-terse PASS/PASS/PASS,
  bad-invented-cite FAIL/FAIL/FAIL, bad-nearmiss-drop FAIL/FAIL/FAIL,
  bad-overlong FAIL/FAIL/FAIL); per-criterion verdicts stable for
  cite-resolve, length-bound, coverage-sources (deterministic) and
  judged-coverage, judged-no-invention (emitted UNVERIFIED, score null,
  structurally identical every run)
covers: cs-judged-fresh/target benchmark_identity
  sha256:49359fe7b3919f4ea3583374cd4e2b02a833f6cc464e1a83277810beb837f36d;
  runnable_cases sha256:1290ac8e...; runner sha256:35318954...;
  scoring sha256:42e68362...
required: true
```

Recorded numbers: per-criterion score variance across 3 reruns = **0.0** for
every criterion of every inner implementation (population variance over the
emitted scores; judged criteria emit score null + verdict UNVERIFIED
identically each run). The package's judged path is fully deterministic at
probe level — the runner never executes judgment; judging is a separate
budgeted channel. Determinism at probe level was the design's jd intent
(jd.1-jd.3 audit structure, not live judging), so variance 0 is recorded with
that note. The package's own judge-rerun ledger
(qualification/verdicts.json `judge_variance`) records reruns=3 per judged
criterion with scores [2,2,1] (judged-coverage, spread 1) and [2,2,2]
(judged-no-invention, spread 0), recorded at 2026-08-07T05:10:00Z — before the
seal it covers — which is what jd.1 verifies; those ledger numbers are
builder-recorded and are NOT re-derivable by a rerun of the shipped scoring
path (finite and recorded, per design).

---

## Protected store (design §5) — authored by Q2

Store root: `C:\Users\danhm\tools\orchflows-public\.orch\protected\benchmaker-successor-20260807\`
(main-checkout `.orch`, outside the worktree's sealed tree; visibility:
qualification and scoring contexts only; release policy: never to candidate
or builder contexts.)

Canary: every store file carries the marker `CANARY-PROT
2c58e8df-da71-4515-a857-c2275ae246b8` on a `"canary"` line (QC-9 protected
half) — confirmed present in all 5 files at write time.

| store file | sha256 |
|---|---|
| cs-antigoodhart-2/workload.json | f83ad9ea6d934122cfb8cf804162b856600b9331500632ac82479b8497e43e0d |
| stream-held-1.json | f13f1caaf4aafc1ec8f49be1e9bf88d4163d18ad358263c02cfe7a49a18dc5eb |
| stream-held-2.json | 39bd33a4df37567bff1837b4f90714206c476df059506e04c2cb14e9d423af15 |
| stream-held-3.json | 56b3e9654b1c0e8292d5a0ddb02753b026069fa201993c463607fc10488b8296 |
| cs-nondet-fresh/streams.json | 8c0bd8100d501a1188b9e18d215c795015e32c1b9515183e443841541605d4f9 |

held-back stream-set identity (sha256 over sorted `name:sha256` lines of the
three `stream-*.json` files, per the holdback policy's minted-by-Q2 rule):
`sha256:6f86daaef47fe406bab42e94e6dd372f352d48afdf0a41eeb8b1b9b586001115`
— this supersedes the null identity the cs-nondet-fresh manifest recorded at
materialization, per that case's holdback policy. These digests are the
`protected_evidence` values for the suite manifest.

Layout note (load-bearing): cs-nondet-fresh's frozen probe globs
`$BENCH_PROTECTED_DIR/stream-*.json` at the store ROOT, while
cs-antigoodhart-2's probe reads `$BENCH_PROTECTED_DIR/cs-antigoodhart-2/workload.json`.
With one store root serving both cases, the scoring-consumed stream files must
live at the root; `cs-nondet-fresh/streams.json` is the delegation-named index
carrying the same content.

Content facts:

- workload.json: class_identity honors the declared
  `sha256:31cfaadf691d28ad412b4eb30e6a9afc58f1652d52bf261773ee14fc682ac2ce`;
  5 cases in the reserved `HB-Q<digits>` namespace (HB-Q7301..HB-Q7305), all
  rows > 1,000,000 (outside the public class W-PUB), expected plans computed
  from the public rules R1-R3; 4 of 5 defeat the memorizing inner variant
  (verified by simulation before writing).
- streams: 3 held-back streams (k 3/5/4, lengths 14/16/12), item namespace
  `hv-*` verified absent from every file under cs-nondet-fresh (public tree +
  evidence), seeds {977, 1031, 640} disjoint from the public seeds {14, 26};
  divergence of both defective inner samplers verified by simulation on every
  stream (biased: 2/3, 2/3, 3/3 trials; near-miss: 3/3, 2/3, 3/3 trials —
  aggregate FAIL under the all-trials law on every stream).

Full-path smoke (probes rerun with `BENCH_PROTECTED_DIR` = store root):

| case | impl | rc | note |
|---|---|---|---|
| cs-antigoodhart-2 | target | 0 | ag.1 store-token scan + ag.3 held-back discrimination engaged and passed |
| cs-antigoodhart-2 | good-equiv | 0 | |
| cs-antigoodhart-2 | bad-leaked-holdback | 1 | ag.1 |
| cs-antigoodhart-2 | bad-public-only | 1 | ag.2, ag.3 (incl. "does not score the held-back workload class" — full path proven live) |
| cs-antigoodhart-2 | bad-vacuous | 1 | P0.d |
| cs-nondet-fresh | target | 0 | nd.3 held-back sweep engaged and passed |
| cs-nondet-fresh | good-alt-k | 0 | |
| cs-nondet-fresh | bad-anchor-dropped | 1 | nd.2 |
| cs-nondet-fresh | bad-best-of-n | 1 | nd.1 |
| cs-nondet-fresh | bad-offset | 1 | P0.d, nd.2, nd.3 |
| cs-nondet-fresh | bad-vacuous | 1 | P0.d, nd.3 (held-back streams also refuse the vacuous oracle — nd.3 lines prove the protected path executed) |

candidate-inaccessible-check: **null** at this seal (by design) →
**optimization-resistance UNVERIFIED** recorded as an explicit gap. The
barrier is procedural (store location + release policy); detection is by
canary only (GD3/D4).

---

## Liveness trials (design §8 Q2 — matched builder model, capacity-bounded)

Contamination caveat, recorded up front: Q2 had already read every probe's
source and the full seed sweep output before running these trials (QC-5 duty
order). The trials were authored from `evidence/` + the case.toml `outcome` +
repo-law contracts only (no `target/`, no `seeds/`, no `expected.md` was read
for authoring), but knowledge of probe internals cannot be fully unwound; the
attempt-1 failures below are the honest fresh-builder signal, and the
adaptations used exactly the feedback a scored candidate would receive (the
probe's own violation lines).

### Trial 1 — cs-cli-fresh (deterministic) — PASS on attempt 3

Candidate: a full csvmerge benchmark package (manifest with minted identity,
11 cases, runner, scoring, provenance, qualification), authored from
evidence/spec.md, evidence/transcripts.md and the licensed
evidence/inner-impls pool, at
`<scratchpad>/liveness/cs-cli-fresh-candidate` (final benchmark_identity
`sha256:148ec6f67c62c5ece2fd49499b8282f0040ecaa3eb794977c8529c0285f131c0`).
Self-sweep before sealing: reference PASS, good-equiv PASS, bad-drop-dedup
FAIL, bad-near-miss-final-key FAIL (the final-key preference boundary was
derivable from the licensed pool bytes); double-sweep byte-identical.

- Attempt 1: probe FAIL — 6x "P0.b: component lacks identity/locator". The
  manifest schema law (benchmaker-manifest.md) fixes NO component-reference
  key names ("the schema prescribes no storage layout"); this probe demands
  the key `identity`, while a sibling case's own sealed target
  (cs-judged-fresh/target/manifest.json) uses `sha256` — the demanded shape
  varies between cases inside one suite.
- Attempt 2: probe CRASH — `AttributeError` at
  `qualification.get("overall").get("verdict")` when `overall` is the string
  `"PASS"` (the exact shape cs-judged-fresh's sealed target uses). Per design
  §4 a probe crash is UNVERIFIED, never FAIL — this is a probe robustness
  finding: a plausible candidate shape crashes cs-cli-fresh's probe instead of
  producing a violation line.
- Attempt 3: PASS (7 checks, P0.a-P0.d + cli.1-cli.3) after conforming to
  three more probe-dictated schemas: runnable-case record keys
  (`a`/`b`/`stdout`/`exit`, `anchor` = bare transcript id, `{a}`/`{b}` argv
  placeholders), runner report JSON (`{"pass": bool, "cases": [{"id",
  "pass"}]}`), and qualification evidence as a dict carrying a `context` key
  distinct from provenance `builder_context`.
- Time spent: ~40 minutes of one context (authoring + 3 probe runs).

E1-class signal: every SEMANTIC demand (CRLF tolerance breadth, transcript
anchoring, final-key discrimination floor, qualification independence, seal
recomputation) was licensed by the evidence and satisfiable first-try. What
the evidence did NOT license is the interchange shapes: component-reference
key name, case-record field names the anchor check hard-codes, the runner
report schema, and the evidence-dict/context convention. A fresh builder fails
on shape, not semantics, and converges only through probe-feedback iterations
— while the schema law explicitly disclaims layout prescription and sibling
sealed targets exhibit incompatible shapes. If candidates receive only
PASS/FAIL (not violation lines), attempt-1 convergence is near-impossible;
with violation lines it took 3 attempts.

### Trial 2 — cs-intake-refusal (process-shaped) — PASS on attempt 2

Candidate: a blocked return document authored from evidence/packet.md +
evidence/synthesis-offered.md + the verdict contract, at
`<scratchpad>/liveness/cs-intake-refusal-candidate/return.md`. Both intake
defects were independently derivable from the evidence: the packet exhibits
no `bounds` field, and the offered synthesis carries six of the seven
`required_synthesis_artifacts` (provenance missing). The return blocks at
intake, names both defects, carries partial evidence / gaps / spend /
reply_to `orch-main-17`, marks the deficient synthesis not-reusable, and
invents no bound, outcome, or boundary.

- Attempt 1: probe FAIL — "ir.3: no status field in the return" (status was a
  `## Status` heading; the probe wants a `status:` field line). Fairly
  licensed: the packet's own grammar is field-lines, so this shape was
  guessable; scored as a light shape miss.
- Attempt 2: PASS.
- Time spent: ~12 minutes of one context (authoring + 2 probe runs).

Solvability: both trials PASS — the cases are solvable by a matched builder
model from their evidence; the friction is concentrated in unlicensed
interchange shapes (trial 1), not in reasoning or evidence sufficiency.

---

## Final verdicts

- QC-5 equivalence bridge: **PASS** (oracle_class evidence). Equivalent
  variants: **0** of 64 bad seeds; every inert seed behavior-proven.
- QC-6 burn-law / Q-BURN: **PASS** (oracle_class evidence). Burn violations:
  **0**; 5 new names verified; 9 same-family reuses locus-distinct; 2
  freshness-paragraph deficiencies in cs-stateful-fresh defect.md files
  (documentation only, no violation).
- QC-7 judged rerun variance: **PASS** (oracle_class judged). Variance 0.0 on
  every criterion across 3 reruns of the package's own scoring path;
  determinism at probe level per design jd intent; builder judge ledger
  (spreads 1 and 0, 3 reruns each) recorded before seal.
- Protected store: authored at
  `C:\Users\danhm\tools\orchflows-public\.orch\protected\benchmaker-successor-20260807\`;
  5 files, digests above; CANARY-PROT marker in every file; full-path smoke
  green both directions (targets+goods 0, bads 1) for both protected cases;
  held-back stream-set identity
  `sha256:6f86daaef47fe406bab42e94e6dd372f352d48afdf0a41eeb8b1b9b586001115`;
  optimization-resistance **UNVERIFIED** gap recorded
  (candidate-inaccessible-check null by design).
- Liveness: cs-cli-fresh PASS (attempt 3, ~40 min; E1-class signal on
  unlicensed interchange shapes + one probe-crash robustness finding);
  cs-intake-refusal PASS (attempt 2, ~12 min).

Q2 spend: full sweep 96 probe runs (+12 nondet-stability reruns, +15 QC-7
executions, +11 smoke runs, +5 liveness probe runs) ≈ 139 probe/scoring
executions, aggregate wall clock under 4 minutes of probe time; total context
wall time ≈ 2.5 h.
