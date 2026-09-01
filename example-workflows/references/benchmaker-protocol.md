# BenchMaker protocol

Benchmark craft for a domain with no pack: what the calls of
[the benchmaker workflow](../benchmaker/SKILL.md) make, and nothing
they, a contract, or a rule already state.

## Licensed oracle material

A concrete input, output, or trace the frozen evidence exhibits is
licensed oracle material: an accepted design anchors an oracle to it or
records why casing it is impossible, and a judgment that it is an
implementation artifact is not such a reason.

## Qualification

Check oracle failability, coverage, discrimination, reproducibility,
redundancy, provenance, and execution cost independently. Every oracle must be
capable of failing. Discrimination requires seeded known-good and known-bad
variants supplied by the qualifying context — the benchmark passes every good
seed and fails every bad one. The bad set includes one inert variant with the
intended behavior absent, and a bad variant counts only when shown to change
the observable outcome — an equivalent variant is excluded, not scored. An
inert variant shown equivalent is itself a finding: the chosen outcome does
not observe the intended behavior, recorded as a gap with discrimination
UNVERIFIED for that behavior. Where no known-bad variant can exist, absence
of bad seeds leaves discrimination UNVERIFIED and an explicit gap. For a
nondeterministic outcome, qualification
fixes a declared trial count; good variants pass and bad variants fail on
every trial. A required deterministic failure blocks qualification. Judged
criteria carry anchors, remain secondary, cannot compensate for required
deterministic failure, and record their rerun variance.

Resolve every runnable component before replay.

Fix protected evidence by identity with its visibility and release policy.
When optimization resistance depends on protected evidence, absence of a
candidate-inaccessible check leaves it UNVERIFIED. Record expected cost and
actual qualification spend.

## Audit and measurement

Qualification proves a benchmark measures something. It never asks
whether the target finds it hard, whether the expectation is right, or
whether the probe is passable without the work. Three stages answer
those, in this order, after qualification:

    triage measurement → reference audit → repair
      → attack pass → repair-or-declare
      → recorded measurement

Two measurement passes, not one: the cheap pass targets the expensive
audit, and the second produces the recorded figure. Where the design
declares an expensive execution class, justify the second pass for this
run or declare its absence a gap. None of these stages renders a
pass/fail verdict on the benchmark.

### Reference audit

Prove the expectation right — which oracle failability and expectation
provenance do not. A context disjoint from every builder **and** from
the qualifying context judges each case on a binary fatal-flaw call,
never a graded scale, in three classes: ambiguous (more than one
defensible outcome), wrong key (the stated expectation is not what
correct execution produces), unsolvable (the outcome does not follow
from the prompt and licensed evidence alone).

A case the triage pass recorded `inversion` or `both-fail` is audited by
solving it from the prompt and licensed evidence only, then comparing; a
declared sample of the rest is re-read, and the sample is declared so
that auditing only the hard cases cannot become difficulty filtering by
the back door. Record a defect count and each defect's class, never a
rate — over a small set a rate carries no usable interval; a defect the
run declines to repair is a declared gap naming the case and the class.

### Attack pass

Attempt to pass the benchmark without doing the work, from the
candidate's own scope for that case and nothing else — the access
constraint is the experimental design, and it self-adjusts across target
classes without a per-class rule. Outcomes: `SUCCEEDED`, an artifact
passes the probe without the work, a real hole; `FAILED`, no such
artifact within the bound, evidence of resistance for that class and
never proof; `BLOCKED`, the attack needed material the candidate cannot
reach, which shows the protection is load-bearing. `FAILED` or `BLOCKED`
over the candidate scope is the candidate-inaccessible check
§Qualification leaves UNVERIFIED in its absence.

The attack taxonomy is a **dated** checklist, authored per package by
this pass, and new classes append with their date; freezing it freezes
one year's attack surface as permanent law. Repair `SUCCEEDED` findings
within the remaining allocation, cheapest first. Every hole left
unrepaired is declared with the attack that works. An undeclared hole is
the failure; a declared one is a gap.

### Measurement pass

Recording only. This stage cannot fail, so it can force no revision
loop. Its scope is the candidate-accessible portion alone — running a
candidate against protected evidence exposes it.

Declare before running: the rung pair and its cost, and the authority
each candidate receives — delegation, tooling, network, and evidence —
naming every protocol-required criterion that authority makes
unreachable. A criterion the dispatch made unreachable is an intake gap
recorded before scoring, never a candidate failure. At least two rungs;
where no second configuration exists the pass returns UNVERIFIED with a
declared gap.

Report per case, from the same run: difficulty as the three-valued
status `both-pass`, `split` or `both-fail`; the `split` bucket as the
discriminating set; `inversion`, the weaker rung passing where the
stronger fails, as a defect signal; and the margin in cases. Report the
three-valued form, not a continuous one — at two rungs and one trial a
mean claims resolution the count does not carry. Report beside the
discriminating set **how many distinct failure signatures produced
it**: one repeated candidate habit counted N times is not N angles
discriminating.

Report `(score, cost)` pairs carrying host, price list, and date;
`pass^k` beside `pass@1` at the declared k for a nondeterministic case;
and the fraction of criteria decided by deterministic oracle versus by
judged oracle, which is recorded per criterion and never summed.

The record lands outside the package — in the measuring ticket's
`## Report` — one entry per measurement event, naming the git revision
of the benchmark it covers, the full candidate identity the manifest's
`incomparability` bounds, the date, the measured scope, and these
figures.
Name a revision reachable from the default branch: where the pass ran on
a branch, name the default-branch-reachable ancestor carrying identical
measured bytes and state that relation in one clause. A squash merge
makes no branch commit an ancestor of the default branch, so a branch
revision dangles once the branch is collected.

## Scoring

Never subtract a harness offset: the effect is candidate-dependent, so
one correction term is wrong for every candidate but one. Where a claim
spans the incomparability boundary, re-run every retained candidate and
report the paired per-case verdicts and the count of sign flips, never a
rank correlation over few candidates.
