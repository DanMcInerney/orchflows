# Benchmaker protocol

One invocation chains one research run to one construction run. Each run has
exactly one pack and draws from one partitioned caller bound.

## Intake boundary

Record the target identity, intended outcome, target pack, evidence access,
execution bound, and judgment permission. Make the observable evaluation
boundary explicit: target population; admissible inputs, states, and outputs;
expected outcomes; exclusions; and cost limits. Stop for a material missing
choice; do not infer a different target or outcome.

Before any work, partition the single caller bound into nonnegative research,
bench-design, construction, and qualification allocations whose total cannot
exceed it. A stage may consume only its allocation plus unused budget carried
forward from completed earlier stages. Never copy the caller bound into a run,
lane, design call, or qualification.

The evidence set must name an admitted T0 carrier whose contract can supply the
frozen research synthesis through an existing orch-bench Require field. If it
does not, return the result fields as partial evidence with that missing
carrier as a `decision_gap`; do no work.

## Research delivery

Freeze one research-pack delivery stamped `orch-research-pack`. Its disjoint,
bounded independent lanes cover prior art, real failure modes, edge cases,
authoritative semantics, and oracle options; the pack controls their count and
method within the research allocation. The synthesis carries a claim-to-source
trace, disagreement register, and gaps.

Public cases are provenance-bearing development seeds, not automatically
authoritative or hidden. Preserve source and license constraints for copied
material. Freeze the synthesis and trace as one frozen result identity before
design; a later evidence gap becomes explicit follow-up scope.

If delivery is non-complete, returns a `decision_gap`, or leaves uncovered
remainder, preserve its evidence and return partial result fields; do not enter
bench design.

## Bench design

Through the admitted carrier, pass the evaluation boundary, intended outcome,
frozen research identity, and the target pack's craft, lens, and oracle
references to [`orch-bench`](../../../../skills/workflows/orch-bench/SKILL.md).
The carrier, not this workflow, binds the synthesis to the existing Require
field. The bench owner selects the task set and returns the generation brief.

Accept only a versioned, frozen bench with every contracted field verified
against the carrier and bench contracts. An invalid identity, missing field, or
UNVERIFIED design returns partial result fields with the defect as a
`decision_gap` or remainder; do not freeze construction.

## Case construction

Freeze one target-pack construction delivery under the stamped target pack,
with the frozen research synthesis and frozen bench as its evidence. The
construction spec requires exact materialization of the frozen task set under
the exact generation brief. Pack slicing cuts only disjoint execution and
write scopes among those cases and preserves provenance per case; it never
selects, adds, removes, ranks, rewrites, or substitutes a case.

Any requested selection change returns partial construction evidence and
remainder to the bench owner. Only that owner may version the task set before a
new construction spec is frozen.

## Qualification

Qualify the assembled suite at a fixed result identity in an independent
context per
[`rules/verification.md` section 10](../../../../rules/verification.md).
Case authors never qualify their own authored oracle as sufficient evidence.
Check oracle validity, coverage, discrimination, reproducibility, redundancy,
provenance, and runtime bound; qualification verdicts include expected cost.

Prefer deterministic oracles wherever the intended quality is executable.
Deterministic failure is non-compensable. Add a judged criterion only when the
caller granted judgment permission or a recorded deterministic-coverage gap
requires it; carry anchors, keep it secondary, and never use it to offset a
deterministic failure. No weight, aggregation result, judged score, or
secondary criterion can offset it.

## Return

Success returns only the runnable suite, execution instructions, coverage map,
research provenance, qualification verdicts and expected cost, and explicit
gaps. Failure preserves partial evidence in those fields and identifies every
incomplete element as an explicit gap.
