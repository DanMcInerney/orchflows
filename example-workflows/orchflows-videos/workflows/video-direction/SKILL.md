---
name: video-direction
description: Fix an original, evidence-informed script and storyboard before video production spends on rendering.
disable-model-invocation: true
---

Require: subject, audience, intent, duration in 1-120 seconds, brand and assets
(explicit none allowed), cited research artifact identity with dated observations
and gaps, selected renderer constraints and dependency identity, rights/provider
limits, Git workspace, brief voice and citation constraints, per-call bound and outside direction verifier. Carry these
semantic inputs in Goal and Context; missing required inputs return partial
evidence and named gaps without making an accepted direction.

    tickets.py frame-open <run> --goal-file <direction-goal> --workflow video-direction

This private journal fixes the message independently before orchflows-videos hands
it to production. [Creative handoff](../../references/creative.md) describes
the document; quality belongs to the shared video standard. Preserve the supplied
authoring-owner pointer in every governed downstream Context.

**Make.** Use `orch-do` for one original script/storyboard answering the brief's
throughline. Transfer all Require inputs through the carriers above. Separate
provisional timing from measured audio, and explain which observations informed
the choices for this subject and audience.

    tickets.py do <run> --parent <frame> --standard orchflows-marketing-videos --goal-file <script-goal>
      --context-file <direction-context> --workspace <workspace>
      --workspace-adapter git --isolation required --bound <per-call-bound>

**Review.** Invoke `review-delivery` in this existing direction frame
with the landed direction commit, brief, evidence, original quality goal, identical
orch-code, short-videos and orchflows-marketing-videos pins, `workspace` git workspace,
`workspace-adapter` git, `isolation` required, `context-file` direction-context, per-call
bound and outside verifier. The direction stage owns its selected rounds.
Repairs preserve the brief, pins and evidence and address the fixed findings.
An exhausted review or unavailable required evidence returns the latest direction commit
as partial, independent findings and gaps; no accepted identity is inferred.

Never: copy reference scripts or assets without rights; turn observed metrics
into causal promises; render inside this journal; or call a script's acceptance
proof of rendered motion or heard audio quality.

Return: `tickets.py frame-close <run> <frame> --done <direction-verifier>` over
the accepted `git:` identity (absent until independently accepted), latest partial
direction commit identity, independent `findings:` lines and review identities, shared
standard pins, production handoff and gaps (`[]` when empty). The caller passes
this fixed record to production; the verifier checks that document and review
evidence outside the children.
