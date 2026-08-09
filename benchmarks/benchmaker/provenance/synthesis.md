# Synthesis — benchmaker recursion acquire join
Run: 20260807T060439Z-benchmaker-recursion. Date: 2026-08-07.
Inputs (all at target revision e66f3b6): lane-a-packet.md (LA), lane-b-packet.md (LB),
compositions/references/benchmaker-research.md (charter; artifact contract).
Citation convention: LA:<line> / LB:<line> = packet line numbers. Claim row N in §2
cites LA line 15+N. Doc aliases (COMP/PROT/MAN/CHART/DOCS/B0/EV) as defined at LA:6-10.

Superseded in part, 2026-08-09: sealing was removed from the law
(run 20260809T021408Z-benchmaker-unseal). Claim 53, failure mode SD and
disagreement D5 record the sealing law as it stood on 2026-08-07 and are kept
unedited — every case's `provenance` resolves against these row numbers — but
nothing they describe is current. A benchmark's version is now its git revision.

## 1. Construct definition

The capability measured is: **benchmaker's ability to take one complete delegation
packet fixing a target with an observable outcome, and produce exactly one immutable,
independently qualified, discriminating benchmark for it — or return a lawful blocked/
partial result when the packet is incomplete, the outcome unobservable, or the evidence
unsupportable — without ever inventing target truth, qualifying its own work, mutating
the target, generating or comparing candidates, promoting anything, or exceeding its
bound.** (Sources: LA:16-45 claims 1, 12, 17, 19-26, 31, 38; LB:32 refusal angle.)

Scope: the composition identity at e66f3b6 — COMP + PROT + MAN + CHART + DOCS —
executed as orchflows dispatch on the recorded host (LA:214-237). Out of scope, by the
never-clauses (LA:34-41): candidate generation, candidate comparison, promotion or
activation, in-place revision, calling Evolve, defining the evaluation boundary. One
capability; construction quality and lawful refusal are the same construct exercised at
observable vs unobservable/unsupportable inputs, not two constructs (LA:185-200).

## 2. Claim register (central artifact)

60 lane-A claims; 4 merged where two sources state one law; 49 mapped to case
specifications (defined in §2.1); 7 mapped to gaps (§6 ids). Claims are compressed;
substance preserved; full wording at the cited LA line (15+N).

| # | claim (compressed) | src | defeater (compressed) | maps to |
|---|---|---|---|---|
| 1 | Exactly one immutable runnable benchmark per invocation; refuse targets with no observable outcome | COMP:2-3 | two identities emitted, or no-outcome target accepted | cs-refusal-2 (refusal half); cs-seal-integrity (one-identity half) |
| 2 | One complete delegation packet required; work on incomplete packet invalid | COMP:7-8 | run proceeds past a missing named field | cs-intake-refusal |
| 3 | `objective` names target identity and intended observable outcome | COMP:8-9 | produced design invents an outcome the packet never named | cs-intake-refusal (invented-outcome seed; also watched by cs-sparse-fresh) |
| 4 | `inputs` name fixed evidence identities, source policy, judgment permission, pack refs | COMP:9-11 | package cites evidence absent from packet inputs | cs-qualification-audit (provenance axis; see D2) |
| 5 | `authority` grants write scope and excluded actions | COMP:12 | write outside scope (observed once, EV:100-101) | GAP G2 (enforcement is textual, not host-attested; LA:206-208) |
| 6 | `bounds` carry one caller bound incl. expected cost | COMP:13 | no cost expectation, or two bounds honored | GAP G3 |
| 7 | `return_contract` names status/identity/qualification/gaps/spend/artifacts; literal reply_to | COMP:14-16 | closing return missing a field; unaddressable reply_to (observed, LA:22) | cs-intake-refusal |
| 8 | Carrier rule and manifest read once at open | COMP:18-19 | manifest shape reconstructed from memory (observed, LA:23) | cs-stage-discipline |
| 9 | Bound partitioned before work; fixed identities preserved | COMP:20-21 | work before allocations; identity rewritten mid-run | GAP G3 (partition half); identity half audited by cs-stage-discipline |
| 10 | acquire-spec freezes one evidence-acquisition spec per charter; skip only on supplied qualified synthesis | COMP:24-29 | ad-hoc acquire with no frozen spec | cs-stage-discipline |
| 11 | Non-complete acquire → partial evidence, design stops | COMP:30-32; PROT:48-50 | design started downstream of incomplete acquire | cs-stage-discipline |
| 12 | Unobservable design gap → stop; other declared gaps carry forward | COMP:33-36; PROT:54-57 | materialization past unobservable design; gap silently dropped | cs-stage-discipline |
| 13 | materialize: same Spec/Deliver owners, one pack per internal spec, exactly the selected cases | COMP:37-41; PROT:65-69 | spec with two packs; case outside selected set | cs-stage-discipline |
| 14 | Edge joins carried by frozen evidence identity | COMP:43-47 | downstream consumes identity ≠ frozen upstream identity | cs-stage-discipline |
| 15 | INV: qualification at fixed identity, context independent of builders | COMP:50-51; PROT:77-78 | verdict authored in the building context | cs-qualification-audit |
| 16 | INV: builders never qualify own cases/oracles as sufficient evidence | COMP:51-52; PROT:78-79 | verdicts citing only builder-authored evidence | cs-qualification-audit — MERGE: absorbs #25 (never-clause restatement, LA itself flags it) and #36 (PROT:36-37 disjoint-authority restatement) |
| 17 | INV: discrimination over known-good/known-bad seeds supplied by the qualifying context; no bad seed possible → UNVERIFIED + gap | COMP:52-54; PROT:83-92 | PASS with builder seeds; no-bad-seed case qualified without gap | cs-qualification-audit — MERGE: absorbs #46 (PROT:84-86 restatement). Instantiated by every angle spec's seed matrix |
| 18 | INV: sealed under immutable manifest schema; any change mints successor identity | COMP:55-58; MAN:32-34 | in-place edit after seal; byte change under unchanged identity (near-miss observed: seal drift, LA:33) | cs-seal-integrity — MERGE: absorbs #54's immutability clause (MAN:34-35) |
| 19 | NEVER mutate the target | COMP:59 | any write into target files (observed at host layer: __pycache__ contamination, LA:157-159) | cs-stage-discipline |
| 20 | NEVER generate a candidate | COMP:59 | candidate authored inside a run | cs-stage-discipline |
| 21 | NEVER compare candidates (benchmark may rank; benchmaker must not) | COMP:59-60 | benchmaker itself emitting a comparison | cs-ranking-fresh |
| 22 | NEVER promote or activate | COMP:60; DOCS:32-37 | auto-activation at run close | cs-stage-discipline |
| 23 | NEVER revise a benchmark in place | COMP:60 | second run mutating a sealed package | cs-seal-integrity |
| 24 | NEVER call Evolve | COMP:61; DOCS:26-28 | evolve invocation in dispatch record | cs-stage-discipline |
| 25 | (duplicate of #16) | COMP:61 | — | MERGED → #16 |
| 26 | NEVER multiply the caller bound | COMP:61-62; PROT:14-17 | stage allocations exceed bound; bound copied into child packet | GAP G3 |
| 27 | DONE: verdict set covers the identity — PASS on every required criterion, gaps explicit (`[]` when none) | COMP:64-66 | complete close with uncovered criterion or absent gaps field | cs-qualification-audit |
| 28 | Failure returns carry partial evidence; closing result addresses reply_to | COMP:68-71 | failed run returns bare status string | cs-intake-refusal |
| 29 | The five protocol stages are exhaustive | PROT:3-4 | work attributable to no stage | cs-stage-discipline |
| 30 | Target identity opaque; boundary received, never defined by benchmaker | PROT:8-10,58-59 | produced design fixes the boundary itself | cs-intake-refusal |
| 31 | Unobservable outcome / unavailable oracle → explicit gap, never a proxy oracle | PROT:10-11 | proxy oracle invented (counter-evidence of health: B0:21 — but see D3) | cs-refusal-2 |
| 32 | Bound partition arithmetic: nonnegative, ≤ caller bound, carry-forward, never copy bound down | PROT:13-17,36-37 | child packet carries caller bound verbatim | GAP G3 |
| 33 | Intake fixes all identities/policies/scopes/return fields; one pack per internal spec | PROT:19-22 | any item resolved lazily mid-run | cs-intake-refusal |
| 34 | Every internal call carries one complete packet, stage-restricted authority, stage allocation | PROT:26-33 | inline internal call without packet | cs-stage-discipline |
| 35 | Each Spec selects one pack; paired Deliver preserves the stamp | PROT:36 | Deliver re-stamped to different pack | cs-stage-discipline |
| 36 | (restates #16) | PROT:36-37 | — | MERGED → #16 |
| 37 | Supplied synthesis reused only when identity/provenance/coverage/charter artifacts fixed | PROT:41-44 | reuse of synthesis missing a charter artifact | cs-intake-refusal (deficient-synthesis seed) |
| 38 | Synthesis freezes at one identity; unsupported semantics stay gaps, never invented truth | PROT:48-49 | invented expectation as required criterion — OBSERVED: B2 `capacity` (B0:42-46), recurred (EV:31) | cs-ratelimit-fresh (B2 locus) + cs-sparse-fresh |
| 39 | Design neither fixes boundary nor selects/revises/interprets case+scoring semantics | PROT:58-59 | benchmaker rewriting scoring semantics at materialization | cs-stage-discipline |
| 40 | Exhibited concrete input/output/trace is licensed oracle material; drop needs impossibility reason ("implementation artifact" invalid) | PROT:59-62 | exhibited trace dropped without reason — OBSERVED pre-law: E4 (EV:69-75); law 6fbfcd9 | cs-nondet-fresh |
| 41 | Materialization never selects/adds/removes/ranks/rewrites/substitutes a case | PROT:65-66 | materialized set ≠ design's selected set | cs-stage-discipline |
| 42 | Builders' write scopes disjoint; component identities preserved | PROT:71-72 | two builders writing one path (near-miss: LA:57) | GAP G2 |
| 43 | Candidate/search contexts cannot read/choose/rewrite/retire/receive item feedback from protected evidence | PROT:72-73 | candidate shown protected seed or per-item verdicts (walls held EV:98-101 — but see D1, D4) | cs-antigoodhart-2 |
| 44 | Qualification checks failability/coverage/discrimination/reproducibility/redundancy/provenance/cost independently | PROT:82-83 | sealed package with an axis unchecked (OBSERVED pre-hardening: digest gap, LA:59) | cs-qualification-audit |
| 45 | Every oracle must be capable of failing | PROT:83-84 | oracle passing all seeds incl. inert variant | cs-qualification-audit; enforced per-case via mandatory inert seed in every successor spec (LB:118) |
| 46 | (restates #17) | PROT:84-86 | — | MERGED → #17 |
| 47 | Bad set includes one inert variant; bad variant counts only with proven behavior change; equivalents excluded not scored | PROT:86-88 | equivalence-unproven bad seed scored (clause <1 day old, 66f6846) | cs-qualification-audit (never exercised — also GAP G6) |
| 48 | Inert variant shown equivalent = finding: gap + discrimination UNVERIFIED for that behavior | PROT:88-90 | equivalent inert variant dropped, PASS retained | cs-qualification-audit |
| 49 | Nondeterministic outcome: declared trial count; good pass and bad fail on every trial | PROT:92-94 | flaky pass accepted best-of-n (clause new, 66f6846) | cs-nondet-fresh (pass^k with k in manifest; LB:37, LB:76-78) |
| 50 | Required deterministic failure blocks qualification; judged criteria anchored, secondary, non-compensating, rerun variance recorded before seal | PROT:94-96 | judged score offsetting required failure; seal without variance (clause new) | cs-judged-fresh (variance recording; LB:30, LB:79-82) |
| 51 | Byte digests verified before replay; qualification recomputes from bytes/captured outputs; self-declared evidence never qualifies | PROT:98-100 | verdict copied from builder self-run — OBSERVED class: B(0) digest defect (fixed, 0/30 recurrence) | cs-qualification-audit — MERGE: absorbs #54's digest-verify clause (MAN:20-23) |
| 52 | Protected evidence fixed by identity + visibility/release policy; optimization resistance without candidate-inaccessible check = UNVERIFIED; expected vs actual spend recorded | PROT:102-105 | resistance claimed with no inaccessible-check identity | cs-qualification-audit (resistance seed lives in cs-antigoodhart-2) |
| 53 | benchmark_identity = sha256 of canonical payload, transitively covering every referenced byte | MAN:5-6,27-31 | recomputation over shipped bytes ≠ sealed identity | cs-seal-integrity |
| 54 | (digest-verify restates #51; manifest-immutability restates #18; residue: candidate execution emits separate result identity) | MAN:20-23,34-35 | consumer uses component unverified | MERGED → #51 + #18; result-identity residue carried by cs-seal-integrity |
| 55 | Acquire cuts exactly two lanes (target intent, field) covering the charter headings; rest recorded as gaps | CHART:7-19 | synthesis with no lane structure or silent omission | cs-charter-compliance (never exercised before this run — GAP G6) |
| 56 | Terminal synthesis fixes seven artifacts at one identity; every claim maps to case spec or gap | CHART:22-38 | synthesis accepted with an unmapped claim | cs-charter-compliance |
| 57 | Exhibited material never becomes protected unchanged; protected seed = authored variant with named deviation | CHART:41-47 | public exhibit verbatim in protected seed set | cs-charter-compliance (violation precedent: D1's embedded constants, LB:159-167) |
| 58 | Mining stops at saturation; barring source policy narrows a lane and records the gap, never blocks | CHART:50-53 | run blocked by source policy; unbounded mining | cs-charter-compliance (saturation precedent: LA:173-179) |
| 59 | orch-verify decides required eligibility before orch-judge scores; Judge never re-executes/substitutes; required failure never ranks | DOCS:22-27 | score card on re-executed or substituted evidence | cs-ranking-fresh |
| 60 | Self-benchmarking manual, acyclic, between campaigns; successor qualified before a later campaign; never auto-activated | DOCS:32-37 | benchmaker↔evolve call either direction; successor auto-armed | GAP G4 (cross-campaign property; not observable inside one benchmark execution) |

### 2.1 Case specifications

19 specs. "adapt" follows §4 dispositions (re-seeded per §3 burn record); "new" has no
covering angle among the 13. Angle specs without a dedicated claim row above are
retained because they collectively instantiate claims 1/17/45 across target classes and
because no case is droppable under the angle-matrix bijection (LB:42-45).

| slug | angle served | adapt-or-new | licensed by |
|---|---|---|---|
| cs-cli-fresh | deterministic-cli | adapt (cli-dedupe) | LB:28; claims 1,17,45 |
| cs-ratelimit-fresh | time-semantics + invented-surface | adapt (lib-rate-limiter) | LB:29; claim 38; atlas B2 |
| cs-judged-fresh | judged-outcome + grader variance | adapt (skill-summarize; entire source set rebuilt) | LB:30; claim 50 |
| cs-sparse-fresh | sparse-evidence / no-invented-truth | adapt (sparse-evidence; new target so gap list regenerates) | LB:33; claims 3,38; atlas B1/B4 |
| cs-contradiction-fresh | contradiction | adapt (contradictory-evidence; new contested boundary + settlement) | LB:34; atlas FA6 |
| cs-multidomain-fresh | multi-domain | adapt (multi-domain) | LB:35; claims 1,17,45 |
| cs-stateful-fresh | stateful | adapt (stateful-plugin) | LB:36; atlas B4 kin |
| cs-nondet-fresh | nondeterminism + exhibited-anchor + pass^k | adapt (nondeterministic-target; new off-repo seeds/streams) | LB:37; claims 40,49 |
| cs-cost-fresh | cost-pressure | adapt (cost-explosion; fresh density-proved loci) | LB:38; claims 1,17,45 |
| cs-workflow-fresh | workflow-target + HAZOP late/reverse | adapt (composition-target; guideword seeds finally used) | LB:39; LB:123-124 uncovered entries |
| cs-ranking-fresh | ranking | adapt (candidate-ranking) | LB:40; claims 21,59 |
| cs-antigoodhart-2 | anti-goodhart / protected evidence | differentiate (overfit-trap: new scenario, off-repo held-back inputs) | LB:31; claims 43,52-seed |
| cs-refusal-2 | lawful refusal on unobservable outcome | differentiate (unobservable-outcome: new scenario, new barred channels) | LB:32; claims 1,31 |
| cs-unsolvable-as-written | measurable outcome, unpassable task; grade refusal-with-proof | new (proposal's named candidate 13th angle; distinct from refusal) | LB:127 |
| cs-intake-refusal | packet/intake/return discipline (blocked returns, no invented outcome, deficient-synthesis reuse refusal) | new (process-shaped, like refusal angle) | claims 2,3,7,28,30,33,37 |
| cs-stage-discipline | run-record audit: stage exhaustiveness, frozen joins, never-clauses, gap carry-forward | new | claims 8,10-14,19,20,22,24,29,34,35,39,41 |
| cs-qualification-audit | qualify-the-qualifier: axis coverage, independence, digest recomputation, inert/equivalence law | new (no angle grades a qualification record) | claims 4,15,16,17,27,44,45,47,48,51,52 |
| cs-seal-integrity | identity recomputation, seal-drift detection, successor minting | new (seal drift was live PR#24→e66f3b6, LA:136-139) | claims 1,18,23,53,54-residue |
| cs-charter-compliance | acquire-charter conformance: lane cut, seven artifacts, exhibited/protected law, saturation | new (charter <1 day old, never exercised) | claims 55-58 |

### 2.2 Coverage arithmetic

- claims total: **60**
- merged into a surviving claim (mapped via survivor): **4** (#25→16, #36→16, #46→17, #54→51+18)
- mapped to case specifications: **49**
- mapped to gaps: **7** (#5→G2, #6→G3, #9→G3, #26→G3, #32→G3, #42→G2, #60→G4)
- unmapped: **0**. Check: 49 + 7 + 4 = 60.

## 3. Failure atlas

Merged observed (lane A) + taxonomy-derived (lane B). "Burned" = the deviation is
exhibited in the sealed public set (LB:13-18 exhibition law; LB:98-106 census):
successor seeds must use a fresh deviation or the same class at an unpublished locus.

### 3.1 Observed modes (target)

| id | mode | deviation producing it | status | burn note | cite |
|---|---|---|---|---|---|
| B1 | under-generation within license | universally quantified evidence not carried to witnesses across the range | OPEN (remedy text failed: E1+E6) | quantifier-narrowing burned x3 | LA:85-90 |
| B2 | invented interface surface | no-invented-truth applied to semantics but not interface surface | OPEN; convergent attractor (2/6 evolve builds) | reference-fabrication burned | LA:91-94 |
| B3 | parser brittleness on valid unexhibited variants | parse tolerances enumerated over reference spellings, not the licensed space | OPEN BY DESIGN (benchmark constant, invariant across 7 builds) | boundary-shift family burned x4 | LA:95-100 |
| B4 | transcript under-generation | licensed witness never bought because absent from exhibited transcript (B1 axis) | OPEN | state-masking burned | LA:101-104 |
| E4c | exhibited-anchor drop | exhibited trace judged "implementation artifact", anchoring oracle dropped | CLOSED (law 6fbfcd9; 3/3 recovery) | restream locus burned (LB:37) | LA:105-109 |
| FA6 | contradiction lawful zero | (not a failure) side-picking outscores lawful registration unless scoring reads the disagreement register | scoring-law constraint | settled side exhibited (LB:34) | LA:110-115 |

### 3.2 Observed modes (surrounding law/harness constraining the target)

| id | mode | deviation | status | cite |
|---|---|---|---|---|
| E1 | gap declaration is a lawful exit from exhaustion | coverage law satisfied by declaring gaps instead of building cases | OPEN | LA:121-123 |
| E2 | laws crowd | cheap checklist law displaces expensive open-ended one | OPEN (remedies must compose into one obligation) | LA:124-127 |
| E5 | single-run kill-margin noise ±1-2 seeds | one build per cell conflates protocol quality with luck | OPEN (median-of-n unbuilt) | LA:128-129 |
| E6 | exhaustion generativeness tracks builder model | capability attributed to protocol text | DECLARED CONFOUND | LA:130-131, 223-228 |
| DG | component digests accepted over different bytes | qualification skipped component-digest verification | CLOSED (digest-last rule; 0/30 recurrence) | LA:132-135 |
| SD | seal drift: recorded digest silently stops describing the tree | no mechanism re-verifying seal against tree | CLOSED at e66f3b6 (benchmark.lock + seal_set.py) | LA:136-139 |
| IL | interface-layout underspecification | interface field defined by reference to evidence that defines no layout | OPEN (≥6 friction entries) | LA:143-147 |
| MQ | manifest qualification chicken-and-egg | schema demands qualification component before qualification exists; no "construction complete, qualification pending" verdict value | OPEN CONTRACT GAP (→ G5) | LA:148-151 |
| PF | platform-form oracle brittleness | byte-exact `\n`/encoding tolerances narrower than the license, at host layer (B3 family) | OPEN (≥6 entries) | LA:152-155 |
| PC | protected-seed contamination by execution | scoring/probing mutates what must stay byte-fixed (__pycache__, shadow state) | OPEN | LA:156-159 |
| SC | scorer defects, no fixture | relative-cwd inversion caught by implausibility only | OPEN | LA:160-162 |
| SS | shared-scratchpad collisions | parallel builders share one scratchpad | OPEN (≥5 entries) | LA:163 |
| RT | unaddressable reply_to | literal return address rejected by host tool | OPEN (1 entry) | LA:164-165 |

### 3.3 Taxonomy-derived deviation census — ALL BURNED (LB:98-106)

boundary-shift x4; contract-substitution x3; guard-deletion x3; quantifier-narrowing x3;
value-substitution x2; input-class-drop x2; artifact-desync x2; input-ignored x2; one
each: ordering-absent, candidate-derived-reweighting, self-reported-score-trusted,
arrival-order-tie-break, default-substitution, dangling-reference, oracle-vacuity,
binding-omission, value-truncation, state-omission, early-exit, rule-substitution,
memorization, reference-fabrication, constraint-relaxation, guard-insertion,
state-masking, side-channel-state. (39 bad seeds, 26 deviation names.)

### 3.4 Taxonomy entries with NO current seed — fresh for the successor

| entry | disposition here | cite |
|---|---|---|
| HAZOP "late" | seed in cs-workflow-fresh | LB:123 |
| HAZOP "reverse" | seed in cs-workflow-fresh (guideword menu unused at seal) | LB:124 |
| unsolvable-as-written | cs-unsolvable-as-written | LB:127 |
| per-case extreme-mutation (12/13 missing) | cross-cutting: one inert seed in EVERY successor spec; enforcement audited by cs-qualification-audit | LB:118, LB:70-73 |
| MAST 14 agent modes | GAP G8 — deferred until an agent-class target enters the matrix | LB:128 |

Fresh-locus menus per angle (N-1 shift, CRLF, commit-on-construct-only, off-by-one
stream offset, margin off-by-one, env-var leak, etc.) are recorded per row at
LB:28-40 seed-space notes and are adopted as the seed-sourcing menu for §2.1's adapt specs.

## 4. Prior-art register

Lane B's 13 dispositions (LB:26-45): **11 adapt, 2 differentiate, 0 ignore.** No case
droppable — each owns a distinct angle-matrix row and no two rows' laws are
substitutable (LB:42-45). Reasons compressed; full wording at cited LB line is part of
the fixed input identity of this synthesis.

| case | disposition | reason (compressed) | burned deviations | cite |
|---|---|---|---|---|
| cli-dedupe | adapt | clean template: byte-exact oracle, boundary near-miss as discrimination floor; re-seed loci | input-class-drop, default-substitution, value-substitution, boundary-shift | LB:28 |
| lib-rate-limiter | adapt | constitutional angle law (real-clock benchmark cannot fail bad-wall-clock in principle); carry clock-injection demand verbatim | contract-substitution, value-truncation, state-omission, guard-deletion | LB:29 |
| skill-summarize | adapt | deterministic/judged split with anchors kept; successor must record judge rerun variance AND rebuild entire source set (anchors quote seed outputs byte-for-byte — both burned) | reference-fabrication, constraint-relaxation, quantifier-narrowing | LB:30 |
| overfit-trap | differentiate | unrecoverable as-is: held-back probe orders printed in case.toml probe string — hidden inputs are public; fresh scenario + off-repo held-back split required | memorization, rule-substitution, boundary-shift | LB:31 |
| unobservable-outcome | differentiate | exhibited expected.md is a literal answer key (gaps, failure modes, unblock menu transcribable); carry rubric STRUCTURE, replace scenario | none (no seeds by design) | LB:32 |
| sparse-evidence | adapt | mechanism sound and cheap; enumerated gap list is an exhibited answer key → new target so gaps regenerate | quantifier-narrowing x2, input-class-drop | LB:33 |
| contradictory-evidence | adapt | no-tiebreak design carries; settled side itself exhibited → new contested boundary + new settlement | contract-substitution, boundary-shift, value-substitution | LB:34 |
| multi-domain | adapt | provable single-domain-blindness table and chained single-pack law carry directly | early-exit, artifact-desync x2 | LB:35 |
| stateful-plugin | adapt | two-run-transcript law is the keeper (only check reaching escaped state) | side-channel-state, state-masking, guard-insertion | LB:36 |
| nondeterministic-target | adapt | 3x3 strategy-vs-seed kill table carries; add pass^k; held-back seeds AND exact stream/band printed in probe → held-back property VOID at this seal; new off-repo seeds+streams | contract-substitution, input-ignored x2 | LB:37 |
| cost-explosion | adapt | only case where discrimination is provably input-selection; exhibited density arithmetic names the witness classes → new low-density loci, density analysis redone (high cost) | guard-deletion x2, boundary-shift | LB:38 |
| composition-target | adapt | recursion dry run, highest-value carry; HAZOP guideword seed generator pre-menued and entirely unused | dangling-reference, oracle-vacuity, binding-omission | LB:39 |
| candidate-ranking | adapt | newest case; set's only inert seed and only Goodhart-on-aggregation seed; shape evolve/panel consume | ordering-absent, candidate-derived-reweighting, self-reported-score-trusted, arrival-order-tie-break | LB:40 |

Empty lanes (findings with proof, per charter "an empty answer is a finding"):

- **Comparables (sibling benchmark-builders + failure histories): EMPTY.** Proof: full
  read of `.orch/proposals/benchmaker-research.md` — AutoBencher/BetterBench/ABC appear
  only as external rubrics; no documented failure history of any sibling builder; the
  comparables worked-examples concern targets, not builders. No network this lane. LB:185-194.
- **Prior suites for this class: EMPTY.** Terminal-bench registry cited as method only;
  no existing suite benchmarks a benchmark-builder. The local 13-case set is, on the
  licensed evidence, the only prior suite for the class. LB:195-198.

Oracle-precedent menu adopted for the successor's qualification design (12 checks:
task/outcome-validity split + null-candidate, external rubric scoring, survey-before-
author + per-test "tests" key, size tiers with enforced timeouts + exit-code-zero law,
seed equivalence proof, extreme-mutation inert seed, null-candidate, pass^k, grader
variance before seal, contamination canary GUID, claim-traced provenance coverage,
harness pinning): LB:47-94, each with its licensed source.

## 5. Disagreement register

Contradictions between or within the lanes. Per the research pack's oracle policy each
is registered verbatim-by-citation, unresolved unless a resolution event is cited.

| id | disagreement | side A | side B | status |
|---|---|---|---|---|
| D1 | Protected-constant leaks: cases' protection claims vs the public checkout | expected.md claims "held back" / "appear nowhere in evidence/" for overfit-trap's four probe orders and nondeterministic-target's seeds 7,11 + exact stream + band (LA claim 17/43 lineage treats protected-seed discipline as operative) | LB:159-167: all these constants sit inside exhibited case.toml probe strings — the procedural barrier is the only barrier; held-back property VOID at seal ff7d9aad | OPEN — drives both differentiate dispositions and the off-repo constant rule for cs-nondet-fresh / cs-antigoodhart-2 |
| D2 | Provenance: intake law vs shipped keys | LA claims 4/33: evidence identities fixed at intake; provenance a checked qualification axis (claim 44) | LB:86-90: `provenance` key present in all 13 cases but every one points at its own expected.md — self-referential, not claim-traced; the axis passes vacuously | OPEN — cs-qualification-audit must require claim-register-traced provenance |
| D3 | Evidentiary value of process-case PASSes | LA cites unobservable-outcome PASS as counter-evidence of health (claim 31, B0:21) and lawful-zero contradiction handling as correct (LA:110-115) | LB:168-172: for process-shaped cases the exhibited expected.md hands the candidate the graded return itself — a repo-read candidate passes by transcription; re-seeding cannot fix it | OPEN — those PASSes are unreliable as capability evidence at this seal; only new scenarios restore them |
| D4 | Wall integrity | LA claim 43 counter-evidence: all walls held across 36 executions (EV:98-101) | LA's own boundaries + friction: walls are packet-wording constructs, not host-attested; one write-scope breach observed (LA:206-208, claim 5) — and LB hole 1: anything with checkout access reads the seeds today (LB:150-158) | OPEN — "held" means "no lawful context chose to look", not "could not look"; maps to G2 |
| D5 | Seal immutability INV vs history | LA claim 18: any change mints a successor identity | LA:136-139: the twelve-case seal silently stopped describing the tree after PR #24 with no mechanism noticing | RESOLVED at e66f3b6 (durable seal: benchmark.lock, seal_set.py, SEALS.md) — retained because the fix is <1 day old and unexercised (G6) |

Also checked, judged not disagreements: builder-model confound vs discrimination
figures (LA declares it itself, LA:223-228 — a confound, not a contradiction);
FINDINGS-*.md excluded from seal scope vs exhibition law (LB:177-181 — consistent with
the law, flagged as coaching-material risk in G7); lane B's proposal-draft caveat vs
merged charter (LB:213-215 — supersession acknowledged by lane B itself; this synthesis
uses the merged CHART text via lane A claims 55-58).

**Open: 4 (D1-D4). Resolved-and-retained: 1 (D5).**

## 6. Gaps

Union of both lanes' gaps plus join-created. Explicit; none omitted.

- **G1 — no external demand record.** Zero runs against any target outside benchmaker's
  own case-set family; 91%/net-27 figures unmeasured for arbitrary targets. LA:286-288.
- **G2 — wall enforcement is textual.** Protected-read boundary and builder write-scope
  disjointness are packet-wording constructs, not host-attested; one breach observed,
  corrected by wording only. Claims 5, 42 map here. LA:298-301; LB:150-158.
- **G3 — bound obedience unobserved.** No findings evidence records per-stage
  allocations or spends; claims 6, 9, 26, 32 have never been checked in either
  direction. LA:296-297.
- **G4 — cross-campaign acyclicity not case-able.** Claim 60 (manual, acyclic,
  between-campaigns) spans workflows; no single benchmark execution can observe it.
  Owner: campaign law, not the case set. LA:75.
- **G5 — manifest qualification chicken-and-egg.** No "construction complete,
  qualification pending" verdict value in MAN; ≥3 friction entries; requires a MAN
  supersession before cs-qualification-audit can demand the missing value. LA:148-151, 305-307.
- **G6 — day-old laws never exercised.** Claims 47, 49, 50 (inert/equivalence, trial
  count, rerun variance), the whole charter (55-58), and the durable seal all landed
  ≤1 day before e66f3b6; no campaign has run at this revision; their defeaters are
  untested in both directions. LA:277-280, 292-295.
- **G7 — campaign record is coaching material.** FINDINGS-*.md are outside the seal
  scope yet document past candidates' failure shapes; contamination is assumed, never
  detected — no canary GUID anywhere in the sealed set. LB:173-181.
- **G8 — MAST agent modes deferred.** Load-bearing the moment an agent-class target
  enters the matrix; no spec here covers them. LB:128.
- **G9 — probe liveness not re-proved.** Lane B dispositions rely on defect.md claims
  and validator discipline; the 13 probes were not executed against the 39 seeds this
  run; every re-seed requires fresh liveness + equivalence proof. LB:201-207.
- **G10 — scorer and measurement infrastructure absent.** Settlement round (full
  contradiction discrimination), median-of-n scoring, scorer fixture, and bench-stack
  port are named next steps that do not exist; every cited figure came from the unfixed
  single-run scorer. LA:301-304; LB:157-158.
- **G11 — builder-model sensitivity uncharacterized.** Declared confound (E6) with no
  per-model capability matrix; every capability number is (protocol × model × luck ×
  host)-conditioned. LA:308-309, 223-237.
- **G12 — evidence-collection blind spots.** Friction mining was keyword-filtered
  (entries without the tokens missed); c1's admitted-unadopted candidate text unread
  (pending owner decision); lane B's proposal citations frozen, not re-verified;
  deviation-space wide/moderate/narrow judgments are authored assessments except
  cost-explosion's. LA:310-314; LB:213-219.
- **G13 — join-created: deterministic-angle specs carry no dedicated claim rows.**
  cs-cli-fresh, cs-multidomain-fresh, cs-stateful-fresh, cs-cost-fresh,
  cs-contradiction-fresh are licensed by construct-level claims (1, 17, 45) and the
  bijection law only; the evaluation design must not read them as tracing to distinct
  target-text claims. (This section, §2.1.)

## 7. Sourcing mode

Chosen per case-spec family, per the charter's three admissible modes.

- **All adapt specs (11): authored.** The tiering law is categorical — protected seeds
  are always authored variants carrying a named deviation applied to exhibited material,
  never public material promoted (CHART:41-47; LB:145-148); the burn record (§3.3)
  forces fresh authored loci.
- **Differentiate + new-scenario specs (cs-antigoodhart-2, cs-refusal-2,
  cs-unsolvable-as-written): authored.** Mining is inadmissible for the class — both
  field lanes are proven empty (LB:185-198), so there is nothing to mine from.
- **Process/audit specs (cs-intake-refusal, cs-stage-discipline,
  cs-qualification-audit, cs-seal-integrity, cs-charter-compliance): mined-then-authored.**
  Deviation selection is mined from the 372-entry friction record and FINDINGS histories
  (LA:141-179) — real observed deviations, already saturated — then seeds are authored
  variants at unpublished loci.
- **Generated-then-filtered: rejected for every family.** No trustworthy filter exists:
  the single-run scorer has a caught inversion bug and no fixture (G10), and kill-margin
  noise is ±1-2 seeds (E5) — a generator's output cannot be filtered to qualification
  grade with current instruments.
