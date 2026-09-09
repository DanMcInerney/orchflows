---
name: video-production
description: Render an independently accepted video direction into a fixed project with independent audiovisual review.
disable-model-invocation: true
---

Require: an independently accepted script/storyboard document identity and its
findings identity; brief with duration, audience, message and brand; pinned
renderer decision; assets, rights and provider constraints; git workspace;
authoring-owner pointer; per-call bound. Inputs are semantic documents, not a
particular creative workflow's file layout.

    tickets.py frame-open <run> --goal-file <production-goal> --workflow video-production
      --context-file <production-context>

Carry the accepted document, findings, brief, renderer decision, constraints and
authoring-owner into governed Context. Read [review](../../references/review.md)
when preparing the production and review goals and the outside probe command.
Resolve its delivery settings before making; unresolved rights remain gaps and
permit only the authorized evaluation scope.

Make through `orch-do`, applying the rendering method inside the isolated call:

    tickets.py do <run> --parent <frame> --standard orch-code --standard video-quality --skill render-video
      --goal-file <render-goal> --context-file <production-context> --workspace <workspace> --isolation required --bound <bound>

The goal requires the rendered project, playable review assets and evidence for
the accepted direction. Land the candidate through the emitted ticket's ordinary
landing door. Invoke `review-delivery` in this existing production frame
over the fixed git output, identical orch-code and video-quality pins,
accepted direction, evidence, workspace, bound and outside probe. The production
stage owns its selected rounds. Repairs retain the rendering method and pins;
scoped verification reads listed repairs at their fixed joined identity. Unavailable listening is an unresolved
criterion, not a repairable render defect: preserve an audition and independent
transcript/signal/timing evidence, request a listening-capable reviewer or human
verdict through the existing user-only question route, and return partial evidence
when that input is unavailable. Do not spend repair rounds fabricating hearing.

Close on a command run outside every child; never on a
child's own claim.
Use the foundation's output probe against the landed video, recording absent or
corrupt failure and actual-output readings. A zero technical probe does not erase
unresolved independent findings. If blocked or exhausted, preserve the last fixed
candidate and findings with explicit gaps under the existing partial-result law.

Never: rewrite accepted creative direction to hide production defects; substitute
screenshots or JSON for audiovisual judgment; imply paid services, cloning or
social publication; claim full acceptance with unresolved hearing or rights.

Return: `tickets.py frame-close <run> <frame> --done <output-probe>`;
fixed `artifact: git:<tip>`, independent `findings:` line, playback/capture/audition
paths and hashes, outside probe commands and observed exits, runtime identities
and shared standard pins, and gaps (`[]` when none). Failed production returns
its fixed partial artifact and gathered evidence without a success claim.
