---
name: compare-candidates
description: Independently compare stable candidates under common criteria; return evidence and a preference without edits or adoption.
disable-model-invocation: true
---

Establish [library context](../../references/library-context.md). Accept at least two stable candidate states, purpose, common criteria/evaluation plan, evidence, constraints and output location. Resolve ordinary missing criteria from request/guidance; label assumptions and fix the comparison basis before dispatch.

Use `orchflows:orch-review` once with a comparer who made no candidate. Supply identities, evaluation instructions, guidance and evidence. Preserve requested isolation, blinding and disclosure order. Permit isolated evaluation artifacts, never candidate edits or repairs.

Return observations, requirement failures, tradeoffs, regressions, uncertainty and supported preference, tie or insufficient evidence. Preserve conflicting evidence and unavailable checks as gaps. Adoption, changed criteria and further confirmation remain with the caller.
