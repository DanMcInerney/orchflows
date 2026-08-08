# Benchmark design

Field evidence distilled to what changes a builder's behavior. Every
figure traces to
[FINDINGS-FIELD.md](../benchmarks/benchmaker/FINDINGS-FIELD.md)
(2026-08-08; 110 benchmarks, 16 domains, 199 sources) — cite that file as
evidence, never this one. These are findings, not law:
[the protocol](../compositions/references/benchmaker-protocol.md) owns
what BenchMaker enforces.

## Difficulty is not validity

Discrimination separates good artifacts from broken ones. It says nothing
about whether the target finds the benchmark hard. A benchmark can pass
every validity check at a 100% target score. Gate validity; **measure**
difficulty and publish the figure.

Measure pre-seal, on the candidate-accessible half only — running the
target against protected evidence exposes it. Publish the score, its
scope, the target identity, and the date. Do not gate on a band: at a
32-case resolution a 5-9% band admits one attainable score, and a FAIL
after qualification has fixed an identity mints a successor per attempt
with no loop bound.

A published launch band is one maintainer's stated practice, not a field
standard. Cite it as an anchor; never as a threshold.

Read a high score two ways — the target is strong, or the oracle is
lenient. Opposite repairs. Never resolve to one without evidence.

## Three ways not to build difficulty

- **Never filter items by model failure.** It is the field's dominant
  filter and it selects wrong answer keys: an expert audit found
  29.3 ± 3.7% of gold answers in one frontier benchmark contradicted
  published literature, attributed to that filter. Label noise is
  indistinguishable from a low score.
- **Procedural generation buys non-memorization, not non-saturation.** A
  fully procedural suite still went 1.57% → 40.0% in ~15 months. A
  generator with few effective degrees of freedom is an answer key with
  extra steps. The hardest interactive benchmark in the field rejected
  generation and authors its novelty.
- **Never calibrate difficulty to the system under test.** It is
  revising the design from scores, and no benchmark in the field does
  it. Incompatible with a sealed set.

## The answer key is the weakest link

Authored oracles are wrong at 10-46% across every domain surveyed.
Proving a probe *can* fail proves nothing about whether its expectation
is *right*. Audit reference correctness in a context disjoint from both
the builders and the first qualifier.

A benchmark with no solution authored from the prompt alone cannot detect
its own misspecified cases.

## Oracles

An oracle that can fail is not an oracle correlated with truth. Measured
against a human median, plausible cheap checkers scored Spearman −0.394,
−0.291 and −0.103 — pointing the wrong way, not merely weak. Certify the
oracle: hand-label a sample, score every candidate oracle against it, pin
the winner, publish the table. Judge-human agreement is a per-slice
number; one aggregate hides where the instrument is worse than the expert
it replaces.

State oracles are blind to read-only work; trajectory oracles break on
error recovery and correct-but-different solutions. Both sides of that
split publish their own counterexample. Require both, or declare which
failure class you accept.

Attackability is architectural. Every one of ten audited agent benchmarks
was passable at near-perfect scores without solving a task (219 flaws).
One round of patching cannot tell a fixable benchmark from a structurally
broken one — only re-running the attacker can. Attempt to pass the
benchmark without doing the work, before sealing.

## Reliability and statistics

Report `pass^k` — all k trials succeed — not `pass@k`. One system fell
~50% → ~25% between k=1 and k=8; the headline described a system that
fails the same task most of the time.

Clustered standard errors run up to 3.05× naive on grouped items.
Detecting a 3-point difference at 80% power needs ~969 independent
items — which collides with the ≤500-item size guidance. Unresolved;
record the collision rather than picking a side.

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
ratings that drift as the pool improves.

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
re-grade. This is the field converging on BenchMaker's successor-identity
rule, arrived at independently.
