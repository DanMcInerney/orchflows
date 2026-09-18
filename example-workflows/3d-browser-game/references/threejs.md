# Three.js implementation reference

Use for foundation, asset integration and profiling. Framework and optimization choices are methods; timing, input, asset and verification contracts remain required. Inspect the installed package and lockfile and consult its matching official documentation before relying on release-sensitive APIs. Do not copy a second Three.js version through an addon/CDN.

## Responsibilities and timing

A practical split is simulation/rules, action input, world/content data, renderer/camera, assets/audio, UI and diagnostics. Small games can use simple modules; a generic entity framework is not a deliverable. Keep simulation data independent of scene object ownership so tests can evaluate rules without a GPU and art swaps do not change collision.

Use one render loop, commonly `renderer.setAnimationLoop`. For time-sensitive gameplay accumulate elapsed seconds into a fixed simulation tick (often 1/60 s), limit unusually large deltas, cap catch-up steps and explicitly handle excess accumulated time. On hidden-tab/pause transitions clear held inputs and reset the clock/accumulator to avoid a resume burst. Interpolate presentation between prior/current states when helpful; test that variable rendering rates produce equivalent rule outcomes within the declared tolerance. Fixed time does not by itself guarantee cross-platform determinism.

In manual test mode stop real-time advancement, consume queued actions for exactly the requested number of ticks and render the resulting state. Both modes call the same update. Seed game randomness, keep wall-clock time out of rules, and document physics tolerances if a third-party engine prevents exact replay. Include scheduled events, transient entities and random state in a reset.

## Input, camera and collision

Map browser inputs to semantic actions such as move, aim, interact and pause. Distinguish held intent from rising-edge actions. Normalize diagonal movement when the design expects equal speed; clear pressed state on blur, pause, pointer-lock loss and restart. Focus the game intentionally after start; menus must not leave controls stuck or swallow their own keyboard interactions. Resume audio on a user gesture and treat pointer-lock requests/failures as UI state.

Choose perspective/orthographic and camera behavior from the mechanic. Handle viewport aspect and projection updates on resize; map pointer coordinates from the canvas bounding rectangle into normalized device coordinates for raycasting. Restrict raycast layers to intended targets. A raycast for selection is not general collision detection.

Use explicit collider shapes/proxies independent of render meshes, with stable IDs and debug drawing. Sweeps or suitable physics handle fast movement that would tunnel through thin obstacles. Decide fixed-step ownership with the physics library; do not step it again from a renderer/framework callback. Check corners, slopes, grounded transitions or moving platforms only where relevant. For third-person cameras, test obstruction and restoration; bound near/far clipping to useful scene scale.

## Assets and animation

Use `GLTFLoader` from the same installed Three.js package. If an asset actually uses Draco, Meshopt or KTX2, configure the corresponding decoder/transcoder and verify its files are served by the production build; compression is optional until it helps a measured budget. KTX2 support detection needs the actual renderer. Validate network errors, loading transitions and missing textures rather than hiding broken hero assets with placeholders. [GLTFLoader](https://threejs.org/docs/pages/GLTFLoader.html)

Keep gameplay roots separate from imported visual roots so scale/pivot adjustments cannot move the collider unexpectedly. Check exported bounds and forward direction, animation clip names and durations. Use `AnimationMixer` for imported clips; update it from the chosen time source. For duplicated skinned models use the package's skeleton-aware cloning utility. Crossfade deliberately, stop stale actions, and keep simulation-owned movement separate from animated root transforms.

## Materials, light and output

Three.js uses a linear working color space. Color textures such as base color and emissive need the appropriate sRGB interpretation; non-color normal/roughness/metalness maps do not. GLTFLoader handles glTF color semantics; avoid applying a second conversion. Match renderer tone mapping/exposure and output settings to the art review scene. Post-processing must preserve the correct final output conversion. [Color management](https://threejs.org/manual/pages/color-management.html)

Start with readable lighting and physically based materials where appropriate. Establish key/fill/environment balance and roughness before bloom, fog or elaborate shaders. Limit shadow-casting lights, shadow distance/map size and transparent overdraw. Tune shadow bias against the actual scene scale. Ensure effects preserve interaction cues. Blender's render settings are not a promise of identical Three.js output.

## Performance and lifetime

Profile production preview during representative busy action after warm-up, and measure cold load/start and repeated retries. Record the build, actual browser/device, viewport, pixel ratio, quality, duration and workload under the evidence contract. Compare results with the agreed target budgets. Retest changed visuals and gameplay at the same workload; measure another target or low-quality settings when required by the brief. A static menu, software/headless renderer or manual simulation stepping cannot establish real-device gameplay performance; report those limits.

Measure first. `renderer.info` helps track draw calls, triangles, textures and geometries, not total GPU memory or displayed-frame timing. Record raw frame intervals before clamping simulation time so long stalls remain visible. With multiple passes configure counter resets so measurements cover the intended frame. Pair counters with browser timing/profiling and observed changing game frames. Cap device pixel ratio or provide quality settings based on measured target cost. Resize the drawing buffer and update camera projection without fighting CSS layout. [WebGLRenderer](https://threejs.org/docs/pages/WebGLRenderer.html)

Batch repeated compatible objects with shared geometry/materials and `InstancedMesh`; update instance matrices/bounds when transforms change. Frustum culling, appropriate LOD, spatial queries, pooled transient effects and fewer allocations in hot loops are options tied to observed bottlenecks. More triangles are not always the dominant cost: material changes, fill rate, shadows and transparent effects can dominate. [InstancedMesh](https://threejs.org/docs/pages/InstancedMesh.html)

Track ownership when unloading scenes. Removing an object does not release geometry, material, texture or render-target GPU resources. Dispose resources when their final owner releases them; preserve shared resources still in use. Tear down mixers, listeners, timers, UI subscriptions and render loops. Repeat scene entry/retry and look for counts that grow without returning to a stable range. Handle WebGL context loss with a clear recover/reload path and recheck restored state when supported. [Resource disposal](https://threejs.org/manual/pages/how-to-dispose-of-objects.html)
