---
name: orch-bench
description: Derive the frozen bench — criteria, task set, generation brief — for evolving any artifact. Use before evolve, panel, or tournament runs.
role: none
---

Require: the artifact or candidate set, the goal as stated, and — when
the artifact's class matches a pack — that pack's craft, lens, and
oracle references; best practices come from the pack, never invented
here.

Design mode. Enumerate the criteria that discriminate on the goal's
axes — inspect the candidates to find which dimensions are in play,
then state each criterion so any candidate of the class can be scored.
Per criterion, per [contracts/verdict.md](../../../contracts/verdict.md):
runnable qualities get executed oracles; the rest get rubric anchors
demanding quoted evidence. When the artifact's quality lives in its
behavior — a skill, a prompt, a program judged by what it produces —
the bench includes a frozen task set of bounded
[work items](../../../contracts/work-item.md) cut to cover the goal's
axes; criteria then score each candidate's outputs over the task set,
never its text alone. Weight the criteria and declare the aggregation
method before any scoring. Include one loss check: what a variant lost
that the incumbent had, outside the other criteria's letter. Emit the
generation brief: dimensions to vary, constraints to hold verbatim,
the pack's executor binding when one matches, and where the
incumbent's score card is weakest. When the goal's axes are genuinely
undecidable, settle those decisions through `orch-elicit`; otherwise
infer and state assumptions. Freeze before any scoring.

Revise mode, between generations only. Rewrite exactly the criteria
the evidence indicts — a panel's disagreement register (ambiguity) or
a criterion with no score spread (discriminates nothing); version the
bench and require retained candidates re-scored under it.

Never: score or run a candidate; state a criterion in terms that name
or favor one; revise toward the current winner; prescribe procedure
where an outcome criterion suffices.

Return: the versioned bench — criteria with oracles, classes, anchors,
weights, aggregation, loss check, task set (`[]` when the artifact is
judged directly) — the generation brief, stated assumptions, and in
revise mode the indicting evidence per change.
