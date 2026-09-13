# Full workflow dogfood: Nightbind

## Scope and ownership

Run the example workflow through all 20 steps for the user brief in request.md. Caller owns scope, tool probing, four child dispatches and joining. The game maker owns game code and production notes; later the Blender maker owns assets/source and the agreed asset export directory. Review candidates freeze during independent browser play.

## Observations

- The workflow is directly usable from example-workflows without installation or a scheduler. Resolved source guidance is passed to native children.
- Capability probing can reuse disposable tooling from an earlier run, but actual version/export/browser checks still run. No game content is copied from the earlier bounded trial.
- The in-app browser cannot hold physical keys or mutate hooks through evaluation. The existing workflow's ordinary-control requirement and DOM diagnostic alternative provide a viable route; the public game needs usable click-to-move.

Further findings, production checkpoints and final coverage will be appended as observed.

## Early production observation

The maker wrote three capture-loop alternatives and experiment predictions before the renderer. Caller then tried ordinary title → start → lantern → capture and click-to-move in the first development build. A real nearby Emberling became a companion and charge was consumed. This was an informal smoke observation, not independent acceptance or a complete session.

At 1280×720 the initial full-arena camera made base creatures roughly 10–15 pixels wide, risking poor role/art readability. Caller sent this observed concern back during step 7, asking the maker to test closer framing without prescribing a camera implementation. Evidence: `evidence/caller/early-camera.png`. The workflow's gameplay-camera check exposed a production risk before asset modeling.

## Testability during mechanics experiments

The maker reported that this browser's read-only evaluation scope could not read arbitrary window globals. A JavaScript test hook alone therefore did not provide the promised observation route. The implementation added a DOM mirror for read-only state, while scenario/reset/step actions remained visible development controls. A diagnostic panel also overlapped a public modal close button; opening a modal was changed to collapse the panel. These are concrete reasons to probe and play the actual tool route early.

Caller source inspection also identified clamped simulation delta being reused for frame-time measurements. The maker will preserve raw frame intervals separately before profiling. The reusable evidence guidance already calls for actual stalls and backend identification; this was an implementation issue caught before a performance claim.

## Full-run pacing challenged before review

The maker's ordinary production-preview route reached the first gate with 76 hostiles and 54 vitality; the planned Pyre evolution reduced the crowd to 48 and raised vitality to 75 after about 4.6 seconds. Continued decisions included taking a second healer while preserving later recipe ingredients.

That sensible composition exposed a problem in wave 9: 88 hostiles still left the keeper near 100 vitality while routing diagonally. The maker explicitly withheld a second-spike pacing pass and planned to finish checking the route's outcome, then tune/replay the affected arc before freezing the core. This is a substantive use of the workflow's full-session experiment gate: a damage upgrade and high enemy count alone did not establish the user's promised pressure and release.

## Caller rule probe before core freeze

Source inspection suggested enemy Moth healing could revive a victim killed earlier in the same tick. A bounded Node fixture confirmed it: fresh playing state, Emberling at (3,0) with 1 HP, enemy Moth at the same location with its heal ready, one update. Output was `kills: 1, defeatedTargetStillAlive: true, remainingHP: 1`. The keeper's lethal bolt was undone by healing before dead-entity removal. Caller sent reproduction to the game maker for a living-target guard and regression check. No game files were edited by the caller; this is ordinary production QA, not the independent core review.

After the maker added the guard, the same caller probe returned `kills: 1, defeatedTargetStillAlive: false, remainingHP: -7`. A separate ordinary browser check confirmed Escape from the current title and its Field guide leaves a usable start screen. No failure was observed in that check.

## Core review and workflow refinements

The maker froze `core-220cfa39951c`; nine rule tests and 16 source/built manifest hashes passed. A fresh reviewer (`nightbind_core_review`, with no conversation history) began production play on port 4191. It read private notes after a recorded recruit/reposition attempt, consistently with the caller's original "first attempt" wording. Only that onboarding is uncoached; its subsequent full run is informed ordinary play. Caller clarified the boundary and explicitly prohibited relabeling a restart as uncoached.

This ambiguity led to a small workflow change: the playtest leaf now reserves private maker material until the first ordinary outcome or observed blocker, reuses a completed run for the next session requirement, and records an early disclosure honestly. The final reviewer will exercise this clarified instruction. The Three.js reference also now says to record raw frame intervals before simulation clamping, addressing the measured-code issue identified above. Both changes are in the source example library; game source remains frozen. Include these two clarifications in final independent review alongside the finished game.

The clarified package passed a fresh disposable install check: all 18 files copied exactly, three skills resolved, 22 local links stayed valid, doctor returned ready, and repeated setup preserved the library. The core installation excluded the `dogfood` game output. Validation script: `C:/Users/danhm/tmp/orchflows-game-validation-20260913/check_package.py`. It creates and validates a contained temporary directory under that explicitly named validation workspace before automatic cleanup.

## Core checkpoint and transition to art

The independent reviewer returned ready on unchanged `core-220cfa39951c`. Its informed ordinary run reached victory at wave 12 with 1,662 kills and Storm, Pyre and Worldcoil earned through public capture/evolution controls. A stationary squad held through wave 8; wave 9 reduced vitality from 120 to 70, prompting escape. Worldcoil at wave 10 reduced 119 hostiles to 13 in approximately four seconds. An ordinary no-capture run lost at wave 2, and both outcome routes supported clean retry. Public and diagnostic movement/capture snapshots matched, pause blocked manual advancement, and nine rule tests passed independently.

These observations support the core pressure/relief and choice promises; they do not establish final art, all full-run compositions or human enjoyment. The reviewer noted a nearly empty wave 11 after Worldcoil and timing-sensitive recruitment because allies may defeat a wanted target. Those are retained for production/final assessment. Caller inspected the actual late-wave pressure and post-ascension captures.

No core repair is required. The same game maker continues to step 12's art direction and asset contract; the caller retains step 13's independent Blender dispatch. This exercises the clarified no-repair and caller-owned handoff boundaries without a redundant rebuild or replay.

## Camera-study inspection

The maker authored a bounded keeper/environment concept and original flat silhouette proposals for the creature lineages. Its browser connection returned no browsers, while the caller's supported in-app runtime remained available. The caller operated that runtime, saved actual views in `evidence/art-direction/`, and returned them for the maker to inspect. This is disclosed shared tool operation, not an independent review or a substitute for later GLB inspection.

The first busy-study capture showed no creatures even though the DOM summary reported 90. A later capture remained empty and browser error/warning logs were empty. Caller reported the visual failure for correction; the counter and successful page load did not establish crowd readability. The initial plain camera and keeper-detail views also exposed a mostly clipped rear landmark and the small keeper silhouette at normal camera scale. These observations inform the art brief before broad production.

The maker gave the SVG textures explicit dimensions and tighter silhouette bounds, enlarged the concept keeper by 18%, broadened Thornback's form, and moved the bell arch to the visible northeast boundary. After reloading, caller observed the 90 creature billboards, distinct outline families and visible arch at 1280×720. Corrected views have `-v2` suffixes; the first failed capture remains. This verifies the bounded concept study, not final three-dimensional creature models. Actual exported models still require their own runtime inspection.

## Blender dispatch and parallel content work

Step 12 delivered `notes/core-baseline.md`, `art-direction.md` and `asset-brief.md`, with all 16 core hashes unchanged. The brief defines 22 models, actual camera/basis/size targets, part and socket ownership, rigid animation, portraits, measured export metadata and target-relative budgets. It explicitly distinguishes planned runtime preview from a route already verified.

Caller dispatched the third child, `/root/nightbind_assets`, through the Blender leaf and `orch-work`, with no children. Its exclusive paths are `assets/source/`, `public/models/`, `evidence/assets/` and `notes/assets.md`. The original game maker continues step 14 on distinct code and content files, starting with the shared loader and `/asset-preview.html`. Representative keeper/lantern and arch/rim exports must be inspected through that loader before the asset family is expanded. Caller will join both outcomes before integrated production QA. No candidate acceptance or full asset production is inferred from the completed art brief.

## Representative source/export checkpoint

The first five actual Blender exports loaded through the shared game GLTFLoader with the expected bounds and vertex colors. Caller runtime inspection exposed a sideways lantern disconnected from the keeper's hand: the exported sockets carried an unintended 90° X rotation. The asset maker independently reproduced it in its own working browser tab, corrected socket transforms in source, and re-exported before producing the creatures. This avoided spreading a basis/attachment error across the full set. The original failed keeper capture and JSON remain under `evidence/art-direction/`; corrected views and metadata are under `evidence/assets/`.

The asset maker then inspected source front/side/three-quarter/game-camera views, the upright held lantern in the actual loader, the arch, and two joined rim exports. It returned the representative checkpoint ready and began the remaining set. Caller also inspected the corrected runtime keeper image. This establishes the staged Blender handoff in observed use; static preview checks remain distinct from subsequent integrated gameplay/performance QA.

## Step 14 and operating boundaries

The original maker completed the shared loader/preview, twelve contextual encounter cues, exact capture-target feedback, and companion attack-source presentation while the asset maker owned exports. Caller ordinary QA found and helped resolve a panel obstruction through a dedicated paused Lantern view. `notes/caller-step14.md` records the corrected center/left/right checks, return-to-movement mapping, actual capture, intermediate candidate identity and interrupted attempts. The isolated temporary preview on 4192 was stopped; both normal project servers remained available.

Concurrent browser activity and a development reload complicated a live check. The caller serialized the remaining input sequence and used a compiled preview; it passed without the earlier unexpected reset. The reset's cause was not established, and a separate tab probe did not prove real blur behavior. The existing library instruction to serialize a shared interactive tool is relevant; no new transport or disabled pause behavior was used.

During preparation for the join, caller checked the QA plan against the existing test-interface contract. A compiled diagnostic page must belong to a separate test build/identity, rather than treating an extra URL in the ordinary release as isolation. Actual release play/performance remains required. This is application of the existing contract, not another package change or a completed final QA claim.

## Asset join

The Blender maker completed 22 GLBs (485,472 bytes), 24 editable `.blend` sources, 15 portraits, source/export tools and an evidence-linked report in `notes/assets.md`. Every export passed Khronos validation with zero errors/warnings, loaded through the shared renderer with the expected hash, and reproduced byte-for-byte when re-exported from saved editable sources. Four-facing runtime inspection prompted changes to Storm's projected form and the ascension openings before handoff; source beauty views alone would not have revealed those weaknesses.

Caller verified all 70 entries in `evidence/assets/delivery-inventory.json` against actual file bytes/hashes, with zero mismatches. Final asset manifest SHA-256 is `b943f7fca7efc58f225fdf6f7add960a1bf71218943df84274434e6628e00f66`. The source and public model directories are frozen for integration. The same original game maker now continues steps 15–18; caller plans actual ordinary Dusk/Eclipse play on the joined release, with no additional worker or premature final review.

The asset maker's later cleanup turn could not reconnect to its previous browser, so its tab closure was unconfirmed. Caller browser inventory showed only the caller's static study tab. This host continuation limitation is retained rather than claiming a successful close or using another browser transport.

## Integrated production play and QA

The original maker integrated the frozen Blender set, portrait UI, rigid part motion, capture/awakening effects, browser audio, settings and loading/error flows. It produced separately compiled ordinary `release-c09f13cac8e9` (4191) and assisted `qa-c09f13cac8e9` (4193) from the same source digest. The release audit excluded the adapter and fixture code. Source/dist remained frozen while the caller operated its working browser and the maker inspected saved images and hashes.

Caller ordinary Dusk/Eclipse play first lost at wave 4 after a costly hunter interception and stationary poison exposure. The retry changed acquisition timing and movement cadence, then earned Dusk at 88.067s and Eclipse at 198.067s, defeated the boss at 252.833s and retried cleanly. The wave-nine horde reached 240 actual enemies; after Eclipse, 238 enemies fell to 42 in about five seconds. Dusk's first relief was slower, stationary tests still caused damage, and the successful route held high health through the busiest wave. The report preserves those qualifications rather than flattening every result into the intended fantasy. Full evidence and decisions: `caller-production-play.md`.

Production frame history recorded raw intervals and live workload. A first attempt to return the entire history through the browser hit a 200,000-character tool limit. The caller and maker both detected invalid truncated JSON. The caller retained the failed exports as `.truncated.txt`, then obtained bounded wave-nine raw rows, metadata and per-run/per-wave statistics through permitted read-only DOM evaluation. The busy section contained 1,160 active frames at 150–240 enemies, p95 16.9ms and max 18.9ms on the actual Intel/D3D11 backend. Public pauses divide these samples; the 91ms reload observation was warm and cannot establish cache-cold load performance.

The separate test build then exercised integrated Pyre, Solar, Storm and Worldcoil using the public recipe actions and exactly 90 manual ticks each. A full-squad release-and-replace check removed one actual hostile without an intervening simulation tick. Reduced-motion combat remained visible and the Settings pause blocked manual advancement. An intentionally missing model in an isolated copy produced a recoverable loading error, and its public retry worked after restoring only that copy. Three additional ordinary retries kept fresh state and stable renderer resource counts. These are production QA observations, not another independent review, an ordinary route through injected states, or a performance claim from manual stepping.

The maker is closing steps 15–18 with those results and explicit host limits. The caller will dispatch the fourth fresh child only on the frozen joined candidate; its first public-only run must reach an outcome or observed blocker before reading these private notes.
