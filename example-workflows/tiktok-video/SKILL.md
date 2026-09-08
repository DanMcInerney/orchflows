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

Carry promotional intent, including mixed education/marketing, into both helpers.
For example provenance, read the non-normative
[reference observations](references/marketing-reference.md).

**Research first.** Own two ordinary `orch-do` lanes under `orch-research`,
using the questions, source policy, bounds and evidence carriers in
[admission](references/admission.md). Run market/reference and renderer research
in parallel when useful. Assess prepared evidence for relevance and gaps;
refresh only decision-sensitive gaps.

    tickets.py do <run> --parent <frame> --standard orch-research
      --goal-file <market-question> --context-file <market-context> --bound <per-call-bound>

    tickets.py do <run> --parent <frame> --standard orch-research
      --goal-file <renderer-question> --context-file <renderer-context> --bound <per-call-bound>

Compare both actual packets, preserving dated observations, viewing evidence,
renderer comparison/constraints/pins, provenance and gaps without format conversion.

    tickets.py judge <run> --parent <frame> --standard orch-research
      --artifacts evidence:<market-id> --artifacts evidence:<renderer-id>
      --goal-file <coverage-goal> --context-file <research-context> --bound <per-call-bound>

Use the makers' exact research standard digest for independent coverage review.
It checks the original question, both lanes and their relevance/gap assessment.
Only blocker-free coverage of the required decisions permits an accepted
handoff; missing required evidence preserves partial packets and findings.
"Where the judge blocks, one repair `do` is handed the
`findings:` line verbatim, then one re-judge; two rounds is the bound."
A repair remains a single research lane. Pin one main renderer and dependency
identity before original artifact production, carrying the accepted packet
identities, coverage findings, license branch and decision into both helpers.

**Direction.** Invoke `video-direction` with the complete brief, actual research
identity and gaps, renderer constraints/pins, rights/provider limits, target
document directory, voice contract, numeric document budget, citation policy,
per-call bound and outside document verifier.

    tickets.py frame-open <run> --parent <frame> --goal-file <direction-goal> --workflow video-direction
      --context-file <direction-context>

Drive each body in its opened frame without reopening.
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
