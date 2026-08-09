# BenchMaker redesign — specification

What BenchMaker becomes, and what it costs. Reasoning and refusals
live in [the handoff](handoff-benchmaker-redesign.md) (P1–P10, its
traps, its arbitration order); field evidence lives in
[FINDINGS-FIELD.md](../benchmarks/benchmaker/FINDINGS-FIELD.md)
(2026-08-08; 110 benchmarks, 16 domains, 199 sources) and
[benchmark-design.md](benchmark-design.md). This file owns the
*shape*: which surface each new figure lands on, in what order the
stages run, and what a stage does when it fails. Cite the evidence
files as evidence; cite this one as design.

Sources retrieved for this spec and not present in the register are
marked **[new]** and carry their identifier inline. They are three
2026 papers on the exact problem BenchMaker has — how do you evaluate
a thing that produces evaluations — and one older meta-benchmark.
They corroborate the register in several places and extend it in
four.

## 0. Revision — 2026-08-08, after the first measurement pass

Two things happened after this spec was written: the owner struck
immutability, and §10 step 1 ran. Both invalidate parts of what follows.
This section is normative over any section it contradicts.

**Immutability is no longer a goal.** BenchMaker may edit the benchmarks
it makes. Everything below whose only argument is successor-minting
therefore loses its ground:

| section | status |
| --- | --- |
| §3, the three surfaces | **withdrawn as a structural argument.** Its case is that post-seal figures mint successors. Splitting the surfaces may still be good hygiene; it is no longer forced, and it may not be argued from immutability |
| §3.2, "outside the package, not merely outside the digest" | **withdrawn.** Pure seal reasoning. The record still lives at `benchmarks/measures/` because a consumer-side record outside the package it describes is right on its own terms — the spec's own second reason, which survives |
| §10 step 3, "re-seal exactly once" | **withdrawn.** There is no supersession to economize |
| P1's rationale | **narrowed.** "A gate that fails after qualification mints a successor per failed attempt" no longer holds. P1's *conclusion* stands on its corollary alone: a high score means the set is too easy **or** the oracle is too lenient, and a gate collapses two readings needing opposite repairs into one verdict. Owner reaffirmed: difficulty stays a recording |
| §7's supersession pricing | **narrowed.** Cross-identity incomparability survives and is now measured; "re-run every retained candidate to span a supersession" was seal bookkeeping |
| P9 row 1, immutable identity | **withdrawn** as library law |

What survives untouched, because it rests on label noise and measurement
validity rather than on sealing: P2 anchors, P3 the reference audit and
the ban on selecting by target failure, P4 oracle certification, P5 the
attack pass, P6 distributions, §5's instrument and its readings table.

**§7 is no longer the spec's most abstract claim; it is its most
demonstrated one.** The measurement pass confounded itself. Every
candidate was dispatched "do not spawn subagents" while the protocol
requires a qualification context disjoint from the builder, so a
required criterion was made unreachable by the harness. Four of six
rung-level FAILs are qualification-shaped in consequence, and one strong
rung failed *for refusing* to author a self-qualified PASS. §4.3
specifies rungs and scope and says nothing about candidate dispatch;
that omission is what let it happen.

**§4.3 gains a required declaration.** A measurement pass declares,
before it runs, the authority each candidate receives — delegation,
tooling, network, and evidence — and any protocol-required criterion
that authority makes unreachable. A criterion the dispatch has made
unreachable is an intake gap recorded before scoring, never a candidate
FAIL. The law half of this landed in `benchmaker-protocol.md`
§Qualification on 2026-08-08.

**§5 gains a distinction the pass needed and did not have.** Separation
produced by one repeated candidate behaviour is not angle-level
discrimination. Three cases produced one `split` and two `both-fail`,
and the weak rung shipped a byte-identical qualification stub in all
three — so a large discriminating set can evidence a single systematic
habit counted N times. Report, beside the discriminating set, how many
distinct failure signatures produced it.

**Three defects the pass found in the library, all recorded before any
repair.** Two are fixed: the manifest licensed a pending qualification
marker the case probes reject (now schema-legal, never task-complete),
and `cs-antigoodhart-2` enforced a runner invocation no candidate-visible
evidence declared (now declared). One is open and belongs to a case-schema
change, not a patch: `case.toml`'s `bound` conflates the construction
allocation with the candidate execution bound. `BC1`–`BC6` are the six
*builder contexts* of the construction run's capacity plan
(`evaluation-design.md` §8), so "one BC1 share" tells a candidate how the
case was authored. Only the probe tier half is candidate-facing, and only
it was measurable.

**A fourth defect, structural, found while re-sealing.** The package's
integrity chain has a hole. `benchmark_identity` recomputes from the
canonical manifest payload, which proves the manifest is internally
consistent; `benchmark.lock` proves the tree matches its own recipe;
**nothing binds the two.** The manifest's directory-component identities
are reproducible by no tool in the package, so a `cases/` change does not
move `benchmark_identity` and nothing detects the divergence. Any surface
this spec adds to the manifest inherits that hole until a component
recompute tool exists.

**Unmeasured, and not to be cited as measured.** Thirteen of sixteen
cases were never dispatched. Rerun spread is unmeasured — neither
three-trial case ran. The judged oracle class, the suite's weakest, is
entirely unexercised. Cost ran ≈1.5x the estimate below: 211,834 tokens
for one case at two rungs, against §4.3's projection.

## 0b. Revision — 2026-08-09, the law landing

**A new owner requirement, and it is not derivable from anything above.**
Speed is now a stated goal, scoped by target class: for a target whose
execution is cheap, BenchMaker builds cases that are fast *and*
comprehensive *and* hard; for a target whose execution is expensive —
BenchMaker building benchmarks for itself is the type case — it stays
comprehensive and may not be fast. This is an owner decision, not a
field finding; no retrieved source states it.

It slots into the arbitration order without disturbing it, because it is
a cost constraint and the order already ranks cost below validity and
coverage. Written as law in `PROT` §Execution tier and difficulty, it
resolves to three rules:

- The declared coverage floor never moves with the target's execution
  cost. A cheap target's suite ceiling is tight and every case sits in
  the smallest tier its angle can be observed in; an expensive target's
  ceiling rises and the cost is declared rather than hidden.
- **Speed is bought from the probe, never from the coverage floor, the
  oracle, or the horizon the outcome needs.** A case made fast by
  loosening its oracle buys a `both-pass` reading, and §5's table says
  no measurement can tell that from a lenient oracle. Where an angle is
  unobservable within its tier, the tier rises and the reason is
  recorded; the angle is never dropped.
- **Difficulty is built, never filtered.** Horizon length, outcome
  specificity, and a stricter oracle that stays correct are the licensed
  levers. P3's ban on selecting by target failure, §9's ban on culling
  low-discrimination cases, and the ban on revising the design from
  scores are the same rule from three directions, and this makes them
  one clause.

The cheap-target half also pays for itself: §4's two measurement passes
run the whole set at two rungs twice, so a slow suite is a measurement
pass that does not get run. Speed is not economy here; it is what makes
the instrument affordable enough to exist.

**Two defects from §0 are closed and one is downgraded.** The
manifest-to-tree hole is closed by `component_identity.py` (§10 step 2).
The `bound` conflation is closed: `case.toml` carries `exec_bound`, the
candidate-facing execution bound alone, and the construction allocation
stays in `evaluation-design.md` §8 where it already lived; the validator
refuses a `BC<n>` token in a candidate-facing key. Both were repaired
for named correctness defects and neither for a score; §4.1's reference
audit should confirm the repairs rather than trust them, which is now
recorded in the manifest's `reference_audit.awaiting_confirmation`.

## 0c. Revision — 2026-08-09, the seal removal

Sealing is withdrawn. A benchmark is an ordinary editable artifact whose
version is the git revision it sits at: no content-hash seal, no
benchmark or component digest, no prohibition on editing a benchmark or
its manifest in place. Run `20260809T021408Z-benchmaker-unseal`. This
section is normative over any section it contradicts, §0 and §0b
included.

**The mechanism goes with the prohibition, and that supersedes §0.** §0
struck immutability as a *goal* and left successor-on-change standing as
machinery; §0b then recorded `component_identity.py` as closing the
manifest-to-tree hole, which only a live identity can have. Both
readings are withdrawn. Nothing mints a successor identity, because
there is no identity to mint, and a later benchmark is a later revision.
The reason, named once: retained machinery drifts back into being
treated as law — this tree is the demonstration, since the 2026-08-09
pass edited in place a package whose text still forbade it.

| section | status |
| --- | --- |
| §1 | **withdrawn as an argument.** Its rearrangement — every forcing check before the seal, every later figure outside it — has no seal to arrange around. The stage order survives on its own ground: a check that can force a repair runs before the result is recorded |
| §3.1, "fixed at seal" | **restated.** The manifest is recorded, not fixed; [the manifest owner](../compositions/references/benchmaker-manifest.md) holds the surviving field set |
| §3.2, "outside the sealed root" | **withdrawn**, the argument by §0 and now the seal it named. The record stays at `benchmarks/measures/` on §0's surviving second reason |
| §4, "Pre-seal stage order" | **renamed, same order.** The stages are [the protocol](../compositions/references/benchmaker-protocol.md) §Audit and measurement |
| §7 | **survives.** Its four candidate axes stand; the manifest field carrying them is restated below |
| §10 steps 1–4 | **the seal bookkeeping falls**: re-sealing, `SEALS.md`, the predecessor digest, and step 2's `component_identity.py`, which is deleted along with the hole it closed. The measurement, the law landing, the remaining stages and the anchors stand |
| §11's standing gaps | unchanged |

**What the deleted tests were proving.** `tests/test_component_identity.py`
went with the tool, 22 tests, plus one in `tests/test_benchmaker.py`:
they proved every manifest component identity recomputes from the tree
bytes and that a forged or stale digest is detected. No digest is
recorded now, so the property has no subject. Five more properties were
dropped from inside tests that survive, each for the same reason and
each with the half that survives named:

| dropped | it proved | what stands in its place |
| --- | --- | --- |
| the fixture runner's component-mutation refusal | appending one byte to `cases.json` is caught by the recorded digest | a component reference that does not resolve is refused |
| `_reference()`'s digest equality | each component's recorded digest matched its bytes | the same |
| the manifest's `benchmark_identity` recomputation | the package digest was non-self-referential and recomputable from the canonical payload | nothing; the field is gone |
| two candidate runs' equal benchmark, design and runner identities | both candidates were scored against the same benchmark bytes | candidate identity differs between candidates, and the evidence identity recomputes over its payload |
| every `covers` entry starting `sha256:` | every cover was a content digest | every cover resolves to a file in the package |

QC-3, "seal reproducibility", is withdrawn with its oracle rather than
reworded; nine required qualification criteria remain, all PASS. The
fall sits inside a rise, so read it as two numbers and not one: 23 tests
deleted, and the suite 532 before the run against 568 after.

**What replaced the seal, and the one place it is weaker.** The git
revision, plus the durability rule
[the protocol](../compositions/references/benchmaker-protocol.md)
§Audit and measurement now states. The seal did not have this failure
mode: this repository squash-merges, so a branch commit is no ancestor
of the default branch and its sha dangles once the branch is collected,
while a content digest resolved from the bytes alone. The rule is what
closes it — name a default-branch-reachable revision, or the reachable
ancestor carrying identical measured bytes and the relation between
them. No check enforces it: CI's shallow checkout cannot resolve a
revision, so a checker would refuse clean records.

**What is not weaker.** The qualification discipline is untouched, at
[the protocol](../compositions/references/benchmaker-protocol.md).
Freezing a benchmark for one campaign's duration is untouched, at
[evolve](../compositions/evolve.md) and
[skill-tournament](../compositions/skill-tournament.md): sealing forbade
*anyone* editing the benchmark *forever* on pain of a new identity,
while freezing binds *one campaign* to *one version* so its candidates
are comparable. Only the first was withdrawn — a campaign comparing
candidates across a moving benchmark measures nothing.

**Off-tree protected evidence is no longer pinned by any digest.** The
manifest named its five held-back files by digest; the digests went with
every other `sha256:`, and those files sit outside the tree the revision
covers. `tools/validate_measures.py` refuses a measurement record that
does not name each protected path, so the scope is guarded — but nothing
checks their bytes, and no rule now claims to. A byte pin, if one is
wanted, belongs in the store's own policy rather than in the manifest.

**`incomparability` survives, and the removal's own delivery spec was
wrong about why.** That spec kept the field on the ground that its
boundary "is candidate identity … never benchmark identity". The field's
text bounds both, and its first clause named the retired mechanism. The
substance is right — a score genuinely does not cross a benchmark
version — so the noun is restated, `identity` → `revision`, and the four
candidate axes of §7 stand. Deleting the clause would have silently
licensed comparing scores across benchmark versions, which is the one
thing the field exists to forbid. Recorded here because that spec is
frozen and was not edited.

## 1. The change, in one paragraph

BenchMaker seals a benchmark whose difficulty is unmeasured and whose
cases are anchored to nothing outside their own package. The repair is
not a new gate. It is a rearrangement: **every check that can force a
repair moves before the seal, where repair is free because no identity
exists yet; every figure that changes after the seal moves outside it,
where recording it does not mint a successor; and the manifest becomes
the fixed middle that carries only what is true at seal time.** The
three pre-seal stages (reference audit, attack pass, measurement) are
new; the immutability law they serve is not.

## 2. What survives contact

These hold, and four of them gained an independent witness while this
spec was written. Do not reopen them.

| law | new corroboration |
| --- | --- |
| immutable identity, successor-on-change | unchanged — the field is still retrofitting it |
| qualification disjoint from every builder | BenchBench **[new]** separates designer models from answerer panels and adds a human audit on top; the same structure, arrived at independently |
| blocked return, UNVERIFIED-on-crash | BenchBench's `skip_core` label for unverifiable or ill-posed items is the same construct under another name **[new]** |
| deterministic oracles required, judged secondary and non-compensating | BenchBench scores in the order exact-match → numeric/symbolic → rubric-judge → `skip_core`; BenchMaker's rule is the stronger form of that ordering **[new]** |
| the equivalence bridge | trace-oracle work keeps publishing the correct-but-different failure the bridge excludes |
| the inert-variant mandate | unchanged |
| protected evidence off-tree | unchanged |
| cost declared and bounded | unchanged |

One cheap addition falls straight out of the fourth row: **scoring
must report the fraction of criteria decided by deterministic oracle
versus judged oracle.** BenchBench's phrasing is "make the instrument
visible" **[new]**. BenchMaker already records `oracle_class` per
criterion and never sums the fraction.

## 3. Three surfaces

The single structural decision in this spec. Today one artifact — the
sealed package — carries figures with three different lifetimes, which
is why RF-10's retirement trigger could be declared but never fired:
recording that it fired changes a covered byte and mints a successor,
so a benchmark could never be marked retired without ceasing to be
that benchmark. That is not a property of retirement. It is a property
of every figure produced by contact with a candidate, and all of them
need the same home.

### 3.1 The manifest — fixed at seal

New fields, all of them true-at-seal and none of them re-derivable
later:

| field | content | source row |
| --- | --- | --- |
| `anchors` | per case: the reference the expected outcome is bound to, or `none` with a reason | RF-18 / P2 |
| `builders` | per case: the builder context's model id, effort, and host binding | **[new]**, §8 |
| `reference_audit` | defect **count**, taxonomy class per defect, auditor context identity, method per case (solve-from-prompt or re-read) | RF-05 / P3 |
| `attack_audit` | dated checklist identity, per-class outcome, and every hole left unrepaired at seal | RF-04 / P5 |
| `seal_measurement` | the recorded measurement pass: candidate identities, per-case status, margin, scope | RF-01, RF-03 / P1 |
| `resolution` | the smallest reportable difference: `max(measured rerun spread, one case)` | RF-06, RF-07 |
| `retirement_trigger` | the declaration only — never the firing | RF-10 |
| `incomparability` | that scores do not cross this identity boundary without re-running every retained candidate | RF-16 / P7 |

### 3.2 The measurement record — append-only, outside the sealed root

`benchmarks/measures/<benchmark>.md`. One entry per measurement event,
newest first, in the idiom `SEALS.md` already uses for the same reason
(avoiding digest self-reference). Each entry names the benchmark
identity it covers, the full candidate identity per §7, the date, the
measured scope, and the figures of §5. The retirement trigger fires
here. Re-measurement of an existing seal lands here and costs no
successor.

**Outside the package directory, not merely outside the digest.**
`seal_set.py` seals every file under `benchmarks/<name>/` except three
named top-level exceptions, and reports an unlisted file as untracked —
so a measurement record placed *inside* the package would fail
`--verify` on creation and would need an exclusion-list amendment to a
file that is itself sealed, minting a successor to record a
measurement. Placing it in a sibling directory needs no amendment, no
law change, and no successor: `--verify` stays green at the existing
digest and proves it. A consumer-side record living outside the
package it describes is also the correct shape on its own terms — the
manifest is package-owned and fixed; this is neither.

### 3.3 Scoring — the vector is the artifact

`scoring.md` gains:

- **The per-angle vector is primary and any scalar is derived.** Not a
  preference. The multi-task benchmark literature **[new]** measures a
  direct trade-off between a benchmark's task diversity and its
  ranking's sensitivity to irrelevant changes, across 7 cardinal and 11
  ordinal benchmarks: the more diverse the suite, the less stable the
  ranking. BenchMaker's set is one case per angle with an enforced
  bijection — maximum diversity, zero within-angle redundancy, and
  therefore the configuration that trade-off predicts is *least*
  ranking-stable. RF-20's own recorded weakness (at n=1 per angle a
  geometric or harmonic mean is dominated by one case) is that finding
  seen from inside. The resolution is not a better mean. It is to stop
  headlining a scalar.
- **`(score, cost)` pairs**, carrying host, price list, and date, with
  the cost axis bound by `incomparability` (RF-08, RF-16).
- **`pass^k` beside `pass@1`** for nondeterministic cases, at the
  declared k, defined in words — G4 records that no primary
  formalization was retrieved and none is cited here.
- **The deterministic/judged fraction** per §2.

## 4. Pre-seal stage order

    triage measurement → reference audit → repair
      → attack pass → repair-or-declare
      → recorded measurement → seal

Two measurement passes, not one. Probe execution is cheap — the
current suite sweep is 171 s — and the audit's solve-from-prompt lane
is the most expensive thing in the redesign, so the cheap pass runs
first to *target* the expensive one, and again at the end to produce
the figure that seals. The difference between the two passes is itself
informative: repairs that move the figures found something real.

P8 requires every new required stage to carry a priced bound and a
failure path. Each stage below states both, and none of them can fail
in a way that mints a successor, because all of them run before an
identity exists.

### 4.1 Reference-correctness audit

**Objective.** Prove the expectation right, which QC-2 (the probe *can*
fail) and QC-4 (where the expectation came from) do not. The field's
prior for hand-authored expert items is 10–46% defective. The good end
of that range is now measurable: BenchBench's two-rater human audit
over ~150 stratified items found a union fatal-flaw rate of 3.4%
**[new]**.

**Context.** A third context, disjoint from every builder *and* from
the first qualifier.

**Method.** Binary fatal-flaw judgment, never a graded scale — the same
audit found weak inter-rater agreement on Likert dimensions and only
moderate agreement on the binary fatal-flaw call **[new]**. Three fatal
classes: ambiguous (more than one defensible outcome), wrong key (the
stated expectation is not what correct execution produces), unsolvable
(the outcome cannot be derived from the prompt and licensed evidence
alone). A case flagged by the triage pass (§5: `inversion` or
`both-fail`) is audited by **solving it from the prompt and licensed
evidence only**, then comparing; every other case gets a re-read. A
benchmark with no solution authored from the prompt alone cannot detect
its own misspecified cases, and the re-read is the cheap approximation,
declared as such per case.

**Output.** Defect count and taxonomy class. Never a rate: at n=16 a
rate has 6.25pp granularity and no usable interval.

**Bound.** One lane; solve-from-prompt on flagged cases plus a declared
sample of the rest. The declared sample is what stops "we only audited
the hard ones" from becoming difficulty filtering by the back door.

**Failure path.** None needed. Defects are repaired before any identity
exists. A defect the run declines to repair is a declared manifest gap
naming the case and the class.

### 4.2 Adversarial attack pass

**Objective.** Pass the benchmark without doing the work. Every one of
ten audited agent benchmarks was passable at near-perfect scores
without solving a task, and one round of patching cannot distinguish a
fixable benchmark from a structurally broken one — only re-running the
attacker can.

**Access — the resolution P8 asks for.** The audit needs exactly the
access it exists to deny. So give the attacker *the candidate's scope,
whatever that is for this case*, and nothing else. The constraint stops
being a problem and becomes the experimental design, and it
self-adjusts across target classes without a per-class rule.

**Outcomes.** `SUCCEEDED` — an artifact passes the probe without the
work; a real hole. `FAILED` — no such artifact within the bound;
evidence of resistance for that class, never proof. `BLOCKED` — the
attack required material the candidate cannot reach; the strongest
result, because it shows the protection is load-bearing.

**This is the candidate-inaccessible check.** `FAILED` or `BLOCKED`
over the candidate scope is precisely the evidence
`protected_evidence.candidate_inaccessible_check` currently records as
`null`, which is why optimization resistance stands UNVERIFIED today.

**Checklist.** The published eight classes (isolation failure, answers
shipped with the test, remote code execution, judge prompt injection,
weak string matching, evaluation-logic gaps, trusting untrusted output,
excessive permissions) as a **dated** opening list. New classes append
with their date. Freezing the list freezes a 2026 attack surface as
permanent law.

**Bound and failure path — the row P8 named as the worst offender.**
One `orch-critique` lane. `SUCCEEDED` findings are repaired within the
remaining allocation, cheapest first; anything not repaired is
**declared in `attack_audit` with the attack that works**. An
undeclared hole is the failure. A declared one is a gap, which is
BenchMaker's existing idiom for exactly this situation and needs no new
law.

### 4.3 Measurement pass

**Objective.** Produce §5's figures. Recording only — P1. A stage that
cannot fail cannot force the revision loop that immutability makes
incoherent.

**Scope.** The candidate-accessible portion only. Running a candidate
against protected evidence exposes it, and `PROT` §Materialization bars
that.

**Rungs.** At least two, per §6's target-class table. Where no second
configuration exists, the pass returns UNVERIFIED with a declared gap —
the same shape as an absent bad seed.

**Bound.** Two rungs × the case set × declared trials, twice.

**Price it honestly, because it depends on the target.** The 171 s
suite sweep grades artifacts that already exist; it is not the cost of
the pass. The pass needs *candidate-produced* artifacts, one per case
per rung, and that cost belongs to the target's own execution. For a
cheap target the pass is the cheapest stage in the redesign. For
BenchMaker's own set it is not: each case asks a candidate to build a
benchmark package, so one rung is sixteen building tasks and two rungs
are thirty-two — the same order as the recursion run that produced the
set (≈2.2M subagent tokens across 15 lanes). The triage pass may reuse
a single rung's artifacts where the second rung is what costs; the
recorded pass may not. Declare the rung pair and its cost before
starting, and treat a target whose candidate execution is expensive as
the case where the two-pass structure of §4 must be justified per run
rather than assumed.

## 5. The instrument

Per case, from the same two-rung run, at no extra execution cost:

| figure | at two rungs | at a larger panel |
| --- | --- | --- |
| difficulty | three-valued status: `both-pass`, `split`, `both-fail` | p(i) = mean correctness across the panel **[new]** |
| discrimination | the `split` bucket is the discriminating set | corrected item–total correlation, point-biserial **[new]** |
| defect signal | `inversion` — the weaker rung passes where the stronger fails | negative-discrimination flagging **[new]** |
| ranking stability | the margin in cases | leave-one-out rank inversions |

Report the three-valued form, not the continuous one. At two rungs and
one trial, p(i) takes three values; presenting it as a psychometric
statistic claims resolution the n does not carry — the same discipline
that makes RF-05 a count and RF-06 an observed spread rather than an SD.

**Reading a case's status.** Three readings, and the redesign's job is
to keep them apart, because they demand different repairs:

| status | readings | repair |
| --- | --- | --- |
| `both-pass` | the case is saturated, **or** its oracle is too lenient | difficulty, **or** the oracle — never resolved to one without evidence (X13) |
| `split` | the case is discriminating | none |
| `both-fail` | the case is genuinely hard, **or** it is broken | §4.1's audit decides; a mis-keyed case is *difficulty-by-corruption*, not difficulty |

That third row is the reading the register never named. BenchBench
states the rule directly: treat hard as progress **only when it
co-occurs with low invalidity and non-trivial discrimination** **[new]**,
having measured a negative association (Pearson r ≈ −0.62) between
item invalidity and discrimination. A `both-fail` case with an
unaudited key is indistinguishable from a wrong answer key, which is
the same reason P3 forbids selecting items by target failure.

**The boundary that keeps this legal.** A flag routes a case to
*audit*. The audit may repair or remove a case only for a **named
correctness defect**, never for its score. Item culling on low
discrimination is standard psychometric practice and it is P3's
forbidden move wearing a lab coat: it selects for wrong answer keys
exactly as target-failure filtering does. BenchBench filters items too
— but on validity flags, before scoring, and never on difficulty. Take
that half and leave the other.

**Two resolution floors, not one.** No delta smaller than the measured
rerun spread is reportable (RF-06), *and* no delta of one case is
reportable at 16 cases, because a one-case margin is flipped by
dropping any single case. Declare `resolution = max(spread, 1 case)` —
6.25pp today. This states the instrument's resolution as a property of
the instrument, which is what the arbitration order's third rule asks
for, and it does so without a sampling-power derivation the purposive
census cannot support (X6 stays unresolved; it is not being resolved
here).

## 6. Anchors by target class

P2 requires every case to name a reference outside the package, or
declare `none` with a reason. A requirement nobody knows how to fill is
a requirement that gets filled with `none`. Per class:

| target class | anchor | cost |
| --- | --- | --- |
| skill | the predecessor version's verdict on the same case — a frozen reference opponent, always available for anything that has shipped once | free |
| workflow / composition | the per-edge human reference trace, or a declared wall-clock and cost budget per edge | one trace |
| harness | a second harness on the same task and model — the factorial design **[new]** | free if two rungs already run |
| model-facing tool | a declared cost, or a world outcome that resolves independently | varies |
| BenchMaker itself | the reference benchmark package (what the 16-case set already does), plus the predecessor set's verdict on the ported case | free — `port` keys already exist |

The harness row is the general lesson: **where two configurations of
the target already run for §4.3's measurement, the second configuration
is an anchor at zero marginal cost.** Most cases can be anchored by
running the pass they were going to run anyway.

## 7. Identity

A score is a property of (**target × model × harness × benchmark**).
BenchMaker pins the benchmark and the target identity and leaves two
free. RF-14 called for binding them; the magnitude was unmeasured. It
is now measured: across 6 harnesses × 8 model backends × 106 tasks
(5,194 trajectories), aggregate scores ranged from 52.4% to 76.2% on
identical tasks with an identical model pool — **a 23.8pp spread
attributable to the harness alone** **[new]**. At 16 cases one case is
6.25pp. The harness is not a confound to note in passing; it is larger
than any candidate delta this benchmark can resolve, by a factor of
about four.

So: the result identity binds model id, effort level, host binding, and
scaffold, and `incomparability` covers all four. Two consequences worth
stating because they are counterintuitive:

- **The harness offset cannot be subtracted out.** The same study finds
  stronger models exhibit *lower* cross-harness variance **[new]**, so
  the effect is candidate-dependent and a single correction term is
  wrong by construction.
- **The escape hatch is a re-run, and it pays for itself.** RF-16
  prices an improvement claim spanning a supersession at re-running
  every retained candidate. That re-run is also the input that
  benchmark agreement testing needs **[new]**: two benchmarks, one
  shared candidate set, compared. Pay once, get the supersession
  agreement figure. At two candidates report the **paired per-case
  verdict table and the count of sign flips**, not a rank correlation —
  BAT's own result is that agreement statistics are unstable and
  method-sensitive with few models, and two is very few.

## 8. Self-benchmarking

Manual, acyclic, between campaigns — unchanged. A `MEASURES.md` entry
is not a campaign and activates nothing; the acyclicity law is
untouched by §3.2.

Three things the redesign adds, all of them recording:

**Benchmark-building is a distinct capability.** Measured Spearman
correlation between a model's benchmark-*design* ability and its
answer-time strength is ≈0.37 **[new]**. That is the empirical case for
BenchMaker existing as an artifact with its own benchmark, and it is
also a warning with teeth: a strong candidate is not thereby a strong
builder, and neither figure may be inferred from the other. Builder
model selection is an independent decision, and §3.1's `builders` field
is where it stops being invisible.

**The builder-family confound has a name and a metric.** When the
builder and the candidate share a model family, the score is
confounded. The measured form is family advantage — mean accuracy on
own-family items minus other-family items — and the finding is that
effects are "measurable but typically modest" and *not uniformly
positive*: some families scored **worse** on their own items **[new]**.
Modest and sign-unstable is precisely the profile that must be recorded
rather than gated. BenchMaker cannot compute it today: the recursion
run used one builder family across all six lanes. So record `builders`
per case now, declare the confound as a manifest gap, and a successor
with two builder families can compute it. This is P10 applied to a
measurement that does not exist yet.

**Prefer the matrix to the number.** A designer × answerer matrix
supports bias audits that a single score conceals **[new]**. For
BenchMaker the axes are builder context × candidate rung, and §3.3's
per-angle vector is one slice of it.

## 9. Traps

The handoff's six traps carry unchanged. Three more, created by the
new instrument:

| trap | why it fails |
| --- | --- |
| culling low-discrimination or `both-fail` cases | P3's forbidden move in psychometric costume — it selects for wrong answer keys by the same mechanism target-failure filtering does. Flags route to audit; only a named correctness defect removes a case |
| subtracting a harness offset to compare across harnesses | the effect is candidate-dependent (stronger models vary less **[new]**), so one correction term is wrong for every candidate but one |
| reporting rank correlation as supersession agreement at two candidates | BAT's own finding is that agreement is unstable and method-sensitive with few models **[new]**. Report paired verdicts and sign flips |

## 10. Sequence

**Superseded by §0 in its ordering constraint.** The rule this section
opened with — the case set is re-sealed exactly once — was an economy
argument about minting successors, and there are no successors to
economize. Re-seal whenever a repair lands, record it in `SEALS.md`, and
carry the predecessor digest into any measurement record the repair
invalidates. The steps below stand; only the once-and-only-once
constraint falls.

1. **Measure the current seal.** ~~Run §4.3 against
   `sha256:0509fe44…4a660787`~~ — **run 2026-08-08, partial.**
   Three cases of sixteen at two rungs
   (`benchmarks/measures/benchmaker.md`, run
   `20260808T061035Z-benchmaker-seal-measurement`): one `split`, two
   `both-fail`, margin one case, rerun spread unmeasured, judged class
   unexercised. Thirteen cases never dispatched; the record declares
   them absent rather than passed, failed or UNVERIFIED.
   **Read §0 before citing any figure from it** — the pass confounded
   itself through candidate dispatch, and the two `both-fail` rows are
   substantially evidence of that confound rather than of case
   difficulty. The instrument built alongside it
   (`tools/validate_measures.py`, 85 tests, 47 mutations 0 survivors)
   is reusable and is the more durable output.
   Re-running the remaining thirteen requires §4.3's new dispatch
   declaration first, or it reproduces the confound.
2. **Land the law.** ~~In reviewable pieces~~ — **landed 2026-08-09**,
   as one change, with the two unresolved owners named first.
   `PROT` = `compositions/references/benchmaker-protocol.md` gained §4's
   stage order and the three stages, §4.3's dispatch-authority
   declaration, §5's distinct-failure-signature count, and a new
   §Execution tier and difficulty; `MAN` =
   `compositions/references/benchmaker-manifest.md` gained §3.1's eight
   fields and the component-identity recipe.
   **The two owners, resolved.** `scoring.md` is not a law surface — the
   only file of that name is `benchmarks/benchmaker/scoring.md`, a
   *package* file inside the case set — so §3.3's scoring law lives in
   `PROT` §Scoring. `EVD` is `skills/workflows/orch-eval-design/SKILL.md`,
   not a file under `compositions/references/`; it gained the tier and
   anchor obligations and the ban on selecting a case by a candidate's
   result.
   `benchmarks/benchmaker/tools/component_identity.py` closes the
   manifest-to-tree hole every `MAN` field would otherwise have
   inherited: it defines the recompute recipe as `seal_set.py`'s own
   line format nested one level, and `benchmark_identity` now moves when
   `cases/` moves. The package re-sealed at
   `sha256:cb06f656…b839088` / set digest `sha256:b236f614…ee8c5712`.
   Still open at this surface: the sixteen cases were cut against the
   predecessor manifest law and case none of the new fields, so a
   candidate that omits all eight still passes every probe. Recorded as
   a manifest gap.
3. **Run the remaining pre-seal stages** on the existing set — triage,
   reference audit, repair, attack, repair-or-declare, recorded
   measurement. The reference audit has four defects waiting for it
   before it starts: the two repaired on 2026-08-08 (which it should
   confirm rather than trust), the `bound` conflation, and the
   manifest-to-tree gap. Re-seal when the repairs land; the
   once-only constraint is withdrawn.
4. **Then anchors** (§6) for target classes as they arrive. The
   successor-per-anchor cost that motivated batching is gone, so add
   each anchor when its reference exists rather than holding a batch.

Deferred, with the condition that would undefer each: judge
certification waits on the WMT/MQM vein (G1), and at one judged case a
mis-certified judge cannot flip a verdict; within-angle redundancy
waits on step 1's margin figure, because if the margin is stable at one
case per angle the redundancy buys nothing and collides with both the
minimality law and the coverage floor.

## 11. Open, unresolved, refused

Recorded so the next run does not re-propose them (P10).

- **G1 — WMT/MQM judge certification is still unsearched.** The
  highest-value follow-up in the register, and RF-12 still waits on it.
- **X6 — the size/resolution collision is not resolved here.** §5
  declares a resolution floor as a property of the instrument; it does
  not settle whether 500 or ~969 items is right, and neither figure
  transfers to a purposive census.
- **G2 — client-rendered leaderboards.** A third of the register's
  current-best cells are gaps. Compounding it, this run found the same
  shape in a new place: arXiv `/pdf` URLs returned degraded
  extractions where `/abs` and `/html` returned usable text. Logged as
  friction; a browser-rendering retrieval path fixes both.
- **Unretrieved, named rather than dropped.** *Automated Benchmark
  Auditing for AI Agents and Large Language Models* (arXiv 2605.26079)
  is directly on §4.2's topic and its PDF did not extract at
  claim-grade. Nothing in this spec rests on it. It is the first fetch
  a successor run should make.
- **Relayed, not primary.** The claim that many SWE-bench passing
  patches would not be merged reaches this spec through a secondary
  citation **[new]**, not from the study itself. Not load-bearing here.
- **Self-verified, still.** RF-18..RF-21 were authored and judged by
  the same context. This spec builds on all four. Sending them to a
  disjoint context remains the first debt, and it now covers more
  ground than when the handoff recorded it.
- **The attack pass's escape hatch may be too soft.** A declared
  unrepaired hole is a gap, not a block. That is consistent with every
  other UNVERIFIED path in BenchMaker, and it is also exactly how a run
  under bound pressure would ship a known-passable benchmark. No
  evidence either way; recorded as a design bet, not a finding.

## Sources new to this spec

- BenchBench: Benchmarking Automated Benchmark Generation —
  [arXiv 2603.20807](https://arxiv.org/abs/2603.20807). Per-item
  difficulty and point-biserial discrimination, negative-discrimination
  flagging, `skip_core`, the invalidity–discrimination association,
  the 150-item two-rater audit and its 3.4% union fatal-flaw rate,
  family advantage, the 0.37 design/answer correlation, and the
  multi-objective reporting recommendations.
- BenchBench (multi-task benchmark evaluation) —
  [socialfoundations.github.io/benchbench](https://socialfoundations.github.io/benchbench/).
  The diversity/sensitivity trade-off across 7 cardinal and 11 ordinal
  benchmarks.
- Do These LLM Benchmarks Agree? Fixing Benchmark Evaluation with
  BenchBench — [arXiv 2407.13696](https://arxiv.org/abs/2407.13696).
  Benchmark agreement testing, and its instability under model-set
  choice and count.
- Harness-Bench: Measuring Harness Effects across Models in Realistic
  Agent Workflows — [arXiv 2605.27922](https://arxiv.org/abs/2605.27922).
  6 harnesses × 8 backends × 106 tasks, 5,194 trajectories, the 23.8pp
  harness spread, and the model–harness reporting level.
- Log analysis is necessary for credible evaluation of AI agents —
  [arXiv 2605.08545](https://arxiv.org/abs/2605.08545). Reward hacking,
  spurious success, and process failure masked by a lucky outcome —
  a second witness for RF-19's dual-oracle contrast, which the register
  carried on one lane plus one corroborator.
