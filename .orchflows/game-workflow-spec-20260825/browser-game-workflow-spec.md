# Browser Game Creation Workflow — Specification

**Status:** authoritative successor specification, registry vBG-1.0
**Frozen:** 2026-08-25
**Workflow name:** `orch-browser-game`
**Audience:** Orchflows maintainers, workflow authors, renderer/physics adapter implementers, QA/evaluation owners
**Scope:** the AI-orchestrated workflow that turns a bounded prompt plus evidence into a playable, verified, editable **browser game — 2D, 2.5D, or 3D by declared profile — that may or may not include local multiplayer**

## 0. Lineage, authority, and supersession

Fifth document in one lineage, and the current execution authority:

| # | Document | Identity | Standing |
| --- | --- | --- | --- |
| 1 | Runtime-neutral program handoff (GameIR, six capabilities, GB-* catalog) | SHA-256 `F661CB57…` | lineage baseline |
| 2 | Browser-first handoff (two-key release, B0–B14, GB-WEB-001..058, Phaser-pinned 2D) | supplement SHA-256 `90417F4D…` | superseded on runtime; its gate and conditional-control machinery survives |
| 3 | Browser-native 3D program decision (2026-08-18: 3D-only, A0–A12 atoms, registry v3D-1.0) | evidence packet SHA-256 `0F321A9C…` | superseded on scope by #5; architecture and atoms survive |
| 4 | 3D workflow spec, registry v3D-1.1 (2026-08-25: LM envelope, physics placement, asset battery, CI rules) | commit `2d297ea` | **superseded on scope by this document**; every obligation preserved (§9) |
| 5 | **This document** — registry vBG-1.0 | — | generalizes #4 from 3D-only to all browser games via presentation profiles; adds the professional-practice QA layer |

**Why one workflow, decided:** of v3D-1.1's ~38 requirements, ~5 are dimension-specific in substance; the spine — deterministic authority, seats and local multiplayer, gates, replay oracles, release, CI — is dimension-agnostic, and 2D is in workflow terms a strict subset of 3D. Dimension therefore becomes a declared **presentation profile** (§3.1), not a workflow fork. All 3D rigor is preserved as the 3D profile's battery; the 2D profile adds a thinner battery of its own. Hybrid (2.5D/isometric: 3D rendering over grid logic) composes naturally, which a binary fork could not.

Evidence keys: **[S1]** Stage-1 synthesis + 18 reports; **[BR]** browser-focus research run; **[R3D]** the 3D program decision report; **[W26]** web research 2026-08-25 (platform facts, primary-source verified unless flagged); **[GD]** professional game-design-practice research 2026-08-25 (named sources: Keith, Librande, MDA, RITE, Swink, Nijman, Schreiber/Romero, Riot/Blizzard balance frameworks, Chen, Fan, Nystrom, Game Accessibility Guidelines, Xbox Accessibility Guidelines, CVAA, console-cert failure patterns); **OJ** = program judgment here. No evidence key promotes a vendor or secondary claim into a measured fact.

Not reopened: the one-authority architecture, the two-key release contract, the seat/LM envelope, physics placement, captured-output replay, the A0–A12 atom workflow.

## 1. Charter

A bounded prompt and evidence brief become an editable, reproducible **browser game**, its co-generated verifier, and a public release packet. "Playable" is two keys: a fresh, logged-out browser reaches an interactive start state at one immutable HTTPS URL, **and** the release ships downloadable editable source plus the exact self-hostable production build. Either key missing fails terminal acceptance. [BR][R3D]

Three envelopes are declared per game at design time, and each activates its conditional contracts automatically, failing closed:

1. **Presentation profile** (§3.1): dimension mode (2D / hybrid / 3D), renderer binding, world-oracle set, asset battery, budget defaults.
2. **Seat manifest + local-multiplayer level** (§5): LM0 single-seat through LM3 split-screen; every level ships bot fill; networked play stays an optional adapter at the controller seam.
3. **Physics placement** (§3.3): P-NONE / P-AUTH / P-VISUAL.

Calibration stands: under strict automated verification, frontier models pass fewer than half of end-to-end interactive builds (ViBench 2026, flagged secondhand) [W26]. The workflow's value is its verification and repair structure. Fun, beauty, feel, and historical treatment remain separately judged claims attached to an exact build.

**Non-goals** (unchanged from lineage): no unchecked prompt-to-finished-game jump; no rules or chance owned by rendering, wall-clock, network peers, or prose; no model call in a mandatory frame/turn path; no learned-opponent selection before the seat contract and baselines pass; no real-time *networked* competitive multiplayer, accounts, matchmaking, monetization, or live-service operations; no provider-owned canonical state; no unledgered historical-accuracy claims. Real-time **local** play is permitted at any profile. [S1][BR][R3D] OJ

## 2. Platform baseline (2026)

Observation-time facts; invalidation triggers in §10. Full detail in the v3D-1.1 lineage document; load-bearing summary:

- **WebGPU is default in all four browser engines but coverage has holes** (Firefox Linux/Android, pre-26 Apple OSes, vendor-dependent Android GPUs). A consumer-reach release SHALL treat WebGPU as preferred with a tested WebGL2 path, or declare a narrowed matrix with an explicit unsupported screen (R3D-PLT-001). This applies to 2D WebGL games as well. [W26]
- **CI:** GPU-less Chromium needs `--enable-unsafe-swiftshader` for WebGL and the Dawn/SwiftShader-Vulkan flag set for WebGPU; software cells are 10–30× slower and prove correctness only; Playwright traces exclude canvas — screenshots/video are the pixel channel; environment-keyed goldens, three.js-e2e style. [W26]
- **3D engines:** Three.js r185 (MIT, WebGPURenderer with automatic WebGL2 fallback, TSL, largest codegen corpus, API-churn hazard); Babylon.js 9.22 (Apache-2.0, TypeScript-first, dual GLSL/WGSL shaders, NullEngine headless); PlayCanvas 2.21 (MIT engine, entity-component, editor MCP server, hosted editor backend). Godot Web: WebGL2-only. [W26]
- **2D engines:** Phaser 4.2.1 is the corpus-evidenced default (MIT, WebGL+Canvas, 345 KB gzip full / 313 KB Arcade build, Arcade+Matter physics, TypeScript templates) [BR, observed 2026-08-17, not re-verified]. Pixi and others are admissible by adapter conformance (§3.1).
- **Physics:** Rapier ships `@dimforge/rapier2d` and `rapier3d` with the same three builds; the `-deterministic` builds guarantee cross-platform determinism under construction-order discipline (no JS transcendentals feeding the sim). Jolt requires a self-built deterministic WASM compile (flagged). cannon-es inactive. WASM float arithmetic is spec-deterministic; JS transcendentals are not. [W26]
- **Assets:** glTF 2.0 chain (glTF-Validator, glTF-Transform 4.4, gltfpack/meshopt, KTX2) for 3D; AI generation license classes — TRELLIS.2 (MIT, self-hostable), Hunyuan3D-2.1 (open weights, non-OSI community license), Meshy/Tripo (commercial APIs, terms vendor-asserted). [W26]

## 3. Architecture

**One authority.** A renderer-, DOM-, clock-, network-, and model-independent TypeScript(+WASM) `game-core` owns canonical state, fixed simulation step, seeded random streams, legal actions, transitions, typed events, objectives, terminal outcomes, serialization/migration, state hashes, and replay. Dependency direction: `versioned inputs → simulation authority → committed transitions → projections/adapters`. Rejections are typed and mutation-free. Camera pose and picking are input translation, never truth. Replay is captured-output replay; determinism claims scope to tested environments. [R3D-ARC-001/002, R3D-DET-001, R3D-RPL-001]

**Mandated programming patterns** (BG-PAT-001, from [GD]: Nystrom's catalog, mandating exactly the patterns whose absence breaks a workflow gate):

- **Fixed-timestep game loop with interpolated rendering** — the precondition for determinism and replay.
- **Command-reified input** — every player intent is a typed action object; this is what the semantic action envelope already is, now named as the load-bearing pattern for recording, replay, and desync testing.
- **Event queue as the only simulation→presentation channel** — sounds, particles, UI, and juice subscribe to committed events; nothing presentational lives in the core, and the feel gate (§7.6) becomes checkable ("every verb emits events").
- **Serializable, hashable state** with component-style composition.

Deliberately left free: archetype-ECS versus plain component objects (pure-ECS cache benefits are negligible in JS; mandating it is cargo cult [GD]), scene-graph organization (owned by the renderer library), and the optimization-pattern long tail.

### 3.1 Presentation profile (new, BG-PRF-001)

Every game's design fixes one profile:

| Field | Values | What it selects |
| --- | --- | --- |
| Dimension mode | `2d` / `hybrid` / `3d` | world-oracle set, asset battery, budget defaults, camera law |
| Renderer binding | `three.js` \| `babylon` \| `playcanvas` \| `phaser` \| `pixi` \| custom | the render-adapter implementation |
| World oracles | grid/layer set or navmesh/camera set (mixable in `hybrid`) | greybox and assembly gates |
| Asset battery | 2D battery / 3D battery / both | §6 gates |
| Budgets | per-device numeric defaults for the mode | §7.7 |

**Renderer flexibility (BG-REN-001):** the workflow requires the **render-adapter contract** — projection of committed state keyed by semantic IDs, pick/input translation into the action union, deterministic capture scenes, performance sampling, backend policy — not any library. Evidenced defaults ship (Three.js for `3d`, Phaser for `2d`; neither is a measured win), and a user-specified library is admissible when its adapter passes the adapter-conformance corpus. The signed bake-off (R3D-QA-004, finalists Three.js/Babylon/PlayCanvas) governs changing a *default*, never a per-game user choice. `hybrid` typically pairs a 3D renderer binding with grid world oracles — the common tactics shape.

### 3.2 (reserved — bake-off protocol unchanged from v3D-1.1)

### 3.3 Physics placement (unchanged law, both dimensions)

P-NONE (rules-resolved movement; default for discrete forms) / P-AUTH (physics is game truth: runs inside the core's fixed step from a pinned-hash deterministic build — `rapier2d`/`rapier3d -deterministic` are the npm-shippable options — with construction-order and transcendental discipline, snapshot-hash desync checks) / P-VISUAL (decoration; may never feed authority, enforced by forbidden-import audit). [R3D-PHY-001][W26]

## 4. GameIR, design artifacts, and studio topology

Carried unchanged: ten GameIR namespaces; five canonical stores; six capability owners; propose→validate→commit transactions with receipts and unknown-outcome reconciliation; producer/checker/fixer separation; bounded repair with a persisted fix ledger. [S1][R3D]

**Design artifacts upgraded from professional practice** (BG-DES-001, [GD]) — the `design` namespace now requires four typed artifacts, replacing any monolithic design document:

1. **Design pillars** — at most five, each phrased as a player experience (Keith; Unpacking precedent). Pillars are the rejection function: a feature ticket serving no pillar is cut, and every human judgment gate scores against them.
2. **One-page design per system** — one diagram-anchored page per mechanic system, hard word cap as the enforceable proxy for Librande's discipline.
3. **Core-loop specification** with machine-checkable closure: challenge→action→reward cycles at declared time scales, every reward carrying a reinvestment edge, and every mechanic in the backlog appearing on some loop or flagged orphan.
4. **Per-feature MDA target** — one line per feature ticket naming the target aesthetic (MDA's eight-aesthetic vocabulary) and the expected dynamic, giving playtest judgment something falsifiable.

The `controls` namespace owns the seat manifest, LM level, device bindings. The `evaluation` namespace owns the QA target manifest (§7.1), CI GPU modes, and the milestone ledger (§7.8).

Repository boundary: as v3D-1.1 §4, with `adapters/renderer` resolved per profile binding and `packages/game-physics` selecting the 2D or 3D deterministic build.

## 5. Seats and the local-multiplayer envelope

Unchanged from v3D-1.1 §5 — it was dimension-agnostic by construction. Summary of the standing law: seat manifest + one declared level (LM0 single-seat / LM1 hot-seat / LM2 shared-screen / LM3 split-screen); every level ships bot fill; the headless **seat-conformance corpus** (seat auth, out-of-turn rejection, per-seat visibility filtering, role swaps, per-seat replay streams) runs regardless of declared level; input devices bind through a pairing ceremony behind a mockable interface (no CDP gamepad domain exists); same-tick simultaneous intents commit under a stable ordering key; LM3 budgets are measured at max declared seats. Split-screen viewports and multi-device input work identically in 2D. [R3D-SEAT/LMP/INP rows]

## 6. World and asset pipeline

The A0–A12 atom graph stands with its v3D-1.1 amendments (design fixes the three envelopes; greybox proves topology, movement legality, and the LM input skeleton before art; integration proves backend parity). Profile-keyed specifics:

**World oracles.** Shared law: semantic topology as a diffable graph independent of appearance; global-before-local assembly; one reconciler for shared-topology changes. `3d`: navmesh/movement-graph reachability, collision intent, camera bounds and readability at target distances. `2d`: grid/graph adjacency, layer ordering, tile traversability, viewport/scroll bounds. `hybrid`: grid oracles plus the 3D camera law.

**Asset batteries** (each gate fail-capable, all feeding the R3D-PRV-001 provenance manifest):

- **3D battery** (R3D-AST-001, unchanged): glTF validation → unit/axis/pivot normalization → budgets → collider/LOD/rig integrity → pinned meshopt/Draco+KTX2 → clean re-import with multi-view anchored review → provenance.
- **2D battery** (BG-AST-002, new): format/atlas validation (packing, bleed/extrusion margins, power-of-two or declared exception) → alpha-coverage and bounds checks on generated sprites (the Rosebud-documented validator pattern [S1: R04]) → pixel-density variants per declared DPR set → animation-frame consistency (dimensions, pivot, frame count vs manifest) → tilemap validation (tile indices resolve, collision layer integrity) → 9-slice integrity where used → clean re-import into the pinned renderer → provenance.

Sourcing routing and style discipline unchanged: libraries first, procedural/instanced second, generation for gaps; explore → freeze hashed style anchors → enforce; staging quarantined. License classes recorded per asset. [S1: R10/R11][W26]

## 7. Verification — the QA subsystem

This section absorbs the professional-practice research and is redesigned around one requirement: **the QA subsystem stands alone.** It runs inside the build workflow as the gate, and it runs by itself against any browser game — including games this workflow did not build — with multiple counterparties when the game is multiplayer.

### 7.1 The QA target manifest (BG-QA-005)

All QA operates on a declared, versioned **QA target manifest**, never on ambient knowledge:

- the target: immutable URL or local build identity;
- the player-facing guide (controls, objective, declared paths);
- the **seat/counterparty configuration**: how many seats, and per seat a driver — `scripted-policy` (typed actions through a hook), `blind-agent` (drives public UI from pixels/DOM only), `mock-device` (init-script gamepad/keyboard mock), or `human`;
- optional **semantic hooks** when the target exposes them: observation/legal-action/action API, replay export, state-hash endpoint, event stream;
- oracle selection and applicability answers (multiplayer? economy? historical content? communication features?).

Games built by this workflow emit a rich manifest automatically (all hooks present). External games get a degraded manifest — blind lanes only — and **every verdict states its evidence ceiling**: a blind-only PASS asserts surface playability, never rules correctness. Honesty about the ceiling is a gate: a lane claiming evidence its manifest cannot support is itself a FAIL.

### 7.2 Suite structure and the one severity taxonomy

Lanes run in the professional suite order, cheap before expensive [GD]: **smoke → functional (blind play) → privileged (rules) → regression → visual/feel → performance/soak → compliance → accessibility → balance → human gates.** Two-lane independence stands: blind lanes never read privileged state; privileged lanes never trust pixels; verdicts join only at the report.

**One taxonomy everywhere (BG-QA-007):** every finding — automated, agent-playtest, or human — carries **A/B/C severity** (A = ship-blocker: crash, softlock, save corruption, compliance failure; B = major: broken behavior, desync, unusable UI, sustained frame collapse; C = minor/cosmetic) plus frequency, resolution cost to the player, and evidence links. Milestone exits are phrased in this taxonomy and are machine-decidable (§7.8). [GD]

### 7.3 Multi-counterparty play (BG-QA-006)

For any multi-seat target, the play lane instantiates the declared counterparties and runs **full matches**:

- local levels: N mock-devices or N driver agents against one page (LM1 handoff, LM2 shared-screen, LM3 split-screen per their contracts);
- networked targets (standalone use against external games): N browser contexts, one per client;
- seats run concurrently within a match; matches run in parallel across the seed matrix; role swaps and paired seeds throughout. [S1: R17/R18]

**Desync battery** (deterministic targets, and mandatory for any networked target with hooks): record initial state + full per-seat input stream; replay must reproduce per-tick state hashes; cross-context replay (second browser engine, or worker vs main thread) is the two-machines analog; in live multi-client sessions, per-tick or periodic checksums compare across clients and the first differing field localizes the nondeterminism (canonical causes: float divergence, iteration order, unstable sorts, uninitialized state). Soak = long random-input replay asserting no NaN, drift, or leak. [GD][W26]

### 7.4 Playtest protocol (BG-QA-008)

- **Freshness is enforced, not assumed** (the Kleenex rule): a first-experience verdict — agent or human — must come from a context that has never seen the game's design docs or source. An agent with the GDD in context is not a fresh tester. First-exposure sessions are single-use. [GD]
- **RITE-shaped convergence**: the playtest-repair loop iterates small fresh batches with immediate fixes, and exits when **N consecutive fresh sessions surface zero new findings of severity B or above** (N declared per game, default 3). This is the bounded-repair loop the workflow already has, with the professional exit criterion. [GD]
- Findings use the severity×frequency×resolution×evidence schema (§7.2), grouped by theme, so they route as repair tickets without translation.
- "Is it fun" remains a low-sample human judgment against the pillars and per-feature MDA targets — scoped by rubric, never faked by automation. [GD]

### 7.5 FTUE gate (BG-FTU-001)

From Fan's onboarding rules, the checkable subset [GD]: instruction surfaces at most **8 words** at a time (static check on the string table); each mechanic's first use is **performed, not described**, in a safe context (checkable against level scripts); mechanics ramp at the declared rate (one new mechanic per level/segment against the core-loop spec); no modal text walls. The tutorial emits one funnel event per step; a fresh blind agent must complete the funnel in CI. Aha-moment/retention analytics are post-release scope, stated honestly.

### 7.6 Feel gate (BG-FEL-001)

Split automatable from judged [GD]:

- **Automated:** input-to-visible-response latency within the declared budget (default ceiling 100 ms, Swink's cycle bound — flagged secondary); every verb in the core-loop spec emits at least one visual and one audio event (checkable because the event queue is the only sim→presentation channel, §3); frame budget holds while feedback plays; independent SFX/music volume controls exist; muted play remains complete.
- **Judged juice checklist**, walked per verb at the slice and beta gates (from the Nijman list, flagged fan-transcript ordering): hit-stop on significant impacts, impact effects, screen shake scaled and cappable, camera smoothing/lookahead, animation anticipation/follow-through, world permanence for consequential events. Presence is checked; tuning is taste and stays human.

### 7.7 Performance, compliance, and accessibility

- **Budgets** (R3D-PERF-001, profile defaults): 3D as v3D-1.1 §7.3; 2D defaults tighten transfer and interactive numbers (signable, OJ). LM3 measured at max seats; software-GPU cells never produce performance verdicts.
- **Web-TRC** (BG-CMP-001, new — the console-cert transfer [GD]): a fixed, versioned, pass/fail compliance checklist run against release candidates, transliterating the public cert-failure patterns to the browser: survives tab-hide/`visibilitychange` and focus loss without state corruption (suspend/resume analog); interrupted localStorage/IndexedDB writes recover; refresh mid-game recovers or cleanly restarts; no console errors or debug surfaces in release; minimum supported viewport works; audio obeys autoplay policies; asset 404s degrade declaredly; load-time budget; legal/license text present. Binary, no averaging.
- **Accessibility** (BG-ACC-002, expanding R3D-ACC-001): **Game Accessibility Guidelines basic tier is a hard gate** — remappable controls covering every verb, sensitivity options, no essential information by color alone or sound alone, subtitles for speech, separate volume controls, readable defaults, settings persistence, photosensitivity limits (automatable frame-analysis pass), pause-anywhere, DOM shell for essential functions. GAG intermediate = scored rubric; advanced = backlog. **CVAA conditional flag:** if player-to-player communication ever ships, accessible-communication requirements become a legal obligation, carried as a conditional row on the communication ticket type. Gate entries follow the XAG shape (goal / scoping questions / implementation checks / player impact). [GD]

### 7.8 Balance gates and milestones

**Balance (BG-BAL-001, conditional on form [GD]):** games with purchasable/upgradable objects carry a typed **cost-curve artifact**; the gate recomputes every object's position and fails on undeclared outliers (Schreiber/Romero). Asymmetric/PvP forms run **self-play matrices** at multiple bot-skill settings; any side leaving the declared win-rate band (default 45–55%) at any skill setting fails (the Riot band rule over deterministic self-play); reachability, not equality, remains the law for deliberately asymmetric scenarios. Difficulty curves: agent-playthrough fail rates per level must ramp within declared tolerance, no undeclared spike; flow judgment stays human (Chen).

**Milestones (machine-decidable [GD]):** **first playable** = the greybox slice joins (G5); **alpha (feature complete)** = every ticket in the feature manifest closed; **beta (content complete)** = asset manifest closed, zero open A-class, B-class within declared bound; **gold** = web-TRC + full regression + rollback drill green + human gates signed. Milestone status derives from the ledgers, never from prose.

## 8. Release and operations

Unchanged two-key spine (immutable URL + editable source/self-hostable build, `release.json` genesis/successor shapes, publisher receives only tested bytes, remote reconciliation and smoke, atomic alias promotion, rehearsed rollback, recovery never regenerates content, publication authority separate from build success), with **web-TRC and the milestone ledger added to the release gate order**, and the release card additionally stating: profile, LM level and device requirements, evidence ceilings of any degraded QA lanes, and the accessibility tier achieved. [BR][R3D][GD]

## 9. Registry vBG-1.0

vBG-1.0 = all v3D-1.1 rows preserved under their existing IDs (`R3D-*` names are lineage identifiers, not scope claims — their obligations are dimension-agnostic except where profile-keyed below) + the following. Governance per R3D-GOV-001; SHALL is release-blocking; conditional rows fail closed with signed N/A.

| Stable ID | Modality | Normative requirement (compressed) | Prerequisites | Applicability | Provenance |
| --- | --- | --- | --- | --- | --- |
| BG-PRF-001 | profile | Every game declares one presentation profile (dimension mode, renderer binding, world oracles, asset battery, budgets) at design time; profile-keyed rows activate accordingly; a profile change is a design revision with a new candidate identity. | R3D-ARC-001 | Every game | OJ; supersedes v3D-1.1's implicit 3D-only applicability |
| BG-REN-001 | renderer | The workflow SHALL require the render-adapter contract, not a library. Evidenced defaults ship per mode; a user-specified binding is admissible when its adapter passes the conformance corpus; the signed bake-off governs default changes only. FAIL if game code depends on renderer internals across the adapter boundary or an unconformant binding ships. | BG-PRF-001 | Every game | W26/BR; amends R3D-DEC-001 |
| BG-AST-002 | assets-2d | 2D assets pass: atlas/format validation, alpha-coverage and bounds checks, DPR variants, animation-frame consistency, tilemap and 9-slice integrity, clean re-import, provenance. | R3D-PRV-001 | 2D/hybrid releases | S1 R04/R03; OJ. R3D-AST-001 becomes the 3D-profile battery |
| BG-PAT-001 | architecture | Generated cores SHALL use fixed-timestep loop with interpolated render, command-reified input, an event queue as the only sim→presentation channel, and serializable hashable state. ECS-vs-component and scene-graph organization stay free. FAIL on wall-clock in the reducer, presentational writes from the core, or unreified input paths. | R3D-DET-001 | Every game | GD (Nystrom); OJ |
| BG-DES-001 | design | The design namespace SHALL contain: ≤5 player-experience pillars; one-page-per-system; a core-loop spec passing closure checks (reinvestment edges, no orphan mechanics); per-feature MDA targets. Human gates score against pillars and targets. | R3D-ARC-002 | Every game | GD (Librande, Keith, MDA); OJ |
| BG-QA-005 | qa-standalone | All QA operates on a versioned QA target manifest (target, guide, seat/counterparty config, optional hooks, applicability); lanes run only what the manifest supports and every verdict states its evidence ceiling. The QA composition SHALL be invocable standalone against any browser game. FAIL on ambient-knowledge QA or a verdict exceeding its ceiling. | R3D-QA-001 | Every QA run | OJ |
| BG-QA-006 | qa-multiparty | Multi-seat targets are exercised by full matches with N declared counterparty drivers (scripted/blind-agent/mock-device/human), seats concurrent within a match, matches parallel across the seed matrix, role swaps and paired seeds; deterministic targets run the desync battery (replay hashes, cross-context replay, per-tick multi-client checksums, soak). | BG-QA-005, R3D-SEAT-002 | Multi-seat targets; signed N/A otherwise | GD; S1 R17/R18; OJ |
| BG-QA-007 | qa-taxonomy | One A/B/C severity taxonomy with frequency, player resolution cost, and evidence links across all findings; milestone exits phrased in it and machine-decided from ledgers (first playable / alpha / beta / gold). | BG-QA-005 | Every release | GD; OJ |
| BG-QA-008 | playtest | First-experience verdicts come only from doc-blind, single-use contexts; the playtest-repair loop exits on N consecutive fresh sessions with zero new ≥B findings; fun verdicts are human, rubric-scoped to pillars/MDA targets. | BG-QA-007, R3D-QA-003 | Every release | GD (RITE, Kleenex); OJ |
| BG-CMP-001 | compliance | A versioned web-TRC checklist (visibility/focus survival, interrupted-save recovery, refresh recovery, clean console, min viewport, autoplay policy, 404 degradation, load budget, legal text) gates every release candidate, binary. | R3D-QA-001 | Every release | GD (cert failure patterns); OJ |
| BG-FTU-001 | onboarding | Instruction surfaces ≤8 words; first mechanic use performed-not-described in safe context; declared mechanic ramp; funnel events per tutorial step with a fresh blind agent completing the funnel in CI. | BG-DES-001, BG-QA-008 | Games with onboarding; signed N/A otherwise | GD (Fan); OJ |
| BG-FEL-001 | feel | Automated: input-to-response latency within declared budget (default 100 ms, flagged secondary); every core-loop verb emits ≥1 visual and ≥1 audio event; frame budget holds; independent volume controls; muted play complete. Judged: per-verb juice checklist at slice and beta. | BG-PAT-001, BG-DES-001 | Every game | GD (Swink, Jonasson/Purho, Nijman); OJ |
| BG-BAL-001 | balance | Economy forms: typed cost-curve artifact recomputed at gate, undeclared outliers fail. PvP/asymmetric forms: self-play matrices at multiple bot skills within declared win-rate bands (asymmetric scenarios keep reachability law). Difficulty fail-rate curves ramp within tolerance. | BG-QA-006, R3D-RPL-001 | Conditional on form; signed N/A otherwise | GD (Schreiber/Romero, Riot, Chen); OJ |
| BG-ACC-002 | accessibility | GAG basic tier is a hard gate (enumerated checks incl. photosensitivity frame analysis, color/sound-alone bans, remap coverage of every verb, settings persistence); intermediate = scored rubric; advanced = backlog; CVAA activates as a conditional legal row if player communication ships. | R3D-ACC-001 | Every release | GD (GAG, XAG, CVAA); expands R3D-ACC-001 |

**Supersession notes:** v3D-1.1's whole-document 3D scope is superseded by BG-PRF-001; R3D-AST-001 is re-keyed as the 3D battery; R3D-DEC-001 is amended by BG-REN-001 (defaults vs per-game choice); every other v3D-1.1 row stands unmodified. No implicit carry-forward: a predecessor obligation not represented here or in v3D-1.1 must enter as a new versioned row.

## 10. Open decisions and invalidation triggers

Carried forward (final default renderers after bake-off; P-AUTH physics engine; WebGL2 sunset; LM3 mobile; multi-seat assistive technology; human-fun sample calibration; historical stance per game; advanced opponent). New:

| Decision | Closer | Notes |
| --- | --- | --- |
| 2D default binding confirmation | Technical owner | Phaser 4.2.1 is corpus-evidenced but not re-verified in [W26]; re-verify at F2, or run a small 2D bake-off (Phaser vs Pixi) under the same protocol discipline |
| Blind-agent driver model/harness | QA owner | which agent drives `blind-agent` counterparties, and its cost/latency budget per match |
| RITE convergence N and severity floor | QA owner per game class | default 3 sessions / ≥B; calibrate from early runs |
| Web-TRC checklist v1 contents | Release owner | §7.7 list is the seed; freeze and version it |

Invalidation triggers as v3D-1.1 §10, plus: GAG/XAG guideline revisions; CVAA interpretation changes; the flagged [GD] items (Swink 100 ms, Nijman list ordering, beta bug-threshold numbers) resolving contrary to their stated readings.

## 11. Implementation frontier

Restated for the generalized scope; QA is now its own early, independently valuable track.

| Work identity | Output | Depends on | Exit condition |
| --- | --- | --- | --- |
| W1-contracts | schemas: GameIR, actions/observations, seats/LM, profile, **QA target manifest**, findings/severity, milestone ledger; failing fixtures | this spec | schema suite + failing-oracle fixtures pass |
| W2-core | `game-core` skeleton: fixed step, seeded streams, command input, event queue, seat corpus, baseline policies | W1 | privileged lane green; two-process determinism |
| W3-qa-standalone | the QA composition + lanes runnable from a bare manifest against **any** browser game (blind mode) | W1 | runs green (and honestly ceiling-limited) against one external game never seen before |
| W4-renderer+input | default render adapters (3D: Three.js; 2D: Phaser) + adapter-conformance corpus; input adapter with mocks | W1 | conformance corpus green on both defaults |
| W5-greybox-slice | one vertical slice per mode kind (first: one `hybrid` tactics slice) with navmesh/grid proof, both-seat completion, LM skeleton | W2, W4 | first-playable milestone; seat corpus; backend parity |
| W6-asset-batteries | 2D + 3D gate batteries + anchor workflow | W1 | batteries reject seeded-defect fixtures; clean assets pass |
| W7-lm+gates | LM modules; FTUE/feel/balance/compliance/accessibility gate suites | W3, W5 | each gate passes on the slice and fails its seeded-defect fixture |
| W8-release | publisher, two-key packet, web-TRC v1, rollback drill | W5 | gold-milestone machinery green end to end |
| W9-bakeoffs | 3D bake-off (Three/Babylon/PlayCanvas); optional 2D (Phaser/Pixi) | W5 | R3D-QA-004 protocol; signed ADRs |

W3 is deliberately early and parallel to W2: the standalone QA track needs only the manifest schema, delivers value immediately against existing games, and dogfoods the finding taxonomy before the factory builds its first game.

## 12. Risks

As v3D-1.1 §12, plus: **profile sprawl** (Medium/Medium — profiles are closed enumerations with signed additions, not free-form config); **QA-standalone drift from the in-workflow gate** (Medium/High — one composition, two manifests; never two QA implementations); **blind-agent cost per match** (Medium/Medium — scripted-policy drivers are the default matrix workhorse, blind agents reserved for FTUE and exploratory passes); **checklist theater** (Medium/Medium — every checklist row keeps a seeded-defect fixture proving it can fail).

---

**Terminal statement.** One workflow, three declared envelopes — profile, seats, physics — and a QA subsystem honest enough to stand alone: every lane knows its evidence ceiling, every finding carries one severity language, every milestone is decided by a ledger, and every checklist row can prove it knows how to fail. Build the smallest game that passes; scale only from an admitted identity.
