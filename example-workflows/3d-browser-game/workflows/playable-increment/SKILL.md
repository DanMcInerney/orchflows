---
name: playable-increment
description: Build one isolated Three.js gameplay increment with QA, adaptive play, and fixed evidence.
disable-model-invocation: true
---

Require: the frozen core contract and traceability identity, a git-backed
`workspace`, target toolchain lockfile, parent frame journal, and an increment
label from I0, I1, or I2.

Read the journal and make one isolated candidate under `threejs-browser-game`:

    tickets.py do <run> --standard threejs-browser-game --parent <frame> --goal-file <code-goal> --isolation required

I0 proves production-like boot, focus, movement, camera, representative asset
loading, damage, restart, and terminal state entry. I1 proves adaptive combat,
rewards, choices, readable placeholder feedback, and several minutes of the
core loop. I2 proves the complete promised waves or level, progression,
terminal or continuing state, boss or other central mechanic, loss, win, and
re-entry. Functional primitives and graybox geometry remain valid core
materials; polish cannot compensate for a missing mechanic.

Run scoped QA separately from ordinary-input play and preserve both identities:

    tickets.py judge <run> --review-independent "scoped increment QA before stage acceptance" --standard threejs-browser-game --parent <frame> --artifacts <candidate-artifact> --goal-file <qa-goal>
    tickets.py do <run> --standard browser-game-playtest --parent <frame> --goal-file <play-goal>

QA reports reproducible blockers and regression checks. Play records
interleaved observation and input, transcript classification, visible facts,
console/network deltas, and captures. Fixed scripts are `scripted input`;
fake time or state mutation is `simulated`; neither is actual play.

Land the increment only with its candidate revision, evidence packet,
traceability updates, and explicit gaps. A failed build, unplayable host,
missing capability, or contradictory evidence preserves partial outputs and
returns an unverified handoff for the gate.

Never change the frozen concept silently, claim a screenshot is play, hide
console or network errors, call production art complete, or widen the change
past the increment's causal seams.

Return: completed ticket with `artifact:` for the landed increment, QA and
play evidence identities, changed seams, regression reading, and declared
gaps.
