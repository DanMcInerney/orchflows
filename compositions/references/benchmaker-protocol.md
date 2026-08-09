# BenchMaker protocol

These stages are exhaustive: evidence acquisition, evaluation-design
invocation, materialization, qualification, the three pre-seal stages,
and manifest sealing.

## Intake and bound

Keep the target identity opaque. Carry its intended observable outcome,
evidence access, and cost limits without defining its evaluation boundary. The
evaluation-design owner records an unobservable outcome or unavailable oracle
as an explicit gap.

Before work, partition one caller bound across evidence, design,
materialization, qualification, and the pre-seal stages. An unpriced
stage is a stage that gets skipped or overruns. Allocations are nonnegative and their
total cannot exceed the caller bound; unused allocation from a completed stage
may carry forward. Never copy the caller bound into a stage, internal spec,
delivery, or lane.

Fix the evidence identities, source policy, judgment permission, applicable
pack references, benchmark write scope, excluded actions, protected-evidence
policy, and contracted return fields. Every internal spec selects one
applicable pack; exactly one pack per internal spec.

Declare, before work, the target's execution class and the execution
budget that class carries — per §Execution tier and difficulty — and the
authority each candidate context will receive at the measurement pass.

## Internal call carriage

Every internal Spec, Deliver, and evaluation-design invocation carries one
complete delegation packet. `objective` names that stage's observable result;
`inputs` bind fixed upstream identities, inherited constraints, and applicable
pack references, plus the frozen stamped spec identity for Deliver;
`authority` restricts stage write scope and exclusions; `bounds` carries only
the stage allocation, expected execution cost, and unused carry;
`return_contract` points to the callee's canonical Return; `reply_to` names the
literal closing recipient.

Each Spec selects one applicable pack and its paired Deliver preserves that
stamp. Qualification authority is disjoint from builders. A packet receives
the stage allocation, never the caller bound.

## Evidence acquisition

Reuse a supplied qualified synthesis only when its identity, provenance,
boundary coverage, and the
[research charter](benchmaker-research.md)'s artifacts are fixed. Otherwise
obtain a converged synthesis under the source policy — lanes and artifacts
per that charter — before evaluation design.

Freeze the synthesis and sources at one result identity. Unsupported semantics
remain gaps; they never become invented target truth. A non-complete delivery,
decision gap, unresolved source, or uncovered remainder returns partial
evidence and stops the later stages.

## Evaluation design

Accept only those contracted fields at one package-owned identity. A missing
field or gap that leaves the intended outcome or materialization unobservable
returns partial evidence and stops materialization; carry every other declared
gap into qualification and the manifest. BenchMaker neither fixes the
evaluation boundary nor selects, revises, or interprets its case and scoring
semantics. A concrete input, output, or trace the frozen evidence exhibits is
licensed oracle material: an accepted design anchors an oracle to it or records
why casing it is impossible, and a judgment that it is an implementation
artifact is not such a reason.

## Execution tier and difficulty

The target's own execution cost sets the pace. The declared coverage
floor never moves with it. Intake declares one execution class, and the
class fixes each case's execution tier and the suite's wall-clock
ceiling — never which angles are cased.

**Cheap execution — every case fast.** Where a case's probe grades an
artifact that already exists, every case sits in the smallest tier whose
outcome its angle can be observed in, and the suite sweep stays inside a
declared ceiling. Speed here is not economy: the recorded measurement
pass runs the whole set at two rungs twice, so a slow suite is a
measurement pass that does not run.

**Expensive execution — declare it, do not hide it.** Where a case asks
a candidate to produce the artifact, as BenchMaker's own set does, the
per-case cost belongs to the target and the suite ceiling rises with it.
The coverage floor does not fall, and §Pre-seal stages' two measurement
passes are justified per run rather than assumed.

**Speed is bought from the probe, never from the coverage floor, the
oracle, or the horizon the outcome needs.** A case moved to a faster
tier by loosening its oracle or shortening its horizon has bought a
`both-pass` reading, which no measurement can tell from a lenient
oracle. Where an angle's outcome is unobservable within the declared
tier, raise that case's tier and record why; never drop the angle.

**Difficulty is built, never filtered.** The licensed levers are horizon
length, outcome specificity, and a stricter oracle that stays correct.
Never select or retain a case by target failure, never remove one for
low discrimination, and never revise the design from a candidate's
scores. A recorded status routes a case to §Pre-seal stages' reference
audit; only a named correctness defect removes it.

## Materialization

Materialize the selected case specifications without selecting, adding,
removing, ranking, rewriting, or substituting a case. Each construction spec
uses one applicable pack and only its allocation; when cases span domains,
chain single-pack runs through frozen evidence identities.

Keep builders' write scopes disjoint. Preserve each case, runner, scoring, and
provenance identity. Candidate and search contexts cannot read, choose,
rewrite, retire, or receive item-level feedback from protected evidence.

## Qualification

Qualify the assembled result at a fixed identity in a context independent of
its builders. Builders never qualify their own cases or authored oracles as
sufficient evidence.

Independence per [rules/verification.md](../../rules/verification.md)
§10 is the caller's to supply. A dispatch withholding the authority to
reach a builder-disjoint context makes this stage unreachable: the run
returns blocked naming that authority — never a self-qualified verdict
set, never the pending marker presented as finished. A caller unable to
supply it declares qualification unreachable at intake, so the
deficiency is a recorded gap rather than a builder's apparent failure.

Check oracle failability, coverage, discrimination, reproducibility,
redundancy, provenance, and execution cost independently. Every oracle must be
capable of failing. Discrimination requires seeded known-good and known-bad
variants supplied by the qualifying context — the benchmark passes every good
seed and fails every bad one. The bad set includes one inert variant with the
intended behavior absent, and a bad variant counts only when shown to change
the observable outcome — an equivalent variant is excluded, not scored. An
inert variant shown equivalent is itself a finding: the chosen outcome does
not observe the intended behavior, recorded as a gap with discrimination
UNVERIFIED for that behavior. Where
no known-bad variant can exist, absence of bad seeds leaves discrimination
UNVERIFIED and an explicit gap. For a nondeterministic outcome, qualification
fixes a declared trial count; good variants pass and bad variants fail on
every trial. A required deterministic failure blocks qualification. Judged
criteria carry anchors, remain secondary, cannot compensate for required
deterministic failure, and record their rerun variance before sealing.

Resolve every runnable component and verify its byte digest before replay.
Qualification recomputes its checks from those bytes and captured outputs;
self-declared verdicts or evidence never qualify a benchmark.

Fix protected evidence by identity with its visibility and release policy.
When optimization resistance depends on protected evidence, absence of a
candidate-inaccessible check leaves it UNVERIFIED. Record expected cost and
actual qualification spend.

## Pre-seal stages

Qualification proves a benchmark measures something. It never asks
whether the target finds it hard, whether the expectation is right, or
whether the probe is passable without the work. Three stages answer
those, in this order, after qualification and before sealing:

    triage measurement → reference audit → repair
      → attack pass → repair-or-declare
      → recorded measurement → seal

Two measurement passes, not one: the cheap pass targets the expensive
audit, and the second produces the figure that seals. Where §Execution
tier and difficulty declares an expensive class, justify the second pass
for this run or declare its absence a gap. Each stage carries its own
allocation from the intake partition, and none of them renders a
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
rate — over a small set a rate carries no usable interval. Repair
before any identity exists; a defect the run declines to repair is a
declared gap naming the case and the class.

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

The attack taxonomy is a **dated** checklist and new classes append with
their date; freezing it freezes one year's attack surface as permanent
law. Repair `SUCCEEDED` findings within the remaining allocation,
cheapest first. Every hole left unrepaired is declared with the attack
that works. An undeclared hole is the failure; a declared one is a gap.

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

Read a status as ambiguous by construction. `both-pass` means the case
is saturated **or** its oracle is lenient; `both-fail` means the case is
genuinely hard **or** it is broken. Neither resolves to one reading
without evidence, and the reference audit is what decides the second.
Declare the instrument's resolution as `max(measured rerun spread, one
case)` and report no delta below it.

The record lands outside the sealed package, one entry per measurement
event, naming the benchmark identity it covers, the full candidate
identity per §Scoring, the date, the measured scope, and these figures.
Re-measuring an existing seal lands there and mints no successor.

## Scoring

The per-angle vector is the artifact and any scalar is derived. A
one-case-per-angle set is maximally diverse and therefore least
ranking-stable, and at one case per angle no mean repairs that — so
never headline a scalar, and never sum an aggregate in which one
saturated criterion pays for one that still discriminates.

Report `(score, cost)` pairs carrying host, price list, and date;
`pass^k` beside `pass@1` at the declared k for a nondeterministic case;
and the fraction of criteria decided by deterministic oracle versus by
judged oracle, which is recorded per criterion and never summed.

A score is a property of target × model × harness × benchmark. Bind
model id, effort level, host binding, and scaffold into the result
identity and declare that scores do not cross that boundary. Never
subtract a harness offset: the effect is candidate-dependent, so one
correction term is wrong for every candidate but one. Where a claim
spans a boundary, re-run every retained candidate and report the paired
per-case verdicts and the count of sign flips, never a rank correlation
over few candidates.

## Manifest and return

Seal the qualified result under the package's immutable manifest schema. Every
component reference and qualification verdict is fixed by identity; any
change requires a successor benchmark identity.
