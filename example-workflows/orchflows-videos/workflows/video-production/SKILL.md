---
name: video-production
description: Render an independently accepted video direction into a fixed project with independent audiovisual review.
disable-model-invocation: true
---

Require: an independently accepted script/storyboard Git commit identity and its
findings identity; brief with duration, audience, intent, message and brand; pinned
renderer decision; assets, rights and provider constraints; git workspace;
authoring-owner pointer; per-call bound. Inputs are semantic documents, not a
particular creative workflow's file layout.

    tickets.py frame-open <run> --goal-file <production-goal> --workflow video-production
      --context-file <production-context>

Carry the accepted direction commit, findings, brief, renderer decision, constraints and
authoring-owner into governed Context. Read [review](../../references/review.md)
when preparing the production and review goals and the outside probe command.
Resolve its delivery settings before making; unresolved rights remain gaps and
permit only the authorized evaluation scope.

Keep this helper in the orchflows-videos owner scope. Making, review and repairs
share direction's ordered orch-code, short-videos, orchflows-marketing-videos pins.

Make through `orch-do`, applying the rendering method inside the isolated call:

    tickets.py do <run> --parent <frame> --standard orchflows-marketing-videos --skill render-video
      --goal-file <render-goal> --context-file <production-context> --workspace <workspace> --workspace-adapter git --isolation required --bound <bound>

Land the candidate, then judge its fixed git output through `orch-judge` with
the identical ordered standard digests and package identity; a pin mismatch
requires fresh admission.

    tickets.py judge <run> --parent <frame> --standard orchflows-marketing-videos
      --goal-file <review-goal> --context-file <production-context> --artifacts <git-artifact> --workspace <workspace> --workspace-adapter git --isolation required --bound <bound>

Where the judge blocks, one repair `do` is handed the
`findings:` line verbatim, then one re-judge; two rounds is the bound.
Repairs use the making call and pins on the latest fixed candidate; each
re-judge reads that repair's fixed identity. Unavailable listening is an unresolved
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
