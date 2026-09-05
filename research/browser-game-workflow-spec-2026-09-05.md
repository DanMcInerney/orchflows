# Three.js and Blender browser-game workflow specification

The rebuilt `browser-game` workflow has one production route: a 3D browser game implemented with a pinned Three.js dependency and assets authored in a pinned Blender executable. It earns a complete-game claim only when one fixed revision survives playable vertical increments, inspected Blender-to-GLB handoffs, ordinary-input play by agents that can see and control the game, measured presented-frame performance on declared hardware, and maker-independent judgment. This document specifies that reusable workflow; it does not implement the workflow or build a game.

All **MUST**, **SHOULD**, and **MAY** statements are proposed workflow policy. Statements labeled **Current fact** report primary documentation checked on 2026-09-05. A run rechecks facts whose pinned Blender, Three.js, browser, graphics backend, or model identity has changed. Recommendations are defaults to test, not guarantees about an unmeasured project.

## Outcome and completion contract

The public workflow remains `browser-game`. It takes `brief`, the user's complete natural-language request, and `workspace`, the target git repository. Three.js and Blender are fixed by this workflow. The brief remains authoritative for the game, and the workflow must not silently create promises about browser support, hardware, accessibility, licensing, monetization, telemetry, or release.

A successful return contains:

- `artifact: git:<commit>` for the accepted game revision;
- an evidence-index identity binding the brief, research, concept, asset manifests, playable increments, play sessions, captures, performance traces, judgments, and repairs;
- the exact outside probe and its passing observation at that commit; and
- `gaps: []`.

A non-success return names the fixed artifact reached, all evidence gathered, and every remaining gap. The complete-game gate requires a browser-served production build that starts without developer tools; documented controls; a coherent brief-derived core loop; every promised mechanic, progression path, terminal or continuing state, and replay or re-entry behavior; final assets with closed provenance; no blocking console, network, or load errors; actual play evidence; independent acceptance; and every declared continuously animated performance cell passing. The frozen concept may define completion as a conventional win/loss cycle, a bounded session, a stable sandbox loop, or another observable form suited to the brief. A prototype, scripted state transition, screenshot gallery, or green unit suite cannot satisfy the gate by itself.

Publishing, buying or accepting licensed assets, installing Blender or other system software, and making commercial or support promises require current or standing user authority. The future workflow may perform an authorized bounded setup step and resume its capability gate; this document-only specification change performs no installation.

## Baseline and deliberate replacement

This revision was derived from clean repository revision `bbdc7effbf00ed8f7d58eff1b422513bb9d1b9b2`. The earlier draft covered 2D and 3D routes, compared engines, and treated MCP as a possible Blender path. This revision supersedes those choices. Discovery proves that the fixed tools are usable; it does not reopen engine selection or route around a missing Blender installation with another DCC.

The current public [browser-game workflow](../example-workflows/browser-game/SKILL.md) already records a program, evidence, a checkpoint, and a successor plan. It does not make assets or code, open playable increments, perform actual play, gather presentation evidence, or judge a complete game. The rebuilt package SHOULD preserve its atomic authority, immutable evidence identities, and explicit invalidation while replacing its fixed questionnaire with the smaller gates below.

Current package law permits one public workflow to own private helper workflows, applied skills, standards, references, scripts, and dependency declarations under its directory. All private items share one package digest. The migration therefore moves useful browser-game references and validators behind that owner before retiring legacy allowlists. It migrates responsibilities, not old schemas: brief cells become the brief audit; decisions become a compact decision ledger; asset and performance claims become manifests and measurement cells; and the successor plan becomes the playable-increment ledger.

## Package shape and ownership

Only `browser-game` is public. The following proposed paths are private to `example-workflows/browser-game/` (or to the corresponding project/user ring package if authored there):

| Package path | Responsibility |
| --- | --- |
| `SKILL.md` | Public contract, stage order, frame ownership, and close behavior. |
| `workflows/discovery/SKILL.md` | Brief audit, capability probes, focused research, concept freeze, and increment plan. |
| `workflows/blender-asset/SKILL.md` | One asset batch through source edit, inspection, render, export, validation, judgment, and handoff. |
| `workflows/playable-increment/SKILL.md` | One build/check/land/play/judge checkpoint from the prior accepted commit. |
| `workflows/final-acceptance/SKILL.md` | Fixed-revision evidence fan-out, independent judgment, bounded repair, and re-judgment. |
| `skills/blender-bpy/SKILL.md` | Reusable method for job-driven `bpy`/BMesh creation, editing, inspection, rendering, and export. |
| `standards/browser-game-3d-asset/STANDARD.md` | Private 3D game-asset root: source authority, budgets, manifest, previews, runtime handoff, and artifact evidence. |
| `standards/blender-game-asset/STANDARD.md` | Blender-specific narrowing of `browser-game-3d-asset`. |
| `standards/threejs-browser-game/STANDARD.md` | Three.js game-code narrowing of `orch-code`. |
| `standards/browser-game-interface/STANDARD.md` | Rendered canvas, menu, HUD, focus, and accessibility narrowing of `orch-design`. |
| `standards/browser-game-playtest/STANDARD.md` | Ordinary-input session and provenance narrowing of `orch-research`. |
| `references/` | Run-record, job, asset-manifest, evidence-index, capture-matrix, rubric, and worked-example contracts. |
| `scripts/` | Capability probes, Blender process launcher and worker, manifest/GLB checks, capture indexing, and outside probe. |
| `tools.txt`, optional `requirements.txt`, `package.json`, lockfile | Tools and libraries used by package scripts only. Game dependencies stay in the target workspace. |

The standard bases are deliberate:

- `threejs-browser-game` MUST declare `narrows: orch-code`. Its artifact is executable repository code with ordinary git identity and code seams. A second generic game-code layer has no independent caller in this fixed-stack package and would duplicate ownership. If another engine later creates a real shared caller, that is the time to extract a common narrowing.
- `browser-game-3d-asset` MUST be a private root with the git adapter. A `.blend` source, GLB export, manifest, structural inspection, and rendered review require materially different evidence from code even though they land in the same repository. That satisfies the root admission rule without broadening the library. `blender-game-asset` MUST name that root as its one `narrows:` base and add only Blender-specific criteria.
- `browser-game-interface` MAY narrow `orch-design` for rendered interface evidence: canvas states, menus, HUD, focus, keyboard reach, breakpoints, and captures. It MUST NOT own mesh, material, rig, or animation quality; `orch-design` is a rendered-interface domain, not a generic 3D-asset base.
- `browser-game-playtest` MAY narrow `orch-research` because its artifact is a traceable evidence packet rather than a git candidate.

Each standard contains domain knowledge only. It contains no stage order, delegation, stop condition, or return contract. `blender-bpy` carries reusable technique and MUST declare `role: worker`; every making call that applies it resolves the `orch-worker` profile before the skill runs. The active host's existing profile record owns the concrete model and effort. Planner-profile asset judges inspect fixed outputs without entering the applied skill. Helper workflow prose orders calls. Package scripts own deterministic process and file boundaries. A standard has no scripts or dependencies.

A narrowing has one base. A ticket may list orthogonal standards only when they address the same coherent artifact and resolve to one adapter; a list is not a substitute for splitting different domains and handing identities across. This design normally keeps the calls separate:

1. an asset-making `do` stamps `blender-game-asset` and the applied `blender-bpy` skill;
2. an asset `judge` stamps the identical asset-standard chain against its fixed git revision and manifest;
3. after landing, the parent relays the asset's `artifact: git:<commit>` and manifest identity into a Three.js integration `do` stamped `threejs-browser-game`;
4. separate fixed-revision judges apply `threejs-browser-game` and, where relevant, `browser-game-interface`; and
5. actual-play calls stamp `browser-game-playtest` and hand evidence-packet identities to final acceptance.

All calls using these private names MUST occur in `browser-game` itself or one of its private helpers, which preserves the enclosing package scope. Calling another public workflow changes package scope, so that callee cannot resolve the caller's private standards. The rebuild needs no new public workflow, command registry, or generic workflow engine.

## Run record, authority, and invalidation

One compact run record indexes rather than transcribes the work. It identifies the brief and open decisions; target-workspace baseline; host, Blender, Three.js, browser, hardware, and backend capabilities; research packets; concept and acceptance matrix; every asset source/export manifest; each increment's input and output commit, checks, play evidence, findings, and disposition; and final evidence, repairs, and gaps.

Every decision records its owner, evidence identity, revision, and invalidation trigger. Product intent and promises are `kind: user-only`. Exact installed versions, renderer/backend choice, collision route, asset budgets, and test mechanics are empirical decisions. An unrelated user-only gap parks only its dependent work.

The brief revision, pinned dependencies, concept, art direction, target hardware, control map, asset contracts, and acceptance matrix freeze before production. A contradiction creates a new evidence and decision revision, names every invalidated descendant, and resumes at the earliest affected gate. It never silently rewrites a build ticket.

## Stages and literal gates

The workflow opens one frame. It reads the journal at the start of every wave, lands each completed wave before opening its successor, and relays typed artifact and findings lines verbatim.

| Stage | Inputs | Output and gate |
| --- | --- | --- |
| 0. Ask and audit | Brief, workspace, baseline | Prioritized self-question ledger, brief audit, capability inventory, and target hardware. Every material gap or user decision has an owner and route. |
| 1. Research, design, and reference freeze | Stage 0 identities, independent research packets | Synthesized evidence; detailed game concept; inspected GPT concept-art set; asset budgets; increment plan; and acceptance, capture, and performance matrices. A reader can build and falsify the whole game without selecting another engine. |
| 2. Prove pipelines | Frozen contract, representative asset jobs | I0 control tracer plus one Blender-to-GLB representative set imported through `GLTFLoader`. Production build, ordinary input, renders, validation, and in-engine scale/material/animation checks pass. |
| 3. Grow vertically | Prior accepted commit, next increment goal, accepted assets | Ordered playable commits I1–I4. Each commit builds, plays, is captured, and resolves blocking judgment before its successor opens. |
| 4. Accept | One frozen release-candidate commit and closed matrices | Maker-independent functional, asset, visual, play, compatibility, and performance evidence. Every hard gate and quality floor passes or returns findings. |
| 5. Repair and close | Verbatim findings, fixed evidence, round count | At most two scoped repair/re-judge rounds, then an outside probe over the joined tip or an honest return of remaining blocks. |

## Stage 0 — ask, audit the brief, and prove the fixed tools

The audit covers the game fantasy and audience; core and session loops; mechanics, world/content structure, progression, and terminal or continuing states; camera and controls; target hardware/browser/display; art, audio, and accessibility scope; asset and license constraints; delivery boundary; repository conventions; and the user's quality bar. It separates supplied facts, repository facts, reversible defaults, empirical questions, and user-only questions.

The capability inventory observes:

- clean/dirty workspace state, baseline, package manager, lockfile, build/test/serve commands, and installed Three.js identity;
- exact CPU, GPU, memory, OS, display refresh, viewport, device-pixel ratio, power mode, browser/version, and available WebGL/WebGPU backend;
- whether an agent can receive current visual feedback; focus the canvas; click; hold and release composite keyboard/mouse input; recover focus; pass user-gesture and pointer-lock gates; capture images/video/traces; and read console/network failures;
- the absolute Blender executable, version output, executable identity, background Python execution, render engines/devices, glTF exporter, and package script compatibility; and
- whether a production-like build can be served and reached without privileged game-state calls.

Missing Blender is a capability gap, so the workflow probes first. With current or standing installation authority, it performs one bounded, recorded setup step through the host's ordinary boundary and repeats the complete probe. Without authority, it returns the exact `kind: user-only` question with requirement/resume state and parks only dependent work. A changed executable invalidates dependent spikes, assets, renders, exports, and performance evidence. The workflow neither changes DCC nor accepts primitives as final art; it has no MCP, custom RPC service, or persistent Blender daemon.

The LLM then creates a numbered, prioritized self-question ledger from the brief, audit, probes, and repository evidence. It exposes missing, contradictory, risky, or infeasible promises and evidence needed for the fun loop, controls/camera, mechanics/states, world/content, progression/pacing, Three.js, Blender, assets, presentation, and target hardware. Rank follows ability to change the concept or acceptance plan. The LLM may propose reversible defaults but never answers a `kind: user-only` question.

## Stage 1 — research, design, and reference freeze

One independent research lane per material question cluster launches in parallel inside the fixed Three.js-and-Blender scope. The wave covers game/mechanic comparables, Three.js/browser feasibility, Blender asset feasibility/budgets, and host play/performance evidence. Without reading another lane's packet, each returns its question, source policy, dated source identities, claims/counterevidence, authorized spike observations, supported decisions, confidence, disagreements, and gaps. Synthesis waits for at least two independent packets, correlates them rather than voting, records unresolved conflicts, and gives every ledger item an answer or explicit gap under one evidence identity. Research does not compare engines or DCCs.

Synthesis feeds a build-ready concept, not a label. As applicable, it freezes the fantasy/fun loop and session shape; controls, disclosure, and camera; mechanics, rules, ownership, and state transitions; level/world/content design; progression, pacing, difficulty, terminal or continuing states, and replay/re-entry; art, animation, audio, UI, and accessibility direction; asset/provenance and geometry/material/rig/texture budgets; target hardware; and the vertical-slice plan. It marks inapplicable fields with reasons and derives required paths, play sessions, stress/capture matrices, rubric dimensions, and acceptance from the brief, preventing a later genre example from widening the contract.

After the written concept and before dependent Blender jobs, a GPT image model produces the required concept-art set. Its record binds exposed provider/model identity, prompt revision, inputs, rights/restrictions, output hashes, and asset/view coverage. A visual-capable maker and separate inspector view every candidate, record rejections/risks, and freeze selected silhouettes/views, scale cues, palette, materials, and lighting by identity for affected jobs. References never prove `.blend` or runtime quality. Unavailable generation or inspection yields `concept-art: unverified`, resume state, and parked dependent asset work rather than an unreviewed substitute.

New material evidence reopens the affected questions and lanes. A successor synthesis/concept revision names invalidated art selections, asset jobs, increments, captures, play accounts, performance cells, and judgments before resuming at the earliest affected stage; build steps never overwrite the decision in place.

## Native Blender job boundary

**Current fact:** Blender's command line can run without a UI, execute a Python file with `--python`, turn an uncaught command-line script exception into a chosen nonzero status with `--python-exit-code`, and pass following arguments untouched after `--`. Blender evaluates arguments in order ([command-line arguments](https://docs.blender.org/manual/en/5.1/advanced/command_line/arguments.html)).

The default route MUST launch the absolute, capability-probed Blender executable as a fresh subprocess for one job. The host-side package runner builds an argument array rather than interpolating a shell string. An illustrative launch is:

```text
<BLENDER_EXE> --background --factory-startup --python-exit-code 23 --python <PACKAGE>/scripts/blender_asset_job.py -- <JOB_DIR>/job.json
```

The executable path and version are pinned by the run's capability identity; `<PACKAGE>` is fixed by the workflow-package digest. The runner sets an explicit wall timeout and owns process-tree termination. The worker gets all variable input from `job.json`; it does not receive generated Python through `--python-expr` or open a socket.

Every job has a never-reused directory and id. The input file records schema version, job id, asset id, source mode, exact input hashes, expected source hash, seed, unit/axis/pivot contract, collection and object allowlists, mesh/material/texture/rig/animation budgets, render cameras, engine/device/sample settings, export options, and expected output paths. Paths resolve inside the job or declared workspace roots. One Blender process owns one `.blend` state. CPU jobs run under a measured process cap; GPU renders are serialized per GPU by default and widen only after a resource probe. Concurrent jobs never share a writable source or output path.

Source authority is explicit:

- **Procedural:** the generator/edit script, job JSON, and pinned reference inputs are authoritative. The `.blend`, GLB, and previews are derived and must rebuild from those identities.
- **Edited:** the pinned `.blend` is authoritative. A one-purpose Python edit job asserts its input hash, saves a new source revision, and records the edit script/job as provenance; it does not claim that earlier manual modeling is reproducible from code. Later validation/render/export jobs never mutate that accepted source.

Each affected job names the selected GPT concept-art identities frozen in Stage 1 and the concrete views or qualities they constrain. These images are references, not proof of a runtime asset. The accepted object is the inspected `.blend` plus its validated runtime export and in-engine evidence.

### Python method inside Blender

The worker prefers `bpy.data` and BMesh for deterministic object, mesh, material, collection, transform, and topology edits. Blender documents that operators depend on implicit UI context and may fail their poll where a direct API would give clearer access, while BMesh can be created, modified, written back, and freed without Edit Mode ([operator limitations](https://docs.blender.org/api/current/info_gotchas_operators.html), [BMesh API](https://docs.blender.org/api/current/bmesh.html)). The applied `blender-bpy` method therefore requires explicit names and direct references rather than selection-driven mutation.

Operators remain deliberate boundaries when they are the supported operation: open a pinned `.blend`, save a new `.blend`, bake materials, render, and export glTF. Before each operator, the worker sets and asserts scene, view layer, mode, active object, selection, render engine, device, frame, and output path as applicable; it checks the returned status and then validates the observable file or data change. Version-specific keyword support is capability-probed rather than inferred from moving `main`/`current` API pages.

Structural inspection records object/collection names; dependency and external-file references; unit scale; transforms, origin, forward marker, bounds, and ground contact; mesh triangle/vertex counts after evaluated modifiers; UVs, normals, tangents where required, non-manifold and degenerate geometry; material slots and texture dimensions/color roles; armatures, bone influences, actions, clip names/ranges, root motion, and sampled poses; cameras/lights used only for review; and every budget verdict. Seeds cover procedural choices, but the record does not promise byte-identical GPU renders across drivers or devices. It binds Blender/executable, OS/driver/backend, scene, script, job, source, export, and render identities and uses numeric and visual tolerances where bytes may vary.

### Render, inspect, export, and promote

The worker renders the asset from the actual gameplay camera and lighting contract, not only a flattering studio angle. It also emits a fixed turntable and, for animated assets, representative clip frames or a review animation that exposes silhouette, deformation, foot contact, looping, and attachments. The asset maker and judge MUST actually view these renders with a visual-capable tool and record which files and frames they inspected. A file's existence is not visual evidence.

The source uses a small glTF-compatible Principled metal/rough material vocabulary. Procedural or unsupported Blender shader networks are baked deliberately to the agreed base-color, metallic/roughness, normal, occlusion, and emissive textures; color textures and data textures retain distinct color-space roles. The export contract fixes whether modifiers are applied, because applying them can conflict with shape keys, and fixes action/NLA handling, clip names, sampling, skin influence limits, morph targets, textures, extras, and extensions. Blender's exporter supports meshes, metal/rough materials, textures, skinning, shape keys, and animation, but Blender and glTF material systems are not identical ([Blender glTF manual](https://docs.blender.org/manual/en/5.1/addons/import_export/scene_gltf2.html), [versioned export API](https://docs.blender.org/api/5.1/bpy.ops.export_scene.html)). The workflow verifies the chosen subset; it never assumes the viewport look survives export.

The handoff uses `.glb` for runtime delivery and keeps `.blend` as source. Its manifest fixes meters, exported +Y up, the model's gameplay-forward vector, pivot/origin, transform policy, bounds, collider/attachment metadata, material and texture roles, animation names/ranges, skeleton and morph budgets, required loader extensions/decoders, and hashes. Three.js recommends glTF for runtime assets and exposes glTF scenes, cameras, and animation clips through `GLTFLoader` ([Three.js loading guide](https://threejs.org/manual/en/loading-3d-models.html), [`GLTFLoader`](https://threejs.org/docs/pages/GLTFLoader.html)).

Blender writes candidate outputs and a worker-result manifest inside the unique job directory, with the manifest last. The host runner accepts nothing unless the process exits zero; the echoed job id and input digest match; every expected output is new, contained, nonempty, and hash-matched; structural and render evidence is complete; and the pinned Khronos validator produces a machine-readable report with no errors. The validator documents JSON reports and a nonzero CLI status on errors ([glTF Validator](https://github.com/KhronosGroup/glTF-Validator)). The runner then imports the GLB through the pinned Three.js production path, checks scale, orientation, materials, clip playback, bounds/collider alignment, load errors, and representative-device cost, and only then promotes source/export/manifest files into the candidate commit.

A timeout, nonzero exit, missing manifest, mismatched nonce/hash, validator error, stale path, partial file, or in-engine mismatch keeps the job directory as failed evidence and promotes nothing. There is no automatic retry. Diagnosis names the failed boundary; a new attempt gets a new job id and records its relationship to the failure.

**Qualified alternative:** Blender publishes a pip-installable `bpy` module, but its official documentation notes one active `.blend` per process, unsupported module reload, different startup/preferences, unavailable CLI-controlled functions, different signal handling, and possible GPU conflicts ([Blender as a Python module](https://docs.blender.org/api/current/info_advanced_blender_as_bpy.html)). A run MAY use embedded `bpy` only after pinning a distribution compatible with the required Blender version and passing the same render/export/signal/timeout probes. It still uses one disposable worker process and the same job/result files. It is not installed into or assumed compatible with the Orchflows interpreter. The executable subprocess remains the default because it preserves Blender's tested CLI, add-on, render, crash, and isolation behavior.

## Three.js runtime contract

Three.js supplies scene, rendering, loading, and animation primitives; it does not choose the game's architecture. Before I0, the concept assigns each system to an explicit module and seam:

- normal-clock loop and fixed/variable simulation timing, pause, visibility loss, and catch-up limits;
- ordinary input action map, focus/pointer lock where applicable, brief-derived navigation/interaction, collision/physics when used, and camera;
- game-state machine for boot, loading, entry, active play, pause where promised, every concept-derived phase or mode, terminal or continuing states, and replay or re-entry;
- entities and world/content ownership, every concept-derived mechanic and progression system, seeded randomness where used, lifecycle/pooling, and read-only diagnostics;
- `GLTFLoader` registry, progress, cancellation, error presentation, decoders/extensions, and fallback behavior;
- `AnimationMixer`/clip ownership, transitions, root-motion policy, skeleton budgets, and animation cleanup;
- renderer, scene, lights/shadows, materials, color management, culling, LOD, instancing, particles, and post-processing;
- audio unlock, mixing, pause/disposal, and observable failure where audio is promised; and
- DOM/canvas UI, HUD, accessibility, resize/DPR policy, and resource disposal.

The target workspace pins Three.js and every runtime decoder or physics dependency in its own lockfile. The workflow package owns none of them. A manifest using Draco, Meshopt, or KTX2 names the corresponding loader setup and decoder identity; omission or load failure is fatal. Load errors are visible game states and test seams. Removal disposes geometries, materials, textures/image bitmaps, render targets, skeletons, mixers, listeners, and audio according to ownership; Three.js warns that loader-created image bitmaps need special disposal handling ([`GLTFLoader`](https://threejs.org/docs/pages/GLTFLoader.html), [disposal guide](https://threejs.org/manual/en/how-to-dispose-of-objects.html)).

Renderer choice remains an empirical decision within Three.js. The default acceptance baseline SHOULD use pinned `WebGLRenderer` on WebGL 2. `WebGPURenderer` MAY replace it only when the exact Three.js revision, materials/post-processing, fallback behavior, browsers, captures, and performance cells pass; the current Three.js guide calls it experimental and documents material/post-processing differences and a WebGL 2 fallback ([renderer guide](https://threejs.org/manual/en/webgpurenderer)). A backend change invalidates visual and performance evidence.

Color inputs, working space, output transform, tone mapping, environment maps, and post-processing output are explicit. Three.js uses Linear-sRGB as its working space and requires correct annotations for color versus data textures ([color management](https://threejs.org/manual/en/color-management.html)). The imported asset test catches washed-out base color, incorrect normal/roughness treatment, lighting mismatch, and missing output conversion.

Instancing is admitted only for compatible shared geometry/material and a measured draw-call win. Animated crowds receive a declared strategy and peak-scenario proof; an ordinary `InstancedMesh` is not assumed to solve skeletal animation. Skeleton/bone/influence, active mixer, morph, particle, light/shadow, triangle, texture-memory, and draw-call limits come from the representative asset and peak-density measurements. They are budgets, not fashionable constants.

The production input boundary also serves testing. Browser automation may focus the canvas and press, hold, move, and release ordinary inputs. A lab build may select a seed, load a scenario, control simulation time, or expose a read-only snapshot; those controls are absent from production and never count as actual play or normal-clock performance.

## Playable vertical increments

Each `playable-increment` starts from the last accepted commit and performs one bounded sequence: make in an isolated candidate, run seam checks and a production build, land the checked commit, serve that exact identity, play with ordinary input, capture new and regression states, judge the fixed revision, and resolve any blocking finding before its successor opens.

| Increment | Required playable proof |
| --- | --- |
| I0 control tracer | The production build boots; entry/start, canvas focus, the primary control and camera actions, one representative concept-derived state transition, and replay or re-entry where promised cross the final input/state boundaries. A representative GLB loads through the production path. |
| I1 fun-loop slice | Several minutes of adaptive ordinary-input play prove the smallest complete fun loop, readable action/interaction feedback, the intended challenge or expressive opportunity, and meaningful choice or progression where promised. Representative playable subjects or focal props, interactive content, environment, animation, VFX, UI, and audio establish the applicable quality bar. |
| I2 full-session skeleton | The complete bounded acceptance journey or continuing-loop observation window is reachable with all required mechanics, world/content topology, progression, and terminal or continuing states. Every placeholder is identified, and every concept-derived stress scenario runs. |
| I3 production-content candidate | Approved Blender assets, animation, VFX, UI/audio, promised content breadth, balance or tuning, pacing, and distinctive moments replace every placeholder. Asset manifests and disposal checks close. |
| I4 release candidate | Full adaptive ordinary-input sessions cover every concept-derived required path and re-entry behavior; the complete capture matrix, compatibility checks, clean production build, declared-hardware traces, and outside-probe preparation bind one commit. |

Mass asset production begins only after the representative pipeline and I1 fun loop pass. Thereafter asset batches and code increments may run in parallel from explicit baselines, but asset commits land and hand manifests to the integration increment before that increment is judged. A final assembly view checks cast-wide scale, palette, lighting, density, animation, and camera readability because separately approved assets can still conflict in a scene.

## Actual agent playtesting

The target carries a small browser harness that can start/stop the server and browser, focus the game, issue ordinary keyboard/pointer actions, wait on a normal clock, return a current screenshot plus a compact read-only state snapshot, and start/stop evidence capture. It may adapt [Playwright's ordinary input APIs](https://playwright.dev/docs/input) or an equivalent host. It never invokes game methods to move the player, perform interactions, grant progression, advance content, or set a terminal or continuing state.

Evidence uses three labels:

- **actual play:** a player receives current visual feedback, sustains ordinary input on a normal clock, and adapts later input to observations;
- **scripted input:** a fixed ordinary-input sequence runs without adaptive observation; and
- **simulated:** fake time, scenario jumps, direct state mutation, bots, or headless/null rendering.

Only the first supports play-quality and complete-game claims. A session records artifact commit, harness/browser/device/backend, seed, real start/end time, input mode, checkpoints/captures, actions and choices, mechanic/progression/state transitions, recovery or re-entry, control problems, pacing, readability, feedback, fun/frustration observations, console/network errors, and confidence limits.

At least two maker-independent agents or contexts play I4. Together they cover every required ordinary-input path, mechanic, progression or content phase, terminal or continuing-state observation, and replay or re-entry behavior frozen by the concept; at least one begins from the normal entry surface and traverses control/tutorial disclosure. The concept defines a bounded observation goal for games without a conventional ending. If no available agent can both see and control real-time play, the workflow returns `actual-play: unverified` and cannot claim completion; scripted and simulated evidence retain their narrower labels.

## Real presented-frame performance

“60 fps” is a measurement cell. Each cell binds device/CPU/GPU/RAM, OS and power mode, browser/version, renderer/backend, display refresh, viewport/DPR, quality settings, commit, scenario/seed, warm/cold state, duration, instrumentation, raw paths, metric definitions, thresholds, and invalidation rule.

The frozen concept separates static readiness from animation cells. A stationary menu/pause surface must stay stable, error-free, and responsive to a marked ordinary-input transition; Chrome idle frames are expected and receive no 59 fps threshold. Promised continuous menu motion makes it an animation cell. Required animation cells cover representative ordinary-input play, each concept-derived worst case, and a full adaptive session's predeclared active spans, using brief-derived motion or a visible sentinel rendered through the game canvas. A separate DOM/compositor animation cannot satisfy the cell. The default 60 Hz contract uses three warm 60-second runs per bounded animation/stress scenario after warm-up.

For an animation run, let `T` be the complete marked foreground normal-clock window in seconds. `requestAnimationFrame` evidence must average at least 59 callbacks per second over `T`, place at least 99% of callback intervals at or below 18.33 ms, and contain no unexplained stall above 100 ms. Callback cadence remains necessary but does not prove Chrome compositor presentation.

**Current fact:** Chrome's protocol exposes `Tracing.start` with `traceConfig` and `ReturnAsStream`, `Tracing.end`, and `tracingComplete` with the stream and `dataLossOccurred`; JSON support is marked for future deprecation ([CDP Tracing](https://chromedevtools.github.io/devtools-protocol/tot/Tracing/)). The collector preserves the raw stream/completion metadata, pins and probes Chrome, CDP schema, format, categories, and parser, and pads both sides of the marked window.

**Current fact:** Pinned DevTools `FramesHandler` uses Meta, Renderer, and LayerTree handlers; consumes `BeginFrame`, `DrawFrame`, `DroppedFrame`, `RequestMainThreadFrame`, `BeginMainThreadFrame`, `Commit`/legacy `CompositeLayers`, `ActivateLayerTree`, `NeedsBeginFrameChanged`, and `SetLayerTreeId`; and emits `TimelineFrameModel` start/end/duration plus `idle`, `dropped`, and `isPartial` ([source revision `9f9f40b`](https://github.com/ChromeDevTools/devtools-frontend/blob/9f9f40ba5bca7e385be30535cdbf01a3a7e5ba44/front_end/models/trace/handlers/FramesHandler.ts)). Partial and dropped flags may overlap on one row. Some undrawn non-dropped `BeginFrame` events are omitted and widen the preceding frame. The versioned adapter therefore never treats row count as exhaustive display opportunities or claims physical scanout.

Before accepting a cell, discovery qualifies that binding with fixed static-idle, continuous-game-animation, and deliberate-stall traces. It proves padded extraction, `dataLossOccurred: false`, clock reconciliation, raw joins, game-canvas renderer/layer attribution, all flag overlaps, and stall failure through a flag or reduced wall-time clean rate. A negative fixture keeps callbacks or another compositor layer active while delaying canvas draws; the game-cadence claim must fail. This document has not implemented or tested the adapter. Unparsed formats, unqualified flags, missing/ambiguous attribution, loss, or incomplete coverage make dependent cells `performance: unverified`.

For a qualified animation window, `N` counts unique rows starting in `[start, end)`; `C` counts rows both attributed to the game canvas and free of `idle`, `dropped`, or `isPartial`; `I` counts idle rows; and `D` counts rows with `dropped OR isPartial`, once when both. Reports retain row identities and flags. Passing requires `N > 0`, `C / T >= 59`, `D / N <= 1%`, and callback thresholds. Idle/omitted/unattributed rows add nothing to `C`, so wall duration exposes lost cadence. Static windows report `N`, `I`, and flags without this denominator. Animation evidence reconciles callbacks, trace, rows, canvas attribution, and captures; static responses bind ordinary input and resulting capture to covered trace time.

Instrumented and minimally instrumented runs stay separate. Callback and clean-frame thresholds must both pass, while scenario, seed, markers, duration, and artifact must reconcile; contradictions close only after cause and matching rerun. Fake clocks, background tabs, throttling, null renderers, fast-forward, and dev builds are diagnostic only.

Failure attribution distinguishes simulation/main-thread work, garbage collection, draw calls, GPU/fill rate, shader compilation, asset decode/upload, animation/skinning, memory growth, and harness overhead. One repair targets the measured bottleneck and repeats the identical cell. Lowering resolution, content density, effects, browser cohort, or hardware target requires a visible decision revision; it cannot recolor a failure.

## Fixed-revision judgment, repair, and close

Final acceptance freezes one release-candidate commit before review. Maker-independent lanes gather deterministic build/mechanics results, asset/provenance manifests, visual captures, ordinary-input play accounts, compatibility/console/network results, and physical-device traces. Collectors do not edit the candidate. Judges receive the Goal, fixed artifact identity, their one stamped lens, and the evidence index rather than maker conversation.

The concept-derived capture matrix covers every viewport/DPR at boot/loading/errors, normal entry/control disclosure, opening play, each required mechanic/progression/content phase, representative session or continuing-loop states, every visual stress/readability condition, promised pause/settings, terminal or continuing states, and replay/re-entry. Inapplicable cells need a frozen rationale. Each capture binds commit, viewport/DPR, browser/backend, state, seed, and timestamp.

Before scoring, the final maker-independent judge enumerates and visually inspects every required capture and reads every playtester account in full. Its coverage record maps every matrix cell, gate, and score to identities; names omissions; and correlates conflicts among visuals, accounts, snapshots, console/network results, and performance. A missing capture, unread account, broken identity, or unresolved conflict is an unverified hard gate; curated subsets cannot pass. Asset gameplay-camera and turntable/animation inspection remains distinct and never substitutes for in-engine captures.

Hard gates cover production boot; controls/focus; every concept-frozen mechanic, content promise, progression, terminal/continuing observation, and replay/re-entry; zero undisclosed placeholders or blocking errors; provenance closure; complete play/capture coverage; and each performance cell with callback/Chrome-frame agreement. The brief adds genre-specific gates and dimensions before production. The universal 0–4 floor covers loop/purpose clarity, control/camera feel, interaction feedback, state/opportunity readability, appropriate pacing, promised choice/progression, level/world and 3D art/motion coherence, promised UI/audio/accessibility support, stability, and polish. Only the frozen concept may omit a dimension, with reason. Every gate and applicable score of at least 3 must pass.

Findings are observable complaints tied to evidence and a responsible seam. They distinguish defects, unverified claims, and preferences. **Where the judge blocks, one repair `do` is handed the `findings:` line verbatim, then one re-judge; two rounds is the bound.** A repair goal names only the accepted complaints, affected evidence, and regression subset. Re-judgment repeats affected gates and a smoke subset of unaffected paths.

**Close on a command run outside every child; never on a child's own claim.** The outside probe checks the joined commit, installs/builds from the workspace lockfile, serves production output, exercises boot, normal entry, representative concept-derived mechanics/state transitions, and replay/re-entry where promised through ordinary input, validates evidence/manifest identities and complete judge-coverage records, and verifies collector qualification, raw callback/trace identities, metric rows, thresholds, and agreement verdicts for every required cell. It prints the exact accepted git identity. After two blocked rounds or any unclosed hard gate, the workflow returns the fixed revision and gaps without claiming completion.

## Failure and resumption

| Event | Required behavior |
| --- | --- |
| Missing product promise | File one `kind: user-only` question verbatim; park only dependent work and revise the brief on answer. |
| Missing/changed Blender, browser, or tool | Record observed and required capability. Use current or standing installation authority for one bounded setup step and re-probe; otherwise return the verbatim user-only question and resume state. Invalidate dependent evidence on identity change. |
| Blender job failure | Preserve job, source, script/package identity, stdout/stderr, partial outputs, and diagnosis; promote nothing; retry only as a new job. |
| Three.js load/runtime failure | Keep candidate unlanded, bind console/network/manifest evidence, and repair the responsible loader, asset, or runtime seam. |
| Agent cannot see/control play | Preserve narrower scripted/simulated evidence; dispatch a capable lane or return actual play unverified. |
| Performance miss/contradiction | Preserve raw callbacks and trace, attribute, repair one seam, and repeat the same cell. |
| Judge block | Apply the two-round rule, then return remaining blocks. |
| Crash/context loss | Use `orchflows resume`, read the frame journal, resolve recorded identities/package digest, land completed outcomes, and reopen only absent or expired dispatches. |
| Package changes mid-run | Refuse stale admission and start a successor run citing predecessor evidence; never mix package contracts. |

## Worked invocation: one-level 3D survivor game

```text
/browser-game build me a 3d vampire survivors-like game with 1 level but many waves that ends in a final boss fight
```

Discovery treats 3D, one level, many waves, and a final boss as fixed intent; Three.js and Blender come from the workflow contract. It audits session length, controls, target hardware/browser, art/audio/accessibility, asset rights, and delivery. A reversible proposal might be a 12-minute local run, keyboard movement with automatic attacks, an original stylized low-poly direction, and the available development machine plus pinned Chromium/WebGL 2 as the first 60 Hz cell. Broader support remains user-owned.

The LLM's prioritized questions include how many simultaneous threats remain readable, what makes upgrades change play, how keyboard-only and pointer variants steer, how waves create relief and escalation, how the boss tests learned movement, which Blender set proves the style, and what the declared machine can present at 60 Hz. Independent lanes research survivor pacing and boss counterplay, Three.js many-entity/runtime feasibility, Blender geometry/material/rig production, and host play/performance capture in parallel; synthesis resolves their evidence and gaps before concept work. There is no engine or DCC bakeoff.

The detailed concept fixes an arena with landmarks and spawn exclusions; controls and camera; attack, damage, experience, upgrade, spawn, death, win, and restart states; grace, escalation, relief, peak, and boss beats; melee/ranged/fast/tank/elite pressures; upgrade families and build choices; readable damage and telegraphs; asset/audio/UI budgets; and a multi-phase final boss. GPT image generation then produces inspected hero/enemy/boss silhouettes, environment/prop language, palette/material references, and useful views by recorded identity for the Blender jobs. Exact counts, timings, and selected art come from the synthesized evidence and review, not this example.

The representative Blender set contains hero, enemy, environment kit, one effect mesh/material, and named clips. Each runs through a unique file job, gameplay-camera and turntable/animation review, GLB validation, and `GLTFLoader` import before I1. The vertical plan is:

1. I0 proves production boot, focus, movement, camera, damage, terminal states, restart, and representative GLB loading.
2. I1 proves a three-minute combat/reward loop with the representative production set.
3. I2 makes the full 12-minute wave and boss skeleton playable, inventories placeholders, and runs peak/boss stress seeds.
4. I3 replaces every placeholder and closes animation, VFX, UI/audio, balance, pacing, disposal, and asset manifests.
5. I4 gathers two independent ordinary-input accounts, full win/loss/restart coverage, the complete combat/wave/upgrade/boss capture matrix, static-menu readiness, and three-run callback/Chrome-frame cells for representative play, peak wave, heaviest boss effects, and the full adaptive session.

Final judgment blocks on incomplete boss play, unreadable peak action, hollow upgrades, focus failure, asset/scale/material drift, unviewed renders, actual-play gaps, or any failed or contradictory 60 fps cell. The workflow gets two scoped repair/re-judge rounds. The outside probe alone closes the joined revision.

## Implementation acceptance for the future rebuild

The future workflow implementation is complete when the package has one public entry and the private structure above; all literal private names resolve inside its package scope; a scratch run journals prioritized self-questions, parallel independent packets, synthesis, the detailed concept, inspected GPT concept-art identities, pipeline proof, at least two vertical increments, actual play, complete final-judge evidence coverage, bounded repair, and outside close; missing-tool or image capability, absent user authority, Blender failure, unplayable host, unqualified/lost performance trace, evidence contradiction, and repair-exhaustion paths return closed evidence and resume state; validators check identities and shapes rather than sentences; target dependencies remain in the target lockfile; and the repository's full required gate passes at the implementation commit.

## Compact primary-source list

Internal owners: [custom workflow authoring](../docs/custom-workflow-authoring.md), [standard authoring](../docs/standard-authoring.md), [standard contract](../contracts/standard.md), [composition](../rules/composition.md), [vocabulary](../docs/vocabulary.md), [architecture](../ARCHITECTURE.md), and [repository checks](../AGENTS.md).

External primary sources: [Blender command-line arguments](https://docs.blender.org/manual/en/5.1/advanced/command_line/arguments.html), [Blender as a Python module](https://docs.blender.org/api/current/info_advanced_blender_as_bpy.html), [operator limitations](https://docs.blender.org/api/current/info_gotchas_operators.html), [BMesh](https://docs.blender.org/api/current/bmesh.html), [Blender glTF manual](https://docs.blender.org/manual/en/5.1/addons/import_export/scene_gltf2.html), [Blender 5.1 export API](https://docs.blender.org/api/5.1/bpy.ops.export_scene.html), [Three.js model loading](https://threejs.org/manual/en/loading-3d-models.html), [`GLTFLoader`](https://threejs.org/docs/pages/GLTFLoader.html), [Three.js color management](https://threejs.org/manual/en/color-management.html), [Three.js renderer guide](https://threejs.org/manual/en/webgpurenderer), [Three.js disposal](https://threejs.org/manual/en/how-to-dispose-of-objects.html), [Khronos glTF Validator](https://github.com/KhronosGroup/glTF-Validator), [Playwright input](https://playwright.dev/docs/input), [Chrome performance reference](https://developer.chrome.com/docs/devtools/performance/reference), [CDP Tracing domain](https://chromedevtools.github.io/devtools-protocol/tot/Tracing/), and [pinned DevTools `FramesHandler`](https://github.com/ChromeDevTools/devtools-frontend/blob/9f9f40ba5bca7e385be30535cdbf01a3a7e5ba44/front_end/models/trace/handlers/FramesHandler.ts). Claims were checked on 2026-09-05; moving API pages describe current capability only, while each run pins and probes the versions it actually invokes.
