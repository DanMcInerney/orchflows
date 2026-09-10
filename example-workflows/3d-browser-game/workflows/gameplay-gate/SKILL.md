---
name: gameplay-gate
description: Judge fixed core gameplay with independent play, evidence floors, and bounded repair successors.
disable-model-invocation: true
---

Require: fixed I2 `artifact:` identity, frozen traceability and [core rubric](../../references/core-rubric.md),
complete core capture/performance matrix, QA result, at least two
maker-independent play contexts, parent frame journal, and package digest.

Freeze every input and judge the I2 identity independently:

    tickets.py judge <run> --parent <frame> --standard threejs-browser-game
      --standard browser-game-interface --standard browser-game-playtest
      --artifacts git:<i2-commit> --goal-file <gate-goal> --context-file <context-file>
      --workspace <workspace> --workspace-adapter git --isolation required --bound <bound>

Carry the frozen goal, evidence and outside probe. Repair accepted blockers
through `orch-do` under the same pins and Context, then verify the affected
QA and play at the resulting fixed revision.

The verdict checks production boot, focus and ordinary controls, fundamental
loop, central mechanics and reachable states, readable timing and feedback,
challenge and counterplay, meaningful choices, pacing, prompt traceability,
complete core captures, and qualified representative performance. Graybox
assets pass the art bar when they support fair play and legibility; final
polish belongs to the whole-game gate. Every dimension scores 0–4 and every
complaint has an ID, seam, cause, evidence, kind, and expected improvement.

Repairs name accepted complaints, causal seams and regression checks. Retain
unaffected smoke coverage. Continue required repair while scope, evidence and
bound permit it; an unavailable capability or bound returns the best fixed
revision, complaint ledger and exact resume state. Redesign names invalidated
descendants.

Never lower a critical floor, let a maker judge its own work, treat preference
as a blocking defect, discard contrary evidence, or accept art as a gameplay
substitute.

Return: completed ticket carrying `artifact:` for the best fixed revision,
the gate-verdict identity, complaint ledger, disposition, evidence coverage,
and exact resume state or accepted core baseline.
