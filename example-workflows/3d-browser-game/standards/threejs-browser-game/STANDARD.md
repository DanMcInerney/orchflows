---
name: threejs-browser-game
description: Stamp when Three.js game code is judged for pinned dependencies, playable seams, lifecycle, and runtime evidence.
narrows: orch-code
adapter: git
---

The target workspace owns Three.js, decoder, physics, and build dependencies
in its manifest and lockfile. Code evidence identifies the exact revision,
build command, served production route, browser/backend, and package inputs.
The runtime has explicit ownership for scene objects, loaders, animation,
collision, input focus, audio, UI, resize, and disposal; each ownership seam
has one observable check.

The game loop keeps simulation timing independent from rendering while making
the timing contract, collision route, camera behavior, and state transitions
visible. Normal keyboard and pointer input reaches the same paths a player
uses. Loading, failure, restart, win, loss, continuing state, and re-entry
are reachable without test-only mutation. Placeholder geometry is acceptable
for the core gate when it preserves mechanics, readability, and feedback.

Reviewers inspect lockfile fidelity, production boot, console and network
errors, deterministic state boundaries, asset disposal, input and focus
behavior, camera occlusion, hitbox correspondence, animation timing, and
measured peak-density behavior. A unit or build pass without a served,
ordinary-input reading leaves the runtime seam unverified.
