# Three.js browser game

Keep Three.js presentation around explicit game state, with one owner for simulation, input intent, entity lifecycle and assets. Rendering frequency must not determine movement, timers, damage or costs. Use the established framework; add physics/ECS/state libraries only for concrete benefits.

Resolve collisions/events against gameplay geometry/rules, independent of art hierarchy or pixels. Synchronize camera/feedback with authoritative state. Keep collider, aim and camera diagnostics inspectable outside normal play.

Match APIs, addons and decoders to installed Three.js. Make loading failures actionable. Inspect exports through the production loader, camera and lighting. Profile busy gameplay before reducing fidelity or adding optimization; use the Three.js reference for implementation details.

Keep controls/camera responsive and predictable at play speed. Check applicable movement/interaction tolerances, diagonals, walls, edges, occlusion/camera collision, resize, pause/focus loss and resumed input. Art must preserve silhouette, perceived hitbox, line of sight and event timing; recheck changed gameplay conditions.

## Make

Tune the main verb in a simple space before mechanics experiments. After integration, play normal camera routes through important environments and actual asset failures. Follow the Three.js reference and required test-interface behavior.

## Review

Check frame-dependent rules, duplicate loops/listeners, stuck input after blur, clipping, stale reset state, hitbox mismatch and unhandled asset errors. Ordinary/diagnostic controls must share action/rule ownership. Require actual rendering backend/workload in performance claims; repeat restart/load to expose leaks.
