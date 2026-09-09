---
name: video-production
description: Render an independently accepted video direction into a fixed project with independent audiovisual review.
disable-model-invocation: true
---

Require: independently accepted direction Git commit containing script,
illustrated panels/contact sheet and editable source; findings identity; brief
(duration, audience, intent, message, brand); pinned renderer; assets/rights/providers;
Git workspace; authoring-owner pointer; per-call bound. Accept semantic documents,
not a prescribed file layout.

    tickets.py frame-open <run> --goal-file <production-goal> --workflow video-production
      --context-file <production-context>

Carry Require inputs into governed Context. Read [review](../../references/review.md)
for production/review goals and the outside probe. Resolve delivery settings;
unresolved rights permit only authorized evaluation and remain gaps.

Keep this helper in the orchflows-videos owner scope. Making, review and repairs
share direction's ordered orch-code, short-videos, orchflows-marketing-videos pins.

Reuse direction's layout components in animation, preserving typography,
cards and relationships. Check significant design changes against accepted direction
within existing review allowance and requested user approval.

Make through `orch-do`, applying the rendering method inside the isolated call:

    tickets.py do <run> --parent <frame> --standard orchflows-marketing-videos --skill render-video
      --goal-file <render-goal> --context-file <production-context> --workspace <workspace> --workspace-adapter git --isolation required --bound <bound>

The goal requires the rendered project, playable review assets and evidence for
the accepted direction. Land the candidate through the emitted ticket's ordinary
landing door. Invoke `review-delivery` in this existing production frame
over the fixed git output, identical orch-code, short-videos and orchflows-marketing-videos pins,
accepted direction, evidence, workspace, bound, outside probe, `context-file`
production-context, `workspace-adapter` git, `isolation` required and
`repair-skill` render-video. The production stage owns its selected rounds;
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
