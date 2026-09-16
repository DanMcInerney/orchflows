---
name: orch-dynamic-workflow
description: Use when no more specific workflow or skill fits the request. Coordinate work and one final independent review.
disable-model-invocation: false
---

State the intended result and its checks; investigate missing information. Select relevant [guidance](../../docs/architecture.md#guidance-selection) and resolve dependencies once. Carry the caller's [model and effort choices](../../docs/architecture.md#model-and-effort) through each assignment. Make an already-clear change directly when those settings permit; use [orch-work](../orch-work/SKILL.md) for investigation, shared prerequisites and independent deliverables, giving each maker clear ownership and running them concurrently once their inputs are ready.

Join and verify the result. Use [orch-review](../orch-review/SKILL.md) once; let the reviewer return its findings and finish before repairs. Make one repair pass, giving each shared fix one owner with the current joined result and needed inputs. Continue makers whose context helps when they can honor the fixer's settings, make clear fixes directly when permitted, or use orch-work. The pass includes repairs and their checks, without another review. Verify the revision and report what was made, checked, and remains unresolved.
