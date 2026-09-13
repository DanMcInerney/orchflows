# Three.js browser game

## Make

Treat Three.js as the presentation layer around explicit game state. Keep a single owner for simulation updates, input intent, entity lifecycle and asset ownership. Rendering frequency must not determine movement, timers, damage or resource costs. Use the project's established framework; add physics/ECS/state libraries only when their complexity buys something concrete.

Resolve collision and game events against gameplay geometry and rules, not incidental art hierarchy or pixel appearance. Keep camera and feedback synchronized with authoritative state. Debug displays should make collider, aiming and camera errors inspectable without leaking into normal play.

Use current APIs matching the installed Three.js release and keep addons/decoders compatible. Make loading failures actionable. Inspect exported assets through the production loader with game lighting and camera settings. Profile actual busy gameplay before reducing fidelity or adding optimization machinery. See the library's Three.js reference for implementation details.

## Review

Look for frame-rate-dependent rules, duplicate loops/listeners, stuck input after blur, camera clipping, stale state on reset, mismatched hitboxes and unhandled asset errors. Verify ordinary and diagnostic controls share action/rule ownership. Check that performance claims identify the real rendering backend and workload. Restart and load repeatedly to expose lifecycle leaks.
