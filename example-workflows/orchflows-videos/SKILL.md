---
name: orchflows-videos
description: Create original 1–120 second Orchflows marketing videos through cited research, accepted direction and independent playback review.
disable-model-invocation: true
---

Require: Orchflows marketing subject, audience, intent, duration in 1–120 seconds, brand and assets
(explicit none allowed), git workspace, provider and license constraints,
authoring-owner pointer and per-call bound. Carry the brief in Goal and all
constraints and the owner pointer in governed downstream Context.

Resolve `rounds` through `docs/review-policy.md`; forward to this root and independent stages.

    tickets.py frame-open <run> --goal-file <video-goal> --workflow orchflows-videos --review-rounds <rounds>
      --context-file <video-context>

Read [admission](references/admission.md) for inputs, installation and verifiers;
[inventory](references/inventory.md) identifies boundaries and qualified resources.

The external short-videos standard must resolve before work; package-only copying
is insufficient. Both helpers share orch-code -> short-videos ->
orchflows-marketing-videos pins.
Read [research](references/research.md) for dated evidence and gaps.

**Research first.** Own two ordinary `orch-do` lanes under `orch-research`,
using the questions, source policy, bounds and evidence carriers in
[admission](references/admission.md). Assess prepared market/reference and renderer evidence; refresh decision-sensitive gaps.

    tickets.py do <run> --parent <frame> --standard orch-research
      --goal-file <market-question> --context-file <market-context> --bound <per-call-bound>

    tickets.py do <run> --parent <frame> --standard orch-research
      --goal-file <renderer-question> --context-file <renderer-context> --bound <per-call-bound>

Compare both actual packets, preserving dated observations, viewing evidence,
renderer comparison/constraints/pins, provenance and gaps without format conversion.

    tickets.py judge <run> --parent <frame> --standard orch-research
      --review-independent "research coverage before production"
      --artifacts evidence:<market-id> --artifacts evidence:<renderer-id>
      --goal-file <coverage-goal> --context-file <research-context> --bound <per-call-bound>

Use the makers' exact research standard digest for independent coverage review.
It checks the original question, both lanes and their relevance/gap assessment.
Only blocker-free coverage of the required decisions permits an accepted
handoff; missing required evidence preserves partial packets and findings.
Missing coverage names required acquisition; new research stays independent.
A repair remains a single research lane. Pin one main renderer and dependency
identity before original artifact production, carrying the accepted packet
identities, coverage findings, license branch and decision into both helpers.

**Direction.** Invoke `video-direction` with the complete brief, actual research
identity and gaps, renderer constraints/pins, rights/provider limits, Git workspace, brief voice/citation constraints,
per-call bound and outside direction verifier.

    tickets.py frame-open <run> --parent <frame> --goal-file <direction-goal> --workflow video-direction
      --review-new-work "independent direction acceptance" --review-rounds <rounds>
      --context-file <direction-context>

Drive each opened body.
Only its independently accepted direction Git commit and actual findings feed
`video-production`, with the brief, renderer decision, assets/rights/provider
constraints, git workspace, owner pointer and per-call bound.

    tickets.py frame-open <run> --parent <frame> --goal-file <production-goal> --workflow video-production
      --review-new-work "independent production acceptance" --review-rounds <rounds>
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
