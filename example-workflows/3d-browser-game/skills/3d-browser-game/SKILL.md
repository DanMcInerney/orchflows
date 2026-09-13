---
name: 3d-browser-game
description: Build substantial Three.js browser games from mechanics brainstorming through playable experiments, Blender assets, progression, QA and independent agent playtests. Use for a complete game or an explicitly bounded production phase.
---

Run this coordination in the caller. Establish [library context](../../references/library-context.md). The outcome is a complete game at the caller's scope with evidence of player decisions, usable controls, coherent art and tested outcomes. Choose depth and finish over feature count. Preserve an existing game's intent and architecture when extending it.

## People, boundaries and checkpoints

Declare four children for one full game: a game maker through `orchflows-light:orch-work`, a core reviewer through [playtest-3d-browser-game](../playtest-3d-browser-game/SKILL.md), an asset maker through [make-blender-game-assets](../make-blender-game-assets/SKILL.md), and a new final reviewer through the playtest leaf. Each child works without children. Continue the same maker through native messaging; do not create an agent per numbered step. A caller-requested partial phase uses only the roles it reaches and is delivered as partial work.

The caller handles steps 1–2. Give the game maker steps 3–9 as one staged assignment, require its outputs before step 10, then continue it for any needed step 11 repairs and step 12's asset brief. The caller owns step 13's Blender delegation while the game maker handles step 14. These two phases may run concurrently. The caller joins their outcomes before continuing the game maker through steps 15–18. Step 19 freezes all edits for the final reviewer. The caller coordinates any step 20 repairs, joins evidence and delivers. Children receive only their production assignments; delegation and joining remain with the caller.

Include two focused mechanics experiments at step 9. Allow at most one repair pass after each independent review at steps 11 and 20 when material findings or relevant candidate changes require it. If the review is ready and the candidate is unchanged, preserve its evidence and close without repair, rebuilding or replay. A needed pass includes reproducing findings, changes and affected checks; it does not include another independent review. Within production, maker QA and tuning are ordinary work, not new reviewer rounds. Additional agents or review/repair rounds require a caller request. If a checkpoint remains needs change or unverified, return the best runnable state, remaining findings and the precise next action; do not advance or declare acceptance.

Use [evidence](../../references/evidence.md) for build identity, notes and findings. Record checkpoint outcomes as ready, needs change or unverified, with supporting observations. These checkpoints are working decisions, not user approval prompts. Resolve unspecified creative choices from the brief and report assumptions; ask only when the missing choice materially prevents progress.

## 1. Define the intended player experience

Extract fantasy, audience, target device/browser, controls, session length, desired difficulty, visual tone, distribution and required features. Distinguish caller requirements from chosen design defaults. In `notes/design.md`, state what the player repeatedly decides, what improves with mastery and what ends a session. Identify a complete first release and an optional expansion list. For a large brief, propose a coherent release boundary without discarding required mechanics silently.

**Advance with:** a playable scope, player promise, target conditions and observable completion criteria. Avoid genre defaults that force combat, bosses, timers or a score onto a different game.

## 2. Prove the production tools and testing route

Inspect the repository and preserve its framework. Establish install, development server, build and production-preview commands. Check a real 3D scene renders in the available browser and accepts press, hold, release, focus and camera input. Test screenshot/motion inspection. If pointer lock cannot be operated, plan a compatible explicit look control without changing the public control scheme unnecessarily. Locate Blender and export a disposable source mesh to GLB, then load it in Three.js. Probe audio only if it is part of the promise.

**Advance with:** observed tool results, versions and a feasible agent play route. Keep this probe disposable and out of the finished game's content. Record blocked capabilities before delegating dependent work.

## 3. Brainstorm different mechanics

Generate at least three materially different ways to realize the player promise. For each describe the main verb, constraint, competing choices, risk/reward, feedback, skill ceiling, interaction between systems and one concrete 30-second episode. Include how the idea could become boring or exploitable and a cheap experiment that would expose that failure. Cosmetic themes of the same loop do not count as different mechanics.

**Advance with:** a compact comparison that makes design tradeoffs visible, using the `browser-game` guidance.

## 4. Choose and develop the strongest loop

Choose using player agency, depth from interacting rules, readable consequences, feasibility and testability. Explain the tradeoff. Define the second-to-second action, encounter/session loop and longer progression if appropriate. Describe at least two viable approaches whose advantage changes with circumstances. Specify costs, recovery, loss, success and restart, plus how the player learns through play. List the highest-risk assumptions rather than designing all content in advance.

**Advance with:** a concise design, controls/state diagram, tunable parameter table and explicit reasons someone would play again.

## 5. Plan experiments, levels and acceptance observations

For each risky assumption, define a scenario, action, expected player-visible result and a failure signal. Lay out an introductory situation, a complication, a combination of learned mechanics and a mastery situation. Select a small graybox arena/course/puzzle set that exercises those decisions. Plan ordinary success, failure or setback, recovery, retry, alternate strategy and an exploit attempt. Set target load time, frame-time and content/asset budgets for the agreed device; label initial budgets as hypotheses.

**Advance with:** a scenario list and experiment predictions written before implementation. Do not use playtest scores as a substitute for explaining why a mechanic works.

## 6. Build the testable Three.js foundation

Read [Three.js reference](../../references/threejs.md) and [test interface](../../references/test-interface.md). Separate simulation, input actions, scene presentation, assets and UI. Make simulation timing explicit; use fixed updates for time-sensitive mechanics. Implement seeded resets, safe scenario entry, an observable state summary and bounded action/step controls using the same game rules as ordinary play. Provide the DOM alternative if the host cannot call hooks. Add meaningful rule tests and a production boot check.

**Advance with:** a build that can boot, start, observe, act, reset and reproduce a scenario; timed and real-time modes do not double-advance the simulation. Prove at least one ordinary browser input changes both game state and the visible scene.

## 7. Establish movement, camera and interaction feel

Build the main verb in a simple space. Tune acceleration/braking, turning, aiming or selection, jump/interaction tolerances and feedback as the chosen game requires. Check diagonals, walls, edges, occlusion, camera collision, resizing, pause, focus loss and resumed input. Bind intent once so automation and human controls agree. Inspect gameplay at the actual camera distance and speed.

**Advance with:** responsive, predictable control and camera behavior, with no control defect that would distort a mechanics experiment.

## 8. Complete a graybox session

Implement the central mechanic, its counterpressure, a meaningful resource or tradeoff, readable consequences and a reachable session outcome. Connect start, onboarding, play, setback/failure, success and replay as relevant. Use clear placeholder silhouettes and feedback. Build the planned situations with actual collision and progression, not a showroom of disconnected features.

**Advance with:** at least one entire session reached through ordinary input, including restart, and runnable scenarios for the main decisions. Keep final asset production behind the core checkpoint.

## 9. Run two focused mechanics experiments

Play the graybox while watching the game. For each experiment predict how changing one rule or parameter should alter player decisions, compare against the baseline in the same scenario, and record actual behavior. Try different strategies, deliberate misuse and recovery from a mistake. Adjust the mechanic, opponent/hazard behavior or layout when decisions collapse into one obvious action. Prefer changing a rule over adding unrelated systems to hide weak play.

**Advance with:** two observed before/after experiments, chosen settings and an explanation of the remaining interesting decisions. If the loop is still mechanically empty, report needs change before asking an independent reviewer to judge it.

## 10. Independently play the core

Freeze the graybox candidate and invoke the playtest leaf in `core` mode. Give the reviewer the brief, public instructions, build/run location, target conditions, test interface and scenarios; keep maker findings available for its later diagnostic pass. Require actual observation–action–observation play, initial uncoached onboarding, alternate strategies, failure/recovery and a complete session, with evidence.

**Advance with:** a reviewer report tied to the core build. Automated routes demonstrate reachability; independent decisions assess understanding, fairness, control and depth. Missing browser play is unverified.

## 11. Repair and establish the core baseline

When a repair pass is needed under the checkpoint rule above, return findings to the original maker. Prioritize confusion about goals/controls, dead or dominant strategies, unfair setbacks, softlocks and unrecoverable states. Reproduce each material finding, repair shared causes and replay the affected situations plus the main session. Keep the original review and identify changed files/settings and the new build. For an unchanged ready candidate, record no repair required and reuse the independent evidence.

**Advance with:** a ready core checkpoint, or stop with needs change/unverified. Maker retests after repair are not a second independent acceptance. Record the established rules, camera, timing and collider contract; art changes that affect them require affected gameplay checks again.

## 12. Direct the art from gameplay

Create a visual brief: mood, silhouette families, palette/value hierarchy, scale, material language, focal points, animation style and UI/audio treatment. Make reference sketches, concept images or Blender studies for the hero object and a representative environment section. Inspect them at the intended game camera. Derive an asset list from actual gameplay roles and reuse opportunities, with dimensions, origins, attachment points, colliders, animation names, budgets and production priority.

**Advance with:** an art direction and [Blender asset handoff](../../references/blender.md) precise enough for an independent maker. The hero/interactive assets get deliberate design; low-priority background content gets a consistent reusable kit.

## 13. Produce and inspect Blender assets

Invoke the Blender leaf with the established core, art brief and owned output directory. Start with a representative hero asset plus environment piece, inspect source renders and a GLB loaded using the game's renderer settings, and resolve export or style problems before the rest of the set. The leaf owns blockout, modeling, UV/material work, necessary baking, rig/animation when needed, export and inspection.

**Advance with:** editable `.blend` files, reproducible scripts/settings, GLBs, texture dependencies, contact views and asset metadata with checked budgets. A successful Blender process or beauty render alone does not establish runtime quality.

## 14. Build content and progression around the proven rules

While assets are made, continue the game maker on distinct code/layout files. Develop the planned teach–test–combine–mastery sequence, meaningful variations and pacing with recovery/quiet intervals where appropriate. Add variety by changing relationships, space, information and tradeoffs before increasing health, speed or counts. Tune the economy and unlocks only if the game needs them. Keep content data separate from rule code so repeated scenarios stay maintainable.

**Advance with:** a complete content arc at the agreed scope, no required content left as a promised later feature, and test scenarios for each new decision.

## 15. Integrate assets and preserve gameplay readability

Join asset and code outcomes. Load through the production loader and validate scale/orientation, pivots, materials, animations, attachment points and asset failures. Compare collisions, silhouettes, occlusion and event timing with the graybox baseline. Play a normal camera route through every important environment. Recheck affected gameplay when meshes, layout or animation alter timing, line of sight or perceived hitboxes.

**Advance with:** a playable build using the delivered GLBs, coherent visual scale and feedback, and no silent missing-asset fallback masking a broken export.

## 16. Finish the player's experience

Build a clear title/start flow, concise contextual teaching, legible HUD, pause/settings, outcome explanation and quick retry. Add action anticipation, response and consequence through animation, sound and VFX. Provide volume/mute and motion controls where needed; redundant shape/text/audio cues should support essential information. Handle loading/progress/error states, unavailable rendering and input changes. Read the game at target resolution, not only enlarged captures.

**Advance with:** an understandable, consistent complete session. Ensure polish does not hide actionable cues or delay input/interaction for the sake of animation.

## 17. Run scenario QA and regression play

Use the playtesting guidance and [evidence contract](../../references/evidence.md). Exercise ordinary entry through completion and retry, failure/recovery, each mechanic/content branch, alternate strategies and abuse cases. Test pause/focus loss, resize, repeated restart, resource exhaustion, asset load failure and saved-state behavior where present. Cover the declared browser/device/input matrix; viewport emulation alone does not prove touch, controller or device performance. Check diagnostics alongside actual rendered captures. Repeat deterministic scenarios across seeds/configurations that can expose bugs, while keeping genuine play separate from scripted coverage.

**Advance with:** passing behavior checks, observed important branches and an honest gap list. Fix known material defects before final independent review; do not convert an unvisited state into a pass.

## 18. Measure and optimize real gameplay

Profile production preview during representative busy action after warm-up; also measure cold load/start and repeated retries. Record actual browser/device, viewport, pixel ratio, quality, duration, workload and build. Inspect frame-time distribution, long stalls, renderer counters and loading/memory trends. Use profiler evidence to choose batching/instancing, culling, simpler shaders, shadow/texture changes or simulation work. Retest changed visuals and gameplay at the same workload. Measure low-quality settings or another target only when supported by the brief.

**Advance with:** target-relative results and captures of the measured workload. A static menu, headless software renderer or manual simulation stepping cannot establish real-device gameplay performance; label those limits explicitly.

## 19. Independently play the production candidate

Freeze the exact production build and invoke a new playtest reviewer in `final` mode. It receives source/build identity, original brief, public instructions, core review/repairs, asset/runtime evidence, scenarios and measured conditions. It first attempts uncoached play, then exercises the QA matrix and challenges the fun/depth claims. It inspects the actual finished game's assets, motion, cues and readable outcomes.

**Advance with:** independent findings and coverage on that exact build, including contradictory evidence or untested conditions. A pass on the graybox is not acceptance of the finished game.

## 20. Repair, verify and deliver

When a repair pass is needed under the checkpoint rule above, use the existing makers, each owning its shared causes. For changed candidates, rebuild and replay affected cases plus start–play–outcome–retry; recapture changed visual states and rerun affected performance conditions. Keep the reviewed build identity distinct from the delivered revision and label subsequent checks as maker verification. An unchanged ready candidate uses its existing review and evidence without another pass. No further independent review is implied.

Deliver the runnable game/preview location, editable sources including Blender files, build/run/test/re-export commands, controls, scenario entry points, design/asset notes, review reports and evidence. State whether the result is ready, needs change or unverified against the brief, and identify unresolved gaps with a next action. Keep the actual playable result prominent. Use a hosting skill when the caller requested deployment; do not treat local preview as public hosting.
