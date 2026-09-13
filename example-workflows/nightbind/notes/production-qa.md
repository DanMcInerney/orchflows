# Integrated production QA

Status: **READY for the final independent production review; steps 15–18 closed.** No material integration blocker remains in the observed target conditions. The game and assets remain frozen on `release-c09f13cac8e9`; this is maker/caller production QA, not final independent acceptance. The caller operated the supported in-app browser because the maker's documented connection retry returned no available browser. The maker implemented the game, inspected saved images/state and performed source/tests; no alternate browser transport or injected gameplay mutation was used.

## Candidate and asset join

The ordinary release is `dist/` on 4191. The separately compiled assisted build is `test-dist/` on 4193, identity `qa-c09f13cac8e9`. They have common `source-c09f13cac8e9`, with only the diagnostic build flag differing. Fixture construction is in the diagnostic dependency path. Build audits found neither `__gameTest` nor `boss-danger` fixture text in release JavaScript, and both in the test build. There is no release QA URL that enables the adapter.

`evidence/builds/integration-initial-verification.json` checked all 97 fingerprinted source files and 41 release output files with zero mismatches after compilation. `public/models/manifest.json` matches the frozen asset join SHA-256 `b943f7fca7efc58f225fdf6f7add960a1bf71218943df84274434e6628e00f66`. Its 22 GLBs total 485,472 bytes. The source/Blender export validation and byte-identical source re-export are documented by the asset maker in `assets.md`.

All graybox creatures, keeper, lantern, floor and environment objects were replaced with authored GLBs. Repeated rigid parts and modular kit use shared instancing. Keeper/lantern and arch/bell attach at the exported identity-oriented sockets; the suspended bell keeps its top origin. Authored model portraits appear on the title, guide, capture choices, squad and outcome. Rigid wing/jaw/head/boss-arm motion and decorative bob follow existing simulation time and attack states. No new collider, displacement, capture/damage center, health, spawn, recipe or timing rule was introduced. Ground rings, shadows, projectiles and particles are procedural feedback, not substitute creatures or kit.

Thirteen meaningful tests passed after integration. The diagnostic extraction initially dropped the live `BASE` import needed by `candidates`; the seeded snapshot test caught it, it was restored, and the suite passed before the candidate was built. The release and test builds both compiled successfully, with only Vite's known uncompressed chunk-size advisory. This ordinary production repair happened before browser play.

## Observed presentation and controls

At 1280×720 the caller inspected title, guide, settings, ordinary game-scale models and capture planning. All 22 assets reached ready. The maker inspected `evidence/caller/integrated-title.png` and `integrated-guide.png`: keeper and lineage portraits are legible, guide recipes retain their names/ingredient mapping, and the existing capture viewport remains clear of the choice panel.

Settings mute, reduced motion and 49% volume persisted through reload. The caller then restored unmuted/normal motion. Actual gameplay observations report a running Web Audio context, emitted cues and no audio error. Audible quality has not been claimed from those readouts. The settings affect presentation/preferences only; runs still start fresh.

## Ordinary Dusk-route attempts

These are observation–action–observation runs through public start, movement, capture, guide, pause and retry. Public pauses/tool deliberation are disclosed; this does not test uninterrupted human reaction speed. No seeded fixture or manual ticking supplies the ordinary outcome.

**Attempt 1 — loss, retained.** The caller took Ember, then Thorn protection while Dusk ingredients were unavailable, then intercepted Fang at about 55.95s. That exposed the keeper and reduced vitality from about 112 to 82. A later movement destination was reached, followed by roughly seven seconds between commands; poison underfoot repeatedly dealt about five damage with Thorn's protection. The run ended at wave 4/time 69.95, 115 kills, three captures and no evolutions. This is a real setback in ordinary play, with no confirmed rule regression. `evidence/caller/dusk-run/05-danger-before-wave4.json` and `.png` record the actual loss/outcome despite the earlier working filename. The maker inspected the outcome, surviving squad portrait identities and damage history. The caller retried with more frequent movement/public pause and planned earlier recruitment/Moth recovery.

**Attempt 2 — ordinary victory.** The caller recruited all six roles by about 75s and retained Fang/Moth for Dusk while using Thorn protection, Volt chains and Mire control. At 88.067s the squad earned Dusk with 65 hostiles, nine within six units and 120 vitality. At 93.517s there were 56 hostiles, none within six units, 108.42 vitality and 463.33 recorded Dusk damage. After recruiting a replacement Moth around 94s, the 99.35s observation had 41 hostiles, none nearby, full vitality and 1,222.64 Dusk damage. The maker inspected `12-wave4-pressure.png`, `14-after-dusk-live.png` and `15-dusk-relief-live.png`, with the paired JSON state for observations 13–15. The working filename `13-before-dusk-live.png` actually shows the automatically opened guide, so it is recipe/gate evidence rather than an unobscured horde image.

This Dusk route provides gradual local relief and recovery, not an immediate arena wipe. Movement and the replacement Moth contribute, so the observation does not isolate Dusk as the sole cause. Its distinction from the earlier area-clearing and chain routes remains meaningful. The caller retained Ember/Mire for Eclipse and continued with Dusk, Ember, Thorn, Volt, Mire and Moth.

The caller deliberately kept Ember/Mire through waves 6–8, foregoing another first evolution to preserve the Eclipse recipe. Taking Volt earlier instead of waiting for a desired ingredient gave immediate coverage; taking Moth completed Dusk and helped recovery. These are observed decisions with consequences. The six-place limit also matters: a full useful squad does not need another capture every time the lantern recharges.

At 181.483s / wave 9 there were 176 hostiles, 20 nearby and 108.2 vitality. The keeper crossed from the crowded right side into western space, avoiding the existing poison trail. At 187.433s and 193.367s the arena held 240 hostiles. Health recovered to 120 with the chosen protection/healing support, so this establishes spatial crowd pressure and successful escape rather than near-death drama. The maker inspected the actual crowded [wave-nine image](../evidence/caller/dusk-run/22-wave9-escape-live.png), not just its count.

At 198.067s / wave 10, Dusk + Ember + Mire became Eclipse with 238 hostiles present. By 203.033s the population fell to 42 and vitality remained 120. The [awakening](../evidence/caller/dusk-run/25-eclipse-awakening.png) and [relief](../evidence/caller/dusk-run/26-eclipse-relief-live.png) show the transformed silhouette, opened paths and surviving ground hazards. The ordinary comparison includes the wave's scheduled spawn change; the earlier controlled core no-ascension comparison isolates that confound separately. It is not being relabeled as a production experiment.

Both evolved states still required movement: remaining stationary after Dusk reduced vitality 120 → 98.74 despite a healer, and a center hold after Eclipse reduced it to 95.02. Moving off poison recovered health. Wave 11 retained 40–62 foes in samples on this route. The caller filled freed slots with Fang for focused damage and another Moth for recovery.

The Bellkeeper arrived at 242s. Its large model, aimed projectile fan and distinct warning/impact circles were visible while the keeper actively changed ground. Boss HP fell 3,902 → 2,421 → 987 in observations at 242.933, 246.45 and 249.967s. [Boss combat](../evidence/caller/dusk-run/30-boss-volley-live.png) and [outcome](../evidence/caller/dusk-run/32-outcome.png) were inspected. Victory arrived at **252.833s: 12 waves, 1,453 kills, 113.38 vitality, nine captures and exactly two evolutions, Dusk then Eclipse**. Public retry returned to fresh wave 1, 120 vitality, empty squad, full charge and no movement intent. No ordinary-release browser warnings/errors were returned.

The full decisions, preserved first loss, nearby snapshots and pacing limitations are in [caller-production-play.md](caller-production-play.md). Images are taken just before the paired public pause/snapshot, so nearby image/JSON observations are not atomic. The failed glyph-based locator associated with `07-wave3-live.png` is retained as an operator failure, not successful capture evidence or a confirmed game bug.

## Assisted production branch and boundary checks

These checks used **qa-c09f13cac8e9 on 4193**, seed 12345, the visible scenario panel and **manual** clock. Fixture setup was assisted; evolution/release/capture/settings actions used the normal public UI. They validate integrated presentation and action rules, not earned ordinary progression or real-time performance. The maker inspected every PNG listed below and read the state snapshots.

| Check | Observed result and evidence |
| --- | --- |
| Pyre, default pre-evolution | Public awakening, then 90 ticks: actual Pyre model, gold response and area combat; tick 90, time 89.5, 64 hostiles, 28 kills. [01](../evidence/caller/production-scenarios/01-pyre.png) and matching JSON. |
| Solar, default second-evolution | Public ascension, then 90 ticks: distinct open halo/wing form and wide clearing; tick 90, time 199.5, nine hostiles, 88 kills. [02](../evidence/caller/production-scenarios/02-solar.png). |
| Storm, storm-route pre-evolution | Public awakening, then 90 ticks: angular serpent form and chain combat; tick 90, time 89.5, 76 hostiles, 16 kills. [03](../evidence/caller/production-scenarios/03-storm.png). |
| Worldcoil, storm-route second-evolution | Public ascension, then 90 ticks: ring silhouette and broad chain effect; tick 90, time 199.5, 37 hostiles, 60 kills. [04](../evidence/caller/production-scenarios/04-worldcoil.png). |
| Full six-place roster | `late-pressure` opens the real capture panel at tick 0 with 60 hostiles; choices disabled and release instruction visible. Full reach and keeper remain visible. [05](../evidence/caller/production-scenarios/05-full-circle.png). |
| Release and actual capture | Release Fang through Field guide, then bind a reachable Ember without stepping: six → five → six allies; 60 → 59 hostiles; charge 1 → 0; tick remains 0, kills remain 0. This separates capture removal from auto-fire. [06](../evidence/caller/production-scenarios/06-release-and-real-capture.json), matching PNG. |
| Reduced motion | Enable through Settings, close it and step 60: combat/warnings persist, nine kills, time 177, charge 0.091. [07](../evidence/caller/production-scenarios/07-reduced-motion-combat.png). Decorative motion is optional; essential feedback remains. |
| Paused manual parity | While Settings is open, a further Step 60 leaves tick 60/time 177 unchanged; restoring normal motion leaves the same state. [08](../evidence/caller/production-scenarios/08-restored-settings.json). |

Dusk/Eclipse, all six bases and boss presentation were covered in the ordinary release run. Missing-recipe/cooldown rules and alternate seeded invariants remain covered by unchanged meaningful tests and identified core experiments, rather than being claimed as new ordinary production runs. Native Space/Enter and left/center/right capture-camera parity were observed before integration in [caller-step14.md](caller-step14.md); the integrated run exercised the public Space/click route again. Deliberate focus-loss recovery was not re-exercised in this production candidate.

## Loading, failure, preferences and repeated sessions

A separately copied release at port 4194 intentionally omitted `keeper.glb`. The loader rejected the HTML fallback as invalid binary glTF, blocked start and presented a specific error plus **Try loading again**. [Failure image](../evidence/caller/integrated-load-failure.png). Restoring only that copy's exact keeper export and using the public retry reached the real title with all 22 models ready. [Recovery state](../evidence/caller/integrated-load-recovery.json), [recovery image](../evidence/caller/integrated-load-recovery.png). Ordinary `dist` and all source assets were unchanged. The fault entry is expected; it was the only error carried into the later tab log.

A first visit to previously unused local origin 4195 loaded the same frozen ordinary release, reached the title with 22 models and accepted public start → Pause into a fresh run. [Fresh-origin observation](../evidence/caller/fresh-origin-load.json). This adds a fresh application/origin boundary in an existing browser; it is not a clean browser-profile, cold GPU or network benchmark. Both temporary ports were closed after observation.

Three additional public Pause → Start a new run → Light the lantern → Pause cycles returned fresh health, empty squad and no stale keys/destination. Renderer resources stayed **58 geometries / one texture**, assets stayed 22 and audio voices settled to zero. [Repeated retries](../evidence/caller/dusk-run/repeated-retries.json). This is a bounded stable-resource observation, not comprehensive heap analysis. Only preferences persist; reload verified mute, reduced motion and 49% volume, then normal settings were restored.

## Performance and evidence integrity

[performance.md](performance.md) records target-relative results, actual adapter, raw active-frame selection, independent recalculation and limits. The ordinary winning run reached 240 hostiles and 74,736 triangles with at most 45 draw calls. At least 150 hostiles occupied 1,160 measured frames / 19.334 active seconds, with median 16.7ms, p95 16.9ms, maximum 18.9ms and no sample above 50ms. No measured budget failure justified a performance rewrite.

Two oversized browser exports were truncated at 200,000 characters. They are preserved as `.truncated.txt`, never used as complete evidence. Valid compact full-run summary, metadata and a separate 1,321-frame wave-nine raw slice are linked in the performance report. A local recalculation independently reproduces that slice's percentiles/counters.

The final [integrity verification](../evidence/builds/production-final-verification.json) rechecks both build manifests against all fingerprinted source and built files, diagnostics separation, the fixed asset manifest and archived approved core. The [production candidate manifest](../evidence/builds/production-candidate.json) links exact runtime identities and hashes the final maker handoff documents. No source edits, no rebuild and no new mechanics tuning occurred during the successful integrated browser runs or closeout. The 13 tests and initial successful builds apply to this unchanged source.

## Remaining limits and handoff

- The target actually observed is desktop 1280×720, DPR 1, Intel/Direct3D11. Narrow/1920×1080 resize, other browsers/devices, physical held-key sequences, touch and controller are unverified; they are not silently marked passed.
- Audible sound quality, deliberate graphics-context loss and deliberate focus-loss recovery are unverified. Web Audio initialization/cue emission/preferences and public pause/retry were observed. Asset failure was genuinely exercised.
- Initial load numbers describe local asset/portrait readiness before first shader compilation, with the browser already active. No cache-cleared profile, network-throttled load, first-GPU-frame or heap-leak claim is made.
- Ordinary Solar and independently played Worldcoil victories belong to earlier identified core builds. The final presentation of their models was checked with assisted scenarios here; only Dusk/Eclipse has an ordinary complete run on this integrated release. Strong auto-fire can make desired replacement interception timing-sensitive, and the core Worldcoil route's quiet wave 11 remains a nonblocking pacing observation. Those findings were preserved rather than prompting arbitrary new systems or rule changes.
- Public pauses/tool pacing supported adaptive ordinary play. The first loss is retained. This is not a claim of unassisted continuous human reaction-speed or universal fun; the next fresh final reviewer should challenge clarity, depth and pace on the exact production candidate.

The existing maker and asset maker remain available for any concrete repair through the caller. Keep `dist`/4191 and `test-dist`/4193 fixed during final review; the caller owns that independent checkpoint.
