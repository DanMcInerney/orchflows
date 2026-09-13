# Core production and playtest record

Maker: `/root/nightbind_maker`. Date: 2026-09-13. This covers workflow production steps 3–9; it is not an independent review verdict or final asset/polish acceptance.

## Frozen candidate

`core-220cfa39951c`, served at http://127.0.0.1:4191/. Source and export SHA-256 values are in `evidence/builds/core-220cfa39951c.json`. Development at :4190 runs the same source with the diagnostic module included. No source changes after this freeze are authorized by this record; a changed source requires a new build identity.

Nine rules tests pass. These test charge/capture, pause, legal recipes and both gates, all alternate combat routes, deterministic reset, diagonal/border movement, boss and loss outcomes, and a same-tick Moth healing regression. Production build passes with Vite's advisory about one 577.51 kB minified JS chunk (148.88 kB gzip, includes Three.js). Outputs: `evidence/maker/core-tests.txt`, `core-build.txt`.

After freezing, production smoke used native Space to start, an ordinary ground click to move, Space on the arena to open capture, a real Emberling capture (four hostiles to three), Pause/Space resume and Start a new run. Restart returned tick 0, title, empty squad and 120 health. No development panel was in the DOM; searching the exported bundle for the test adapter and scenario controls found no matches. Browser error/warning history contained only the earlier repaired development geometry errors, none from the production URL. All 16 source/build manifest hashes were rechecked and matched. Evidence: `core-title.jpg`, `core-production-smoke.json`. Maker browser tab was closed to free the renderer for independent play; both servers remain available.

The earlier ordinary full-run evidence belongs specifically to `core-472d991faa53`. It is retained rather than represented as a full playthrough of the new candidate. The new candidate changes wave-9 spawning from 10 to 18 per second; repairs Moth resurrection, native menu Space handling and small UI copy; adds route diagnostic fixtures; formats source and enables development file polling. The independent core reviewer must play the exact frozen candidate from start through outcome.

## Design to implementation

Before implementation, `design.md` compared weakening/throwing, lantern selection, and shrine escort. Lantern selection won because it makes immediate ally roles and future recipes compete without allied auto-fire accidentally killing a wanted recruit. The public tactical pause lists only living nearby enemies. Charge, six places and recipe consumption constrain planning. No weapon pickups, permanent upgrades or between-wave resets.

The implementation separates declarative content, deterministic 60 Hz simulation, Three.js presentation, ordinary UI/input and development diagnostics. Public and diagnostic actions dispatch to the same rules. Renderer geometry, instance matrices and effect pools are reused; simulation entities have stable IDs. Browser observations are read-only DOM text. The browser's lack of a sustained held-key action is handled by ordinary click-to-move, not an injected controller.

## Comparison 1: recruiting cadence

Prediction before implementation: an 18-second recharge makes a mistaken capture take too long to recover before the first gate; 11 seconds should permit a deliberate correction without unlimited recruiting.

Setup: seeded `wrong-recipe`, wave 4 at 78 seconds, Emberling/Mireling/Moth, charge 0.15, 85 mixed enemies. Both variants used the same route: (12,-4) for 240 ticks, (-12,-4) for 240, (0,-14) for 120. These are assisted seeded browser experiments with explicit manual ticking and public capture choices.

At +4 seconds health was 85 with 90 enemies; +8 seconds 46 health and 102 enemies. At the gate (+10), 44 health and 108 enemies remained, including 13 within six units. The 18-second lantern was only 0.706 charged. The 11-second lantern was ready. In the normal variant I opened the public lantern and captured the missing Thornback: one real hostile was removed, a ward ally entered the roster and charge returned to zero. This made the first recipe available after the gate. The slow variant could not make that correction at the same point. Thus the observed recovery is a capture at the gate, not a claim that evolution had already occurred before it.

Retained 11 seconds. Evidence: `cadence-slow.json/.jpg`, `cadence-normal.json/.jpg` under `evidence/maker/`.

## Comparison 2: first evolution relief

Prediction before implementation: a weak first evolution will leave essentially the same pressure, while the strong version opens space. Implementation compared damage scale 0.42 versus 1.0, with identical area, slow and knockback behavior (the original design shorthand 1.35/3.2 was normalized to these scales).

Setup: seeded pre-evolution, 85 mixed enemies and Emberling/Thornback. Standing for 180 ticks made 92 enemies, 29 nearby, and 102.02 health. I selected Pyre Warden in the public guide, moved to (12,-4) for 240 ticks, then (12,12) for 240.

| Observation | Weak damage | Full damage |
| --- | --- | --- |
| +4 seconds | 60 enemies, 0 nearby, 107.58 health, 55 kills | 49 enemies, 0 nearby, 109.08 health, 66 kills |
| +8 seconds | 59 enemies, 3 nearby, 105.36 health | 46 enemies, 2 nearby, 105.36 health, 86 kills |

The prediction partly failed: even weak damage produced clear local relief. The evolved area coverage and protection mattered substantially. Full damage killed more enemies and dealt with heavier targets, but poison and charge threats still made destination choice relevant. Kept full strength because the requested event is a pronounced spike; did not describe the weak variant as an observed failure.

Evidence: `evolution-before.jpg`, `evolution-weak.json/.jpg`, `evolution-strong.json/.jpg`. These exploratory comparisons preceded the final Moth same-tick healing repair.

## Ordinary run, original production build

I played from the title through a real boss victory and retry on `core-472d991faa53`, using only public clicks and menus. It used real-time simulation, with the public Pause button between short movement episodes to inspect results and account for browser-tool pacing. This is ordinary gameplay with deliberate public pause assistance, not a human reaction-time benchmark or diagnostic seed/advance run.

Captures were Emberling (~4.8 s), Thornback (~29 s), Voltwing (~40 s), Mireling (~54 s), Moth (~73 s), Fangling (~93 s), and a second Moth (~107 s). Poison led me to take Mireling for control; later I retained Voltwing as a Solar ingredient and Mireling for immediate control instead of spending both on Storm Serpent. Fangling added focused damage; the second Moth was a health recovery choice.

At 84.55 seconds, wave 4, 65 hostiles surrounded the arena and health was 43.04. At 88.067 seconds the first gate had 76 enemies and 54.32 health. Public Pyre evolution then reduced the horde to 48 after 4.6 seconds, with health 74.66 and kills advancing 169→216. I could move through the space its fire had cleared, while avoiding poison left behind.

The six-companion roster [Voltwing, Mireling, Moth, Pyre, Fangling, Moth] recovered to full health by wave 7. The old wave-9 rate reached 88 enemies but left health around 100; this was weaker second-gate tension than intended. Solar ascension at 198.067 seconds cleared 87 enemies down to 22 after 4.6 seconds and restored 120 health. That demonstrated the second spike, but the pre-spike pressure needed improvement.

Wave 12 introduced the visible Bellkeeper, its aimed volleys and large warning areas. I moved away from targeted zones and across the arena between volleys. Victory occurred at 265.683 seconds, health 107, 1,489 kills, twelve waves and two evolutions (Pyre→Solar). Public retry cleared the squad, restored health/charge and restarted wave 1.

Evidence: `ordinary-run.json`, `ordinary-pre5.json`, `ordinary-post5.jpg`, `ordinary-pre10.jpg`, `ordinary-post10.jpg`, `ordinary-win.jpg`. The first exploratory ordinary development attempt also died at wave 4 after a poor escape at low health (114 kills); no ending screenshot was retained for that attempt, so it is an observation with a narrower evidence trail.

## Late pressure correction and no-ascension control

Changed only wave-9 spawn pressure from 10 to 18 per second. The assisted late-pressure fixture begins at time 176 with the same six-companion roster used above and 60 enemies. Route: (10,8) for 360 ticks, (-10,-8) for 360, (10,8) for 360, (-10,-8) for 240.

At +6 seconds there were 128 enemies and 96.68 health; +12 had 155 and 111.96 health; +18 had 174 and 115.8 health. At the gate, 144 enemies and 108.64 health remained. Screens showed a substantially denser field and poison/charger obstacles along the route. Repeated the seeded route and obtained an identical complete snapshot.

Wave 10 itself lowers spawning, so I compared the same next six seconds of travel with and without ascending. Without Solar: 106 enemies, 3 nearby, 109.76 health. With public Solar ascension: 23 enemies, none nearby, 120 health. The transformed companion caused the major clearing beyond the gate's spawn relief. The two-Moth/ward composition still preserves health if moved well; this test supports spatial crowd pressure, not a claim of inevitable near-death desperation.

Continued the changed late arc with actual combat to victory at 265.617 seconds and 107.88 health. This is an assisted fixture continuation with Pyre already provided; its 983 kills and one recorded evolution must not be confused with the ordinary full run. Evidence: `tuned-pressure.json`, `tuned-pre10.jpg`, `tuned-no-ascension.jpg`, `tuned-ascension.jpg`, `tuned-late-arc.json`. This preceded the final Moth repair; the frozen candidate's full run remains an independent review task.

## Alternate roles and interface evidence

On source including the Moth repair, I used the public recipe buttons on seeded alternate-route fixtures and the same five-second route to (10,8). Storm Serpent killed 43, leaving 63 enemies and 72.5 health; Dusk Reaper killed 26, leaving 80 and 77 health. Dusk's targeted kills and recovery left more surrounding bodies than Storm's chains. Both still needed movement and supporting captures. This establishes distinct combat behavior, not complete alternate-route balance or full-run viability.

In separate wave-10 fixtures, Eclipse killed 90 (35 remaining, 96.5 health); Worldcoil killed 106 (19 remaining, 120 health) over five seconds. Public ascension consumed the specified three ingredients. Screens and data: `storm-role.jpg`, `dusk-role.jpg`, `alternate-routes.json`.

Public click-to-move at (800,460) yielded a world destination (8,6.3343). After 60 manual ticks, position was (5.4880,4.3453). Resetting and applying the same world destination through diagnostics yielded an identical full snapshot. Manual clock did not advance between observations. Public pause cleared target and keys. Public capture and diagnostic capture also matched the full snapshot exactly: 85→84 enemies, one Emberling ally added, charge zero. Evidence: `interface-movement.json`, `interface-capture.json`.

A stationary wrong-recipe fixture died at time 86.8 (wave 4, 52 kills). The public result screen and retry worked: a fresh empty roster, 120 health, wave 1 and full charge. Evidence: `assisted-loss.jpg`, `assisted-loss-retry.json`. This challenges stationary play with poor composition; it does not prove every strong late roster requires movement.

Caller source probes found two real defects before freeze: Moth healing could revive already killed enemies in the same tick, and global Space suppression prevented native title-button activation. Both were repaired. The Moth regression covers an ordinary creature and boss, while still asserting living targets receive healing. Browser presses confirmed Space activates Light the lantern, Space activates the pause menu's Return button, and Space on the arena opens capture. Escape/title behavior was also checked by the caller.

## Graphics and limits

Observed browser viewport: 1280×720, DPR 1. Actual backend: ANGLE (Intel, Intel(R) Graphics (0x00007D67) Direct3D11 vs_5_0 ps_5_0, D3D11). `ordinary-performance-observation.json` retains raw RAF intervals from ordinary play. Raw wall intervals are collected before simulation clamping so stalls are visible. Formal busy-scene performance profiling, memory soak and final-model budgets remain later workflow work; no device-wide frame-rate claim is made here.

The original distant camera made enemies 10–15 pixels wide. I reduced orthographic height from 23 to 18 and enlarged creature geometry 1.2×, then played at that camera. Roles became more recognizable among the horde. Blockout geometry is still small enough that Blender silhouettes and final contrast need deliberate review at the actual camera.

Remaining uncertainties for the core reviewer: first-tier routes beyond Pyre have only targeted browser trials; the strong two-Moth roster can preserve health through very dense wave 9; a full six-slot squad can make later recharge opportunities optional unless the player elects to change composition; no physical held-key session, audio quality, mobile/controller, or final Blender readability claim. These are explicit review questions, not silently accepted design quality.

Development friction: Vite initially missed atomic file updates; restart restored fresh modules and `usePolling` now prevents stale source during dev testing. Browser read-only evaluation cannot access arbitrary window state; DOM JSON observations made supported inspection reliable. Public modal opening collapses the dev panel so it cannot block menu buttons.
