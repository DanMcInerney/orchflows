# Caller production play and browser QA

Candidate: `release-c09f13cac8e9`, ordinary compiled preview on port 4191. The original game maker froze `dist` throughout these checks and independently verified its hashes. Caller operated the supported in-app browser because the maker's continued browser connection returned no browsers. These are informed production checks, not the final independent review.

Conditions: 1280×720, DPR 1, ANGLE Intel Graphics / Direct3D11. Click-to-move, named public buttons and Space used the ordinary game. Tactical capture pause and frequent public Pause allowed deliberation; simulation remained live between them. No fixture, manual stepping, test hook, state injection or direct game-state mutation was used. This does not establish uninterrupted human reaction-speed play. Screenshots precede their paired paused snapshots by a fraction of a second; pairs are nearby observations, not atomic captures.

## Presentation and settings

The integrated title, Field guide, all six base forms, Dusk, Eclipse, keeper, attached lantern, environment and Bellkeeper were actually inspected at gameplay scale. The portraits match the arena forms; differentiated silhouettes remain visible in the 240-enemy scene. Capture uses the centered Lantern view with the full reach circle and a highlighted actual target. The full guide scrolls at 720px height. No missing-model fallback was seen; all 22 models reported ready.

Mute, reduced motion and volume changed through public controls. Reload retained mute, reduced motion and the adjusted 49% volume. Ordinary motion and unmuted sound were restored for the run. At victory the AudioContext reported running, 1,219 cues played, no error and four active voices; it settled to zero voices during later paused retries. Audible sound quality was not heard or judged. Settings persistence was checked through visible controls and the DOM observation, not private browser storage.

Evidence: `evidence/caller/integrated-title.png`, `integrated-guide.png`, and the actual play captures below.

## First attempt: preserved loss

The first attempt took Ember at 7.633s, Thorn at 31.633s and Fang at 55.95s. It held a ready charge while waiting for a desired role, then crossed toward a Fangling. Vitality fell from 112.46 to 82.3 during that interception. Subsequent click destinations were reached well before the next command, leaving the keeper standing in poison. Repeated roughly five-point damage events every 0.6s ended the run at wave 4 / 69.95s, 115 kills and no evolution.

The ground warning was visible. This was a consequential setback from movement cadence and composition, not a confirmed presentation or input regression. The outcome explained the loss and offered retry. Retry produced a fresh playing state. Evidence: `evidence/caller/dusk-run/01` through `06` captures and snapshots; `attempt1-performance.json` retains this attempt's valid shorter frame history.

## Second attempt: Dusk → Eclipse → victory

The retry changed both tactics: take a useful third role rather than hoard a charge, and pause after bounded ground routes instead of leaving the keeper stationary during deliberation. Most routes lasted 3–7 live seconds. Public decisions remained adaptive to observed ground warnings, crowd locations, health and reachable capture choices.

| Episode | Observed decision and consequence |
| --- | --- |
| Opening | Ember, Thorn and then Volt at about 40.567s gave splash, protection and chain damage. The earlier Volt was a deliberate immediate-survival choice while Fang/Moth were not both available. |
| Ingredients | Fang at 51.95s and Mire at about 63.5s, then Moth at 75.017s filled all six slots with distinct roles. At the Moth choice: 42 hostiles, 94.74 vitality. Mire was retained for Eclipse; Moth completed Dusk and restored health. |
| First gate | At 88.067s / wave 5: 65 hostiles, nine nearby, 120 vitality, all three first recipes available. The public guide opened and the caller chose Dusk. Fang + Moth were consumed, one Dusk appeared, and one slot became available. |
| Dusk relief | After 5.45s: 56 hostiles, zero nearby, 108.42 vitality. After a replacement Moth and 11.28s total: 41 hostiles, zero nearby, 120 vitality. Relief was gradual on this lineage, not an instant wipe. The later sample also includes the replacement healer and changed position. |
| Stationary challenge | Holding the same western position from 99.35 to 107.75s reduced vitality 120 → 98.74 despite Dusk and one Moth. Poison remained under the keeper while the hostile count declined 41 → 29. Moving to fresh ground restored 120 vitality by 113.717s. The evolution did not make standing still safe. |
| Keep the plan | Through waves 6–8 the caller retained Ember/Mire instead of consuming them in another first evolution. Dusk, Thorn, Volt and Moth supported moving survival. The six-place cap meant further capture required a release or evolution; no claim that every cooldown offered a necessary new choice. |
| Second pressure peak | Wave 8 ended near 104 hostiles and eight nearby. Wave 9 reached 176 hostiles / 20 nearby / 108.2 vitality at 181.483s. The right side was crowded, so the caller crossed to open western space rather than retrace the dense poison trail. At 187.433s the game reached 240 hostiles, ten nearby and 120 vitality; at 193.367s it still had 240. The disciplined route kept health high: this is spatial pressure and observed escape, not a claim of near-death play. |
| Second gate | At 198.067s / wave 10: 238 hostiles, 120 vitality, Dusk + Ember + Mire still held. The public Ascend action consumed those exact ingredients and produced Eclipse, reducing six companions to four. |
| Eclipse relief | By 203.033s, hostiles fell 238 → 42 in 4.967s with vitality at 120. The preceding wave-nine captures show the actual horde, and the subsequent image shows opened space. This ordinary comparison includes the scheduled wave change; prior controlled core experiments isolate the rule effect separately. |
| Prepare for boss | The caller used freed places for Fang's focused damage and a second Moth's recovery. A center hold after Eclipse still reduced vitality to 95.02 by 214.7s, prompting another move. Wave 11 retained 40–62 enemies in observed samples; this lineage did not produce the nearly empty Worldcoil wave noted in core review. |
| Boss | Bellkeeper appeared at 242s. At 242.933s: 3,902 boss HP, keeper 120. The caller crossed its aimed fan and left the gold warning circles, keeping the boss within companion range. Boss HP was 2,421 at 246.45s, then 987 at 249.967s. The distinct large boss form, volleys and warning/impact circles were observed. |
| Outcome and retry | Victory at 252.833s: 1,453 kills, 113.38 vitality, nine real captures and exactly two evolutions (Dusk at wave 5, Eclipse at wave 10). The boss lasted about 10.8s on this focused composition. Public retry returned to wave 1 / 120 vitality / empty squad / full charge / no input intent. No browser warnings/errors were returned for the ordinary release. |

Evidence is under `evidence/caller/dusk-run/08` through `33`. `07-wave3-live.png` is not successful wave-three evidence: an exact locator using the accessibility tree's normalized lightning glyph did not match the DOM name, so no capture or movement occurred. A name substring locator then recruited Volt correctly. The file remains as a failed operator attempt, not a game failure or a passing capture. All three composition families now have ordinary full-run coverage across production and earlier core work; only this run establishes the finished Dusk/Eclipse presentation.

## Measured release rendering

Read-only DOM frame history tagged each active frame by run, simulation time, wave, live hostiles, raw frame interval, renderer calls and triangles. The caller summarized run 2 in read-only evaluation and exported wave-nine raw rows separately to stay under the browser tool's return limit.

| Actual workload | Samples / active time | Median / p95 / p99 / max | Other observations |
| --- | --- | --- | --- |
| Entire winning run | 15,187 / 253.117s raw frame sum | 16.7 / 16.8 / 17.1 / 18.9ms | Max 240 hostiles, 45 calls, 74,736 triangles. |
| At least 150 hostiles | 1,160 / 19.334s | 16.7 / 16.9 / 17.4 / 18.9ms | Max 240 hostiles, 40 calls, 74,736 triangles. |
| Wave 9 | 1,321 / 22.017s | 16.7 / 16.9 / 17.4 / 18.9ms | Raw per-frame rows retained; matching live captures 21–23. |

No sampled active interval exceeded 50ms. These are segmented real-time gameplay samples with public pauses between routes, not a continuous stress test, a GPU-time measurement or a claim about other machines. Initial observed load-to-ready was 91ms after a warm local reload. A later first visit to unused local origin 4195, serving the unchanged release, reported 90.4ms for asset/view initialization and 151.2ms navigation-relative readiness, then passed public start → Pause with all 22 assets. `evidence/caller/fresh-origin-load.json` records it. The existing browser process/profile and machine caches were retained; neither check establishes clean-profile, remote-network or reboot-cold loading.

Valid files: `attempt2-performance-summary.json`, `attempt2-wave9-frames.json`, `performance-metadata-after-retry.json`. Two earlier attempts to export the entire JSON string hit the tool's 200,000-character limit and are intentionally retained as `attempt2-performance.truncated.txt` and `after-win-retry-performance.truncated.txt`. Do not parse or use them as complete performance evidence. Metadata was subsequently read after the clean retry; its current resource counters belong to run 3 while the retained frame samples identify run 2.

Three additional public Pause → Start a new run → Light the lantern → Pause cycles returned fresh state. Geometry/texture counts stayed 58/1; loaded models stayed 22; audio voices settled to zero. `repeated-retries.json` records these observations. This bounded check shows stable renderer resources, not a comprehensive heap-leak proof.

## Fault recovery and assisted branch QA

An isolated fault copy on port 4194 omitted keeper.glb. Its actual error view correctly prevented start and offered “Try loading again,” naming invalid model content instead of silently showing a placeholder. The maker restored only that copy's keeper file, with the expected hash. The public retry then reached the title with all 22 assets ready. `evidence/caller/integrated-load-{failure,recovery}.{png,json}` records the before/after. The release on 4191 remained unchanged.

The caller then used the separately compiled `qa-c09f13cac8e9` on port 4193, seed 12345, with its visible development controls. Clock was explicitly manual. Four injected scenarios used the public Field guide and evolution buttons, then advanced exactly 90 ticks through the real rules:

| Scenario / variant / public evolution | State after 90 ticks | Actual rendered inspection |
| --- | --- | --- |
| pre-evolution / default / Pyre | 89.5s, 64 hostiles, Pyre only | Blocky armored form, warm area pulse and ward, correct portrait and awakening cue. |
| second-evolution / default / Solar | 199.5s, nine hostiles, Solar only | Open radial silhouette, bright ring attack, correct portrait and ascension cue. |
| pre-evolution / storm-route / Storm | 89.5s, 76 hostiles, Storm only | Bent segmented silhouette, lightning effect and cool pulse, correct portrait. |
| second-evolution / storm-route / Worldcoil | 199.5s, 37 hostiles, Worldcoil only | Open coil remained readable beside the keeper; chain attack, cool ring and correct portrait. |

All four had 120 vitality and registered damage by their evolved form. These establish integrated branches and visible rule consequences at injected states, not ordinary reachability or frame-rate performance. Evidence: `evidence/caller/production-scenarios/01`–`04` images and snapshots.

In `late-pressure/default`, the public capture panel explicitly explained the full six-place circle and disabled every capture card. With tick still zero, releasing Fang in the Field guide freed one slot. Returning to the lantern and binding a real Ember changed 60 hostiles to 59, squad five to six and charge one to zero, with one capture recorded and no combat step to confound the count. Evidence `05-full-circle` and `06-release-and-real-capture`.

Reduced motion was enabled publicly in the same fixture. After 60 manual ticks, combat advanced to 177s, attacks registered and visible threat/attack cues remained. Restoring normal motion in the Settings pause and requesting another 60 ticks left the game at tick 60 / 177s; the public pause was respected. Settings were returned to normal, unmuted, at that test origin's default 40% volume. Evidence `07-reduced-motion-combat` and `08-restored-settings.json`.

The diagnostic summary appears as a button in native accessibility, but did not match Playwright's exact button-role locator. Exact `getByLabel('Clock')` likewise did not match its implicit label. The inspected `.diag summary` and documented control IDs operated the visible UI successfully. These locator mismatches are operator/tool-route observations; neither caused a game-state change. Browser logs after this sequence contained only the earlier intentional fault-copy error, identified by its 4194 URL; no 4193 error was returned. The caller left the gameplay tab on the static art-study page after checks.

Resize/other physical devices, deliberate blur, graphics context loss, cache-cold loading and audible quality remain unverified. The complete ordinary run and targeted checks found no material defect requiring a production repair. A new independent final playtester still owns acceptance; this caller report is maker-side evidence.
