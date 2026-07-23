---
name: benchmaker
description: Construct and qualify one runnable benchmark suite from a declared target and intended outcome.
role: none
---

Require: a request naming one target identity, one intended outcome, one
applicable target pack, evidence access, the execution bound, and whether
judged criteria are permitted.

Read [references/protocol.md](references/protocol.md) once at open.
Through `orch-spec`, first freeze the research run and, after bench design,
freeze the target-pack construction run.
Run the research spec through `orch-deliver`; after the target spec is
frozen, run it through the same delivery owner.
Give the exact target, intended outcome, frozen research synthesis, and
target-pack references to `orch-bench`; its result governs construction.

Never: improve or mutate the target; design criteria, oracles, anchors,
weights, aggregation, a loss check, or a generation brief outside the bench
owner; let a case builder qualify its own oracle.

Return: the runnable suite, execution instructions, coverage map, research
provenance, qualification verdicts and expected cost, and explicit gaps; on
failure, the same fields populated by partial evidence and gaps.
