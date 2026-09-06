---
name: gameplay-gate
description: Judge fixed core gameplay with independent play, evidence floors, and bounded repair successors.
disable-model-invocation: true
---

Require: fixed I2 `artifact:` identity, frozen traceability and core rubric,
complete core capture/performance matrix, QA result, at least two
maker-independent play contexts, parent frame journal, and package digest.

Read the journal and freeze every input before judging:

    tickets.py judge <run> --standard threejs-browser-game --standard browser-game-interface --standard browser-game-playtest --parent <frame> --artifacts <i2-artifact> --goal-file <core-judge-goal> --isolation required

The verdict checks production boot, focus and ordinary controls, fundamental
loop, central mechanics and reachable states, readable timing and feedback,
challenge and counterplay, meaningful choices, pacing, prompt traceability,
complete core captures, and qualified representative performance. Graybox
assets pass the art bar when they support fair play and legibility; final
polish belongs to the whole-game gate. Every dimension scores 0–4 and every
complaint has an ID, seam, cause, evidence, kind, and expected improvement.

When a verdict blocks, hand its complete `findings:` line to one repair call:

    tickets.py do <run> --standard threejs-browser-game --parent <frame> --goal-file <repair-goal> --isolation required
    tickets.py judge <run> --standard threejs-browser-game --standard browser-game-interface --standard browser-game-playtest --parent <frame> --artifacts <repaired-artifact> --goal-file <rejudge-goal> --isolation required

The repair goal names only accepted complaints, causal seams, affected
evidence, visible improvement, and regression checks. Re-run affected QA and
adaptive play, retain unaffected smoke coverage, and compare before/after
evidence. Two repair rounds is the local bound. Continued authorized progress
opens an automatic successor with the complete ledger; stagnation or reopened
complaints receives a changed-strategy diagnosis. `redesign` names invalidated
descendants and returns to discovery. `unverified` names the missing
capability or evidence and an exact resume cursor.

Never lower a critical floor, let a maker judge its own work, treat preference
as a blocking defect, discard contrary evidence, or accept art as a gameplay
substitute.

Return: completed ticket carrying `artifact:` for the best fixed revision,
the gate-verdict identity, complaint ledger, disposition, evidence coverage,
and exact resume state or accepted core baseline.
