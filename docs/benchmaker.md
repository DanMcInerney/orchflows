# BenchMaker

## Project scope

BenchMaker is admitted only as the repository's
[project-scoped custom workflow](../.orchflows/skills/benchmaker/SKILL.md).
One invocation accepts one declared target and intended outcome, one applicable
target pack, evidence access, an execution bound, and judgment permission. Its
[protocol](../.orchflows/skills/benchmaker/references/protocol.md) owns the
runtime contract.

## Construction

Before work, the workflow partitions the caller's single bound across
research, bench design, construction, and qualification; unused budget carries
forward and no stage receives a copy of the whole bound. It freezes and
delivers research first, and fails closed on a non-complete result,
`decision_gap`, or remainder.

The current repository has not admitted a T0 carrier that can lawfully supply
the frozen research synthesis through an existing
[`orch-bench`](../skills/workflows/orch-bench/SKILL.md) Require field. Without
one, BenchMaker returns partial evidence and a `decision_gap` instead of
calling outside that owner's contract. Admitting that carrier is queued scope;
the canonical bench owner is unchanged.

When a carrier is admitted, the bench owner alone selects the frozen task set
and generation brief. Construction materializes them exactly; target-pack
slicing cuts only disjoint execution and write scopes, never case selection.

## Qualification

An independent context qualifies the assembled suite at a fixed identity for
oracle validity, coverage, discrimination, reproducibility, redundancy,
provenance, and runtime bound. Deterministic failures cannot be offset.
Judgment enters only with caller permission or a recorded deterministic gap,
uses anchors, and remains secondary.

## Result

Success exposes only the runnable suite, execution instructions, coverage map,
research provenance, qualification verdicts and expected cost, and explicit
gaps. Failure preserves partial evidence and carries `decision_gap` and
remainder in those gaps.
