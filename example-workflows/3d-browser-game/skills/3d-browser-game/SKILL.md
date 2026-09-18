---
name: 3d-browser-game
description: Build a complete Three.js game or bounded production phase through mechanics experiments, Blender assets, QA and independent playtests.
disable-model-invocation: true
---

Apply [library context](../../references/library-context.md) in the caller. Inputs: player brief, existing project, target conditions, workspace and constraints. Choose and record unspecified creative details; ask only when a missing choice blocks progress. A bounded phase uses its prerequisites and returns reached work without claiming a finished game.

Use shared creative direction and one integration owner. Production staffing follows core execution rules; only the two playtests require fresh independent reviewers. Missing capabilities block dependent work.

## Checkpoints

Use [evidence](../../references/evidence.md) for candidate identities and `ready`, `needs change` or `unverified` conclusions. Freeze each candidate until its independent playtest report completes. These are work gates, not user approval prompts.

Each checkpoint permits at most one necessary repair pass: reproduce material findings, fix shared causes, rebuild and replay affected situations plus start–play–outcome–retry. Recapture changed visuals and remeasure affected performance. Preserve the original report and identify the delivered revision; subsequent checks are maker verification, not renewed independent acceptance. Honor scoped repair settings.

An unchanged ready candidate needs no repair, rebuild or replay. Pre-checkpoint QA/tuning is ordinary production. No second independent review is included; extra review/repair rounds require a caller request. If a checkpoint remains needs change or unverified, stop dependent production and return the best runnable state, findings and precise next action.

## 1. Establish scope and capabilities

Record the player promise, requirements versus defaults, browser/device/input, session scope and observable completion criteria. Preserve existing intent and architecture; bound a larger release without silently dropping requirements. Select `browser-game` for design.

Probe install/build/preview, rendered browser input/captures and Blender source-to-GLB loading in Three.js under the [test interface](../../references/test-interface.md) and library capability rules. Probe promised audio. Remove disposable probe content from the finished game. Continue only with a feasible ordinary-play route and recorded capability results.

## 2. Produce and test the core

Compare at least three materially different mechanics; choose rules, controls, tunable parameters and completion states. Before implementation, write experiment predictions and observable success/failure scenarios. Set load, frame-time and asset/content budget hypotheses for the agreed device.

Build a Three.js graybox under the [test interface](../../references/test-interface.md) and [Three.js reference](../../references/threejs.md). Complete the session with responsive controls, readable placeholders, real collision/progression, an outcome and ordinary-input restart. Verify rule behavior, interface and production boot before experiments; control defects must not distort them.

Run **two focused mechanics experiments**. Each predicts how one rule/parameter change affects decisions, compares observed baseline and changed behavior in the same scenario, and records the chosen setting and contrary evidence. Include alternate strategies, misuse and recovery. If meaningful decisions remain absent, report needs change before independent review.

The core handoff includes the runnable graybox, mechanics comparison/choice, scenario predictions, two observed before/after experiments, verified controls/interface and a complete ordinary session. Final assets wait for the core checkpoint.

## 3. Independently establish the core

Apply [playtest-3d-browser-game](../playtest-3d-browser-game/SKILL.md) in `core` mode to the frozen candidate with its required inputs and evidence. Missing uncoached/adaptive browser play is unverified. Apply the checkpoint rule after the completed report.

Only a ready core advances. Record established rules, camera, timing and collider contracts for art/content; later changes require affected gameplay checks. After repair, maker verification establishes the delivered baseline without a second independent acceptance.

## 4. Produce and integrate

Derive art direction and the [Blender handoff](../../references/blender.md) from the ready core. Apply [make-blender-game-assets](../make-blender-game-assets/SKILL.md) with the art brief, actual baseline, runtime loader and owned output directory. Content/progression may run concurrently on separate files under the proven rules. Gather both completed outcomes before integration.

Integrate inspected exports through the production loader; finish agreed content, UI, feedback and session flow under applicable game, Blender and Three.js criteria. Preserve or recheck timing, collision, camera and readability affected by integration. Required content cannot remain a promised later feature.

Run scenario QA/regression play with `browser-game.playtesting`; measure and optimize representative production gameplay under the references. Fix known material defects before final review. Supply editable sources, reproducible exports, runtime asset views, complete-session/branch evidence, behavior checks, target-relative load/performance measurements and explicit coverage gaps. Unvisited states and unsupported targets remain unverified.

## 5. Independently review and deliver

Apply the playtest workflow in `final` mode to the exact frozen production candidate, using a fresh reviewer different from the core reviewer. Supply the brief, public instructions, candidate/run location, test route, core review/repairs, asset evidence and measured conditions as that workflow directs. Apply the checkpoint rule after its completed report; graybox review does not accept production.

Return the game/preview prominently, editable game/Blender sources, build/run/test/re-export commands, controls, scenarios, design/asset notes, independent reports and evidence. State ready, needs change or unverified against the requested scope, with gaps and next actions. Requested public deployment uses a hosting skill; local preview is not hosting.
