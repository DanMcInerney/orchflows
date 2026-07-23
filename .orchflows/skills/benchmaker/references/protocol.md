# Benchmaker protocol

One invocation chains one research run to one construction run. Each run has
exactly one pack and draws from the caller's execution bound.

## Intake boundary

Record the target identity, intended outcome, target pack, evidence access,
execution bound, and judgment permission. Make the observable evaluation
boundary explicit: target population; admissible inputs, states, and outputs;
expected outcomes; exclusions; and cost limits. Stop for a material missing
choice; do not infer a different target or outcome.

## Research delivery

Freeze one research-pack delivery stamped `orch-research-pack`. Its disjoint,
bounded independent lanes cover prior art, real failure modes, edge cases,
authoritative semantics, and oracle options; the pack controls their count and
method within the bound. The synthesis carries a claim-to-source trace,
disagreement register, and gaps.

Public cases are provenance-bearing development seeds, not automatically
authoritative or hidden. Preserve source and license constraints for copied
material. Freeze the synthesis and trace as one frozen result identity before
design; a later evidence gap becomes explicit follow-up scope.

## Bench design

Pass the evaluation boundary, intended outcome, frozen research identity, and
the target pack's craft, lens, and oracle references to
[`orch-bench`](../../../../skills/workflows/orch-bench/SKILL.md). Accept its
versioned bench without amendment; case construction consumes that identity.

## Case construction

Freeze one target-pack construction delivery under the stamped target pack,
with the frozen research synthesis and frozen bench as its evidence. The
pack's slicing cuts disjoint case materialization and preserves provenance per
case. Suite selection maximizes valid coverage and discrimination inside the
runtime bound, not raw difficulty or case count.

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
deterministic failure.

## Return

Success returns only the runnable suite, execution instructions, coverage map,
research provenance, qualification verdicts and expected cost, and explicit
gaps. Failure preserves partial evidence in those fields and identifies every
incomplete element as an explicit gap.
