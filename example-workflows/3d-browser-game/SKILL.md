---
name: 3d-browser-game
description: Build a 3D Three.js browser game through research, playable core gates, Blender production, and evidence-bound acceptance.
disable-model-invocation: true
---

Require: one `brief`, a git-backed `workspace`, and explicit
amendments. The brief and amendments are product authority.

Open one frame and retain its returned frame identity:



    tickets.py frame-open <run> --goal-file <program-goal> --workflow 3d-browser-game

**Research and design.** Open the `discovery` helper under the frame. It audits
promises, runs independent research lanes, records capability gaps and
user-only questions verbatim, and freezes the core concept, controls, state
model, traceability, rubric, capture matrix, and performance plan before code.

    tickets.py frame-open <run> --goal-file <discovery-goal> --parent <frame> --workflow discovery
    tickets.py frame-close <run> <discovery-frame> --done <discovery-check>

**Core implementation.** Open `playable-increment` with the frozen design.
Its I0, I1, and I2 candidates use Three.js primitives or functional
placeholders, ordinary input, readable feedback, and scoped QA/play evidence;
each carries its fixed revision before the next increment.

    tickets.py frame-open <run> --goal-file <increment-goal> --parent <frame> --workflow playable-increment
    tickets.py frame-close <run> <increment-frame> --done <increment-check>

Open `gameplay-gate` over the fixed I2 revision. It separates QA, adaptive
play, and maker-independent judgment. Repairs preserve the complaint ledger
and fixed criteria; a bound or unavailable capability returns the best
identity and unresolved evidence. Redesign names its invalidated descendants.

    tickets.py frame-open <run> --goal-file <core-gate-goal> --parent <frame> --workflow gameplay-gate
    tickets.py frame-close <run> <core-gate-frame> --done <core-gate-check>

**Production and final acceptance.** Only an accepted core identity freezes
mechanics, collision, camera, controls, and timing. Generate and inspect
concept art, then open `blender-asset` jobs for source, render, export,
manifest, GLB, and runtime evidence. Gameplay-changing art invalidates the
affected core verdict. Integrate assets and open `final-acceptance` for play,
captures, performance cells, and independent judgment. Repair cycles preserve
complaint IDs, causes, contrary evidence, and resume state.

    tickets.py frame-open <run> --goal-file <asset-goal> --parent <frame> --workflow blender-asset
    tickets.py frame-close <run> <asset-frame> --done <asset-check>
    tickets.py frame-open <run> --goal-file <final-goal> --parent <frame> --workflow final-acceptance
    tickets.py frame-close <run> <final-frame> --done <final-check>

Close from outside every child only after all children return:

    tickets.py frame-close <run> <frame> --done <outside-probe>

Never invent a promise, settle a user-only question silently, fabricate play
or performance, let art bypass core acceptance, relax a score floor, erase a
complaint, mix package revisions, or claim `gaps: []` without observed gate
and outside-probe evidence.

Return: `tickets.py frame-close <run> <frame> --done <outside-probe>`, carrying
the accepted `artifact: git:<full-commit-id>`, evidence-index and gate
identities, outside-probe reading, or the best fixed revision and exact resume
state with every unresolved gap declared.
