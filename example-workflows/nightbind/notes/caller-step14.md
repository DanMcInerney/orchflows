# Caller capture-view QA

Bounded production QA, not independent final acceptance. The caller operated the supported in-app browser at 1280×720, DPR 1, Intel/D3D11. Only ordinary start/retry, ground clicks, Space, Tab, capture, Cancel and Pause controls were used. Public pauses supported tool deliberation. No scenario or injected state was used.

## Observed change

The initial right-hand planning panel obscured the keeper and its exact highlighted target when the keeper stood at x=11.66. Functional cancel/reopen/capture worked: the chosen real enemy disappeared, one ally appeared and charge was spent. See `evidence/caller/capture-panel-obstruction.png` and corresponding before/after JSON. This was a presentation defect rather than a capture-rule failure.

The maker added a clearly labeled Lantern view during the existing capture pause: the left renderer viewport centers on the keeper and fits the reach radius; the fixed choice panel occupies the right. Ordinary camera and pointer mapping return when planning closes.

## Corrected candidate and checks

Initial center inspection used development. Remaining checks used the compiled `step14-ui-df36d6bac38a` candidate in `evidence/stage14-build`, identified by `evidence/builds/step14-ui.json`. Its public build stamp says `development` because this intermediate compile did not set the final release ID; it is a production bundle without the development panel. An owned temporary preview served it on port 4192 and was stopped after this check. This avoided development reloads while other files were being edited.

| Observation | Evidence |
| --- | --- |
| Right-side keeper at x=11.66, exact target highlighted and visible beside the panel; 734px planning viewport. | `evidence/caller/lantern-view-right.png`, `.json` |
| Left-side keeper at x=-10.85, focused target and full reach visible. A touching enemy can naturally overlap the keeper, but the panel no longer covers them. | `evidence/caller/lantern-view-left.png`, `.json` |
| Cancel from right planning, first ground click at (420,355), reached x=-10.854, z=-0.317 in ordinary full-width mapping. | `evidence/caller/lantern-first-move.json` |
| Exclusive Cancel from left planning, inspect live arena, click (640,360), then reopen capture: same run reached x=-0.1166, z=-0.0034; no reset. Keeper and focused target remained visible. | `evidence/caller/lantern-view-center-isolated.png`, `.json` |
| Centered focus exposed `highlightedCaptureId: 10`, matching the actual candidate. Capturing it added Emberling and started recharge; ordinary auto-fire also killed another enemy before the following Pause. | `evidence/caller/lantern-capture-after-correction.json` |

The one-frame observation read immediately after Tab was stale while the screenshot already showed the highlight. Subsequent settled DOM reads matched. This is not evidence of a missing visual highlight.

## Interrupted checks and limits

A development reload interrupted the first camera-return attempt. During a later compiled check conducted alongside another worker's browser activity, Cancel plus a center click was followed by an unexpected fresh run. The caller did not observe the intervening modal, so the cause is unresolved. Source review found Pause → Start a new run as the explicit reset-to-title path; focus interference is a hypothesis, not a confirmed cause. The exclusive replay above did not reproduce a reset. A separate new-tab probe did **not** trigger pause, so it does not establish real blur handling. Preserve `evidence/caller/lantern-focus-probe.json` as this negative/limited observation.

For clean subsequent play/performance evidence, serialize browser activity as the library context already requires when interaction cannot be isolated. This check is not a full strategy run, final asset/camera acceptance, keyboard-hold test or performance benchmark. No material capture-camera defect remains reproduced in the corrected candidate; final integration must recheck the larger actual meshes in this view.
