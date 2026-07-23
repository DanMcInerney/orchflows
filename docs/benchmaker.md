# BenchMaker workflow design

> **Status: implementation proposal.** Nothing here is installed or callable.

## Proposition

BenchMaker is a capability-discovering benchmark factory governed by stable
invariants; bounded self-improvement snapshots are its primary lifecycle. It
constructs deterministic or judged benchmarks for any artifact class, then
uses the same lifecycle to improve both those benchmarks and BenchMaker's own
benchmark-making policy.

The core specifies outcomes, trust boundaries, and evidence. It does not
prescribe a transport, lane count, model, search algorithm, storage layout, or
implementation sequence. A stronger model or adapter may replace any current
method without changing the core when the invariants still hold.

This direction follows evidence, not a claim that recursion alone improves a
system. Weco reports a run evaluated with fixed cost, private selection,
heterogeneous tasks, and held-out transfer, and distinguishes improving a
system from improving its ability to improve
([AIDE²](https://www.weco.ai/blog/first-evidence-of-recursive-self-improvement),
[RSI levels](https://www.weco.ai/blog/4-levels-of-recursive-self-improvement)).

## Minimal interface

The callable interface freezes only what must remain comparable. Intake names
the exact target and outcome, granted evidence, applicable pack, incumbent
identities, nominee source or immutable nominee identities, resource and
exposure bound, done-check, protected-evidence identity, and any previously
admitted activation-policy identity. It prescribes no candidate width.
BenchMaker returns immutable benchmark artifacts, certification and lineage
evidence, canonical verdicts, the bound spent, and exactly one outcome: a
nomination, verified no-change, or an inconclusive canonical terminal state.

[`orch-bench`](../skills/workflows/orch-bench/SKILL.md) remains the owner of
criteria, oracles, anchors, task selection, aggregation, loss checks, and the
generation brief. [`orch-evolve`](../skills/workflows/orch-evolve/SKILL.md)
remains the manual, external owner of candidate generation and its
campaign-internal promotion. BenchMaker accepts immutable nominees and owns
only benchmark lifecycle and certification. An automatic handoff requires a
separately admitted change to that owner.

Admission must map required data to existing
[`spec`](../contracts/spec.md),
[`work-item`](../contracts/work-item.md),
[`verdict`](../contracts/verdict.md), and
[`worklog`](../contracts/worklog.md) carriers. Any uncovered shape requires a
separate supersession of the waist. One existing pack governs each target.

Instruction and policy surface is a cost, not a target. Deleting prescription
is an improvement candidate only when protected selection and transfer quality
are at least preserved under the same bound. Raw prompt length never decides
certification.

## Bounded recursive loop

One invocation is one bounded campaign snapshot governed by
[`rules/loops.md`](../rules/loops.md): a frozen goal, external done-check, and
bound. It may construct or refresh a benchmark while retaining its predecessor;
request external candidate generation or accept exact immutable nominees;
evaluate nominees under one frozen budget; certify a nomination or verified
no-change; record all evidence and spent bounds; and return. Uncertainty,
exhaustion, stall, or failure returns the matching inconclusive terminal state.
Continual upkeep exists only when a caller or host schedules another bounded
snapshot. The current model and adapters choose the mechanism; no iteration
plan is prescribed.

A benchmark successor improves only when it better discriminates intended
quality without losing validity, leakage resistance, sentinels, or transfer. A
BenchMaker-policy successor improves only when protected downstream outcomes,
independently admitted anchors or audits, or equivalent external semantic
evidence that it cannot amend show better benchmark decisions beyond its
development cases. A better-improver test runs predecessor and successor from
the same frozen start and problem distribution, under one external outcome
evaluator and equal total budget. Uncertainty cannot pass. A fully evaluated
set with no qualifying nominee yields verified no-change; rejection remains
evidence.

## Anti-reward-hacking invariants

Certification evidence is protected from the process it selects. Development
evidence is visible and may guide revisions. Protected selection evidence
chooses between candidates. Protected transfer evidence tests new tasks or
task families beyond those optimized. SpecBench's visible-versus-held-out gaps
show why visible success is not sufficient, and why adding visible tests alone
does not reliably close the gap
([SpecBench](https://www.weco.ai/blog/specbench)).

The improver and every candidate cannot read, choose, rewrite, or retire
protected items, nor receive item-level protected feedback. Protected selection
and transfer results are terminal for the submitted immutable candidate and
never re-enter development. A protected principal freezes and applies the
evidence. Any policy-permitted disclosure retires or versions what it covers.
Every query counts against a lifetime query-and-exposure policy; resubmission
never resets either ledger.

Every successor is tested against immutable known-bad mutants and stable
sentinels retained from its predecessor. It cannot win by removing a blocker.
Benchmark quality covers discrimination, construct validity, leakage, and
transfer. Before observing results, the evaluation policy declares the target
population and contrast, uncertainty treatment, and repeated-look policy;
freezing an arbitrary test does not establish validity. Deterministic scoring
is not deterministic model behavior, and retries are predeclared and charged,
never run until green. Uncertainty remains `UNVERIFIED`.

These invariants apply equally when the candidate is the benchmark factory,
its policy, its scorer, or a target benchmark. The predecessor evaluates the
successor; a candidate never changes its evaluator in the same epoch. A model,
tool, or evaluator change starts a new capability epoch. Cross-epoch scores
require bridge evidence. Capability advances invite deletion-first challengers
but never inherit scores.

## Activation and recovery

Every passing candidate is an inert nomination under current
[`rules/improvement.md`](../rules/improvement.md). Self-edits may be generated
and evaluated automatically, but only a human-reviewed merge activates them;
only a later matching run verifies the change.

Automatic activation is a future option, not present permission. It requires a
prior human-reviewed change to the owning cross-cutting rule, never a caller's
intake choice. Its exact policy identity is frozen for the epoch. A protected
principal may then act on the exact immutable nominee only after every frozen
certification check passes and within a bounded blast radius. Activation and a
complete durable receipt binding candidate, evaluator, evidence, budgets,
policy, and resulting state are one atomic transaction. An incomplete
transaction remains or reverts inert.

No candidate approves itself, amends its activation policy or evaluator in the
same epoch, classifies its own blast radius, or resets a bound. A missing,
mismatched, replayed, or partial protected receipt yields `UNVERIFIED`.
Post-activation sentinel failure triggers rollback; rollback must be confirmed
before further activation. Failed recovery closes safely. Void evidence is
never reused.

## Admission boundary

BenchMaker should first be admitted as one project-scoped custom workflow
through [`orch-build`](../skills/workflows/orch-build/SKILL.md). The proof must
show useful benchmark construction, protected selection and transfer,
externally grounded self-improvement, verified no-change behavior, and recovery
before canonical scope is considered.

Host adapters may realize isolation, protected storage, scheduling, and atomic
activation by any mechanism that satisfies the invariants. A host unable to
attest protected read and egress isolation, evidence integrity, and budget
accounting may still produce development benchmarks, but cannot certify a
nomination. Scope and ownership remain governed by the
[`architecture`](../ARCHITECTURE.md),
[`verification`](../rules/verification.md),
[`visibility`](../rules/visibility.md), and
[`delegation`](../rules/delegation.md) owners.
