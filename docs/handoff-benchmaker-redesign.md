# Handoff — BenchMaker redesign

Guiding principles for the redesign, from the field research at
[FINDINGS-FIELD.md](../benchmarks/benchmaker/FINDINGS-FIELD.md)
(2026-08-08; 110 benchmarks, 16 domains, 199 sources). That report owns
the evidence and the eighteen ranked recommendations; this file owns the
*reasoning* an executor needs when the register does not cover the case
in front of them. [Benchmark design](benchmark-design.md) is the terse
rule set. Delete this file when the redesign lands.

Read the register before acting. Every principle below has already been
attacked once by a disjoint context, and the surviving form is narrower
than the obvious one.

## The problem in one sentence

BenchMaker qualifies that a benchmark **measures something real**; it
never asks whether the target **finds it hard**. QC-1..QC-10 are ten
integrity checks, so a benchmark its target scores 100% on seals cleanly
with a recomputable identity — and nothing distinguishes that from a
benchmark whose oracle is simply too lenient.

## Principles

### P1 — Gate validity; *record* difficulty

Difficulty enters as a published figure with a declared gap, never as a
pass/fail threshold. The sealing argument that once forced this is
withdrawn ([spec](benchmaker-redesign-spec.md) §0c); the corollary below
carries P1 alone. The measurement is cheap and the gate is incoherent.

Corollary: a high incumbent score has **two** readings — the set is too
easy, or the oracle is too lenient — and they demand opposite repairs.
Never let them share one verdict.

### P2 — Bind every case to an anchor outside the package

The deepest gap in the current design, and the one no recommendation
originally proposed: cases are scored against **authored expectations
only**. Nothing is anchored to a human trace, a declared cost, a frozen
reference opponent, or a world outcome that resolves independently.

An anchor is what converts a score into a claim. It is also the honest
alternative to importing someone else's headroom band — a declared
reference makes a case hard or easy relative to something the candidate
cannot move, rather than relative to its author. `ANCHOR: none` with a
reason is a legal and useful declaration; silence is not.

### P3 — The expectation is the weakest link, not the probe

QC-2 proves the probe *can* fail. QC-4 traces where the expectation came
from. **Nothing proves the expectation is right.** The field's measured
prior for hand-authored expert items is 10-46% defective.

So: audit reference correctness in a third context, disjoint from both
the builders and the first qualifier. Record a defect **count** and a
taxonomy class — at n=16 a rate has 6.25pp granularity and no usable
interval.

And the sharp edge: **never select items by target failure.** It is the
field's dominant difficulty filter and it systematically recruits wrong
answer keys, because "no model gets it right" cannot distinguish a hard
item from a mis-keyed one. Label noise and genuine difficulty are
indistinguishable from the outside.

### P4 — A failable oracle is not a correct oracle

Two different properties. Measured against a human median, plausible
cheap checkers have scored *negatively* correlated with truth — pointing
the wrong way, not merely weak. Certification means labelling a fixed
sample, scoring every candidate oracle against it, pinning the winner by
identity, and publishing the agreement table. Assertion is not
certification.

Judge-human agreement is a per-slice number; one aggregate conceals the
slices where the instrument is worse than the expert it replaces.

### P5 — Assume attack, and treat attackability as architectural

Every one of ten audited agent benchmarks was passable at near-perfect
scores without solving a task. The decisive result: **one round of
patching cannot tell a fixable benchmark from a structurally broken
one** — only re-running the attacker can. Benchmaker's probes execute in
the same tree as the packages they grade.

Add an attack pass whose objective is to *pass the benchmark without
doing the work*. This is also the candidate-inaccessible check whose
absence currently leaves optimization resistance UNVERIFIED. Name any
attack taxonomy a **dated** checklist; freezing one freezes a 2026
attack surface as permanent law.

### P6 — Report distributions, never bare points

Any single number that hides variance, cost, or heterogeneity is a
headroom leak.

- No delta smaller than the measured rerun spread is reportable. At k=3
  report observed spread (max−min); an SD carries two degrees of freedom.
- Report `(score, cost)` pairs. A higher score bought with more spend is
  otherwise indistinguishable from a better candidate.
- Report the per-criterion vector beside any aggregate. An arithmetic
  net sum lets one saturated criterion pay for one that still
  discriminates — which is what `net 27/32` currently is.
- Report `pass^k` beside `pass@1` in campaigns.

### P7 — A score is a property of (candidate × harness × benchmark)

BenchMaker pins two of the three. Bind model id, effort level, host
binding and scaffold into the result identity, and declare
cross-identity incomparability explicitly. Price the escape hatch: an
improvement claim spanning a supersession requires **re-running every
retained candidate**, and "annotated regrade" is the name of that
re-run, not a substitute for it.

### P8 — Every new required stage carries a priced bound and a failure path

An unpriced stage is skipped or overrun. The adversarial audit (P5) is
currently the worst offender: no repair bound when it fails, and the
auditing context needs exactly the access the audit exists to deny.
Resolve that before making it required.

This principle earned itself during the research run: two of eight lanes
overran their bound, both on retrieval-tool failure rather than scope
creep. The bound was priced for working tools.

### P9 — Do not break what the field arrived at later

Several current laws are correct and were reached independently by the
field *after* BenchMaker had them. Treat them as load-bearing:

| keep | why |
|---|---|
| ~~immutable identity, successor-on-change~~ | **withdrawn 2026-08-09 with the seal** ([spec](benchmaker-redesign-spec.md) §0c). What the field retrofitted is that scores do not cross a version boundary, and that survives; the minting mechanism it was carried on does not |
| qualification disjoint from every builder | the structural answer to self-grading |
| blocked-return shape, UNVERIFIED-on-crash | a crash is not a FAIL; this predates the field's version |
| the equivalence bridge | a bad variant counts only when shown to change the outcome |
| the inert-variant mandate | probe inversion as a floor check |
| protected evidence off-tree | the only mechanism behind the exhibited/protected line |
| cost declared and bounded | most published benchmarks never do this |

### P10 — Record refusals, not just decisions

A withdrawn recommendation that leaves no trace gets re-proposed by the
next run. Three rows were withdrawn at the gate and sit in `### Declared
non-opportunities` with the reasoning intact. Preserve that habit: gaps,
non-opportunities and unresolved disagreements are outputs, not
housekeeping.

## Traps

Each looks like the obvious fix and is not. All were proposed and killed
in this run, or ruled out by the evidence.

| trap | why it fails |
|---|---|
| a numeric headroom band as a gate | at 32-case resolution a 5-9% band admits one attainable score; and the band is two maintainer self-reports, not a standard |
| procedural generation as anti-saturation | buys instance non-memorization only; a fully procedural suite still went 1.57% → 40.0% in ~15 months |
| calibrating a difficulty dial to the target | "revise the design from scores" — named under **Never** in `orch-eval-design`; a convergent *empty* result in the field |
| building N+k cases and holding k as refill | k cases from the same sitting, builders and evidence is the maximally inherited successor — what the burn-law was written against |
| a power-derived smallest detectable difference | sampling power presumes a super-population; the cases are a purposive census, so it answers a question the set does not ask |
| scoring on a trace oracle | re-imports the correct-but-different failure the equivalence bridge exists to exclude. Report the pair; never sum it |

## Sequence

1. **Measure before changing anything.** Score the incumbent against the
   candidate-accessible scope of the sealed 16-case set, and record
   separation across two candidate rungs. Both are recordings, so
   neither can fail and force a revision. Until those figures exist,
   every other change is advice about a benchmark whose difficulty is
   unmeasured.
2. **One supersession PR, not five.** Difficulty is measured and
   recorded; minimality cannot trade it away; discrimination is proven
   against real candidates; every case declares an anchor; and an
   arbitration order says which wins on conflict. That is one law.
   Splitting it mints five successor identities for one idea.
3. **Then the oracle work** — reference-correctness audit, adversarial
   attack pass, dual-oracle reporting.
4. **Judge certification waits** on the WMT/MQM follow-up; at one judged
   case, and with judged criteria unable to compensate for a required
   deterministic failure, a mis-certified judge cannot flip a verdict.

## Arbitration order

Three pressures conflict: minimality pushes set size down, resolution
pushes it up, headroom pushes difficulty up. When they collide:

1. **Validity first** — no case is added or removed to move a score.
2. **Coverage second** — the declared coverage floor is not tradable.
3. **Resolution third** — declare the resolution and report it; do not
   buy cases toward a power target.
4. **Headroom is recorded, never bought** — it produces figures, not
   gates, so it never wins an argument against validity.

This is BenchMaker policy, not a field finding. No retrieved source
states this ordering, and the underlying disagreement is recorded
unresolved. It is written down so the tie is not broken by whoever
happens to write the ticket.

## Open state the executor inherits

- **Four recommendations (RF-18..RF-21) are self-verified.** The gate
  authored them and rendered their verdicts; author and reviewer are the
  same context. Sending them to a disjoint context is the first debt.
- **The WMT/MQM vein is unsearched** and owns the evidence judge
  certification needs.
- **A third of the register's current-best cells are gaps** because
  leaderboards render client-side. More web calls will not fix it; a
  browser-rendering retrieval path will.
- **The report is 212 KB** against a repository law that every sentence
  be load-bearing. One economy pass was attempted and netted −10 lines.
