# 3D Browser Game Creation Workflow — Specification

**Status:** authoritative successor specification, registry v3D-1.1
**Frozen:** 2026-08-25
**Audience:** Orchflows maintainers, workflow authors, renderer/physics adapter implementers, QA/evaluation owners
**Scope:** the AI-orchestrated workflow that turns a bounded prompt plus evidence into a playable, verified, editable **3D browser game** that **may or may not include local multiplayer**

## 0. Lineage, authority, and supersession

This specification is the fourth document in one lineage and the current execution authority:

| # | Document | Identity | Standing |
| --- | --- | --- | --- |
| 1 | Runtime-neutral program handoff (GameIR, six capabilities, GB-* catalog) | SHA-256 `F661CB57…` | lineage baseline for GameIR ownership, studio topology, transaction discipline |
| 2 | Browser-first handoff (two-key release, B0–B14 gates, GB-WEB-001..058, Phaser-pinned 2D) | supplement SHA-256 `90417F4D…` | superseded on runtime by #3; its release, gate, and conditional-control machinery survives |
| 3 | Browser-native 3D program decision ("The Program Decision", 2026-08-18: 3D-only, Three.js provisional, A0–A12 atoms, registry v3D-1.0) | evidence packet SHA-256 `0F321A9C…` | **current baseline**; this spec extends it |
| 4 | **This document** — registry v3D-1.1 | — | supersedes #3 wherever local multiplayer, physics authority, 3D asset gates, verification mechanics, or 2026 platform facts differ |

Evidence keys used throughout: **[S1]** Stage-1 cross-system synthesis and its 18 reports (R01–R18); **[BR]** browser-focus research run (files 01–06 + supplement); **[R3D]** the 3D program decision report; **[W26]** fresh web research executed 2026-08-25 against primary sources (versions and dates verified unless flagged); **OJ** = explicit program judgment in this spec. Nothing in [W26] promotes a vendor claim into a measured product fact.

Two prior decisions are explicitly **not** reopened: the one-authority architecture (R3D-ARC-001/002) and the two-key release contract (R3D-REL-001, R3D-OWN-001). Two prior decisions are **amended by evidence**: the WebGL2-fallback obligation returns as an active row (§2), and the engine bake-off finalist set is refreshed (§3.1).

## 1. Charter

The workflow's promise: a bounded prompt and evidence brief become an editable, reproducible **3D browser game**, its co-generated verifier, and a public release packet. "Playable" means a fresh, logged-out browser reaches an interactive start state at one immutable HTTPS URL, **and** the same release ships downloadable editable source plus the exact self-hostable production build. Either key missing fails terminal acceptance. [BR][R3D]

This is a production-system charter, not a one-shot autonomy claim. External calibration: under strict automated verification, frontier coding models pass fewer than half of end-to-end interactive-app builds (ViBench, 2026: best models ~42–46% Pass@1, flagged secondhand) [W26]. The workflow's value is therefore its verification and repair structure, not a promised generation success rate. Fun, beauty, and (where applicable) historical treatment remain separately judged claims attached to an exact build. [S1][R3D]

**Local multiplayer is a per-game envelope, not a program stage.** Every generated game declares a seat manifest and a local-multiplayer level at design time (§5); the declared level's contracts activate automatically and fail closed; a game that declares none still proves the multi-seat seam headlessly (§5.2). Networked multiplayer remains an optional adapter at the controller seam, out of scope for first delivery. [R3D-MP-001]

### Non-goals

Unchanged from the lineage, restated for this scope: no unchecked prompt-to-finished-game jump; no rules or chance owned by rendering callbacks, browser wall-clock, network peers, or prose; no LLM/model call in a mandatory frame or turn path; no learned/LLM opponent selection before the seat contract and baseline curriculum pass; no real-time *networked* competitive multiplayer; no accounts, matchmaking, monetization, or live-service operations; no provider-owned canonical state; no claims of historical accuracy without a claim ledger. Real-time **local** play is permitted: with no network and no model in the loop, a fixed-timestep deterministic core handles simultaneous local input (§5.4). [S1][BR][R3D] OJ

## 2. Platform baseline (2026)

Facts below are [W26] against primary sources, and they are observation-time facts, not permanent truths; each carries an invalidation trigger in §10.

**WebGPU ships by default in all four browser engines, but coverage has holes.** Chrome/Edge: stable since 113 (Windows/macOS/ChromeOS), Android since 121, Linux partial (Intel Gen12+ in 144, NVIDIA/Wayland in 147, rest flagged). Firefox: 141 on Windows, 145 on Apple-Silicon macOS; Linux/Android still Nightly, targeted 2026. Safari: default in Safari 26 (macOS Tahoe 26 / iOS 26 / iPadOS 26, Sept 2025). Chrome 146 added opt-in WebGPU **Compatibility Mode** for GLES 3.1-class hardware (Chrome-only).

**Consequence (normative):** a consumer-reach release SHALL treat WebGPU as a preferred backend and ship a tested WebGL2 path, or declare a narrowed support matrix with an explicit unsupported-browser screen. Firefox on Linux/Android, pre-26 Apple OS versions, and vendor-dependent Android GPUs are the current long tail. This re-instates superseded GB-WEB-039 as active row R3D-PLT-001 (§9). [W26] OJ

**CI reality.** Chromium removed automatic SwiftShader fallback for WebGL: GPU-less CI now needs `--enable-unsafe-swiftshader` (or explicit `--use-angle=swiftshader`). Headless WebGPU runs on Dawn-over-SwiftShader-Vulkan via `--headless=new --enable-unsafe-webgpu --use-webgpu-adapter=swiftshader` (+Vulkan features on Linux). Software rendering is 10–30× slower and flaky on heavy scenes; hardware-GPU runners exist (paid) via xvfb. Playwright (v1.62) stopped capturing canvas content in traces (since v1.50) — screenshots/video are the only pixel evidence channel. Precedent: three.js's own e2e suite renders every example headlessly and pixelmatch-compares against goldens with frozen timers and seeded RNG. [W26]

**Engines.** Three.js r185 (2026-07-01, MIT): `WebGPURenderer` with automatic WebGL2 fallback; TSL node shaders compile to WGSL or GLSL (shaders become typed JS — material for code generation); types community-maintained (`@types/three`); largest training corpus of any web-3D library; API churn between releases is its documented codegen hazard. Babylon.js 9.22.2 (Apache-2.0; 9.0 released 2026-03-26): TypeScript-first, all core shaders dual-authored GLSL+WGSL since 8.0, `NullEngine` for headless scene-logic tests. PlayCanvas engine 2.21.4 (MIT): entity-component model, new WebGPU renderer in 2.19 (June 2026), Editor frontend open-sourced July 2025, editor REST API and an official **MCP server** for agent-driven editor automation; editor backend remains hosted/proprietary. Godot Web: still WebGL2-only Compatibility renderer, no WebGPU. Unity 6 Web: WebGPU non-experimental as of 6.6, but C# and heavy builds — poor fit for a TS codegen loop. [W26]

**Physics.** Rapier (`@dimforge/rapier3d` 0.20.0, Apache-2.0) documents three builds; the `-deterministic` build guarantees **cross-platform determinism** (same version, same inputs and construction order → bit-identical results across browsers/OS/CPUs), with the explicit caveat that JS `Math.sin/cos/…` are not cross-platform deterministic and must not feed the simulation. Snapshot+hash is its documented desync check. Jolt (`jolt-physics` 1.1.0, MIT) supports a cross-platform-deterministic WASM compile, but the published npm artifact is not verified to be that compile — self-build required (flagged). Havok for Babylon is a closed-source binary. cannon-es is inactive; ammo.js legacy. WASM float arithmetic is spec-deterministic (except NaN payloads); JS transcendental functions are not — the deterministic boundary should sit at WASM or determinism-disciplined JS (the Rune platform's patched-Math approach is the JS-side precedent). [W26]

**Asset chain.** glTF 2.0 is the interchange contract: Khronos glTF-Validator (maintenance-mode but functional) as the conformance gate; glTF-Transform 4.4.2 (MIT, scriptable Node SDK) and gltfpack 1.2.0 (meshopt) as the optimization pipeline; KTX2/BasisU textures mainstream (Khronos Asset Creation Guidelines 2.0, SIGGRAPH 2025); meshopt default, Draco for hero meshes. AI 3D generation: Microsoft TRELLIS.2 (MIT, weights + training code — the license-clean self-hostable option); Hunyuan3D-2.1 (open weights under a non-OSI community license with territory/usage restrictions); Hunyuan3D 3.x API-only; Meshy-6 / Tripo 3.1 as commercial APIs (output-ownership terms vendor-asserted, not re-verified). [W26]

## 3. Architecture

Adopted from [R3D] unchanged in substance; compressed here because this spec is the operating document.

**One authority.** A renderer-, DOM-, clock-, network-, and model-independent TypeScript(+WASM) `game-core` owns canonical state, fixed simulation step, seeded random streams, legal actions, transitions, typed events, objectives, terminal outcomes, serialization/migration, state hashes, and replay. Dependency direction: `versioned inputs → simulation authority → committed transitions → projections/adapters`. Renderer objects, prose, sockets, and storage records never point inward. Rejected inputs produce typed rejections with no hidden mutation. [R3D-ARC-001/002, R3D-DET-001]

**Semantic envelopes are the sole control surface.** Observation envelopes carry state version, logical time, observer identity, visible entities, affordances, objectives, and legal actions, visibility-filtered per seat. Action envelopes carry controller identity, observed version, typed action, targets by semantic ID. Every controller — human UI, heuristic bot, test, replay, hot-seat, split-screen seat, future network client, future model agent — uses the same envelopes and receives explicit accept/reject. Camera pose and raycast picking are presentation-side translation into semantic actions; camera state is never game truth. [R3D-OBS-001, R3D-ACT-001] OJ

**Replay is captured-output replay.** Saves/replays record schema versions, seed material, ordered accepted actions (per seat), captured nondeterministic service outputs, checkpoints, and hashes; replaying reapplies inputs through the live transition function and compares hashes. Fresh model output is never re-called during replay. Determinism claims are scoped to tested environments; cross-browser bit-equality is proven by repeated replay-hash trials on the release matrix, never assumed. [R3D-RPL-001][BR][W26]

**Renderer adapter.** Three.js remains the provisional default render adapter (R3D-DEC-001). The projection contract: engine scene nodes are ephemeral projections keyed by semantic entity/asset IDs; a renderer restart rebuilds them without changing the world; the adapter emits pick intents, performance samples, and diagnostics, and owns nothing else.

### 3.1 Engine bake-off refresh (amendment)

The signed, pre-committed bake-off before irreversible engine adoption stands (R3D-QA-004). Two evidence-driven amendments, OJ on [W26] facts:

1. **Finalist set refreshed to {Three.js, Babylon.js, PlayCanvas}.** Godot Web's continued lack of WebGPU and its Compatibility-renderer ceiling, plus the wasm/C# language mismatch with a TS authority core, demote it from runner-up to a contrast candidate admitted only by a signed priority change. Babylon.js returns to the finalist set (it was in the original GB-WEB-057 trio): TypeScript-first authoring and dual-authored WGSL/GLSL shaders directly serve the codegen and backend-parity requirements.
2. **Bake-off adds two measured axes:** AI-repairability under the pinned toolchain (three identical repair tasks, held from GB-WEB-057) now also records model-familiarity failure modes (deprecated-API emission rate — Three.js's churn is a live hazard), and per-backend parity (same scene on WebGPU and WebGL2 cells).

No ordering below is a measured win; the bake-off decides. [R3D-DEC-001, R3D-QA-004]

### 3.2 Physics placement (new)

Physics is a capability decision made at design time (A2), one of three placements:

- **P-NONE.** Turn-based/discrete games need no physics engine; movement and collision resolve as rules. Default for tactics/grid/card forms.
- **P-AUTH.** Physics affects game truth (a physics platformer, vehicle game, destructible arena). Then the physics engine SHALL run inside `game-core`'s fixed step, from a pinned-by-hash deterministic build — Rapier `-deterministic` is the only npm-shippable option meeting this today; Jolt qualifies only via a self-built deterministic WASM compile — with construction-order discipline, no JS transcendentals feeding the sim, and snapshot-hash desync checks in the replay corpus.
- **P-VISUAL.** Physics is decoration (debris, cloth, ragdoll flourish). Any engine and nondeterminism are acceptable; its outputs SHALL NOT feed authority, enforced by the same forbidden-import audit that guards the renderer boundary.

Registry row R3D-PHY-001 (§9). [W26] OJ

## 4. GameIR, stores, and studio topology

Carried from lineage, unchanged: GameIR as a versioned content-addressed graph with ten namespaces (brief, history, design, rules, world, content, assets, controls, evaluation, release), each node bearing stable ID, schema version, dependency hashes, status, provenance, owner [S1]; five canonical stores (intent, GameIR, source/build, evidence, provenance), conversational memory never a canonical store [S1]; six capability owners — producer/orchestrator, design(/history) director, technical/rules lead, gameplay/renderer implementer, world/asset producer, independent QA — with a new role admitted only for a distinct tool, oracle, write scope, or material risk [S1]; propose → validate → commit-or-repair transactions with checkpoints, operation IDs, receipts, and unknown-outcome reconciliation before any retry [S1][R3D]; producer, checker, and fixer as distinct authorities; bounded repair loops with attempt/cost budgets and a persisted fix ledger so a fresh fixer never repeats a failed approach [S1: R02/R03/R06].

The `controls` namespace is expanded by this spec: it now owns the seat manifest, LM level, input-device bindings, and per-seat control schemes (§5). The `evaluation` namespace now owns the CI GPU-mode declaration and per-backend matrix (§7).

Repository boundary (successor of SPD-03):

```text
packages/game-ir          schemas, graph, migrations, canonical serialization
packages/game-contracts   observations, actions, events, seats, saves, ReplayV1
packages/game-core        rules, fixed step, seeded RNG, legality, outcomes, hashes
packages/game-physics     optional: pinned deterministic physics behind the core's step
packages/game-content     versioned scenarios and admitted primitive definitions
adapters/renderer         Three.js provisional; bake-off may replace (§3.1)
adapters/input            device pairing, keyboard partition, gamepad polling, mocks
adapters/policy           seeded-random-legal and heuristic seat providers
adapters/playwright       blind-surface and browser evidence capture
adapters/publisher        immutable candidate upload, reconciliation, alias/rollback
adapters/net              optional later server-authoritative transport (unchanged seam)
```

## 5. Seats and the local-multiplayer envelope (new)

This section is the spec's main extension. The lineage proved the seat/action seam with hot-seat as a fixed P1 stage [BR: GB-WEB-045]; [R3D] preserved multiplayer as conditional (R3D-MP-001) but specified only the networked case. Local multiplayer needs its own contract because the user-facing promise is "may or may not include it."

### 5.1 Seat manifest and LM levels

Every game's design (A2) SHALL fix a **seat manifest**: the set of seats, each seat's role and visibility class, its permitted fill policies (human-local, bot, empty), and one declared **local-multiplayer level**:

| Level | Name | Shape | Input | Rendering |
| --- | --- | --- | --- | --- |
| **LM0** | Single-seat | One local human; bots fill other seats | any devices, one player | one camera |
| **LM1** | Hot-seat | N humans alternate at turn boundaries on one device | shared devices, sequential | one camera; per-seat view masking at handoff |
| **LM2** | Shared-screen | N humans act simultaneously, one shared view | per-seat device binding (§5.3) | one camera framing all seats |
| **LM3** | Split-screen | N humans act simultaneously, per-seat views | per-seat device binding | per-seat cameras/viewports |

Rules, OJ:

- The level is declared at design time and fixed for the candidate; changing it is a design revision with a new identity, not a patch. Conditional controls for the declared level activate automatically and fail closed; undeclared levels get signed N/A — the machinery is inherited verbatim from the browser handoff's conditional-control semantics [BR §2].
- **Every level ships bot fill.** A game at any LM level SHALL be startable and completable by one human with bots in the remaining seats, with model and network providers disabled. Local multiplayer is additive, never load-bearing. (Generalizes GB-WEB-006/044.)
- LM1 requires turn-based or pausable rules. LM2/LM3 permit real-time local play under the fixed-timestep core; the turn-based-first recommendation for *generated* first slices stands (model-latency playtest evidence [BR: Play2Code]; R3D-THM-002 pattern), but is a template default, not a level constraint.
- Networked play (the `adapters/net` seam) composes with any level later; nothing in LM0–LM3 may import transport concerns into the core. [R3D-MP-001]

Existence proof that the ceiling is not browser-imposed: 6-player single-keyboard browser play has shipped continuously since 2011 (Achtung die Kurve / Curve Fever lineage); multi-gamepad shared-screen play is routine in web builds. [W26]

### 5.2 Unconditional seam evidence

Declaring LM0 does not skip the multi-seat proof. Regardless of level, the core SHALL pass, headlessly, the **seat-conformance corpus**: two-plus-seat scenarios exercising seat authorization, out-of-turn and stale-action rejection without state change, per-seat observation filtering with zero privileged leakage, role swap under paired seeds, and replay equivalence with per-seat action streams. This preserves what hot-seat's mandatory sequencing was actually buying — proof of the shared action contract — while letting the shipped UI mode be optional. (Successor to GB-WEB-021/022/045's evidentiary role; registry row R3D-SEAT-002.) [S1][BR] OJ

### 5.3 Input-device contract (LM2/LM3, plus gamepads at any level)

- **Pairing ceremony.** Seats bind to devices through an explicit claim step (press-a-button-to-join), because the Gamepad API only exposes a pad after a user gesture and identifies it by integer index. The binding lives in the `controls` GameIR node and in session state; it is presentation-side and never authority state. [W26]
- **Polling.** Gamepad input is poll-per-frame (`navigator.getGamepads()`); the input adapter translates polled state into semantic actions with per-seat identity. Background tabs stop delivering input — a declared-outcome fixture, not an error.
- **Device loss.** A bound device disappearing SHALL produce a declared outcome: pause-and-rebind by default for real-time levels; a bot may substitute only through the normal seat-fill policy with a recorded event.
- **Keyboard sharing.** Two seats on one keyboard is the supported baseline (layout-independent `KeyboardEvent.code` bindings, remappable). Beyond two, key-rollover ghosting is a hardware limit the workflow cannot test away: default control schemes SHALL keep simultaneous-chord requirements within 2-key rollover per seat, and the release card SHALL state the limitation. Reserved browser combos are avoided in defaults; Keyboard Lock in fullscreen is a Chromium-only enhancement, never load-bearing. [W26]
- **Mockability.** No CDP gamepad domain exists — Playwright cannot emit trusted gamepad events. Therefore the input adapter SHALL sit behind an interface that blind QA can drive two ways: an init-script Gamepad-API mock (high fidelity, since the API is poll-based) and scripted keyboard/pointer. A game whose input layer cannot be mock-driven fails its verification-readiness gate. Registry row R3D-INP-001. [W26] OJ

### 5.4 Simultaneous local intent and determinism

For LM2/LM3, multiple seats submit actions within the same fixed tick. The core SHALL order same-tick intents by a stable, documented key (tick, then seat ordinal, then action sequence number), commit them as ordinary sequential transitions, and record the ordered stream per seat in the replay. Local simultaneous play thus needs no lockstep machinery — one machine, one authority, one log — and replay/regression keeps working unchanged. Only local determinism (same build, same machine) is required for LM replay oracles; cross-platform bit-equality remains the separately-tested property it already was (§3, R3D-DET-001). [W26: fix-your-timestep; Rapier snapshot-hash] OJ

### 5.5 Per-level acceptance contracts

Each declared level adds fail-capable gates to the pipeline (§7); each is also a registry row (§9):

- **LM1 (R3D-LMP-001).** Turn-boundary handoff passes control without leaking the incoming seat's hidden state where visibility classes differ (a masking interstitial when applicable); surrender/timeout/concession are typed transitions; a full N-human match completes through the public UI; save/restore at handoff boundaries; replay equivalence.
- **LM2 (R3D-LMP-002).** Pairing ceremony reachable from the start screen; a full simultaneous match completes with N mocked devices; device-loss fixture reaches its declared outcome; same-tick ordering audit (induced simultaneous intents commit deterministically across three repeated runs); shared-camera framing keeps every seat's units and objectives legible at declared resolutions (human readability judgment).
- **LM3 (R3D-LMP-003).** All LM2 gates, plus: per-seat cameras/viewports render correct per-seat visibility filtering (no cross-seat information leak through the other viewport where hidden information exists); performance budgets (§7.3) measured **at maximum declared seat count** — draw submission and fill scale with view count; per-seat HUD legibility judged per viewport.

## 6. 3D world and asset pipeline

The A0–A12 atom graph from [R3D] §4 is adopted as the production workflow — theme interpretation → concepts (≤3) → design spec → **playable greybox before art** → parallel asset generation + behavior → world assembly (global-before-local, one shared-terrain reconciler) → integration (mandatory join) → refinement (≤3 issue batches) → optimization (baseline + ≤2 measured interventions) → QA/publication/rollback handoffs — with each atom's immutable identity, attempt budgets, and fail-capable oracles unchanged. Amendments (OJ):

- **A2 (design)** additionally fixes: the seat manifest and LM level (§5.1), physics placement (§3.2), camera model and readability constraints as designed artifacts, the browser/backend support matrix, and numeric performance budgets (§7.3).
- **A3 (greybox)** in 3D means: semantic topology (regions, traversability, chokepoints, spawns, objectives) as a diffable graph independent of appearance; a navmesh or movement-graph proof that every unit class legally reaches its objectives; collision intent; camera-bound and readability checks at target distances; and — new — the input skeleton for the declared LM level, so device pairing and per-seat control are proven on greybox geometry before any art exists. A beautiful coastline that breaks the movement model is a failed world. [S1: GB-WORLD][R3D]
- **A4 (assets)** binds to the technical gate battery in §6.1.
- **A6 (behavior)** adds the physics determinism fixtures when P-AUTH is declared (§3.2) and the seat-conformance corpus (§5.2).
- **A7 (integration)** adds backend parity: the integrated candidate boots and completes its smoke scenario on both declared backends (WebGPU and WebGL2 cells) with any declared presentation deltas recorded, never silent. [W26]

### 6.1 Asset technical gates (new consolidation, R3D-AST-001)

Every shipped 3D asset SHALL pass, in order:

1. **Format conformance:** glTF 2.0 validation (glTF-Validator) with zero errors.
2. **Normalization:** world-unit scale, axis convention, and pivot/origin placed per the project convention; transforms applied; hierarchy-aware bounds recorded. Import fails rather than guesses when scale cannot be established. [S1: R10]
3. **Budgets:** triangle count, texture resolutions, material/draw-call cost within the per-class numeric budgets signed at A2.
4. **Runtime data:** collider presence and fit where the asset is gameplay-relevant; LOD policy applied per class; rig/animation integrity where applicable (skeleton naming and retarget test when animations are supplied separately). [S1: R11]
5. **Compression:** meshopt (default) or Draco (hero meshes), KTX2/BasisU textures; decoders pinned by version and hash in the build. [W26]
6. **Clean re-import:** the exported artifact imports into a fresh project of the pinned engine version, binds to its intended role, and renders in a multi-view capture (turntable/contact sheet) that passes anchored visual review. [S1: R07/R10/R11]
7. **Provenance:** the full manifest of R3D-PRV-001 — source/provider identity, license class, prompt lineage where retained, hashes, transforms, approvals. Provider history and transient URLs are never storage; generated outputs are copied into content-addressed local storage at acquisition. [S1: R11]

Sourcing routing (unchanged principle, refreshed options): curated/licensed libraries first, procedural/instanced second, generation for gaps — with license classes now explicit: MIT-clean self-hosted generation (TRELLIS.2), open-weights-restricted (Hunyuan3D-2.1 community license: not OSI, territory/usage limits — license review before distribution), and commercial API outputs (Meshy/Tripo — vendor ownership terms recorded per asset, not assumed). [S1: R10][W26]

Style discipline: explore → freeze hashed style/subject anchors → enforce on every production request; identity-preserving revision chains; staging assets quarantined out of context and builds. [S1: R11]

## 7. Verification

The two-lane-plus-human structure is unchanged [R3D-QA-001..003]: a **blind lane** that sees only the guide, rendered output, and normal input against the immutable candidate; a **privileged lane** that drives typed state/actions against the pure authority (legality, invariants, reachability, role views, save/migration, replay); and an **accountable human gate** for fun, visual coherence, readability, accessibility spot-checks, and historical tone — never averaged, never substituted by scores. The B0–B14 fail-closed pipeline from the browser handoff remains the release spine (brief/oracle map → provenance → headless authority → reproducible build → supply chain → boot matrix → semantic public play → replay equivalence → visual intent → performance → security/rights → human play → immutable publication → remote smoke/promotion/rollback drill → terminal packet). This section specifies only what 3D, CI reality, and LM levels change.

### 7.1 The oracle hierarchy for 3D

1. **Replay hashes are the gameplay oracle.** Fixed-tick input logs plus state hashing decide correctness and regression; they are immune to rendering variance and cheap to run. Every critical scenario keeps a replay; failed-oracle scenarios keep a human-viewable capture. [S1: R17/R18][W26]
2. **Semantic observations are the play oracle.** Blind play drives public UI and asserts on the versioned observation contract, not pixels. [S1: R06][R3D-OBS-001]
3. **Screenshots gate rendering only.** Deterministic canonical scenes (frozen timers, stepped rAF, seeded visual RNG, fixed camera set) compared with pixelmatch/SSIM under explicit thresholds against **environment-keyed goldens** (browser+version+OS image+GPU mode+viewport+DPR), generated in the same container CI uses. Cross-GPU pixel drift is expected and keyed away, not tolerated into meaninglessness. A black frame, missing asset, or clipped layout is an automated fail; taste stays human. [BR][W26]

### 7.2 CI mechanics (R3D-CI-001, new)

- Every browser-evidence cell declares its GPU mode: `software` (SwiftShader — WebGL cells pass `--enable-unsafe-swiftshader`; WebGPU cells pass the documented Dawn/SwiftShader-Vulkan flag set) or `hardware` (headed under xvfb on a GPU runner). Budgets and goldens are keyed by that mode; performance verdicts come only from hardware or pinned-device cells — software cells prove correctness, boot, and replay, never speed. [W26]
- Canvas pixels do not appear in Playwright traces; the capture bundle therefore always includes explicit screenshots/video per critical scenario alongside the trace. [W26]
- Cross-browser 3D CI is Chromium-first for WebGPU; Firefox joins on the WebGL2 path; Safari/WebKit cells are best-effort until Playwright's WebKit carries Safari's WebGPU. The declared support matrix (§2) states which cells are release-blocking.
- Gamepad and multi-device scenarios run through the input-adapter mock harness (§5.3); LM2/LM3 matches are driven end-to-end with N mocked devices.

### 7.3 Performance budgets (R3D-PERF-001)

Numeric budgets are signed at A2 per device class; the following are the program's signable defaults (proposed thresholds from [BR: 05], OJ — not measured facts): initial JS ≤ 700 KiB gzip; critical first-scene transfer ≤ 8 MiB; interactive ≤ 8 s desktop / ≤ 12 s named mid-tier mobile for 3D; p95 active frame ≤ 16.7 ms desktop / ≤ 33.3 ms mobile; no main-thread task > 100 ms; no unbounded memory growth over a 20-minute replay. **LM3 budgets are measured at maximum declared seat count.** Raw traces are retained; a silently relaxed threshold is a gate failure. Web Vitals (LCP/INP/CLS) are necessary but insufficient — game-owned frame/simulation instrumentation is additionally required. [BR][W26]

### 7.4 Playtest matrices

Unchanged from lineage, restated: fixed seed matrices × seats × required policies (seeded-random-legal and scripted-heuristic SHALL exist for every seat; both baseline policies complete every scenario with no illegal action or soft-lock while advanced providers are disabled); role swaps and paired seeds; distributional verdicts with confidence intervals; stuck/soft-lock watchdogs on state-hash progress; bare vs harnessed agent playtests distinguished when agent claims are made. Fun, beauty, clarity, onboarding, and accessibility remain five separate judged rubrics. [S1: R17/R18/GB-RULE/GB-EVAL]

### 7.5 Accessibility

The DOM accessibility shell (R3D-ACC-001) is load-bearing in 3D — a WebGL canvas is semantically opaque: semantic DOM for navigation/status/objectives/controls/errors/pause, keyboard-only critical flow, visible focus, text scaling/contrast, reduced motion, independent audio controls, and a structured text state summary. For LM2/LM3, the keyboard-only and assistive-technology guarantees apply to the primary seat; multi-seat AT support is a declared open decision (§10), recorded honestly in the release card rather than silently claimed. Muted play remains complete and understandable. OJ

## 8. Release and operations

Unchanged from lineage, compressed: two-key terminal delivery (immutable logged-out HTTPS URL + editable source and self-hostable exact build, hash-linked via `release.json` with genesis/successor shapes); publication as a controlled effect through a publisher adapter that receives only tested bytes; remote byte/header reconciliation and smoke before atomic alias promotion; rehearsed rollback without rebuilding; recovery never regenerates creative content; deployment/monetization/publication authority separate from build success; canonical everything local and provider-disabled restorable; credentials out of prompts/assets/clients/logs; generated code and downloads treated as hostile under least-privilege bounds; release card states identity, controls, support matrix, data policy, licenses, known limits — including the LM level and its device requirements. [BR: B12–B14, GB-WEB-001..008][R3D-REL/OWN/SEC-001]

## 9. Registry delta — v3D-1.1

v3D-1.1 = v3D-1.0 (all 26 rows, unchanged unless named below) + the following. Format and governance follow R3D-GOV-001: one modality, explicit dependencies, deterministic applicability, fail-capable oracle. GB-* registries remain lineage through v3D-1.0's supersession map.

| Stable ID | Modality | Normative requirement (compressed) | Prerequisites | Applicability | Provenance |
| --- | --- | --- | --- | --- | --- |
| R3D-PLT-001 | platform | Declare a browser/backend support matrix; WebGPU MAY be preferred; every WebGPU feature has a tested WebGL2 path or an explicit unsupported screen; boot/backend-parity cells run per declared backend. FAIL on an unrun declared cell, silent presentation loss, or crash on a declared backend. | R3D-ARC-001 | Every release | W26; re-instates superseded GB-WEB-039; OJ |
| R3D-PHY-001 | physics | Physics placement declared at design (P-NONE / P-AUTH / P-VISUAL). P-AUTH runs inside the core's fixed step from a pinned-hash deterministic build with construction-order and transcendental discipline; P-VISUAL may not feed authority. FAIL on replay-hash divergence in declared environments, a forbidden import, or an unpinned physics artifact. | R3D-DET-001 | 3D products with physics; signed N/A otherwise | W26 (Rapier/Jolt determinism docs); OJ |
| R3D-SEAT-001 | seats | Every game declares a seat manifest (seats, roles, visibility classes, fill policies) and one LM level (LM0–LM3) at design time; declared-level controls activate automatically; every level ships bot fill so one human can complete the game with providers disabled. FAIL on an undeclared level shipping, missing bot fill, or a level change without a new candidate identity. | R3D-ACT-001 | Every game | BR conditional-control semantics; OJ |
| R3D-SEAT-002 | seats | Regardless of LM level, the core passes the headless seat-conformance corpus: seat auth, out-of-turn/stale rejection without mutation, per-seat visibility filtering, role swaps under paired seeds, per-seat replay streams. FAIL on any leak, unauthorized commit, or replay divergence. | R3D-ACT-001, R3D-RPL-001 | Every game | S1 GB-RULE-004/007, GB-WEB-021/022; OJ |
| R3D-LMP-001 | local-mp | LM1 hot-seat contract: masked turn handoff where visibility differs, typed surrender/timeout, full public-UI match, saves at boundaries, replay equivalence. | R3D-SEAT-001/002 | LM1 declared; signed N/A otherwise | Successor of GB-WEB-045, demoted to conditional; OJ |
| R3D-LMP-002 | local-mp | LM2 shared-screen contract: pairing ceremony, N-device simultaneous match via mocked devices, device-loss declared outcome, same-tick ordering audit over repeated runs, shared-camera legibility judgment. | R3D-SEAT-001/002, R3D-INP-001 | LM2 declared; signed N/A otherwise | W26; OJ |
| R3D-LMP-003 | local-mp | LM3 split-screen contract: all LM2 gates; per-seat viewport visibility filtering with no cross-viewport leak; budgets measured at max seats; per-viewport HUD legibility. | R3D-LMP-002, R3D-PERF-001 | LM3 declared; signed N/A otherwise | W26; OJ |
| R3D-INP-001 | input | Input layer sits behind a mockable interface; gamepad handling is poll-based with pairing ceremony, gesture-activation, and background-tab loss as declared outcomes; keyboard defaults respect 2-key rollover per seat and use code-based remappable bindings; blind QA can drive every declared device class via mocks. FAIL if a declared input path cannot be mock-driven or a fixture outcome is undeclared. | R3D-QA-001 | Every interactive product | W26 (no CDP gamepad domain; Gamepad API); OJ |
| R3D-AST-001 | assets-3d | Every shipped 3D asset passes: glTF validation, unit/axis/pivot normalization, numeric budgets, collider/LOD/rig integrity where relevant, pinned compression, clean re-import with multi-view anchored review, full provenance. FAIL on any gate or an unknown-license item in the distributable. | R3D-PRV-001 | 3D releases | S1 GB-ASSET; W26 toolchain; OJ |
| R3D-PERF-001 | performance | Numeric per-device budgets signed at design (defaults in §7.3); measured at max declared seat count; raw traces retained; software-GPU cells never produce performance verdicts. FAIL on breach, silent relaxation, missing raw trace, or a perf verdict from a software cell. | R3D-QA-001 | Every release | BR 05 proposed thresholds; W26 CI facts; OJ |
| R3D-CI-001 | verification | Every browser-evidence cell declares GPU mode with the documented flag sets; goldens are environment-keyed and container-generated; replay hashes decide gameplay, screenshots decide rendering; capture bundles include explicit screenshots/video (traces exclude canvas). FAIL on an undeclared mode, cross-environment golden reuse, or a gameplay verdict from pixels alone. | R3D-QA-001/002 | Every release | W26; three.js e2e precedent; OJ |
| R3D-DEC-001 | *(amended)* | Bake-off finalists refreshed to {Three.js, Babylon.js, PlayCanvas}; Godot Web demoted to contrast candidate absent a signed priority change; repairability axis records deprecated-API emission; backend parity added to the protocol. Provisional Three.js default unchanged; ordering still not a measured win. | — | — | W26; OJ amendment |

**Disposition of prior local-multiplayer obligations:** GB-WEB-045's unconditional hot-seat SHALL is superseded by R3D-SEAT-001/002 + R3D-LMP-001 (the evidence it bought is preserved unconditionally; the shipped mode becomes conditional). BD-06's fixed mode order becomes: single-player SHALL; LM1–LM3 conditional per declaration; networked M2+ conditional and, when enabled, its prerequisite is the seat-conformance corpus (R3D-SEAT-002), not a shipped hot-seat UI. No other v3D-1.0 row changes semantics.

## 10. Open decisions and invalidation triggers

| Decision | Closer | Notes |
| --- | --- | --- |
| Final render engine | Technical owner after the signed bake-off (R3D-QA-004, finalists per §3.1) | Three.js remains provisional default |
| Physics engine for P-AUTH | Rules lead at first P-AUTH game | Rapier `-deterministic` is the default candidate; Jolt requires a verified deterministic self-build |
| WebGL2 sunset date | Program owner, on platform evidence | Reopen when Firefox Linux/Android WebGPU ships stable and Safari 26 adoption saturates |
| LM3 on mobile | Design owner per game | Split-screen thermals/fill on mobile unmeasured; default LM3 to desktop-class matrices |
| Multi-seat assistive technology | Accessibility owner | §7.5 scopes AT to the primary seat; honest release-card language until solved |
| Human-fun sample size and rubric calibration | QA owner | Carried from lineage, still uncalibrated |
| Historical stance per game | Design/history director after claim ledger | R3D-HIS-001 machinery unchanged |
| Advanced opponent algorithm | Deliberately open behind the seat contract | Baselines suffice for acceptance; candidates compete later on the frozen curriculum |

Invalidation triggers: any [W26] platform fact fails re-verification (browser support regresses/advances, Rapier/Jolt determinism guarantees change, Playwright capture behavior changes); the bake-off produces a signed reversal; a Godot Web WebGPU release or PlayCanvas self-hosted editor materially changes §3.1's inputs; flagged [W26] items (Havok license rider, Jolt npm determinism, ViBench figures) resolve contrary to their stated readings.

## 11. Implementation frontier

Dependency-ordered; each item exits through its named oracle, per the atom rules of [R3D] §4.

| Work identity | Output | Depends on | Exit condition |
| --- | --- | --- | --- |
| W1-contracts | game-ir/contracts/seat schemas incl. seat manifest, LM levels, physics placement; deliberately-failing fixtures | this spec | schema suite + failing-oracle fixtures pass |
| W2-core | `game-core` with fixed step, seeded streams, seat-conformance corpus, baseline policies | W1 | privileged lane green: legality, invariants, role swaps, replay hashes, 2-process determinism |
| W3-renderer | Three.js adapter, WebGPU/WebGL2 parity harness, deterministic capture scenes | W1 | boot matrix + parity cells green on the declared matrix |
| W4-input | input adapter with pairing, keyboard partition, gamepad polling, full mock harness | W1 | every declared device class drivable blind via mocks |
| W5-greybox-slice | one complete 3D tactics vertical slice on greybox: navmesh proof, both-seat completion, LM skeleton | W2–W4 | A3 oracle + seat corpus + backend parity at one immutable hash |
| W6-assets | glTF gate battery (validator, transform pipeline, budgets, re-import), anchor workflow | W1 | gate battery rejects seeded-defect fixtures; clean asset passes end-to-end |
| W7-lm-modules | LM1/LM2/LM3 conditional modules + per-level gate suites | W4, W5 | each level's contract passes on the slice; N/A machinery proven on an LM0 build |
| W8-release | publisher adapter, two-key packet, rollback drill, CI GPU-mode cells | W5 | B12–B14 equivalents green; genesis + successor rollback rehearsed |
| W9-bakeoff | frozen protocol + three-engine run (§3.1) | W5 | R3D-QA-004 passes; signed ADR; reversal rule honored |

W1–W5 are the shortest credible path to a verified 3D slice; W7 activates per-game only as declared. The bake-off (W9) may run any time after the slice exists and blocks only irreversible engine adoption, not first delivery on the provisional default.

## 12. Risks

Top rows only; the lineage registers remain in force. Visual polish hiding shallow mechanics (High/High — greybox admission before art, separate verdicts). 3D asset defects surviving to integration (High/Medium — the §6.1 battery, clean re-import as the boundary). Determinism eroded by convenience (Medium/High — forbidden-import audits, replay trials in CI, WASM boundary for P-AUTH). CI flakiness from software GPU cells (High/Medium — correctness-only role for software cells, hardware cells for perf, environment-keyed goldens). LM scope creep toward networked play (Medium/High — the net adapter stays out of first delivery; LM levels are local-only by construction). Model-familiarity drift emitting deprecated engine APIs (Medium/Medium — pinned versions, repair-ledger, bake-off records emission rates). Provider/license contamination of assets (Medium/High — license classes per asset, non-OSI weights flagged before distribution). Overclaiming from one passing game (Medium/Medium — ViBench-calibrated humility; per-claim evidence discipline).

---

**Terminal statement.** Build the smallest complete 3D browser game that honestly passes this document: one authority, one seat seam at every level of local play, greybox before beauty, replay hashes before screenshots, two keys at release, and every conditional gate failing closed. Nothing here promises fun, beauty, or autonomous reliability; it defines who must prove each, against which evidence, with which oracles — and keeps the proof burden attached to every claim that ships.
