---
name: compare-candidates
description: Independently compare identified candidates under common criteria, returning evidence and a supported preference without changing or adopting them.
disable-model-invocation: true
---

Establish [library context](../../references/library-context.md). Accept at least two stable candidate states, their purpose, common criteria or evaluation plan, evidence, constraints and an output location. Resolve ordinary missing criteria from the request and guidance, label assumptions and fix the comparison basis before dispatch.

Use `orchflows:orch-review` once with a comparer who made none of the candidates. Supply their identities, evaluation instructions, guidance and evidence. Preserve requested isolation, blinding and disclosure order. The comparer may create isolated evaluation artifacts, but edits or repairs no candidate.

Return that comparison: observations, requirement failures, tradeoffs, regressions, uncertainty and a supported preference, tie or insufficient evidence. Preserve conflicting evidence and unavailable checks as gaps. Adoption, changed criteria and further confirmation belong to the caller.
