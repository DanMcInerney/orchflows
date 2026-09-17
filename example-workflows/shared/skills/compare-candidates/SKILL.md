---
name: compare-candidates
description: Independently compare identified candidates under common criteria, returning evidence and a supported preference without changing or adopting them.
disable-model-invocation: true
---

Establish [library context](../../references/library-context.md). Accept at least two candidate states, their purpose, common criteria or evaluation plan, relevant evidence, constraints and an output location. Resolve ordinary missing criteria from the request and guidance, label assumptions and fix the comparison basis before dispatch. Keep candidates stable and identifiable; unavailable candidates or evidence remain gaps, not losing scores.

Default to one fresh reviewer and a one-child ceiling. A caller may request several reviewers within an explicit allocation for this one round; assign comparable scopes with coverage of the overall comparison. Preserve any caller-required isolation, blinding or disclosure order. Do not expose one independent judge's verdict to another before it finishes.

Use `orchflows:orch-review` for each assignment with the actual states, unchanged criteria, reproduction/evaluation instructions, guidance and evidence locations. Reviewers must have made none of the candidates. They perform the comparison, preserve observations and report requirement failures, tradeoffs, regressions, uncertainty and a preference only where supported. They may create isolated evaluation artifacts but must not modify candidates, make repairs or delegate.

Gather every outcome and return candidate identities, the comparison basis, evidence, coverage and gaps, and a supported preference, tie, disagreement or insufficient evidence. Preserve conflicting judgments rather than manufacture agreement. Adoption, additional confirmation, evaluation changes and another round belong to the caller; this component performs none of them.
