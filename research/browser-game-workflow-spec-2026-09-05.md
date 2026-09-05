# Browser-game workflow rebuild specification

The current `browser-game` workflow can decide what should happen next, but it cannot yet earn the claim that it built a complete game. The rebuilt workflow earns that claim only when a fixed revision survives playable vertical increments, coherent asset production, ordinary-input play by agents that can actually see and control the game, and independent acceptance on declared hardware. This document specifies that workflow; it does not implement it or a game.

All **MUST**, **SHOULD**, and **MAY** statements below are recommended workflow policy. Statements labeled **Current fact** report primary documentation checked on 2026-09-05. A future run must recheck facts whose tool, engine, browser, or model identity has changed.

## Outcome and completion contract

The public workflow remains `browser-game`. Its invocation takes `brief`, the user's complete natural-language request, and `workspace`, the target git repository. Options embedded in the brief are authoritative. The workflow may derive routine implementation defaults, but it must not silently create a product promise about supported hardware, browsers, accessibility, licensing, monetization, telemetry, or public release.

A successful return contains:

- `artifact: git:<commit>` for the accepted game revision;
- an evidence-index identity binding the brief revision, research packets, concept revision, asset manifest, playable-increment ledger, play sessions, captures, performance traces, judge findings, and repair history;
- the exact outside probe and its passing observation at that commit; and
- `gaps: []`, or a non-success disposition with every remaining gap.

The complete-game gate requires a browser-served production build that a player can start without developer tools; documented controls; a coherent core loop; the promised level and progression; reachable win and loss states; pause where applicable; restart from both terminal states; final production assets rather than undisclosed placeholders; no blocking console or asset-load errors; actual play evidence; and the declared 60 fps performance contract. A prototype, automated state simulation, screenshot gallery, or locally green unit suite cannot satisfy this gate by itself.

The workflow ends at an accepted repository revision. Publishing, buying assets, accepting licenses, installing system software without standing authorization, and making commercial or support promises are separate user-authorized actions.

## Baseline and migration

The specification was derived from clean repository revision `a7f19004d595fa09ab1aeda685f70002af2388fd`. At that revision, the [public workflow](../example-workflows/browser-game/SKILL.md) makes a program record, an evidence packet, a checkpoint, and possibly a kind-separated successor plan. Its [intake policy](../example-workflows/references/browser-game-intake-policy.json) usefully separates user-only decisions from empirical ones; its validator binds evidence and invalidation identities. It does not make assets or code, open playable increments, perform actual play, gather frame evidence, or accept a complete game.

The updated authoring contract at `C:/Users/danhm/.orchflows/lib/docs/custom-workflow-authoring.md` permits a public workflow package to own private workflows, skills, standards, references, scripts, and dependencies under its directory, all pinned by one package digest. The rebuild MUST use that package shape. It SHOULD preserve four ideas from the current design: two invocation inputs, atomic authority, immutable evidence identities, and explicit invalidation. It SHOULD replace the fixed Q-01–Q-12 ceremony with a smaller run record driven by this workflow's gates. It MUST migrate browser-game-specific references and validators into the package before removing the current validator allowlist; compatibility tests stay green until that migration lands.

The current records migrate by responsibility rather than by copying their schemas. Product-brief cells become the brief audit and open-decision list. Decision, risk, and experiment entries become the discovery ledger, retained only when they change a downstream gate. Asset and performance contracts become the manifest and measurement cells defined below. QA-oracle entries become the frozen acceptance matrix. The successor plan becomes the ordered playable-increment ledger. Release-policy fields are created only when the brief actually asks the workflow to prepare a release; they do not burden an ordinary local game build.

## Package and reusable composition

The public `SKILL.md` must stay short enough to expose control flow at a skim. Domain knowledge and executable checks belong in private standards, references, and scripts.

| Package path | One owner and purpose |
| --- | --- |
| `SKILL.md` | Public `browser-game` contract and ordered stage calls. |
| `workflows/discovery/SKILL.md` | Brief audit, capability inventory, parallel research, synthesis, and concept-ready gate. |
| `workflows/playable-increment/SKILL.md` | One durable build/check/play/judge checkpoint, invoked once per planned vertical increment. |
| `workflows/final-acceptance/SKILL.md` | Fixed-revision evidence fan-out, discriminating judgment, bounded repair, and re-judgment. |
| `standards/browser-game-code/STANDARD.md` | Narrowing of `orch-code`: runtime states, input boundary, deterministic lab mode, production build, game probes, and performance instrumentation. |
| `standards/browser-game-visual/STANDARD.md` | Narrowing of `orch-design`: art direction, asset budgets, capture states, readability, feedback, and visual coherence. |
| `standards/browser-game-playtest/STANDARD.md` | Narrowing of `orch-research`: ordinary-input session protocol, player account, provenance, confidence, and gaps. |
| `references/` | Lean contracts for the run record, asset manifest, evidence index, rubrics, capture matrix, and worked 3D example. |
| `scripts/` | Deterministic capability, evidence, asset, and outside-probe checks only; generation judgment stays in agents. |
| `tools.txt`, optional `package.json` and lockfile | Only tools and Node packages that package scripts themselves execute. Game dependencies remain in the target workspace and its lockfile. |

The public workflow opens one frame with `tickets.py frame-open <run> --goal-file <goal> --workflow browser-game`. It calls `discovery`, then freezes the resulting research and concept inputs before any production candidate exists. Art-direction alternatives SHOULD use the existing public `bakeoff` workflow when more than one credible direction remains; that call intentionally enters `bakeoff`'s own package scope and carries no browser-game-private standard. Each planned vertical increment calls the private `playable-increment`; its making stays in `browser-game` package scope, so every standard-stamped `do`/`judge` call resolves `browser-game-code`, `browser-game-visual`, and `browser-game-playtest` there. It does not call public `checkpointed-build`; the private workflow owns its wave plan and close behavior and quotes the shared idioms: **Where the judge blocks, one repair `do` is handed the `findings:` line verbatim, then one re-judge; two rounds is the bound.** **Close on a command run outside every child; never on a child's own claim.** The final fixed revision calls `final-acceptance`.

Only `tickets.py do` makes artifacts and only `tickets.py judge` judges fixed artifacts. Every making call names the target workspace, isolation, bound, and applicable package-private standard. Calls in one parallel wave land before the next wave opens. Parents relay `artifact:` and `findings:` lines verbatim and read each frame journal at the start of the next wave. Package-private literal names resolve in `browser-game` scope. The public `bakeoff` call is an intentional cross-package composition and opens `bakeoff`'s own package scope; it does not receive browser-game-private standards. No browser-game standard moves to a public ring without independently justified callers and ownership.

This split earns its context cost. Discovery has independent research lanes and must survive interruption. Each playable increment needs an isolated candidate, evidence-bound landing, and a journal. Final acceptance needs eyes independent of the makers. Small deterministic operations remain scripts or prose rather than new agents.

The stage contracts are closed before implementation:

| Stage | Inputs | Outputs | Gate to the next stage |
| --- | --- | --- | --- |
| 0. Brief and capabilities | Brief, workspace, baseline, host/tool access | Brief-audit revision, open decisions, capability inventory, declared development hardware | No hidden material gap; every missing capability or user decision has a route. |
| 1. Research and route | Stage 0 identities, bounded research questions | Independent evidence packets, engine spikes, synthesis, selected/pinned production route | Primary support or declared gap for every load-bearing claim; route identity frozen. |
| 2. Concept and art direction | Brief revision, research identity, selected route | Game concept contract, level/wave/boss plan, acceptance matrix, winning art direction and style bible | Whole game is buildable and falsifiable; content and asset budgets close. |
| 3. Asset-pipeline proof | Style bible, representative asset contracts, tool identities, engine import proof | One approved representative 2D or 3D set plus a costed production backlog and source/export/preview evidence | The pipeline validates and renders in engine within budget. Mass production remains closed until I1 proves the fun loop. |
| 4. Playable increments | Frozen concept, accepted prior commit, applicable assets, increment goal | Ordered accepted git commits and increment evidence ledger | Each commit builds, plays through its promised slice with ordinary input, passes checks, and resolves blocking findings before its successor opens. |
| 5. Final evidence and judgment | One frozen release-candidate commit and closed acceptance matrix | Functional results, capture inventory, play accounts, compatibility logs, physical-device traces, independent findings | Every hard gate passes and every quality score reaches the stated floor, or findings enter bounded repair. |
| 6. Repair and close | Findings line, fixed evidence, repair-round count | At most two scoped repair commits and re-judgments; final evidence index; outside-probe observation | Outside probe passes at the joined commit, or the run returns fixed remaining blocks and gaps without a complete-game claim. |

## Run record, authority, and invalidation

One compact run record is the index, not a transcript. It MUST version and identify:

1. the brief and open decisions;
2. host, tool, engine, model, browser, hardware, and target-workspace capabilities;
3. research claims and evidence packets;
4. the concept contract and its frozen acceptance matrix;
5. the asset manifest and production provenance;
6. each playable increment's goal, input commit, output commit, checks, play evidence, findings, and disposition; and
7. final acceptance evidence, repairs, and gaps.

Every decision records its owner, rationale, evidence identity, revision, and invalidation trigger. Product intent and promises are `kind: user-only`; the root relays one such question verbatim when the missing answer would materially change scope or acceptance. Engine choice, renderer/backend choice, implementation structure, and tool route are empirical decisions resolved by documented capability checks or experiments. An unrelated user-only gap must not stop independent research or making.

The concept revision, selected engine and lockfile, art-direction identity, target hardware matrix, asset budgets, control map, and acceptance matrix are frozen inputs to production. A later contradiction does not get smuggled into a build ticket: it creates a new evidence packet and decision revision, names every invalidated descendant, and resumes at the earliest affected gate. This keeps all research in the research stage while allowing an explicit research resumption when reality disproves a premise.

## Stage 0 — audit the brief and prove capabilities

Discovery first asks itself what is missing. The audit covers game fantasy and audience; 2D/3D; core loop and comparable mechanics; session length; level, wave, boss, progression, and terminal states; controls and input devices; target hardware/browser/display; visual and audio direction; asset and license constraints; accessibility promises; delivery boundary; existing repository conventions; and the user's definition of quality. It records supplied answers, derivable repository facts, reversible workflow defaults, empirical questions, and user-only questions separately.

The capability inventory MUST observe rather than assume:

- clean/dirty workspace state, baseline commit, package manager, lockfile, build and test commands;
- exact CPU, GPU, memory, OS, display refresh, viewport, device-pixel ratio, power mode, browser/version, and graphics backend available for performance work;
- whether the agent can receive current visual feedback; focus the canvas; click; hold and release multiple keys; sustain composite keyboard/mouse input in real time; recover focus; satisfy a user-gesture gate; use pointer lock when the design needs it; capture screenshots/video/traces; and read console/network failures;
- whether image generation can generate, edit, retain references across turns, and deliver the required transparency and dimensions with the currently available model/tool;
- for 3D, the exact Blender executable/version, background Python execution, render and glTF export, and whether an MCP server is installed and callable; and
- whether the target repository can serve a production-like build and the harness can reach it without privileged application calls.

**Policy:** Blender is the default 3D authoring application, not an assumed capability. If it is missing, discovery records the gap. With prior authorization, a separate preparation action may install and pin it, then repeat the capability checks. Without authorization, the 3D asset branch pauses for one user decision; it must not quietly switch DCCs or claim that generated primitive geometry is production art.

**Gate:** the audit has no hidden material gaps; every required tool is observed or routed; at least one credible engine/asset/playtest path is testable; and a physical development target is declared for 60 fps. If no available agent can both see and control fast real-time gameplay, discovery records that actual play requires a compatible external lane. It does not downgrade scripted simulation into playtesting.

## Stage 1 — concentrate research and select the production route

All planned external research runs here, in parallel lanes under `orch-research`. Each lane dates atomic claims, uses current primary sources, searches for disconfirming evidence, and returns explicit gaps. Synthesis begins only after the lanes land.

| Lane | Required questions and evidence |
| --- | --- |
| Mechanics and comparables | What makes the requested loop readable and fun; how comparable games pace threat, rewards, build choices, level pressure, bosses, loss, and replay; direct gameplay or developer material for every cited behavior. |
| Engine and browser | Current 2D/3D engine fit, license, browser/backend support, repository integration, build size, input, audio, physics, asset loading, debugging, automation, and maintenance; a pinned minimal spike for each finalist. |
| Art and asset pipeline | Feasible style, production volume, 2D/3D branch, image-generation capability, Blender/automation route, interchange, compression, animation, provenance, licensing, and validation. |
| Playtest and performance | Host control limits, ordinary versus privileged input, deterministic test mode, trace/capture methods, target hardware scenarios, metrics, thresholds, and failure attribution. |

Current documentation supports these starting facts and policies:

| Current fact (checked 2026-09-05) | Workflow policy it informs |
| --- | --- |
| Phaser describes itself as a browser-first **2D** framework using JavaScript/TypeScript with WebGL and Canvas renderers ([Phaser docs](https://docs.phaser.io/)). | Start a 2D selection with Phaser unless the workspace or brief establishes a stronger candidate. |
| PlayCanvas supports standalone Vite/TypeScript projects; its current engine requires WebGL 2, offers WebGPU in beta with WebGL 2 fallback, and exposes a null backend for headless use ([standalone](https://developer.playcanvas.com/user-manual/engine/standalone/), [graphics](https://developer.playcanvas.com/user-manual/graphics/), [browser support](https://developer.playcanvas.com/user-manual/engine/supported-browsers/)). | Start a code-first 3D selection with PlayCanvas standalone and a WebGL 2 acceptance baseline. Treat WebGPU as a separately measured backend. Compare Babylon.js when its integrated game features reduce project risk; use Three.js only when the team deliberately accepts assembling more game systems. |
| Godot 4 web export currently requires WebAssembly and WebGL 2, has no C# web export, defaults to a more compatible single-thread export, and requires cross-origin isolation for threaded export ([Godot web export](https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_web.html)). | Admit Godot only when editor workflow or native portability is valuable and a browser export spike passes the actual host, headers, payload, audio, and automation gates. |
| Blender exposes background command execution and Python glTF export; Blender's glTF exporter covers meshes, PBR materials, textures, skinning, animation, and related features ([CLI](https://docs.blender.org/manual/en/5.1/advanced/command_line/arguments.html), [Python export API](https://docs.blender.org/api/main/bpy.ops.export_scene.html), [glTF add-on](https://docs.blender.org/manual/en/dev/addons/scene_gltf2.html)). | Make checked-in or generated `bpy` scripts plus background Blender runs the reproducible production route. |
| Blender's official Lab MCP requires Blender 5.1 or newer and external components, executes model-generated code without guards, and recommends isolation ([Blender Lab MCP](https://www.blender.org/lab/mcp-server/)); community servers add different bridges and capabilities ([community example](https://github.com/MCPBlender/blender-mcp)). | MCP is an optional interactive inspection route after an exact capability, version, network, and trust probe. Pin it, isolate it, save before use, and reproduce accepted asset changes through the deterministic Blender script/export path. |
| glTF is a runtime delivery format rather than an authoring format, and Khronos publishes a validator that emits machine-readable issues and exits nonzero on errors ([glTF specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html), [validator](https://github.com/KhronosGroup/glTF-Validator)). | Keep `.blend` or other source identity beside exported `.glb`; validate every export and test it in the selected engine. Optimize only after visual and runtime comparison. |
| Playwright distinguishes ordinary-condition clicks from programmatic `dispatchEvent`, can hold/release keyboard input, and its clock overrides `requestAnimationFrame` and `performance` ([actions](https://playwright.dev/docs/input), [keyboard](https://playwright.dev/docs/api/class-keyboard), [clock](https://playwright.dev/docs/clock)). | Use browser-level actions and an unmodified clock for actual play and FPS. Fake time and direct state hooks are deterministic functional evidence only. |
| Chrome's Performance panel records runtime activity, screenshots, frame duration, partially presented frames, and dropped frames ([performance reference](https://developer.chrome.com/docs/devtools/performance/reference), [runtime guide](https://developer.chrome.com/docs/devtools/performance)). | Bind raw real-time metrics to a browser trace on the declared device; a game-owned FPS counter alone cannot close performance. |
| OpenAI's current image guide documents generation, editing, and multi-turn reference editing; output options such as transparency depend on the selected model and parameters ([image generation guide](https://developers.openai.com/api/docs/guides/image-generation)). | Probe the available image tool/model at run time. Use it for concept exploration and only for production assets whose consistency, transparency, dimensions, rights, and in-engine result pass their asset contract. |

Each engine finalist spike MUST boot from a pinned lockfile, import one representative asset, accept ordinary input, expose the proposed observation-only harness, produce a production build, and run the peak-density micro-scenario on the declared device. Synthesis records why the winner won and what would invalidate it. Popularity, model familiarity, or an unrun template is not evidence.

**Gate:** one engine/backend, language, package/version lock, rendering strategy, physics/collision approach, 2D/3D asset route, test harness, target device matrix, and performance protocol are selected. Load-bearing claims have primary evidence or a declared gap. No production call opens before the research identity and decision revision are fixed.

## Stage 2 — freeze the concept and visual system

Conceptualization turns the brief and research into one buildable game contract. It MUST define the player fantasy; moment-to-moment and session loops; controls; camera; game-state machine; combat verbs; damage and invulnerability rules; enemy and upgrade taxonomies; progression economy; loss, win, and restart; session length; level topology; wave pacing; boss phases and counterplay; HUD and feedback; audio cues; accessibility scope; content budget; and measurable acceptance examples. Tunable content lives in data rather than being scattered through engine code.

Level design begins as a graybox evidence problem. For each level, the contract fixes traversable bounds, camera behavior, landmarks, spawn and exclusion zones, obstacle readability, density limits, hazard/relief rhythm, and the path from opening safety through peak pressure to boss space. A wave table names time/trigger, enemy composition, spawn rule, intensity purpose, reward beat, performance budget, and boss transition. The final boss has readable telegraphs, distinct phases, a reachable defeat condition, and a terminal-state handoff.

Art direction begins with a reference board and three sufficiently different concept directions unless the brief already fixes one. When image generation is available, it MAY make concept boards and turnarounds under a recorded model/tool identity, prompts, inputs, and edit lineage. `bakeoff` selects against a frozen rubric: silhouette readability at play distance, originality, palette and material coherence, production feasibility, animation needs, UI compatibility, and target-device cost. The winner becomes a style bible with approved shapes, palette, materials, lighting, camera, scale, VFX density, UI rules, and forbidden drift.

**Gate:** a reader can implement and falsify the game without inventing its loop; the whole session, level, waves, and boss are represented; the capture matrix and quality rubric are closed; asset counts and budgets fit the chosen route; and concept art proves direction rather than masquerading as runtime production.

## Stage 3 — prove the asset pipeline, then produce against accepted play

Every asset has one manifest entry: stable id and gameplay role; source and license/provenance; style tags; dimensions or world scale; pivot/origin; silhouette target; animation/state list; collider and attachment rules; geometry, texture, material, atlas, draw-call, and memory budgets as applicable; source identity; runtime export identity; preview captures; validation output; and in-engine observation. Generated or downloaded material with unresolved rights remains a gap and cannot enter the accepted build.

The 2D branch SHOULD make a small representative atlas before fan-out. It fixes pixel density, working and runtime color space, palette, transparency, trim, pivot, padding/extrusion, filtering, animation cadence, naming, and fallback rules. A script checks dimensions, alpha, duplicate names, atlas bounds, and manifest coverage; a visual judge checks animation, play-distance silhouette, palette, and in-engine compositing.

The 3D branch uses Blender by default. It SHOULD create one representative character, enemy, environment kit, and effect before parallel production. Accepted source changes must be reproducible from a pinned `.blend` identity and/or checked-in `bpy` script. Exported `.glb` files pass the Khronos validator, engine import, scale/orientation, transform, skin, animation, material/texture, collider, and preview checks. Optimization produces a new identity and must show both size/performance gain and no blocking visual regression. MCP-created work is provisional until saved, manifested, and reproduced or normalized by the deterministic export path.

The representative set proves feasibility before mechanics harden around bad assets, but mass production MAY fan out only after both that set and I1's fun-loop gate pass. Production then runs alongside the content-bearing increments, with each lane receiving the frozen style bible and asset contract rather than another lane's improvisation. A terminal integration pass inspects the assembled cast and level because individually attractive assets can still disagree in scale, palette, lighting, or density.

## Stage 4 — build in playable vertical increments

The plan cuts the game into the smallest sequence whose every revision is bootable and playable. Each `playable-increment` starts from the last landed commit and follows the same contract:

1. make the scoped mechanics/content/assets in an isolated candidate;
2. run deterministic seam checks and a production build;
3. land only the checked commit;
4. serve that exact commit and perform a short ordinary-input play session;
5. capture the increment's new and regression states;
6. judge the fixed commit against code, visual, play, and increment criteria; and
7. repair a blocking finding within the increment before opening its successor.

The default milestone shape is:

| Increment | Required playable proof |
| --- | --- |
| I0 control tracer | Production build boots; menu/start, focus, movement/aim, pause if promised, loss, win stub, and restart use the final input boundary. Graybox visuals are explicit. |
| I1 fun-loop slice | Several minutes of representative combat include one weapon, damage/feedback, enemy pressure, rewards, an upgrade choice, death, and restart. One representative production asset set proves the visual pipeline. |
| I2 full-session skeleton | The complete level, all wave timings, progression topology, boss phases, win/loss, and restart are reachable with placeholder content clearly inventoried. Peak-density and boss stress seeds run. |
| I3 production-content candidate | Approved assets, animation, VFX, UI, audio in scope, enemy/upgrade variety, balance, pacing, and boss polish replace every placeholder. The asset manifest has no unowned entry. |
| I4 release candidate | Full ordinary-input sessions, capture matrix, compatibility checks, target-device traces, clean production build, and final outside probe pass at one revision. |

Mechanics MUST expose seams that support both play quality and diagnosis: explicit game states; an input action map separated from simulation; seeded randomness; stable time-step policy; data-driven waves, enemies, upgrades, and boss phases; bounded entity/particle/audio lifecycles; and observable counters for state, entities, draw calls, frame timing, and errors. The chosen collision, pooling, instancing, culling, and spatial-query strategies are settled by the peak scenario, not prescribed by fashion.

A deterministic lab build MAY select a seed, load a scenario, advance controlled time, or expose a read-only snapshot. Those controls are disabled or inaccessible in the production build. They accelerate functional and balance tests but never replace ordinary-input play or normal-clock performance evidence.

## Actual agent playtesting and the harness boundary

The target repository SHOULD carry a small, engine-neutral play harness so Codex, Claude Code, or another capable agent can use the same protocol. It provides commands to launch/close the server and browser, focus the game, press/hold/release ordinary keys or pointer buttons, wait in real time, observe a current screenshot plus a compact read-only state snapshot, and start/stop evidence capture. The harness adapts to Playwright or a host's equivalent; it does not call game methods to move, damage, choose upgrades, kill a boss, or set a win state.

Evidence is labeled in three classes:

- **actual play:** the agent receives current visual feedback, issues sustained ordinary browser input on a normal clock, and can adapt actions from observations;
- **scripted input:** a fixed ordinary-input sequence runs without adaptive observation; useful for regression, weaker for play quality; and
- **simulated:** fake clock, scenario jump, direct state mutation, bot policy, or headless/null rendering; useful for mechanics and scale, inadmissible as actual play.

An actual full-session account records artifact commit, harness and browser versions, device/backend, seed, start/end time, input mode, checkpoints/screenshots, build choices, damage/death/win state, control problems, pacing dead zones, unreadable threats, confusing feedback, fun/frustration observations, console errors, and confidence limits. At least two maker-independent agents or contexts MUST play the release candidate; together they cover a complete win through the final boss, a loss, and restart from both outcomes. At least one session traverses the normal menu and tutorial/control disclosure. If no available host can sustain the game in real time, the workflow returns `actual-play: unverified` and cannot claim completeness.

## Declared-hardware 60 fps contract

“60 fps” is a measurement cell, not an adjective. Each cell binds exact device/CPU/GPU/RAM, OS and power mode, browser/version, graphics backend, display refresh, viewport and device-pixel ratio, quality settings, production-build commit, scenario and seed, warm/cold state, duration, instrumentation, raw sample path, metric definition, threshold, result, and invalidation rule.

Required scenarios are idle/menu, representative play, peak wave density, boss with its heaviest promised effects, and one full actual-play session. The default protocol on a 60 Hz target is three 60-second warm runs per stress scenario after a documented warm-up. Each run must average at least 59 animation-frame callbacks per second, keep at least 99% of foreground normal-clock callback intervals at or below 18.33 ms, and have no unexplained stall above 100 ms. The same run record also requires a Chrome trace to classify every display opportunity as fully presented, partially presented, or dropped. Let `F` be fully presented opportunities divided by elapsed seconds and `M` be (partially presented + dropped) divided by all classified opportunities; each trace run must have `F >= 59` and `M <= 1%`. A partially presented frame counts as zero fully presented frames because some visual updates missed the deadline; a dropped frame counts as zero and remains a miss. Missing or unclassified opportunities, incomplete trace coverage, or unavailable presentation counts fail the run. A project MAY set a stricter contract; changing a failing threshold or quality setting creates a new decision revision rather than turning red evidence green.

Game-owned `requestAnimationFrame` samples provide distributions and scenario markers. A separate Chrome performance recording at the same commit, scenario, seed, device/backend, and duration supplies the required presented-frame counts alongside frame duration, dropped or partially presented frames, main-thread work, GPU/render activity where exposed, memory trend, console failures, and screenshots. Because tracing and screenshots add overhead, the record keeps instrumented and minimally instrumented runs separate. Any callback/trace contradiction (one source passes its thresholds while the other fails, or their run markers cannot be reconciled) fails the cell until the cause is attributed and a matching rerun resolves it; passing callback metrics cannot override a failing presented-frame trace. Fake-clock runs, background tabs, DevTools CPU throttling, null renderers, and synthetic scenario fast-forward are diagnostic evidence, never the physical-device pass.

Failure starts with attribution: CPU simulation, garbage collection, GPU/draw calls, fill rate, asset decode/upload, memory growth, or harness overhead. One repair targets the measured bottleneck and reruns the same scenario. The workflow cannot silently lower resolution, enemy count, effects, browser cohort, or hardware target; those are visible product/quality decisions.

## Final evidence fan-out and discriminating judgment

Final acceptance freezes one candidate commit before review. Independent lanes gather: deterministic build/mechanics evidence; asset/provenance/manifest evidence; visual captures; ordinary-input play accounts; compatibility/console/network evidence; and physical-device performance traces. Evidence collectors may not edit the candidate. The final judge runs in a fresh maker-independent context and receives the fixed Goal, artifact identity, rubric, and evidence index rather than the makers' conversational history.

The capture matrix MUST include, at every declared viewport, boot/loading, menu/control disclosure, opening play, first reward choice, representative early and mid pressure, peak density, low-health/readability stress, pause/settings if promised, boss entrance, each boss phase, loss, win, and restart. The worked 3D example uses at least 18 distinct view × state captures, separated by state or meaningful play time rather than near-duplicate bursts. Each capture binds commit, viewport, DPR, browser/backend, state, seed, and timestamp. The judge inspects the full matrix and every playtester account, not a curated highlight reel.

Hard gates are binary: production boot; ordinary controls and focus; promised content; complete win/loss/restart paths; final boss; no undisclosed placeholders; no blocking errors; manifest/provenance closure; actual-play minimum; and every declared 60 fps cell, including both callback and presented-frame metrics and their agreement verdict. Quality is then scored 0–4 for core-loop clarity, control feel, combat feedback, threat and reward readability, pacing, meaningful build choices, level pressure, boss telegraph/counterplay, art coherence, UI/audio support, and polish. Passing requires every hard gate, no quality score below 3, and an evidence-backed rationale for each score. An average cannot hide one core failure.

The judge returns blocking findings as observable complaints tied to evidence and a responsible seam, for example “boss phase-two ground tell is lost under peak-wave particles in captures C14/C15 and caused both players to take unavoidable damage,” not “needs polish.” It distinguishes a defect, an unverified claim, and a preference.

The workflow quotes the library idiom exactly: **Where the judge blocks, one repair `do` is handed the `findings:` line verbatim, then one re-judge; two rounds is the bound.** A repair goal lists the allowed complaint set, affected evidence, and regression matrix; it does not grant a general redesign. Re-judgment repeats all affected hard gates and quality criteria plus a smoke subset of unaffected paths. After two blocked rounds, the frame closes with the fixed artifact identity, findings, completed evidence, and unresolved gaps; it does not loop or claim success.

The final close uses an outside command against the joined tip. The probe MUST build from the lockfile, serve the production output, exercise boot/start/win-or-loss/restart through the admitted smoke path, validate evidence-index identities and asset coverage, and verify that every required acceptance cell has passing callback and presented-frame records, their raw counts and thresholds, and an agreement verdict; a missing, unclassified, or contradictory trace fails the probe. It runs outside every child and prints the exact accepted git identity.

## Failure and resumption behavior

| Event | Required behavior and resume point |
| --- | --- |
| Missing product promise | File one `kind: user-only` question verbatim. Park only dependent branches; resume after recording the answer as a new brief revision. |
| Missing or changed tool | Record observed capability and expected requirement. Install only when authorized. Re-probe and resume at capability inventory; version change invalidates dependent evidence. |
| Research gap or contradiction | Return partial packets and gaps. If discovered later, open an explicit research resumption, revise the decision, and invalidate concept/build descendants named by identity. |
| Maker/check failure | Keep the candidate unlanded, record command/output and partial artifact identity, and retry only the scoped unit within its bound. |
| Asset generation/export failure | Preserve source, prompt/script, tool version, and validator output. Placeholders may keep an early increment playable but remain blocking in I3/I4. |
| Agent cannot see/control real-time play | Label its evidence scripted or simulated, dispatch a capable actual-play lane if available, otherwise close completeness as unverified. |
| Performance miss | Preserve raw samples and trace, isolate the bottleneck, and repair the responsible seam. A target/quality change requires a visible decision revision. |
| Judge block | Apply the two-round bounded-repair rule, then return the remaining blocks without another loop. |
| Crash or context loss | Use `orchflows resume`, read the open frame journal, resolve recorded artifact lines and package digest, land completed outcomes, and reopen only missing/expired dispatches. Never reconstruct state from memory. |
| Package changed mid-run | Refuse stale dispatch/admission, open a successor run against the new package digest, and cite the predecessor evidence rather than mixing contracts. |

## Worked invocation: one-level 3D survivor game

The user invokes:

```text
/browser-game build me a 3d vampire survivors-like game with 1 level but many waves that ends in a final boss fight
```

Discovery treats “3D,” one level, many waves, and a final boss as fixed intent. It audits omitted session length, control/device scope, target hardware, art direction, audio/accessibility, and delivery. As reversible workflow defaults it proposes a 12-minute local-development run, keyboard movement with automatic attacks, original rather than imitative visual identity, and the exact available development machine plus current Chromium/WebGL 2 as the first declared 60 fps cell. A broader support claim remains a user-owned decision.

Research compares current PlayCanvas standalone and Babylon.js with a many-entity spike, keeping Three.js or Godot only if repository facts justify them. The spike imports one Blender-authored animated enemy, drives normal input, spawns the peak target, builds production output, and records traces. Blender background Python/GLB is the default asset path; MCP is used only if the capability and isolation probe passes. Concept bakeoff selects an original stylized low-poly direction with silhouettes readable from the fixed top-down camera.

The frozen concept defines one arena with landmarks and spawn exclusions; an opening grace beat; data-driven waves that introduce melee, ranged, fast, tank, and elite pressures; reward/upgrade choices; intensity valleys; a peak swarm; and a boss with entrance, two or more telegraphed phases, adds or arena pressure, defeat, reward, and win transition. Counts, timings, upgrades, and exact boss mechanics are settled in research/concept evidence rather than copied from this example.

The increment plan is concrete:

1. I0 boots the production shell and proves movement, camera, focus, damage, death, win stub, and restart in a graybox.
2. I1 proves a three-minute combat/reward loop with representative hero, enemy, arena, UI, animation, and VFX assets.
3. I2 makes the entire 12-minute wave schedule and boss completable with explicit placeholder inventory, then runs peak-wave and boss stress seeds.
4. I3 lands all production assets, enemy/upgrade variety, audio/feedback, balance, wave pacing, and boss polish; placeholder count becomes zero.
5. I4 gathers two independent full ordinary-input play accounts, loss/win/restart coverage, at least 18 matrix captures per declared viewport set, and three-run performance cells with callback/presented-frame agreement for representative, peak-wave, and boss scenarios.

Final judgment blocks on any missing boss completion, unreadable peak state, hollow upgrade choice, control/focus failure, asset drift, actual-play gap, or failed 60 fps cell. Two scoped repair/re-judge rounds are available. The outside probe closes only over the accepted joined commit.

## Implementation acceptance for the workflow rebuild

The future implementation of this specification is complete when:

- the package has one public workflow and the private structure above, with literal names resolving under the updated package rules;
- the old record/checkpoint evidence that remains useful migrates behind package ownership and the legacy allowlist can be removed without weakening tests;
- a scratch invocation produces a durable frame tree whose journals show discovery, frozen concept, at least two playable increments, actual play, independent judgment, bounded repair behavior, and outside close;
- capability failure, one user-only question, research resumption, an unplayable host, an FPS miss, and repair-bound exhaustion each have a tested closed outcome;
- the target game's dependencies remain in its own lockfile while package-only dependencies and tool probes are declared by the workflow package;
- validators check identities and evidence shapes rather than prose sentences;
- repository validation, affected tests, adapter/routing tests, deterministic scratch admission, and the full required gate pass at the implementation commit; and
- the public help text can explain what evidence earns “complete game” without duplicating the private standards.

## Compact source list

Internal owners: [custom workflow authoring](../docs/custom-workflow-authoring.md), [composition](../rules/composition.md), [vocabulary](../docs/vocabulary.md), [architecture](../ARCHITECTURE.md), [repository checks](../AGENTS.md), [current browser-game workflow](../example-workflows/browser-game/SKILL.md), [checkpointed-build](../skills/workflows/checkpointed-build/SKILL.md), [bakeoff](../skills/workflows/bakeoff/SKILL.md), [code standard](../standards/orch-code/STANDARD.md), [design standard](../standards/orch-design/STANDARD.md), and [research standard](../standards/orch-research/STANDARD.md).

External primary sources are linked beside the claims they support in Stage 1. They were checked on 2026-09-05; engine, browser, Blender/MCP, Playwright, and image-model facts must be refreshed when their pinned identities change.
