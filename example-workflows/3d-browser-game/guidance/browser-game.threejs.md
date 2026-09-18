# Three.js browser game

Treat Three.js as the presentation layer around explicit game state. Keep a single owner for simulation updates, input intent, entity lifecycle and asset ownership. Rendering frequency must not determine movement, timers, damage or resource costs. Use the project's established framework; add physics/ECS/state libraries only when their complexity buys something concrete.

Resolve collision and game events against gameplay geometry and rules, not incidental art hierarchy or pixel appearance. Keep camera and feedback synchronized with authoritative state. Debug displays should make collider, aiming and camera errors inspectable without leaking into normal play.

Use current APIs matching the installed Three.js release and keep addons/decoders compatible. Make loading failures actionable. Inspect exported assets through the production loader with game lighting and camera settings. Profile actual busy gameplay before reducing fidelity or adding optimization machinery. See the library's Three.js reference for implementation details.

Controls and camera should remain responsive and predictable at actual play speed. Check movement/interaction tolerances, diagonals, walls, edges, occlusion, camera collision, resizing, pause/focus loss and resumed input as the game requires. Art integration must preserve readable silhouettes, perceived hitboxes, line of sight and event timing; changed gameplay conditions need new checks.

## Make

Build and tune the main verb in a simple space before relying on it in mechanics experiments. Play a normal camera route through each important environment after integration, including actual asset failures. Use the Three.js reference for engineering and profiling methods and the test-interface contract for required diagnostic behavior.

## Review

Look for frame-rate-dependent rules, duplicate loops/listeners, stuck input after blur, camera clipping, stale state on reset, mismatched hitboxes and unhandled asset errors. Verify ordinary and diagnostic controls share action/rule ownership. Check that performance claims identify the real rendering backend and workload. Restart and load repeatedly to expose lifecycle leaks.
