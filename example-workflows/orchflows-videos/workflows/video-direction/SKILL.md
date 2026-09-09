---
name: video-direction
description: Fix an original, evidence-informed script and storyboard before video production spends on rendering.
disable-model-invocation: true
---

Require: subject, audience, intent, 1-120s duration, brand/assets (none explicit),
cited research identity with dated observations/gaps, pinned renderer constraints
and dependencies, rights/providers, Git workspace, voice/citation constraints,
per-call bound and outside verifier. Carry these in Goal/Context; missing inputs
return partial evidence and named gaps, never accepted direction.

    tickets.py frame-open <run> --goal-file <direction-goal> --workflow video-direction

Read [creative handoff](../../references/creative.md) for the fixed production
record. Preserve the authoring-owner pointer in downstream Context.

**Make.** Use `orch-do` for an original script, illustrated panels/contact sheet
and editable layout source committed together. Carry all Require inputs;
distinguish provisional timing from measured audio and justify creative choices.
Review the actual assets/source at that commit, including target-display panel
and join inspection.

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

**Present.** Show reviewed panels/contact sheet, direction, commit, findings and
gaps before full rendering. Pause only for requested user approval, recording its
covered identity; otherwise continue authorized end-to-end work. Independent
review is not user approval.

Never: copy reference scripts or assets without rights; turn observed metrics
into causal promises; render the final video inside this journal (static storyboard
rendering is required); or call a script's acceptance
proof of rendered motion or heard audio quality.

Return: `tickets.py frame-close <run> <frame> --done <direction-verifier>` over
the accepted `git:` identity (absent until independently accepted), latest partial
direction commit identity, independent `findings:` lines and review identities, shared
standard pins, production handoff including illustrated assets and editable source,
presentation/approval evidence where applicable, and gaps (`[]` when empty). The caller passes
this fixed record to production; the verifier checks that document and review
evidence outside the children.
