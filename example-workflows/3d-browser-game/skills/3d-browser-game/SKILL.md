---
name: 3d-browser-game
description: Build substantial Three.js browser games from mechanics brainstorming through playable experiments, Blender assets, progression, QA and independent agent playtests. Use for a complete game or an explicitly bounded production phase.
disable-model-invocation: true
---

Apply this workflow in the caller with [library context](../../references/library-context.md). Inputs are the player brief, existing project when present, target conditions, workspace and caller constraints. Resolve unspecified creative choices from the brief and record assumptions; ask only when a missing choice materially prevents progress. A bounded phase uses its applicable prerequisites and returns the work and evidence it reaches without claiming a finished game.

Production staffing follows core execution rules, with shared creative direction and one integration owner. A production stage does not require a fresh maker. The two playtests below require independent reviewers through [playtest-3d-browser-game](../playtest-3d-browser-game/SKILL.md). Missing capabilities stop dependent work while independent authorized work may continue.

## Checkpoint rule

Use [evidence](../../references/evidence.md) to identify candidates and record ready, needs change or unverified outcomes. Freeze the candidate during each independent playtest and wait for its completed report before changing it. These are working checkpoints, not user approval prompts.

Each checkpoint permits at most one repair pass when material findings or relevant candidate changes require it. Reproduce material findings, repair shared causes, then rebuild and replay affected situations plus the main start–play–outcome–retry session. Recapture changed visual states and rerun affected performance conditions. Preserve the original review, identify the delivered revision and label subsequent checks as maker verification; the old independent verdict does not transfer to changed work. Repair staffing follows the assignment's scope and settings.

An unchanged ready candidate keeps its review and evidence without repair, rebuild or replay. No second independent review is included. Production QA and tuning before a checkpoint are ordinary work, not additional review rounds. Extra review/repair rounds require a caller request. If a checkpoint remains needs change or unverified, stop dependent production and return the best runnable state, remaining findings and the precise next action; do not declare acceptance.

## 1. Establish scope and capabilities

Record the player promise, requirements versus design defaults, target browser/device/input, session scope and observable completion criteria. Preserve an existing game's intent and architecture. Use the `browser-game` guidance for brief and design work; a larger brief needs a coherent release boundary without silently dropping requirements.

Probe the actual project install/build/preview route, rendered browser input and captures, and Blender source-to-GLB export loaded in Three.js. Apply the [test interface](../../references/test-interface.md) and library capability rules; a version command alone is insufficient. Probe audio when it is part of the promise. Keep disposable capability content out of the finished game.

Continue with observed capability results and a feasible ordinary agent play route. Record missing capabilities before assigning dependent work.

## 2. Produce the playable core and experiment evidence

Compare at least three materially different mechanics, choose the loop and define its rules, controls, tunable parameters and completion states. Write experiment predictions and observable success/failure scenarios before implementation. Establish target load, frame-time and asset/content budgets as hypotheses for the agreed device.

Build a testable Three.js graybox using the required [test interface](../../references/test-interface.md) and the [Three.js reference](../../references/threejs.md). Complete the intended session with responsive controls, readable placeholder feedback, actual collision/progression and ordinary input through an outcome and restart. Verify the interface, rule behavior and production boot; no control defect should distort the experiments.

Run **two focused mechanics experiments**. For each, predict how one rule or parameter change will affect player decisions, compare observed baseline and changed behavior in the same scenario, and record the chosen setting and contrary evidence. Include different strategies, deliberate misuse and recovery. Apply the shared design criteria: if the loop still has no meaningful decisions, report needs change before requesting independent review.

Continue with the runnable graybox, mechanics comparison and chosen design, scenario predictions, two observed before/after experiments, tested controls/interface and a complete ordinary session. Keep final asset production behind the core checkpoint.

## 3. Independently review and establish the core

Freeze the core candidate and apply the playtest workflow in `core` mode with its declared inputs, scenarios and evidence. Require actual uncoached/adaptive browser play and a report tied to that build; missing play is unverified. Apply the checkpoint rule to its completed findings.

Only a ready core advances. Record the established rules, camera, timing and collider contract for art and content production; later changes affecting them require affected gameplay checks. A repaired core's maker verification establishes the delivered baseline without claiming a second independent acceptance.

## 4. Produce and integrate the finished game

Derive art direction and the [Blender asset handoff](../../references/blender.md) from the ready core. Apply [make-blender-game-assets](../make-blender-game-assets/SKILL.md) with the art brief, actual baseline, runtime loader and owned output directory. Content/progression work may proceed concurrently on separate files under the proven rules. Gather both completed outcomes before integration.

Integrate the inspected exports through the production loader and finish the agreed content, interface, feedback and session flow under the shared game, Blender and Three.js criteria. Preserve or recheck the core's timing, collision, camera and readability when art/content changes affect them. No required content remains a promised later feature.

Run scenario QA and regression play using `browser-game.playtesting`, then measure and optimize representative production gameplay using the Three.js and evidence references. Fix known material defects before final review. Continue with editable sources and reproducible exports, integrated runtime asset views, complete-session and branch evidence, behavior checks, target-relative load/performance observations and explicit coverage gaps. An unvisited state or unsupported target is not a pass.

## 5. Independently review, verify and deliver

Freeze the exact production candidate and apply the playtest workflow in `final` mode with a fresh reviewer different from the core reviewer. Supply the original brief, public instructions, candidate identity, run location, test route, core review/repairs, asset evidence and measured conditions as the leaf directs. A graybox review does not accept the production candidate. Apply the checkpoint rule to the completed final report.

Return the runnable game/preview prominently, editable game and Blender sources, build/run/test/re-export commands, controls, scenario entry points, design/asset notes, independent reports and evidence. State ready, needs change or unverified against the caller's scope, with unresolved gaps and next actions. Use a hosting skill when the caller requested deployment; local preview is not public hosting.
