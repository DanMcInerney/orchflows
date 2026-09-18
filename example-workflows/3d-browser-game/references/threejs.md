# Three.js implementation

Use for foundation, integration and profiling. Framework/optimization techniques are optional; timing, input, assets and verification contracts are required. Inspect installed packages/lockfile and matching official docs for release-sensitive APIs. Addons/CDNs must not introduce a second Three.js version.

## State and time

Separate rules, semantic input, content, renderer/camera, assets/audio, UI and diagnostics as useful; simple modules may suffice. Keep simulation independent of scene ownership for GPU-free rule tests and art-independent collision.

Use one render loop, commonly `renderer.setAnimationLoop`. For time-sensitive rules, accumulate seconds into fixed ticks (often 1/60 s), limit large deltas/catch-up steps and handle excess time explicitly. Hidden-tab/pause transitions clear input and clock/accumulator to prevent resume bursts. Interpolate presentation where useful. Check equivalent rule outcomes across rendering rates within declared tolerance; fixed time alone does not guarantee determinism.

Manual mode stops real-time advancement, consumes actions for exactly requested ticks and renders, sharing the live update. Seed randomness, exclude wall-clock time from rules and record physics tolerances. Reset scheduled events, transient entities and random state.

## Input, camera and collision

Map inputs to move/aim/interact/pause, distinguishing held intent from rising edges. Normalize diagonals when equal speed is intended. Clear pressed state on blur, pause, pointer-lock loss and restart. Focus intentionally after start; menus must neither stick controls nor swallow their own keys. Resume audio on user gestures; expose pointer-lock requests/failures as UI state.

Choose projection/camera for the mechanic. Update aspect/projection on resize; derive raycast coordinates from the canvas rectangle and restrict target layers. Selection raycasts are not general collision detection.

Use explicit collider proxies, stable IDs and debug drawing independent of meshes. Handle fast-object tunneling with sweeps or suitable physics. Give fixed-step physics one owner, never a duplicate renderer callback. Check relevant corners, slopes, grounded transitions/platforms. Test third-person camera obstruction/restoration and scene-appropriate clipping bounds.

## Assets and animation

Use the installed package's `GLTFLoader`. Configure Draco, Meshopt or KTX2 only for assets using them; verify decoder/transcoder files in production. KTX2 detection needs the actual renderer; compression should address measured cost. Test network errors, loading and missing textures instead of concealing broken hero assets with placeholders. [GLTFLoader](https://threejs.org/docs/pages/GLTFLoader.html).

Separate gameplay and visual roots so pivot/scale fixes cannot move colliders. Check bounds, forward direction and clip names/durations. Drive `AnimationMixer` from the chosen clock; clone skinned models with the package's skeleton-aware utility. Crossfade deliberately, stop stale actions and separate simulation movement from animated root transforms.

## Materials and light

Use correct color semantics: sRGB for base-color/emissive textures, not normal/roughness/metalness data. `GLTFLoader` handles glTF conversion; avoid doubling it. Match tone mapping, exposure and output to the art preview; post-processing must preserve final output conversion. [Color management](https://threejs.org/manual/pages/color-management.html).

Establish readable key/fill/environment light, roughness and appropriate PBR materials before bloom/fog/shaders. Bound shadow lights, distance/map sizes and transparent overdraw; tune bias to scene scale. Effects must preserve interaction cues. Blender settings do not promise identical runtime output.

## Performance and lifetime

Profile warmed-up busy production play, cold load/start and repeated retries under the [evidence contract](evidence.md). Compare target budgets and remeasure changes under the same workload; test other targets/quality levels when requested. Idle menus, manual stepping and software/headless rendering cannot establish real-device gameplay performance.

Measure first. `renderer.info` reports draw calls, triangles, textures and geometries, not total GPU memory or presented-frame timing. Record raw frame intervals before simulation clamping; configure multipass counter resets for the intended frame. Combine counters, browser profiles and observed moving frames. Set pixel-ratio caps/quality by target cost; resize drawing buffers/projection without fighting CSS. [WebGLRenderer](https://threejs.org/docs/pages/WebGLRenderer.html).

For measured bottlenecks, consider shared geometry/materials, `InstancedMesh` with updated matrices/bounds, culling, LOD, spatial queries, transient pools or reduced hot-loop allocation. Material changes, fill rate, shadows and transparency can dominate triangle cost. [InstancedMesh](https://threejs.org/docs/pages/InstancedMesh.html).

Track resource ownership: removing objects does not free GPU resources. Dispose geometry, materials, textures and render targets only after their final owner releases them. Clean mixers, listeners, timers, subscriptions and loops. Repeat entry/retry and check counts stabilize. Give context loss a clear recovery/reload path and verify restored state where supported. [Disposal](https://threejs.org/manual/pages/how-to-dispose-of-objects.html).
