# Benchmark design

Field evidence distilled to what changes a builder's behavior. These
are findings, not law:
[the protocol](../compositions/references/benchmaker-protocol.md) owns
what BenchMaker enforces and
[the redesign spec](benchmaker-redesign-spec.md) owns what changes.

Two evidence sets, and every figure below belongs to one of them. Most
trace to
[FINDINGS-FIELD.md](../benchmarks/benchmaker/FINDINGS-FIELD.md)
(2026-08-08; 110 benchmarks, 16 domains, 199 sources). The rest name
their study in prose — *the generation meta-benchmark*, *the harness
study*, *the multi-task suite analysis*, *the agreement-testing work*,
*the log-analysis paper* — and resolve at the end; those were
retrieved after that report closed. Cite those files as evidence,
never this one.

## Difficulty is not validity

Discrimination separates good artifacts from broken ones. It says nothing
about whether the target finds the benchmark hard. A benchmark can pass
every validity check at a 100% target score. Gate validity; **measure**
difficulty and publish the figure.

Measure in the measurement pass, on the candidate-accessible half
only — running the target against protected evidence exposes it.
Publish the score, its scope, the target identity, and the date. Do not
gate on a band: at a 32-case resolution a 5-9% band admits one
attainable score, and a gate forces one verdict on the two readings
below, which demand opposite repairs.

A published launch band is one maintainer's stated practice, not a field
standard. Cite it as an anchor; never as a threshold.

**Measure per item, not per suite.** A suite score says a set is easy;
it never says which case leaks the headroom. The generation
meta-benchmark's instrument is two numbers per item — difficulty as
mean correctness across a panel, discrimination as the corrected
item–total correlation — plus a flag for items where weaker systems
outperform stronger ones. All three come free from a run made for
another reason. Report only the resolution the panel carries: at two
rungs and one trial, difficulty is a three-valued status
(both-pass, split, both-fail), not a statistic.

**A score has three readings, not two.** High: the set is too easy, or
the oracle is too lenient — opposite repairs, never resolved to one
without evidence. Low: the case is genuinely hard, **or it is broken**.
The same work measures invalidity and discrimination as negatively
associated (Pearson r ≈ −0.62) and states the rule that follows: treat
hard as progress only when it co-occurs with low invalidity and
non-trivial discrimination. Difficulty-by-corruption looks exactly like
difficulty from the outside.

## Four ways not to build difficulty

- **Never filter items by model failure.** It is the field's dominant
  filter and it selects wrong answer keys: an expert audit found
  29.3 ± 3.7% of gold answers in one frontier benchmark contradicted
  published literature, attributed to that filter. Label noise is
  indistinguishable from a low score.
- **Never cull items for low discrimination.** Item culling is routine
  psychometric practice and it is the same move in a lab coat — it
  drops the items a wrong key would produce, by the same mechanism.
  Filter on **validity** (broken, ambiguous, mis-keyed), before
  scoring, for a named defect. Never on difficulty. A flag routes an
  item to audit; only the audit removes it.
- **Procedural generation buys non-memorization, not non-saturation.** A
  fully procedural suite still went 1.57% → 40.0% in ~15 months. A
  generator with few effective degrees of freedom is an answer key with
  extra steps. The hardest interactive benchmark in the field rejected
  generation and authors its novelty.
- **Never calibrate difficulty to the system under test.** It is
  revising the design from scores, and no benchmark in the field does
  it.

## The answer key is the weakest link

Authored oracles are wrong at 10-46% across every domain surveyed.
Proving a probe *can* fail proves nothing about whether its expectation
is *right*. Audit reference correctness in a context disjoint from both
the builders and the first qualifier.

A benchmark with no solution authored from the prompt alone cannot detect
its own misspecified cases. Solving the item from the prompt and its
licensed evidence, then comparing, is what makes an audit more than a
re-read — and it is the expensive half, so target it.

**Audit on a binary, not a scale.** The generation meta-benchmark's
two-rater audit over ~150 stratified items found weak inter-rater
agreement on graded dimensions and only moderate agreement on the
binary fatal-flaw call. Its union fatal-flaw rate was 3.4% — the
measured good end of the 10-46% band, and what a disciplined pipeline
achieves rather than what authoring achieves unaided. Record a defect
count and a taxonomy class; a rate over a small set carries no usable
interval.

## Oracles

An oracle that can fail is not an oracle correlated with truth. Measured
against a human median, plausible cheap checkers scored Spearman −0.394,
−0.291 and −0.103 — pointing the wrong way, not merely weak. Certify the
oracle: hand-label a sample, score every candidate oracle against it, pin
the winner, publish the table. Judge-human agreement is a per-slice
number; one aggregate hides where the instrument is worse than the expert
it replaces.

**Order the oracles by objectivity and publish the mix.** The generation
meta-benchmark scores in a fixed order — exact match, then
numeric/symbolic matching, then rubric-guided judging, then *skip* for
the unverifiable — and recommends reporting the fraction decided by
objective verifier versus by judge, because the mix changes both what is
measured and how reproducible it is. Deterministic-required with judged
criteria secondary and non-compensating is the stronger form of the same
ordering. The unverifiable-item label is the same construct as an
UNVERIFIED verdict, reached independently.

State oracles are blind to read-only work; trajectory oracles break on
error recovery and correct-but-different solutions. Both sides of that
split publish their own counterexample. Require both, or declare which
failure class you accept. The log-analysis paper is the second witness:
outcome-only scoring misses reward hacking, spurious success, and
process failure rescued by a lucky outcome. Report the pair; scoring on
the trace re-imports the correct-but-different failure.

Attackability is architectural. Every one of ten audited agent benchmarks
was passable at near-perfect scores without solving a task (219 flaws).
One round of patching cannot tell a fixable benchmark from a structurally
broken one — only re-running the attacker can. Attempt to pass the
benchmark without doing the work, in the attack pass, from the
candidate's own scope. An attack that needs material the candidate
cannot reach is the strongest result available: it shows the protection
is load-bearing.

## A score is a property of its configuration

Not of the model, and not of the artifact under test alone. The harness
study fixed the task, sandbox, budget, timeout and evaluator and varied
only the execution layer across six harnesses, eight model backends and
106 tasks — 5,194 trajectories — and measured aggregate scores from
52.4% to 76.2%. **23.8 points from the harness alone.** Where one case
in a sixteen-case suite is 6.25 points, the harness is not a confound
worth noting; it is several times larger than any delta the suite can
resolve.

Two consequences. Report at the configuration level — artifact × model ×
harness × benchmark — and bind all four into the result identity. And do
not subtract a harness offset: the same study finds stronger models vary
*less* across harnesses, so the effect is candidate-dependent and one
correction term is wrong for every candidate but one.

## Benchmarks that are generated, not written

**Building a benchmark is a different capability from solving one.**
Measured Spearman correlation between a model's benchmark-design ability
and its answer-time strength is ≈0.37. Neither figure may be inferred
from the other; builder selection is an independent decision and belongs
in the record.

**Builder and candidate sharing a model family is a confound with a
metric.** Family advantage — mean accuracy on own-family items minus
other-family items — is measurable, typically modest, and *not uniformly
positive*: some families scored worse on their own items. Modest and
sign-unstable is the profile that must be recorded rather than gated.
Recording the builder identity per item is what lets a later run compute
it at all.

**Prefer a matrix to a number.** A designer × answerer matrix supports
bias audits that a single leaderboard score conceals. Report
multi-objective quality — validity, diagnostic utility, and reliability
as separate axes — rather than one figure that lets a gain on one axis
pay for a loss on another.

## Reliability and statistics

Report `pass^k` — all k trials succeed — not `pass@k`. One system fell
~50% → ~25% between k=1 and k=8; the headline described a system that
fails the same task most of the time.

**Diversity costs ranking stability.** The multi-task suite analysis
measures a direct trade-off across seven cardinal and eleven ordinal
benchmarks: the more diverse a suite, the more sensitive its ranking to
changes that should not matter. One case per angle with no within-angle
redundancy is the maximally diverse configuration and therefore the
least stable one. The repair is not a better aggregate — at one item per
angle a geometric or harmonic mean is dominated by a single item. It is
to report the per-angle vector as the artifact and treat any scalar as
derived.

Clustered standard errors run up to 3.05× naive on grouped items.
Detecting a 3-point difference at 80% power needs ~969 independent
items — which collides with the ≤500-item size guidance. Unresolved;
record the collision rather than picking a side. Sampling power also
presumes a super-population; a purposive census of declared coverage has
none, so declare the instrument's own resolution instead — no delta
below the measured rerun spread, and none below one item.

Partial credit and binary scoring produce different rankings on the same
suite. Do not headline a partial score.

A net-sum aggregate leaks headroom: gains on easy items mask failures on
hard ones.

## Ground truth where no test can run

Expert oracles have a measured noise floor — 70.8% human-human agreement
on one expert suite. **A model gap narrower than the floor is grader
variance.** Require both cost and agreement per item; almost no
benchmark reports them.

Ground truth can be manufactured instead of authored: inject a single
error of known type and magnitude into a verified-correct artifact, and
magnitude becomes a difficulty dial at near-zero labelling cost. Or
harvested from decisions experts already wrote. Both defer an audit
rather than avoid one.

An outcome oracle removes the annotator but rots the baseline: a frozen
expert baseline expires against a moving question set.

Where correctness is defined by an opponent, freeze the reference
opponent or hold out the co-player population. An open ladder yields
ratings that drift as the pool improves. Where two configurations of the
target already run, the second one is a reference opponent at zero
marginal cost.

## Lifecycle

Saturation is a retirement trigger, and the only stated trigger is
statistical indistinguishability between frontier systems — undetectable
without error bars most benchmarks never compute.

When a state oracle saturates, lengthen the horizon; never loosen the
check.

Contamination canaries are provably defeated (a base model reproduced a
published canary GUID) and n-gram decontamination falls to paraphrase.
Treat a canary as detection, never as resistance.

At a version boundary, declare cross-version results not comparable and
re-grade. This is the field converging on BenchMaker's incomparability
rule, arrived at independently.

**The re-grade is also an agreement test.** The agreement-testing work
validates a new benchmark against an established one by comparing how
they rank a shared system set — which is exactly what re-running every
retained candidate across a version boundary produces. Its own finding
is the caveat: agreement statistics are unstable and method-sensitive
under the choice and number of systems compared. With two systems,
report the paired per-item verdicts and the count of sign flips; a rank
correlation over two points is not a statistic.

## Sources retrieved after the register closed

- *The generation meta-benchmark* — BenchBench: Benchmarking Automated
  Benchmark Generation, [arXiv 2603.20807](https://arxiv.org/abs/2603.20807).
  Per-item difficulty and discrimination, negative-discrimination
  flagging, the unverifiable-item label, the invalidity–discrimination
  association, the 150-item two-rater audit and its 3.4% fatal-flaw
  rate, family advantage, the 0.37 design/answer correlation, and the
  multi-objective reporting recommendations.
- *The harness study* — Harness-Bench: Measuring Harness Effects across
  Models in Realistic Agent Workflows,
  [arXiv 2605.27922](https://arxiv.org/abs/2605.27922).
- *The multi-task suite analysis* — BenchBench,
  [socialfoundations.github.io/benchbench](https://socialfoundations.github.io/benchbench/).
  The diversity/sensitivity trade-off.
- *The agreement-testing work* — Do These LLM Benchmarks Agree? Fixing
  Benchmark Evaluation with BenchBench,
  [arXiv 2407.13696](https://arxiv.org/abs/2407.13696).
- *The log-analysis paper* — Log analysis is necessary for credible
  evaluation of AI agents,
  [arXiv 2605.08545](https://arxiv.org/abs/2605.08545).
