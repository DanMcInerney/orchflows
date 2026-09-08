---
name: tiktok-video
description: Create an original 1–120 second portrait video through brief-specific research, accepted direction and audiovisual review.
disable-model-invocation: true
---

Require: subject, audience, intent, duration in 1–120 seconds, brand and assets
(explicit none allowed), git workspace, provider and license constraints,
authoring-owner pointer and per-call bound. Carry the brief in Goal and all
constraints and the owner pointer in governed downstream Context.

    tickets.py frame-open <run> --goal-file <video-goal> --workflow tiktok-video
      --context-file <video-context>

Read [admission](references/admission.md) for required input preparation,
verifiers and partial-result handling; [inventory](references/inventory.md)
identifies the package boundaries and qualified resources.

**Research first.** Invoke `super-research` for one bounded brief-specific
question: which market/reference observations inform this subject, audience and
intent, and does current Remotion-versus-HyperFrames evidence change the renderer
choice? Supply named live primary sources, window where applicable, frozen as_of
at or after reads and a hard per-step cap. Ask for actual available playback
inspection, citations, dates, exposed metrics with sampling limits, contradictions
and gaps. Reuse applicable prepared evidence explicitly with provenance; refresh
only decision-sensitive gaps. This public call resolves its own standards.

    tickets.py frame-open <run> --parent <frame> --goal-file <research-question> --workflow super-research

Consume the actual dossier identity and coverage findings, never a planned path.
Missing required verification returns partial research and prevents an accepted
handoff. Pin one main renderer and dependency identity before original artifact
production, carrying the evidence, license branch and decision into both helpers.

**Direction.** Invoke `video-direction` with the complete brief, actual research
identity and gaps, renderer constraints/pins, rights/provider limits, target
document directory, voice contract, numeric document budget, citation policy,
per-call bound and outside document verifier. At 1s reduce to one readable idea,
explicitly deciding voice/CTA omission; at 120s budget explanation and proof.

    tickets.py frame-open <run> --parent <frame> --goal-file <direction-goal> --workflow video-direction
      --context-file <direction-context>

Drive each invoked body in its opened frame, without opening its entry twice.
Only its independently accepted document and actual findings feed
`video-production`, with the brief, renderer decision, assets/rights/provider
constraints, git workspace, owner pointer and per-call bound.

    tickets.py frame-open <run> --parent <frame> --goal-file <production-goal> --workflow video-production
      --context-file <production-context>

Preserve partial returns and unresolved listening/license findings; a technical
probe does not establish audiovisual acceptance.

Never: invent accepted identities, rank efficacy from exposed counts, force
variants or cut quotas, copy unlicensed expression, authorize paid providers or
publication implicitly, or claim admission from static checking.

Return: `tickets.py frame-close <run> <frame> --done <outside-output-probe>`;
research and direction identities, fixed production artifact and independent
findings, renderer/package/standard pins, preview/capture/audition evidence,
outside probe exits and gaps (`[]` when none), preserving partial results.
