# BenchMaker protocol

These stages are exhaustive: evidence acquisition, evaluation-design
invocation, materialization, qualification, and manifest sealing.

## Intake and bound

Keep the target identity opaque. Carry its intended observable outcome,
evidence access, and cost limits without defining its evaluation boundary. The
evaluation-design owner records an unobservable outcome or unavailable oracle
as an explicit gap.

Before work, partition one caller bound across evidence, design,
materialization, and qualification. Allocations are nonnegative and their
total cannot exceed the caller bound; unused allocation from a completed stage
may carry forward. Never copy the caller bound into a stage, internal spec,
delivery, or lane.

Fix the evidence identities, source policy, judgment permission, applicable
pack references, benchmark write scope, excluded actions, protected-evidence
policy, and contracted return fields. Every internal spec selects one
applicable pack; exactly one pack per internal spec.

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

## Manifest and return

Seal the qualified result under the package's immutable manifest schema. Every
component reference and qualification verdict is fixed by identity; any
change requires a successor benchmark identity.
