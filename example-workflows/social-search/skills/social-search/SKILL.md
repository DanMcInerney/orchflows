---
name: social-search
description: Collect what people say across public communities and the web in parallel, then return one independently written, cited brief.
disable-model-invocation: true
---

Establish [library context](../../references/library-context.md).

Split the caller's sources into a few collection assignments that can run at once. Keep sources that share discussions together, and give each original that several sources discuss one owner. Reuse supplied evidence that already covers part of the scope. Divide the caller's bounds, keeping time for the final review.

Launch every assignment through `orchflows:orch-work` before gathering any. Give each collector the question, window, sources, bounds, its own directory for `results.md`, and the paths of the [evidence contract](../../references/evidence.md), [public access](../../references/access.md) and its collection guidance.

At the handoff deadline, stop unfinished collectors. Record missing or failed assignments as gaps, and keep useful partial evidence.

Use `orchflows:orch-review` once. The assessor collected nothing. Give it the question, the caller's output requirements, every handoff and gap, the evidence contract and the assessment guidance. It checks claims against the saved support and writes the cited brief from that evidence alone, to the caller's requirements. The brief is about the topic: its gaps name what it could not cover, not how the research ran.

Return the assessor's brief unchanged, with its coverage and gaps.
