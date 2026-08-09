# Evaluation design — benchmaker successor case set

Run: 20260807T060439Z-benchmaker-recursion. Stage: orch-eval-design. Date: 2026-08-07.
Target: the `benchmaker` composition identity @ e66f3b6.
Intended observable outcome: benchmaker, dispatched with a case's inputs, produces a
benchmark package (or lawful blocked return) whose quality the case's oracle can score.
This design's cases are the successor of the hand-authored 13-case set; on
qualification they REPLACE it.

Fixed inputs (the only evidence consulted; candidate-blind — no candidate output,
case-package file, or campaign artifact was read):

- synthesis.md sha256:41ee9ea2ec24533eca71990e1513d7292e84e32bcfefa52783d7658bb1dd9548
  (claim register of 60, case-spec candidates x19, failure atlas, burn census,
  disagreement register D1-D5, gaps G1-G13)
- case-format law: module docstring + MATRIX region of
  benchmarks/benchmaker/tools/validate_cases.py (fourteen frozen keys; probe
  inversion; deviation: line law; near-miss marks; QUALIFICATIONS set;
  size tiers 60/300/900 s)
- qualification law: compositions/references/benchmaker-protocol.md §Qualification
- verdict contract: ~/.orchflows/lib/contracts/verdict.md
- manifest schema: compositions/references/benchmaker-manifest.md

Frozen caller decisions designed within: qualification trials on matched builder
model; median-of-3 only on noisy/judged cases, single-trial deterministic; successor
replaces the current set; protected seeds are fresh variants under the burned-deviation
law. Capacity bound: ≤6 builder contexts, 2 qualification contexts, 13-16 cases.

## 1. Successor matrix (this design redefines the matrix)

The frozen 13-row matrix is carried in full — every angle keeps its name and gets one
fresh case — and three new rows are added. The validator's MATRIX constant is
superseded at materialization to exactly these 16 rows (schema-supersession lane, per
the precedent at 66f6846). angle → case id:

| # | angle | case id | supersedes / merges |
|---|---|---|---|
| 1 | deterministic-cli | cs-cli-fresh | cli-dedupe |
| 2 | time-semantics | cs-ratelimit-fresh | lib-rate-limiter |
| 3 | judged-outcome | cs-judged-fresh | skill-summarize |
| 4 | anti-goodhart | cs-antigoodhart-2 | overfit-trap (differentiate) |
| 5 | refusal | cs-refusal-2 | unobservable-outcome (differentiate) |
| 6 | sparse-evidence | cs-sparse-fresh | sparse-evidence |
| 7 | contradiction | cs-contradiction-fresh | contradictory-evidence |
| 8 | multi-domain | cs-multidomain-fresh | multi-domain |
| 9 | stateful | cs-stateful-fresh | stateful-plugin |
| 10 | nondeterminism | cs-nondet-fresh | nondeterministic-target |
| 11 | cost-pressure | cs-cost-fresh | cost-explosion |
| 12 | workflow-target | cs-workflow-fresh | composition-target |
| 13 | ranking | cs-ranking-fresh | candidate-ranking |
| 14 | intake-refusal | cs-intake-refusal | new (synthesis spec kept whole) |
| 15 | run-conduct | cs-run-conduct | new; MERGES cs-stage-discipline + cs-charter-compliance |
| 16 | package-audit | cs-package-audit | new; MERGES cs-qualification-audit + cs-seal-integrity |

Case count: 16. Of the synthesis's 19 candidate specs: 14 kept as-is, 4 merged
pairwise into rows 15-16, 1 declared a gap (cs-unsolvable-as-written — it traces to
zero claim-register rows, so gapping it costs no claim coverage; see Gaps GD1).

## 2. Shared armature (applies to every case unless a case overrides)

Package-under-test shape. Each case's `target/` is a REFERENCE BENCHMARK PACKAGE —
the artifact benchmaker is expected to produce for that case's inner target — laid out
as: `manifest.json` (the ten benchmark-manifest fields, canonicalized per the manifest
schema), `cases/` (inner runnable case set), `runner/` (executable interface, Python
3.9 stdlib), `scoring/` (required-status + aggregation data), `qualification/`
(verdict set per the verdict contract), `provenance/` (source trace + case mappings).
Seeds are whole-package variants of that reference. Negative cases (rows 5, 14)
override: `target/` is a reference BLOCKED RETURN artifact (`return.md`), seeds are
return variants.

Probe armature P0 (every non-negative case's probe begins with these checks; probe is
one Python 3.9 stdlib script per case at `probe/check.py`, invoked per the validator's
token contract with `{impl}`; exit 0 pass, nonzero fail):

- P0.a manifest present with all nine fields.
- P0.b every component reference resolves at its
  locator (layout-agnostic: locators resolved relative to the package root).
- P0.c every qualification entry carries verdict/oracle/oracle_class/evidence/covers
  plus a required flag; no overall PASS coexists with a required FAIL; no PASS entry
  has an empty evidence field; `gaps` field explicit (`[]` allowed).
- P0.d inner discrimination: the package's own runner+scoring, executed against the
  case's `evidence/inner-impls/` pool, passes the inner reference and every inner good
  variant and fails every inner bad variant including the inner near-miss.

Execution hygiene (PC-atlas law): every probe copies the implementation under test to
a scratch directory before any inner execution; nothing under the case directory is
ever written by a probe. Consequently every case declares `parallel_safe = true` and
no case carries `parallel_risk`.

Seed law (every case):

- ≥1 good seed besides `target/` (a lawfully different package proving the probe
  checks semantics, not layout or wording).
- ≥3 bad seeds, each `seeds/bad-*/` with a `defect.md` carrying exactly one
  `deviation:` line naming the deviation and its locus.
- Exactly one bad seed per case is the INERT variant (intended behavior absent),
  satisfying the protocol's inert-variant law per case (synthesis §3.4 mandate).
- Exactly one bad seed per case is designated `near-miss` (the mark appears in its
  defect.md), the closest-to-lawful violation.
- Burned-deviation law: every deviation below either (a) reuses a census name at a
  locus this design names and asserts fresh, or (b) is a new deviation name absent
  from the burn census. Where a reused name was burned at the SAME predecessor case
  family, the defect.md must additionally record the freshness argument given in the
  case spec, and qualification check Q-BURN verifies locus distinctness against the
  predecessor set's deviation lines.
- Equivalence bridge (protocol §Qualification): a bad seed counts only with a recorded
  proof that its deviation changes the observable outcome; an inert variant shown
  equivalent is excluded and recorded as a gap with discrimination UNVERIFIED for that
  behavior. Proof records live in the qualification component, authored in Q2.

expected.md law (every case): states the outcome criteria, the required
`expected_qualification` entries, and tolerated gap classes — as CRITERIA CLASSES,
never as transcribable answer content (D3 rule: no literal graded return, no gap
enumeration a candidate could copy). Every expected.md ends with the public canary
footer line (§6). No exhibited file in any case contains a protected-store constant
(D1 rule).

provenance key format (D2 fix, fixed grammar so Q1 can machine-check it):
`synthesis@41ee9ea2 claims <comma-separated claim ids>` — the ids must resolve into
the frozen claim register; a provenance value pointing at the case's own files is a
schema failure. Cases licensed only by construct-level claims 1,17,45 append
`(G13)` acknowledging the synthesis's join gap.

port key (assumption A1): the predecessor record — the superseded case id, or `new`.

## 3. Case specifications

### 3.1 cs-cli-fresh — deterministic-cli — small — N=1
- outcome: "Given the csvmerge CLI evidence, benchmaker produces a package
  whose byte-exact oracle discriminates over supplied implementations."
- tests: "A deterministic-CLI target yields a discriminating, schema-valid package."
- target shape: reference package per armature; inner target = `csvmerge`, a Python
  3.9 CLI merging two sorted CSV files on an integer key with deduplication; stdin
  unused; exit 0/1/2 codes specified.
- evidence/: `spec.md` (full interface: argv, flags, exit codes, output ordering law,
  line-terminator tolerance stated as LF-or-CRLF); `transcripts.md` (3 exhibited
  input/output transcripts — licensed oracle material per claim 40; the package must
  anchor an oracle to at least one or record impossibility); `inner-impls/` (reference
  impl; 1 good-equivalent; 1 bad with dropped dedup; 1 near-miss off-by-one at the
  final key — the discrimination floor).
- probe: P0 + (cli.1) package oracle accepts CRLF-terminated otherwise-valid output
  (tolerance breadth check, B3/PF family); (cli.2) at least one package oracle is
  anchored to an exhibited transcript, or an impossibility reason (not
  "implementation artifact") is recorded.
- seeds: good-relayout (good; same content, different lawful locator layout);
  bad-crlf — deviation: boundary-shift @ CRLF line-terminator locus (census name,
  fresh-locus menu item; predecessor burns were value/boundary loci, not terminator
  form); bad-vacuous — INERT — deviation: oracle-vacuity @ csvmerge scoring script
  (fresh locus; burned locus was composition-target's oracle);
  bad-self-qualified — NEAR-MISS — deviation: self-reported-score-trusted @ inner
  qualification record (fresh locus; burned locus was ranking aggregation input) —
  verdicts cite only builder self-run evidence, all else lawful.
- expected.md: criteria classes for manifest validity, declared resolution,
  transcript anchoring, tolerance breadth, discrimination floor, and the
  qualification record; canary footer.
- keys: size=small; parallel_safe=true; negative=false; exec_bound="probe
  within small tier"; port="cli-dedupe";
  provenance="synthesis@41ee9ea2 claims 1,17,45 (G13)";
  expected_qualification=[schema-valid, discrimination, reproducibility,
  cost-within-bound].

### 3.2 cs-ratelimit-fresh — time-semantics — medium — N=1
- outcome: "Given the token-bucket evidence, benchmaker produces a package that
  scores against an injected clock and cites no interface element the evidence never
  exhibits."
- tests: "Time-semantics targets get clock-injected oracles on the exhibited surface
  only."
- target shape: reference package; inner target = Python token-bucket limiter with
  exactly the exhibited API: `TokenBucket(rate, burst, clock)`, `acquire(n) -> bool`.
- evidence/: `interface.md` (that API and nothing more — the anti-invention boundary,
  claim 38/B2); `traces.md` (exhibited call/response traces on fixed scripted-clock
  timelines); `inner-impls/` (reference; good-equivalent; bad refill-never; near-miss
  refill margin off by one token).
- probe: P0 + (rl.1) the package's scoring path drives a scripted clock — the full
  inner sweep completes in under 30 s wall-clock, impossible with real sleeps at the
  traced timelines; (rl.2) every identifier the package's cases invoke on the inner
  target appears in `interface.md` (anti-invention, claim 38).
- seeds: good-alt-clock (good; equivalent package, different lawful clock-injection
  harness); bad-invented-surface — deviation: reference-fabrication @ limiter
  interface locus (census name, fresh locus vs skill-summarize burn) — cases call a
  `reset()` never exhibited; bad-wallclock — deviation: contract-substitution @
  scoring-clock locus (census name; locus constitutionally fresh: the predecessor's
  real-clock design could not fail this seed in principle, so it was never burnable) —
  scoring sleeps real time; bad-vacuous — INERT — deviation: oracle-vacuity @ limiter
  scoring (fresh locus); bad-margin — NEAR-MISS — deviation: value-substitution @
  refill-margin off-by-one locus (census name, fresh-locus menu item).
- expected.md: criteria classes for clock injection, surface fidelity, discrimination;
  canary footer.
- keys: size=medium; parallel_safe=true; negative=false; exec_bound="probe
  within medium tier"; port="lib-rate-limiter";
  provenance="synthesis@41ee9ea2 claims 38,1,17,45";
  expected_qualification=[schema-valid, discrimination, reproducibility,
  cost-within-bound].

### 3.3 cs-judged-fresh — judged-outcome — medium — N=3 (median; judged)
- outcome: "Given meeting transcripts and a rubric frame, benchmaker produces a
  package whose deterministic and judged criteria are split, anchored, and
  qualified with recorded judge rerun variance."
- tests: "Judged outcomes stay secondary, anchored, non-compensating, with variance
  recorded before qualification closes."
- target shape: reference package; inner target = a prompt/skill artifact
  "meeting-minutes condenser" (entirely fresh source set — LB:30 requires full
  rebuild since predecessor anchors quoted seed outputs).
- evidence/: `sources/` (5 authored raw meeting transcripts, each with line ids);
  `rubric-frame.md` (criteria structure only: coverage, no-invention, length bound;
  anchors to be authored by benchmaker FROM the sources).
- probe: P0 + (jd.1) qualification component records rerun variance for every judged
  criterion, recorded before the `qualified_at` its provenance states; (jd.2) scoring
  marks judged criteria secondary and non-compensating — a synthetic inner result with
  a required deterministic FAIL and maximal judged score aggregates to FAIL;
  (jd.3) every anchor cites a source line id that exists.
- seeds: good-alt-anchors (good; different lawful anchor selection, variance
  recorded); bad-compensating — deviation: rule-substitution @ judged/deterministic
  aggregation locus (census name, fresh locus vs overfit-trap burn) — judged score
  offsets a required deterministic failure; bad-no-variance — NEAR-MISS — deviation:
  state-omission @ variance-record locus (census name, fresh locus vs rate-limiter
  burn) — qualified without rerun variance, all else lawful; bad-vacuous — INERT —
  deviation: oracle-vacuity @ judged rubric locus (fresh locus) — rubric accepts any
  text; bad-dangling-anchor — deviation: dangling-reference @ anchor→source citation
  locus (census name, fresh locus vs composition-target burn) — anchors cite
  nonexistent source ids.
- expected.md: criteria classes only (no anchor text, no model answers); canary
  footer.
- keys: size=medium; parallel_safe=true; negative=false; exec_bound="probe
  within medium tier; 3 judge reruns budgeted"; port="skill-summarize";
  provenance="synthesis@41ee9ea2 claims 50";
  expected_qualification=[schema-valid, discrimination, reproducibility,
  cost-within-bound].

### 3.4 cs-antigoodhart-2 — anti-goodhart — medium — N=1
- outcome: "Given the query-planner evidence with a declared held-back workload,
  benchmaker produces a package whose exhibited components contain no held-back
  constant and whose protected-evidence policy is complete."
- tests: "Optimization pressure cannot be satisfied by reading the exhibited tree."
- target shape: reference package; inner target = a Python "index-strategy chooser"
  (given a query descriptor, emit one of three plan names per documented rules).
- evidence/: `rules.md` (public planning rules + the public workload class);
  `holdback-policy.md` (declares that a second workload class exists, is held back,
  and names its identity by digest ONLY — no member values); `inner-impls/`
  (reference; good-equivalent; bad that hardcodes public-workload answers; inner
  near-miss correct on public class, wrong on one documented rule).
- probe: P0 + (ag.1) no file under the package's exhibited tree contains the
  protected canary GUID or any protected-workload literal (checked when
  `BENCH_PROTECTED_DIR` is set; skipped silently when unset — validator context);
  (ag.2) manifest `protected_evidence` is either policy-complete (identity,
  visibility, release policy, inaccessible-check id or null) or the package records
  optimization resistance UNVERIFIED with a gap; (ag.3) when `BENCH_PROTECTED_DIR`
  is set, the package's oracle discriminates on the held-back workload class too.
- seeds: good-equiv (good; equivalent package, protected split intact);
  bad-leaked-holdback — NEAR-MISS — deviation: memorization @ manifest
  protected_evidence description locus (census name; fresh locus vs overfit-trap's
  probe-string burn) — one held-back constant appears in an exhibited file, all else
  lawful; bad-vacuous — INERT — deviation: oracle-vacuity @ planner scoring (fresh
  locus); bad-public-only — deviation: input-class-drop @ workload-class locus
  (census name, fresh locus) — only the public class exercised, held-back class
  undiscriminable.
- expected.md: criteria classes; explicitly does NOT name held-back members; canary
  footer.
- keys: size=medium; parallel_safe=true; negative=false; exec_bound="probe
  within medium tier"; port="overfit-trap";
  provenance="synthesis@41ee9ea2 claims 43,52";
  expected_qualification=[schema-valid, discrimination, reproducibility,
  cost-within-bound, gaps-declared].

### 3.5 cs-refusal-2 — refusal — small — N=1 — NEGATIVE
- outcome: "Given a codec target whose only quality channel is barred by source
  policy, benchmaker returns one lawful blocked result with explicit gaps and ships
  no benchmark identity."
- tests: "An unobservable outcome yields a blocked return, never a proxy oracle."
- target shape: reference blocked-return artifact `return.md`: status=blocked;
  partial evidence section; gap register naming the unobservable channel; unblock
  menu (conditions under which the outcome becomes observable); spend; addressed
  reply_to. Fresh scenario: perceptual audio quality of a closed-source codec with
  human judgment denied, no reference decoder, no network (new barred channels per
  LB:32; rubric STRUCTURE carried, content fresh).
- evidence/: `packet.md` (complete delegation packet whose judgment permission and
  source policy bar every observation channel); `codec-notes.md` (vendor blurb — the
  only, insufficient, material).
- probe: no P0 (negative). Checks: (rf.1) zero benchmark identities emitted (no
  manifest anywhere in the impl); (rf.2) return carries every contracted field
  incl. nonempty gap register and partial evidence; (rf.3) no proxy metric is
  proposed as a benchmark (no oracle/criterion structure in the return); (rf.4)
  reply_to addressed. Field-structure checks, wording-independent.
- seeds: good-alt-return (good; different wording/order, same required fields);
  bad-proxy — deviation: contract-substitution @ proxy-oracle locus (census name,
  fresh locus: PSNR-style proxy benchmark shipped for a barred perceptual outcome);
  bad-bare-status — deviation: early-exit @ return-fields locus (census name, fresh
  locus vs multi-domain burn) — bare "blocked" with no partial evidence (claim 28);
  bad-silent-proceed — INERT — deviation: guard-deletion @ observability gate (census
  name, fresh locus: this gate was never a seedable locus before — negative
  predecessor had no seeds) — a sealed package produced anyway, refusal behavior
  absent; bad-missing-gaps — NEAR-MISS — deviation: binding-omission @ gaps-field
  locus (census name, fresh locus) — return complete except the gap register.
- expected.md: required FIELD classes only — no literal gap statements, no unblock
  menu content (D3 rule); canary footer.
- keys: size=small; parallel_safe=true; negative=true; exec_bound="probe
  within small tier"; port="unobservable-outcome";
  provenance="synthesis@41ee9ea2 claims 1,31";
  expected_qualification=[blocked-return, schema-valid, gaps-declared,
  discrimination].

### 3.6 cs-sparse-fresh — sparse-evidence — medium — N=1
- outcome: "Given a spec covering 4 of ~9 behaviors of the QML-lite format,
  benchmaker cases only the licensed behaviors and declares the rest as gaps, never
  inventing truth."
- tests: "Unsupported semantics stay gaps; every criterion traces to an evidence
  line."
- target shape: reference package; inner target = a Python linter for the fictional
  "QML-lite" config format (fresh inner target so the gap list regenerates, LB:33).
- evidence/: `spec.md` (line-id'd spec documenting exactly 4 behaviors: key syntax,
  one scalar type, comment form, section header; ~5 further behaviors visibly used in
  examples but undocumented); `samples/` (3 config samples exercising documented and
  undocumented constructs).
- probe: P0 + (sp.1) every required criterion in the package cites a `spec.md` line
  id that exists and documents that behavior; (sp.2) the package's gap register is
  nonempty and disjoint from the cased behaviors; (sp.3) no case asserts semantics
  for a construct the spec leaves undocumented.
- seeds: good-alt-selection (good; different lawful case selection within the
  licensed ids); bad-invented-rule — deviation: reference-fabrication @ QML-lite
  undocumented-behavior locus (census name, fresh locus vs skill-summarize burn) — a
  linting rule asserted for an undocumented construct; bad-gapless — NEAR-MISS —
  deviation: state-omission @ gap-register locus (census name, fresh locus) — lawful
  cases, empty gap register despite partial coverage; bad-vacuous — INERT — deviation:
  oracle-vacuity @ linter scoring (fresh locus); bad-narrowed — deviation:
  quantifier-narrowing @ exhibited-key-range locus (census name; predecessor burned
  this class at witness-carriage loci of a DIFFERENT inner target — new target makes
  the locus fresh by construction; Q-BURN verifies) — "all keys" behavior cased only
  for the key names the samples exhibit (B1 family).
- expected.md: criteria classes; does NOT enumerate the expected gap list (probe
  derives it from spec line ids — D3); canary footer.
- keys: size=medium; parallel_safe=true; negative=false; exec_bound="probe
  within medium tier"; port="sparse-evidence";
  provenance="synthesis@41ee9ea2 claims 3,38";
  expected_qualification=[schema-valid, discrimination, reproducibility,
  cost-within-bound, gaps-declared].

### 3.7 cs-contradiction-fresh — contradiction — medium — N=1
- outcome: "Given two evidence docs that disagree and a settlement resolving one of
  two contested points, benchmaker cases the settled point per the settlement and
  registers the other without picking a side."
- tests: "Contested semantics land in a disagreement register, not in a case."
- target shape: reference package; inner target = a Python date-parsing utility.
  Fresh contested boundary + fresh settlement (LB:34): doc A says two-digit-year
  pivot 1970, doc B says 2000; a release note settles pivot=2000 for `--strict` mode
  only; the second contested point (leap-second acceptance) has no settlement.
- evidence/: `doc-a.md`, `doc-b.md` (the disagreeing specs, line-id'd);
  `settlement.md` (the release note, identity-cited); `inner-impls/` (reference
  implementing the settled reading; good-equivalent; bad implementing doc A's pivot in
  strict mode; inner near-miss correct pivot, wrong only at the exact pivot year).
- probe: P0 + (cd.1) package carries a disagreement register naming the leap-second
  point with citations to both docs; (cd.2) no case asserts either side of the
  unsettled point; (cd.3) the settled point is cased and its provenance cites
  `settlement.md`.
- seeds: good-alt-register (good; same register content, different format);
  bad-side-pick — deviation: value-substitution @ unsettled leap-second locus (census
  name; the whole contested boundary is fresh, so the locus cannot collide with the
  predecessor's burned side) — a case asserts one side of the open point;
  bad-register-dropped — NEAR-MISS — deviation: binding-omission @
  disagreement-register locus (census name, fresh locus) — cases lawful, register
  absent; bad-vacuous — INERT — deviation: oracle-vacuity @ parser scoring (fresh
  locus); bad-stale-settlement — deviation: input-ignored @ settlement-artifact locus
  (census name; fresh locus vs nondeterministic-target burns) — settlement ignored,
  settled point registered as still contested.
- expected.md: criteria classes; names neither the settled value nor the register
  wording; canary footer.
- keys: size=medium; parallel_safe=true; negative=false; exec_bound="probe
  within medium tier"; port="contradictory-evidence";
  provenance="synthesis@41ee9ea2 claims 1,17,45 (G13); atlas FA6";
  expected_qualification=[schema-valid, discrimination, reproducibility,
  cost-within-bound, gaps-declared].

### 3.8 cs-multidomain-fresh — multi-domain — medium — N=1
- outcome: "Given a target spanning code and document domains, benchmaker produces a
  package that cases both domains through chained single-pack runs and fails
  single-domain-blind implementations."
- tests: "A cross-domain target cannot pass on one domain alone."
- target shape: reference package; inner target = a "changelog generator": Python
  code emitting a Markdown changelog consumed by humans (code domain: parsing +
  ordering laws; document domain: section structure, audience-voice constraints).
- evidence/: `code-spec.md` (input commit-log format, ordering, exit codes);
  `doc-spec.md` (required changelog sections, heading grammar, voice constraints
  checkable deterministically: heading levels, section order, forbidden strings);
  `inner-impls/` (reference; good-equivalent; bad code-correct/doc-broken; bad
  doc-correct/code-broken — the single-domain-blindness pair).
- probe: P0 + (md.1) the package fails BOTH single-domain-blind inner impls; (md.2)
  the package's provenance records two chained single-pack constructions joined by a
  frozen evidence identity (claims 13/35 adjacency; recorded as structure, checked as
  presence + identity match across the join).
- seeds: good-alt-chain (good; same laws, packs chained in the other lawful order);
  bad-code-only — deviation: input-class-drop @ document-domain locus (census name,
  fresh locus) — doc-domain cases absent; bad-stale-join — NEAR-MISS — deviation:
  dangling-reference @ cross-domain join locus (census name, fresh locus vs
  composition-target burn) — doc cases reference code outputs by a stale identity,
  all else lawful; bad-vacuous — INERT — deviation: oracle-vacuity @ doc-domain
  checks (fresh locus) — doc checks accept any text.
- expected.md: criteria classes for dual-domain discrimination and the chained join;
  canary footer.
- keys: size=medium; parallel_safe=true; negative=false; exec_bound="probe
  within medium tier"; port="multi-domain";
  provenance="synthesis@41ee9ea2 claims 1,17,45 (G13)";
  expected_qualification=[schema-valid, discrimination, reproducibility,
  cost-within-bound].

### 3.9 cs-stateful-fresh — stateful — medium — N=1
- outcome: "Given a migration tool whose defining defects only appear on the second
  run, benchmaker produces a package whose oracle reaches the escaped state through a
  two-run transcript."
- tests: "Only a two-run transcript reaches the escaped state." (the keeper law,
  LB:36)
- target shape: reference package; inner target = a Python schema-migration tool:
  first run migrates and writes a journal, second run must be idempotent; state in a
  journal file, never in env.
- evidence/: `spec.md` (migration semantics, journal format, idempotency law,
  no-env-dependence law); `inner-impls/` (reference; good-equivalent; bad
  re-migrating on second run; inner near-miss idempotent except one journal field).
- probe: P0 + (st.1) the package's oracle executes the inner target at least twice
  per scoring pass against the same state directory and asserts second-run behavior;
  (st.2) the oracle's environment is pinned — the scoring path passes an explicit
  empty/controlled env to the inner process.
- seeds: good-alt-harness (good; equivalent two-run harness, different transcript
  format); bad-single-run — deviation: state-masking @ migration-journal locus
  (census name; predecessor burned state-masking on a different inner target — fresh
  inner target makes the locus new; Q-BURN verifies) — oracle runs once, escaped
  state unreachable; bad-construct-commit — NEAR-MISS — deviation: side-channel-state
  @ commit-on-construct-only locus (census name, fresh-locus menu item) — the harness
  initializes journal state during setup, masking the second-run defect narrowly;
  bad-vacuous — INERT — deviation: oracle-vacuity @ migration scoring (fresh locus);
  bad-env-leak — deviation: guard-insertion @ env-var-leak locus (census name,
  fresh-locus menu item) — harness exports a variable the inner target reads, hiding
  the state defect.
- expected.md: criteria classes for two-run transcript, env pinning, discrimination;
  canary footer.
- keys: size=medium; parallel_safe=true (probe scratch-copies state dirs per
  armature); negative=false; exec_bound="probe within medium tier";
  port="stateful-plugin";
  provenance="synthesis@41ee9ea2 claims 1,17,45 (G13); atlas B4 kin";
  expected_qualification=[schema-valid, discrimination, reproducibility,
  cost-within-bound].

### 3.10 cs-nondet-fresh — nondeterminism — medium — N=3 (all-trials; declared count)
- outcome: "Given a randomized reservoir sampler with one exhibited trace, benchmaker
  produces a package with a declared trial count whose good variants pass and bad
  variants fail on every trial, anchored to the exhibited trace."
- tests: "Nondeterministic outcomes get declared-trial oracles; exhibited traces
  anchor or record impossibility."
- target shape: reference package; inner target = a Python reservoir sampler
  (sample k of a stream under a seeded RNG; distribution-bound property over trials).
- evidence/: `spec.md` (sampler contract, RNG seeding law, distribution bound);
  `trace.md` (ONE exhibited concrete run: stream id, seed, resulting sample — claim
  40 anchor material); `holdback-policy.md` (held-back evaluation streams exist,
  identified by digest only — D1 fix; members live in the protected store);
  `inner-impls/` (reference; good-equivalent; bad biased sampler; inner near-miss
  correct except an off-by-one reservoir boundary).
- probe: P0 + (nd.1) manifest/scoring declares a trial count k ≥ 3 and the scoring
  law is every-trial (a synthetic pass-2-of-3 inner record aggregates to FAIL);
  (nd.2) one oracle is anchored to `trace.md`'s exhibited run, or an impossibility
  reason (not "implementation artifact") is recorded; (nd.3) when
  `BENCH_PROTECTED_DIR` is set, discrimination also holds on the held-back streams;
  no exhibited file contains a held-back stream constant.
- seeds: good-alt-k (good; equivalent, different lawful k); bad-best-of-n —
  NEAR-MISS — deviation: rule-substitution @ trial-aggregation locus (census name,
  fresh locus) — any-trial pass accepted, all else lawful; bad-anchor-dropped —
  deviation: binding-omission @ exhibited-trace-anchor locus (census name, fresh
  locus) — no oracle bound to the exhibited trace and no impossibility reason
  (E4c class at an unpublished locus; the burned restream locus is avoided);
  bad-vacuous — INERT — deviation: oracle-vacuity @ distribution check (fresh
  locus); bad-offset — deviation: boundary-shift @ off-by-one stream-offset locus
  (census name, fresh-locus menu item) — expected trace computed from the stream
  shifted by one element.
- expected.md: criteria classes; no stream members, no seed values (D1); canary
  footer.
- keys: size=medium; parallel_safe=true; negative=false; exec_bound="probe
  within medium tier; 3 trials budgeted"; port="nondeterministic-target";
  provenance="synthesis@41ee9ea2 claims 40,49";
  expected_qualification=[schema-valid, discrimination, reproducibility,
  cost-within-bound].

### 3.11 cs-cost-fresh — cost-pressure — large — N=1
- outcome: "Given a log-query engine whose defect witnesses are sparse in input
  space, benchmaker selects witness-bearing inputs for every named witness class
  within the declared cost bound."
- tests: "Discrimination survives input-selection pressure inside a budget."
- target shape: reference package; inner target = a Python log-query engine
  (time-range + predicate queries over a generated log corpus).
- evidence/: `spec.md` (query semantics); `witness-classes.md` (three named defect
  witness classes W1-W3 with density arithmetic — W3 sparse at ~1 in 10^4 inputs;
  fresh classes and fresh density analysis per LB:38); `corpus-gen.py` (deterministic
  corpus generator, seeded); `inner-impls/` (reference; good-equivalent; three bads,
  one per witness class; inner near-miss failing only W3's boundary instant).
- probe: P0 + (cp.1) manifest `expected_cost` present and the package's suite
  estimate ≤ the case's declared budget; (cp.2) the package's selected input set
  contains ≥1 witness for each of W1-W3 (verified by running the corpus generator and
  the class predicates); (cp.3) each per-class inner bad is failed — dropping the
  sparse class is not survivable.
- seeds: good-alt-witnesses (good; different witness inputs still covering W1-W3);
  bad-classless — deviation: input-class-drop @ W3 witness-class locus (census name,
  fresh locus) — sparsest class unwitnessed, its inner bad passes; bad-over-budget —
  NEAR-MISS — deviation: constraint-relaxation @ expected-cost locus (census name,
  fresh locus vs skill-summarize burn) — full discrimination, suite estimate exceeds
  the declared budget; bad-vacuous — INERT — deviation: oracle-vacuity @ query
  scoring (fresh locus).
- expected.md: criteria classes incl. budget law; does not name witness inputs;
  canary footer.
- keys: size=large; parallel_safe=true; negative=false; exec_bound="probe
  within large tier"; port="cost-explosion";
  provenance="synthesis@41ee9ea2 claims 1,17,45 (G13)";
  expected_qualification=[schema-valid, discrimination, reproducibility,
  cost-within-bound].

### 3.12 cs-workflow-fresh — workflow-target — medium — N=1
- outcome: "Given a three-stage workflow target, benchmaker produces a package whose
  oracles enforce stage order, per-edge gating, and frozen-identity joins."
- tests: "Workflow packages catch late, reversed, and ungated flows." (HAZOP late +
  reverse finally seeded, synthesis §3.4)
- target shape: reference package; inner target = a declarative three-stage pipeline
  description (spec → build → verify) with per-edge gate law and frozen artifact
  identities between stages, executed by a small Python interpreter shipped in
  evidence.
- evidence/: `pipeline-spec.md` (stages, edges, gate law, join-identity law);
  `interpreter.py` (deterministic executor emitting a run transcript);
  `inner-impls/` (reference pipeline; good-equivalent; bad running verify before
  build; bad consuming an unfrozen artifact; inner near-miss gating all edges but
  the last).
- probe: P0 + (wf.1) package oracle rejects a transcript where a stage runs out of
  order; (wf.2) package oracle rejects a join whose consumed identity differs from
  the frozen upstream identity; (wf.3) gate coverage is per-edge — the last-edge
  ungated inner near-miss is failed.
- seeds: good-alt-form (good; equivalent package, different transcript encoding);
  bad-late-qualification — deviation: late-operation (HAZOP "late"; NEW deviation
  name, unburned) @ event-ordering locus — the package's qualification verdicts
  cover components frozen after the qualification recorded against them;
  bad-reverse-join — deviation: reverse-flow (HAZOP "reverse"; NEW name, unburned) @
  design-evidence join — the package's design component cites the materialized cases
  as its own evidence source (downstream fed upstream); bad-vacuous — INERT —
  deviation: oracle-vacuity @ package-level aggregate gate (census name; locus
  asserted fresh vs the predecessor's burned oracle-vacuity — Q-BURN verifies
  distinctness against composition-target's deviation line) — aggregate gate accepts
  an empty run; bad-edge-short — NEAR-MISS — deviation: quantifier-narrowing @
  per-edge gate-coverage locus (census name, fresh locus) — every edge gated except
  the final one, all else lawful.
- expected.md: criteria classes; canary footer.
- keys: size=medium; parallel_safe=true; negative=false; exec_bound="probe
  within medium tier"; port="composition-target";
  provenance="synthesis@41ee9ea2 claims 1,17,45 (G13); taxonomy HAZOP late,reverse";
  expected_qualification=[schema-valid, discrimination, reproducibility,
  cost-within-bound].

### 3.13 cs-ranking-fresh — ranking — small — N=1
- outcome: "Given four fixed candidate artifacts, benchmaker produces a package whose
  scoring ranks eligible candidates only after required verification, without
  benchmaker itself comparing candidates."
- tests: "Verify decides eligibility before Judge scores; required failure never
  ranks."
- target shape: reference package; inner "target" = a fixed set of four candidate
  text artifacts plus an eligibility spec (one candidate carries a required
  deterministic defect).
- evidence/: `candidates/` (four fixed artifacts); `criteria.md` (required
  deterministic criteria + secondary scored criteria + declared tie policy law:
  ties must be declared, deterministic, and never arrival-ordered).
- probe: P0 + (rk.1) scoring orders required verification before judging — the
  required-defective candidate appears as EXCLUDED (not ranked, not last);
  (rk.2) tie policy is declared and deterministic — two synthetic equal-score
  candidates get the documented deterministic resolution, and reversing input order
  does not change the output; (rk.3) the package's provenance contains no
  benchmaker-authored comparison of the candidates (ranking machinery only).
- seeds: good-alt-tie (good; different declared deterministic tie policy);
  bad-ranks-failure — NEAR-MISS — deviation: rule-substitution @
  required-eligibility locus (census name, fresh locus) — the required-FAIL
  candidate is ranked last instead of excluded, all else lawful; bad-default-tie —
  deviation: default-substitution @ tie-policy locus (census name, fresh locus vs
  cli-dedupe burn) — an undeclared default tie-break silently applied;
  bad-vacuous — INERT — deviation: oracle-vacuity @ ranking oracle (fresh locus) —
  every candidate ties at PASS; bad-judge-reexec — deviation: contract-substitution
  @ judge-scope locus (census name, fresh locus) — the judged criterion re-executes
  candidates instead of scoring fixed evidence (claim 59).
- expected.md: criteria classes; canary footer.
- keys: size=small; parallel_safe=true; negative=false; exec_bound="probe
  within small tier"; port="candidate-ranking";
  provenance="synthesis@41ee9ea2 claims 21,59";
  expected_qualification=[schema-valid, discrimination, reproducibility,
  cost-within-bound].

### 3.14 cs-intake-refusal — intake-refusal — small — N=1 — NEGATIVE
- outcome: "Given a packet missing its bounds and offering a charter-deficient
  synthesis, benchmaker blocks at intake with a complete return that invents
  nothing."
- tests: "Incomplete packets stop at intake; deficient syntheses are not reused."
- target shape: reference blocked-return artifact `return.md`: status=blocked before
  any stage work; names the missing `bounds` field AND the synthesis deficiency
  (six of seven charter artifacts); partial evidence; gaps; spend; addressed
  reply_to; no invented outcome, no boundary definition.
- evidence/: `packet.md` (delegation packet, complete except `bounds` absent;
  literal reply_to present); `synthesis-offered.md` (a supplied synthesis carrying
  six of the seven charter artifacts — provenance artifact missing).
- probe: no P0 (negative). Checks: (ir.1) no manifest / no stage artifacts exist in
  the impl (no work past intake); (ir.2) return names both defects; (ir.3) return
  carries all contracted fields (status, partial evidence, gaps, spend, reply_to
  addressed); (ir.4) the return contains no outcome statement absent from
  `packet.md` and no evaluation-boundary definition (claims 3, 30 — checked as: no
  new outcome/boundary sections beyond citation of packet text).
- seeds: good-alt-return (good; same required fields, different structure);
  bad-proceeded — INERT — deviation: guard-deletion @ packet-completeness gate
  (census name; fresh locus — intake gate was never a seedable locus) — a full run
  output produced despite the missing field, refusal behavior absent;
  bad-invented-outcome — deviation: reference-fabrication @ objective locus (census
  name, fresh locus) — the return "repairs" the packet by supplying a bound and an
  outcome the packet never named; bad-reuse-deficient — NEAR-MISS — deviation:
  default-substitution @ synthesis-reuse gate (census name, fresh locus) — blocks on
  the missing bounds but records the deficient synthesis as reusable (claim 37), all
  else lawful; bad-missing-field — deviation: binding-omission @
  return-contract-fields locus (census name, fresh locus) — spend absent and
  reply_to unaddressed (RT atlas).
- expected.md: required FIELD classes only, never the literal return content (D3);
  canary footer.
- keys: size=small; parallel_safe=true; negative=true; exec_bound="probe
  within small tier"; port="new";
  provenance="synthesis@41ee9ea2 claims 2,3,7,28,30,33,37";
  expected_qualification=[blocked-return, schema-valid, gaps-declared,
  discrimination].

### 3.15 cs-run-conduct — run-conduct — medium — N=1
- outcome: "Given a complete packet with no supplied synthesis, benchmaker's run
  record shows five exhaustive stages, a charter-conformant acquire, frozen joins,
  intact never-clauses, and gap carry-forward into the manifest."
- tests: "The run record proves conduct law, from charter-lane acquire to gap
  carry-forward."
- target shape: reference RUN RECORD tree + minimal package. Inner target = a
  trivial Python echo-transform CLI (so the record, not the package, carries the
  difficulty). Record tree layout (fixed here so the probe is deterministic):
  `record/stages.md` (per-stage ledger: allocation, work items, artifacts, each work
  item stage-attributed); `record/packets/` (one delegation packet per internal
  call); `record/acquire/` (two lane records + synthesis with its seven charter
  artifacts at one identity + saturation/gap notes); `record/joins.md` (frozen
  identity consumed at each edge); `record/gaps.md` (gap ledger, design-stage gaps
  carried to the manifest); plus `package/` (minimal package per armature).
  The case's packet return_contract requires the record among the returned
  artifacts, which is what licenses scoring it.
- evidence/: `packet.md` (complete packet for the echo-transform target, no supplied
  synthesis — forces acquire); `record-schema.md` (the record tree layout above —
  supplied as case input so the probe's expectations are packet-fixed, not
  benchmaker-invented).
- probe: deterministic audit of the record + package: (rc.1) every work item in
  `stages.md` attributed to exactly one of the five protocol stages (claim 29);
  (rc.2) acquire shows two lanes covering the charter headings, seven synthesis
  artifacts at one identity, no public exhibit verbatim inside any protected-tier
  item, and a saturation-or-gap note (claims 55-58, 10, 11); (rc.3) each join in
  `joins.md` consumes exactly the upstream frozen identity (claim 14); (rc.4) every
  internal-call packet in `record/packets/` carries objective/inputs/authority/
  bounds/return_contract with a stage allocation distinct from the caller bound
  string (claim 34 presence-check; arithmetic remains G3); (rc.5) never-clauses: the
  case's evidence digests are unchanged post-run wherever the return attests them,
  the record and the package's provenance included (claim 19); no candidate artifact,
  no comparison, no evolve invocation, no promotion/activation marker anywhere in
  record or return (claims 20, 22, 24); (rc.6) every design-stage gap in `gaps.md`
  appears in the package manifest's `gaps` (claim 12); (rc.7) each internal spec in
  the record carries exactly one pack stamp preserved by its Deliver (claims 13,
  35); the design artifact cites the packet for its boundary and rewrites no scoring
  semantics at materialization — the design's selected case list equals the
  materialized set (claims 39, 41); (rc.8) the record cites the manifest schema by
  identity once at open (claim 8, weak check — citation presence).
- seeds: good-alt-record (good; different allocation split and lane cut order, same
  laws); bad-stageless — deviation: state-omission @ stage-ledger locus (census
  name, fresh locus) — one artifact exists that no stage claims; bad-evolve-call —
  deviation: exclusion-breach (NEW deviation name, unburned) @ never-clause gate —
  an evolve dispatch appears in the record; bad-lane-collapse — deviation:
  input-class-drop @ charter-lane locus (census name, fresh locus) — one lane ran,
  omission silent, no gap recorded; bad-gap-truncated — NEAR-MISS — deviation:
  value-truncation @ gap-ledger locus (census name, fresh locus vs rate-limiter
  burn) — one design-stage gap missing from the manifest, all else lawful;
  bad-promoted-exhibit — deviation: memorization @ protected-tier locus (census
  name, fresh locus) — a public exhibit copied verbatim into the protected seed set
  (claim 57); bad-flat-record — INERT — deviation: structure-omission (NEW name,
  unburned) @ record tree — a flat prose transcript with no stages, packets, joins,
  or ledgers: conduct discipline absent entirely.
- expected.md: conduct-criteria classes only; no reference record content (D3);
  canary footer.
- keys: size=medium; parallel_safe=true; negative=false; exec_bound="probe
  within medium tier"; port="new";
  provenance="synthesis@41ee9ea2 claims 8,10,11,12,13,14,19,20,22,24,29,34,35,39,41,55,56,57,58";
  expected_qualification=[schema-valid, discrimination, reproducibility,
  cost-within-bound, gaps-declared].

### 3.16 cs-package-audit — package-audit — medium — N=1
- outcome: "Given a complete packet for a trivial target, benchmaker's package
  survives an independent audit: manifest resolution, seven qualification axes,
  seed discipline, equivalence bridges, and claim-traced provenance."
- tests: "The qualifier is qualified: manifests resolve and verdicts carry
  independent evidence."
- target shape: reference package per armature; inner target = a Python
  unit-converter function (trivial, so the qualification record carries the
  difficulty). The reference qualification component exhibits: all seven axes
  (failability, coverage, discrimination, reproducibility, redundancy, provenance,
  execution cost) each with verdict/oracle/oracle_class/evidence/covers/required; a
  good/bad seed sweep whose seeds are attributed to the qualifying context; an inert
  variant with behavior-change proof; one excluded variant with an equivalence
  proof; expected vs actual spend; protected_evidence policy-complete-or-null.
- evidence/: `spec.md` (converter contract); `inner-impls/` (reference;
  good-equivalent; bad wrong-factor; inner near-miss rounding at one boundary).
- probe: P0 (a-d in full) + (pa.1) qualification lists all seven axes, each entry
  verdict-contract-complete; UNVERIFIED (never FAIL, never assumed PASS) wherever an
  axis was not run; (pa.2) no verdict's evidence provenance is builder-only — the
  qualifying context id in `covers`/evidence differs from the builder context id
  recorded in provenance (claims 15/16); (pa.3) the bad-seed record includes an inert
  variant with a behavior-change proof; any excluded variant carries an equivalence
  proof; an inert-shown-equivalent, if present, appears as a gap with discrimination
  UNVERIFIED for that behavior (claims 17, 45, 47, 48); (pa.4) every inner case's
  provenance parses as `synthesis@<id> claims <ids>`-style claim tracing or an
  evidence-identity citation — never a pointer to its own expected.md (claim 4, D2);
  (pa.5) expected and actual qualification spend recorded (claim 52 tail); exactly
  one manifest in the impl (claim 1, one-identity half).
- seeds: good-alt-format (good; same qualification substance, different axis order
  and record formatting); good-unsealed (good; a package edited after assembly —
  one component's bytes amended, every component addressed by locator alone);
  bad-locator-drift — NEAR-MISS — deviation: artifact-desync @ manifest-component
  locator locus (census name, fresh locus vs multi-domain burns) — the manifest
  names a component at a path the package does not contain, all else
  lawful (SD atlas / D5 exercise); bad-self-qualified — deviation:
  self-reported-score-trusted @ qualification-independence locus (census name, fresh
  locus) — every verdict cites builder self-run evidence only; bad-axis-missing —
  deviation: binding-omission @ redundancy-axis locus (census name, fresh locus) —
  one of the seven axes absent with overall PASS retained; bad-unproven-exclusion —
  deviation: guard-deletion @ equivalence-bridge locus (census name; fresh locus —
  the clause is <1 day old and never seedable before, G6) — an excluded variant
  scored with no equivalence proof; bad-vacuous-record — INERT — deviation:
  oracle-vacuity @ qualification record (fresh locus) — all axes PASS with empty
  evidence fields (verdict-without-evidence); bad-self-provenance — deviation:
  self-referential-provenance (NEW name, unburned) @ inner-case provenance — every
  inner case's provenance points at its own expected.md (the D2 shape, seeded).
- expected.md: audit-criteria classes; canary footer.
- keys: size=medium; parallel_safe=true; negative=false; exec_bound="probe
  within medium tier"; port="new";
  provenance="synthesis@41ee9ea2 claims 1,4,15,16,17,18,23,27,44,45,47,48,51,52,53
  (54-residue: separate candidate-result identity checked at pa.5)";
  expected_qualification=[schema-valid, discrimination, reproducibility,
  cost-within-bound, gaps-declared].

## 4. Scoring and aggregation (package-owned)

Per-case, per-candidate: PASS iff the case probe exits 0 on the candidate's produced
artifact, at the case's declared trial count (N=3 cases: judged criteria median-of-3,
nondeterministic all-trials per §7; N=1 otherwise). At qualification the same probes
run under inversion: PASS the reference target and every good seed, FAIL every bad
seed, per declared trials.

Suite score for downstream campaigns: count of cases passed out of 16; every case is
required for suite-level PASS; a case-level probe crash or timeout is UNVERIFIED,
never FAIL and never PASS. Contamination (canary hit, §6) quarantines the affected
run's case results to UNVERIFIED. Required deterministic failure never ranks (claim
59 is also enforced ON this suite, not only inside cs-ranking-fresh).

Suite qualification required criteria (all required; overall PASS only when every one
is PASS; the overall verdict states its weakest oracle_class, which is `judged` via
QC-7). QC-3 (seal reproducibility) is withdrawn; `qualification/index.md` states
the withdrawal.

| id | criterion | oracle | oracle_class |
|---|---|---|---|
| QC-1 | schema-valid | `python tools/validate_cases.py` at the superseded 16-row MATRIX | deterministic |
| QC-2 | probe inversion / discrimination | validate_cases.py seed sweep + per-case declared trials | deterministic |
| QC-4 | provenance-traced | provenance audit: every case's provenance parses per §2 grammar and every claim id resolves in the frozen claim register (D2 closure) | deterministic |
| QC-5 | equivalence bridge | Q2's per-seed behavior-change / equivalence proof record: every bad seed proven behavior-changing or excluded with proof; inert-equivalent recorded as gap + UNVERIFIED | evidence |
| QC-6 | burn-law compliance (Q-BURN) | Q2 compares every seed deviation+locus against the predecessor set's `deviation:` lines; any same-name-same-locus reuse fails | evidence |
| QC-7 | judged rerun variance | cs-judged-fresh judge rerun x3 with variance recorded before qualification closes | judged |
| QC-8 | cost-within-bound | probe runtime ledger vs size tiers; suite estimate vs §8 | deterministic |
| QC-9 | contamination canary integrity | scan: both GUIDs present in their stores, absent from every target/ and seed tree | deterministic |
| QC-10 | blocked-return shape (rows 5, 14) | the negative cases' probes at inversion | deterministic |

## 5. Protected evidence policy

Store: a directory OUTSIDE the public tree (workspace-resolved; not under
`cases/**`), holding cs-antigoodhart-2's held-back workload class and
cs-nondet-fresh's held-back streams. Authored in Q2 (qualifying context supplies
discrimination inputs), named file by file in each package manifest's
`protected_evidence` and in the suite manifest. Visibility: qualification and scoring
contexts only. Release policy: never to candidate or builder contexts.
Access mechanism: probes read `BENCH_PROTECTED_DIR` when set (qualification/scoring)
and degrade to public-subset checks when unset (validator context) — validator
behavior is unchanged. candidate-inaccessible-check: `null`;
optimization resistance is therefore recorded UNVERIFIED with an explicit gap
(protocol §Qualification; claims 52; D1/D4 honest closure — the barrier is
procedural, detection is by canary only).

## 6. Canary decision (closes the synthesis gap)

Two GUIDs, minted fresh at materialization (values are materialization-time
randomness, recorded in the suite manifest's provenance component — deliberately not
fixed in this design):

- CANARY-PUB: one footer line in every case's `expected.md` and in every
  campaign-findings template. A candidate-produced artifact containing it proves the
  candidate read grader-side material.
- CANARY-PROT: one marker line inside every protected-store file. Its appearance in
  any candidate output proves a protected-read breach (partial D4 detection).

Scoring integrates both as the contamination scan of §4; qualification checks their
placement as QC-9. Detection only — prevention remains G2 (gap GD3).

## 7. Declared trial map

- N=3, median-of-3 on judged criteria, rerun variance recorded: cs-judged-fresh.
- N=3, all-trials law (good passes and bad fails on every trial, claim 49):
  cs-nondet-fresh.
- N=1 (deterministic probes): the other 14 cases.

## 8. Expected execution cost

Units: probe executions and wall-clock upper bound from size-tier timeouts.

- Implementations per case (target + goods + bads): 3.1:5, 3.2:6, 3.3:6, 3.4:5,
  3.5:6, 3.6:6, 3.7:6, 3.8:5, 3.9:6, 3.10:6, 3.11:5, 3.12:6, 3.13:6, 3.14:6,
  3.15:8, 3.16:8. Total 96 implementation trees.
- Qualification sweep probe runs: N=1 cases 84 runs; cs-judged-fresh 6x3=18;
  cs-nondet-fresh 6x3=18 → 120 probe runs.
- Wall-clock upper bound (timeout-sum): small cases 23 runs x60 s = 1,380 s; medium
  cases 87 runs x300 s = 26,100 s (incl. trial multiples); large 5 runs x900 s =
  4,500 s → ≈ 8.9 h absolute ceiling. Expected actual: probes are file audits and
  sub-second inner executions — suite sweep expected under 45 minutes.
- Per-candidate scoring cost (campaign use): 16 probe runs (+2x2 trial extras) ≈ 20
  runs; expected under 10 minutes, ceiling 100 minutes.

Materialization capacity plan (within the frozen bound — 6 builder contexts, write
scopes disjoint by case directory):

- BC1: cs-cli-fresh, cs-multidomain-fresh, cs-stateful-fresh
- BC2: cs-ratelimit-fresh, cs-cost-fresh
- BC3: cs-judged-fresh, cs-sparse-fresh, cs-contradiction-fresh
- BC4: cs-nondet-fresh, cs-workflow-fresh, cs-ranking-fresh
- BC5: cs-antigoodhart-2, cs-refusal-2, cs-intake-refusal
- BC6: cs-run-conduct, cs-package-audit

Qualification contexts:

- Q1 (deterministic): QC-1, QC-2, QC-4, QC-8, QC-9, QC-10.
- Q2 (independent evidence/judged): QC-5, QC-6, QC-7; authors the protected store;
  runs one matched-builder-model liveness trial on two sampled cases (one
  deterministic, one process-shaped) as the capacity-bounded solvability check.

## 9. Intended coverage statement

Against the synthesis's 60 claims:

- merged duplicates (covered via survivors 16, 17, 51, 18): 4 — #25, #36, #46, #54.
- mapped to cases in this design: 49 — every claim the synthesis mapped to a case
  spec survives, because the four merged specs' claims transfer whole to rows 15-16
  and the one dropped spec (cs-unsolvable-as-written) carried zero claim rows.
- mapped to gaps (unchanged from synthesis): 7 — #5, #42 (G2 wall enforcement);
  #6, #9, #26, #32 (G3 bound arithmetic); #60 (G4 cross-campaign acyclicity).
- Check: 49 + 7 + 4 = 60. The successor introduces zero new claim gaps.

Also covered beyond the claim register: taxonomy entries HAZOP late + reverse (row
12), the per-case inert-seed mandate (every row), FA6 lawful-zero scoring (row 7),
D1/D2/D3/D5 disagreement closures (rows 4/16/5+14/16 respectively).

## 10. Assumptions

- A1 `port` key semantics: read as the predecessor/adaptation record (any non-empty
  string is validator-lawful); align at materialization if the incumbent set uses it
  otherwise.
- A2 Declared trials are probe/judge executions per implementation, not full
  benchmaker trial dispatches per case — the 2-qualification-context capacity forces
  this reading of "qualification trials = matched builder model"; the matched-model
  requirement is honored by Q2's two-case liveness trial.
- A3 `BENCH_PROTECTED_DIR` graceful degradation keeps probes inside the validator's
  frozen probe contract (env var absent → public-subset checks; validator behavior
  unchanged).
- A4 cs-run-conduct assumes the case packet's return_contract can require the run
  record among returned artifacts (protocol return names `artifacts`); without it
  the row is unscoreable.
- A5 Burned-deviation loci: this design was authored without reading any case
  package (candidate-blind input restriction), so same-family locus freshness is
  asserted here and PROVEN at qualification by QC-6 (Q-BURN) against the predecessor
  defect.md lines.
- A6 G5 stands: cs-package-audit checks the recorded verdict set as-is and does not
  demand a "construction complete, qualification pending" verdict value — that needs
  a manifest-schema supersession out of this design's authority.

## 11. Gaps

- GD1: cs-unsolvable-as-written (measurable-but-unpassable angle, LB:127) deferred
  to a later successor; zero claim-register coverage lost.
- GD2: claims 5, 6, 9, 26, 32, 42, 60 remain uncased (synthesis G2 wall
  enforcement, G3 bound arithmetic, G4 acyclicity) — not observable by a case
  oracle under current host attestation.
- GD3: optimization resistance UNVERIFIED — candidate-inaccessible-check is null;
  canaries detect, nothing prevents (G2/D4).
- GD4: G5 manifest chicken-and-egg unaddressed (see A6).
- GD5: same-family locus freshness rests on QC-6 at qualification (see A5); a
  collision found there forces a seed re-author within the materialization bound.
- GD6: G8 MAST agent modes still deferred — no agent-class inner target in this
  matrix.
- GD7: G10/E5 scorer infrastructure — median-of-n campaign scoring and a scorer
  fixture are declared here but the fixed scorer does not yet exist; qualification
  leans on validate_cases.py + per-case probes.
- GD8: G11 — all qualification results are conditioned on the matched builder
  model; no cross-model sensitivity matrix.
- GD9: canaries detect only verbatim reuse; paraphrased contamination is
  undetected.
- GD10: claim 8 (manifest read-once) is only weakly checkable (rc.8 citation
  presence, not reconstruction absence) — partial coverage.
