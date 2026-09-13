# Nightbind independent core review

**READY for core-to-production development.** The frozen core supports an intelligible capture/composition loop, an ordinary twelve-wave victory and defeat/retry, distinct companion effects, two earned clearing spikes, and a late horde that punished stationary play even with a strong composition. No material core blocker was found. This is not final art/audio acceptance or proof of every composition's full-run balance.

Reviewer: `/root/nightbind_core_review`, a fresh non-maker reviewer, 2026-09-13. No repairs, rebuilds, injected production state or child agents. Only this report and `evidence/core-review/` were written. Review tab was closed; both existing servers were left running.

## Exact candidate and conditions

- Production: `core-220cfa39951c`, http://127.0.0.1:4191/, local `dist/`. The visible build stamp and DOM snapshots identify the candidate. All 13 source and 3 built-file hashes matched [the frozen manifest](../evidence/builds/core-220cfa39951c.json) before and after review: [initial checks](../evidence/core-review/identity-check.json), [final checks](../evidence/core-review/final-identity-check.json).
- Browser: Codex in-app browser, own fresh tab 1; supported browser runtime only. Viewport 1280×720, DPR 1, default quality, no viewport override or throttling. Actual backend: `ANGLE (Intel, Intel(R) Graphics (0x00007D67) Direct3D11 vs_5_0 ps_5_0, D3D11)`.
- Ordinary play used public clicks, click-to-move, Space, Pause, guide and outcome controls. Public pause/menu deliberation was frequent; active movement episodes usually lasted 2.8–7 seconds. This is ordinary input and natural progression with deliberation assistance, not a human reaction-time benchmark. Explicit stationary challenges used 7–10 second observed intervals. No seed/scenario/step control was used on production.
- Diagnostics: http://127.0.0.1:4190/, displayed build `development`, seed 12345, manual clock, legal documented fixtures and DOM controls. The current source matches the frozen manifest; the caller's existing Vite development server serves that same source with diagnostics enabled. These observations establish same-source rule behavior, not production performance or ordinary reachability.
- Production displayed no diagnostic panel. The exported bundle had no diagnostic adapter/panel strings ([isolation probe](../evidence/core-review/production-isolation.json)). Production and development console warning/error queries both returned empty arrays.

## First-play boundary and initial understanding

I read only the public title and game instructions before the first action attempt. I then recorded the following before opening request, acceptance, README, design or maker playtest notes. Those private notes were read **after onboarding and the first recruit/reposition attempt, before the first outcome**. Therefore only this onboarding is uncoached; subsequent full play is informed. The caller later clarified a first-outcome boundary for future reviews. I did not restart to manufacture an uncoached label.

The title clearly communicated twelve waves, automatic companion combat, a nearby recruit every 11 seconds, six places, and recipes at waves 5/10. I understood click movement and survival. I did not yet know there was a starter attack with an empty circle, the numerical capture reach, or exact recipes without opening the public guide.

| Observation | Intent and ordinary input | Consequence |
| --- | --- | --- |
| Start showed a centered keeper, empty circle, 120 vitality and an orange foe at the right edge. | Clicked Light the lantern, then ground at (850,365) to approach that foe; pressed Space. | Time stopped in a binding modal offering Emberling, with five in reach. Nine hostiles and three kills had accrued during tool-decision time. |
| One available species was described as splash damage. | Chose Emberling; clicked (790,300) to reposition. | The allied shape appeared beside the keeper, the circle became 1/6, and an 11-second charge began. Destination and attack rings were visible. Health remained 120. |
| Simulation continued while I considered feedback. | Used public Pause before recording. | Paused at wave 2 with 120 vitality, 14 hostiles and 30 kills. [Initial paused capture](../evidence/core-review/01-first-play-paused.jpg). |

The recruit feedback and primary action were readily understandable. Initially I could not distinguish every ring's purpose; subsequent poison trails, ally rings and boss volleys were more informative in movement than a single still.

## Complete ordinary run and decisions

The same run continued from the first attempt to a natural boss victory at **265.05 simulation seconds**, 1,662 kills, 108.26 vitality (HUD rounded to 109), eight successful captures and three transformations: Storm Serpent at the first gate, an additional Pyre Warden for recovery, then Worldcoil at the second gate. The public win screen and retry worked. [Outcome image](../evidence/core-review/38-outcome.jpg), [complete final observable state](../evidence/core-review/38-outcome.json), [retry](../evidence/core-review/39-retry.json).

| Episode | Decision and consequence | Evidence |
| --- | --- | --- |
| Waves 2–4: composition and setback | Took Thornback for protection and a first recipe, Voltwing for spread damage, then Fangling when Mireling was not offered. Health later fell from 112 to 78 while poison/nearby foes occupied my destination. Took Mireling for control and changed from retracing routes to fresh ground; then took Moth for recovery. | [Wave 3](../evidence/core-review/05-wave3-fang.jpg), [setback and poison trail](../evidence/core-review/06-setback.jpg), [six roles before gate](../evidence/core-review/08-pre5.jpg). |
| First earned spike | All six base roles had been captured. At 88.017 s: 80.98 health, 59 hostiles, six nearby, 184 kills. Chose Storm instead of spending Fang/Moth on Dusk, retaining Thorn/Fang for Worldcoil. By 102.467 s: seven hostiles, none nearby, 296 kills. Space opened dramatically. Health was only 62.84 because I delayed repositioning after the evolution; the immediate +25 heal did not make lingering in poison safe. This interval is 14.45 s, not a four-second controlled experiment. | [Gate state](../evidence/core-review/09-gate5.json), [cleared field](../evidence/core-review/10-post-storm.jpg), [post-state](../evidence/core-review/10-post-storm.json). |
| Recovery and a changed plan | At about 63 health I recruited a second Moth, then spent Ember/Thorn on Pyre for immediate protection and its 25-health reward, knowingly breaking my Worldcoil recipe. Moths sometimes had no target in their attack range while Storm killed distant recruits. Several searches returned no reachable targets. I shortened movement to intercept an approaching Thornback and restored the recipe. Health recovered to 116.74 by 145.983 s. | [Pyre recovery](../evidence/core-review/16-pyre-recovery.jpg), [restored recipe/state](../evidence/core-review/19-recipe-recovered.json). |
| Strong-composition dominant-strategy challenge | Roster: Fang, two Moths, Storm, Pyre, Thorn. I moved to the center and deliberately stopped moving or recruiting. It stayed at full health through wave 8. Wave 9's ranged pressure then reduced health to 105.18 at 188.483 s and 69.54 at 195.583 s; 113 enemies surrounded the field. This disproved indefinite stationary safety for that composition over the late pressure interval. The nearby-under-six count remained zero: the damage pressure was primarily ranged/zone pressure, not physical body contact. | [Early stationary safety](../evidence/core-review/21-stationary-wave8.jpg), [dense wave 9](../evidence/core-review/24-wave9-stationary.jpg), [late setback](../evidence/core-review/25-wave9-stationary.jpg), matching JSON files. |
| Second earned spike | I abandoned the center for the right side. The natural gate opened at 198.033 s with 119 hostiles and 84.54 health. Public Worldcoil ascension consumed Storm/Thorn/Fang. After 4.117 s of travel, 13 hostiles remained, kills rose 1,012→1,151 and health was 101.88. A visibly large clearing caused real relief. The wave's spawn reduction also contributes; this ordinary episode alone does not isolate its share. | [Gate state](../evidence/core-review/26-gate10.json), [Worldcoil clearing](../evidence/core-review/27-worldcoil-spike.jpg), [post-state](../evidence/core-review/27-worldcoil-spike.json). |
| Final stretch and boss | Four companions remained: two Moths, Pyre and Worldcoil. I hoarded the ready charge. Center standing after ascension left wave 11 nearly empty; health recovered. The boss was visually distinct with a health bar, pink fan volleys and large targeted warning circles. I moved laterally, then used the open lower route and escaped warning circles. Some hits still landed, but the boss fell naturally. | [Quiet wave 11](../evidence/core-review/29-wave11-idle.jpg), [boss and volley](../evidence/core-review/33-boss-warning.jpg), [targeted area](../evidence/core-review/36-boss-late.jpg), [win](../evidence/core-review/38-outcome.jpg). |

Capture/composition choices were meaningful after the first six slots filled because evolution consumed future ingredients and opened a slot; protection now versus retaining Worldcoil ingredients was a concrete tradeoff. Replacing the missing Thornback required a changed interception tactic. This does **not** mean every later charge mattered: I made no further captures after that recovery and left two slots empty after Worldcoil. The continuing value of late recruitment is weaker than the early planning loop.

## Failed alternate route and retry

After winning, Light another lantern reset to wave 1, an empty roster, full charge and 120 health. I deliberately tried starter-attack/no-capture play, including rightward travel, a long escape toward the left after dropping to 48 health, and then stationary defense. The escape stopped health loss briefly; standing failed at **27.317 s**, wave 2, 12 kills, zero captures/evolutions. This is evidence that ignoring captures and standing is not viable in this attempt, not proof that expert continuous kiting without captures cannot succeed. [Route](../evidence/core-review/40-no-capture-route.jpg), [loss](../evidence/core-review/43-loss.jpg), [loss state](../evidence/core-review/43-loss.json).

The loss message explained the result and suggested an actionable protective recipe. A second public retry again cleared squad, enemies, outcome, damage/capture history and movement. A Right press/release followed by Pause left keys zero and target null; its movement displacement was not measurable at this short press duration. [Loss retry](../evidence/core-review/44-loss-retry.json).

## Targeted same-source diagnostics and source review

All fixture evidence below is **assisted/scenario only**. I used the page's documented DOM controls; no evaluate mutation, hidden shortcut or external browser driver.

- Manual mode remained at tick 60 between decisions. Sixty steps advanced exactly one simulated second. Public ground click at (800,460) produced target (8,6.33430791721743). Repeating from the same fresh seed with the diagnostic Move control produced an identical inspectable snapshot at tick 60, player (5.487995392795924,4.345331583280003). [Parity](../evidence/core-review/45-interface-parity.json).
- Public Emberling capture and the diagnostic capture action, with the same input-release condition, produced identical snapshots: two hostiles→one, one Emberling ally, charge zero. [Capture parity](../evidence/core-review/46-capture-parity.json).
- Public pause cleared movement; attempting 60 manual ticks while paused left the snapshot unchanged, including charge. [Pause/step](../evidence/core-review/47-pause-step.json).
- A full six-slot `late-pressure` fixture visibly disabled all capture choices and directed the player to release a companion in the guide. Releasing Fangling then capturing a real Emberling changed only that squad place, 60→59 hostiles and charge 1→0. [Full roster UI](../evidence/core-review/51-full-circle.jpg), [replacement](../evidence/core-review/52-full-circle-swap.json).
- The `wrong-recipe` fixture showed incomplete ingredients and disabled pre-wave-5 buttons. Missing pairs and future ascensions were also disabled in all route comparisons. [Wrong-recipe DOM](../evidence/core-review/53-wrong-recipe-dom.txt).
- Three same-seed `pre-evolution` fixtures used the public awakening buttons, then identical diagnostic travel toward (10,8) for 300 ticks. The simple fixture supplies only the recipe pair; it is substantially weaker than a naturally built full squad.

| Single evolved companion, 5 s fixture | Hostiles remaining / kills | Nearby under 6 / health | Interpretation |
| --- | --- | --- | --- |
| Dusk Reaper | 80 / 26 | 26 / 77 | Focused damage and healing; crowd remains close. [Image](../evidence/core-review/48-dusk-route.jpg), [state](../evidence/core-review/48-dusk-route.json). |
| Storm Serpent | 63 / 43 | 1 / 72.5 | Chains/slow open local space, but poison still damages this unwarded setup. [Image](../evidence/core-review/49-storm-route.jpg), [state](../evidence/core-review/49-storm-route.json). |
| Pyre Warden | 58 / 48 | 0 / 87.86 | Protective area clearing preserves more health on this route. [Image](../evidence/core-review/50-pyre-route.jpg), [state](../evidence/core-review/50-pyre-route.json). |

These effects and the ordinary mixed Storm/Pyre run support credible distinct strengths. They do not establish three equally viable independent full-run compositions. Source rules corroborate why: Pyre provides ward and clustered area damage, Storm covers ten targets at longer range with slowing, and Dusk prioritizes maximum-health targets with stronger focused damage and recovery.

The nine existing Node tests independently passed: [test output](../evidence/core-review/node-tests.txt). They cover actual capture charge/hostile removal, pause/release, recipe ingredients and gates, alternate combat/evolution behavior, seeded reset, diagonal/border movement, boss/loss/reset, and same-tick Moth healing. Tests are isolated through fresh game state. Source ownership is coherent: declarative content, simulation/action dispatcher, presentation, UI and development adapter. The adapter calls the same `act`/`update`; `main.js` has one Three.js animation loop using fixed 60 Hz simulation steps. Source uses explicit collision geometry rather than model mesh intersections. Its frame catch-up limit discards excess elapsed time during long stalls; I found no such stall in the retained ordinary frame interval sample.

## Render/performance evidence and limits

I inspected the actual canvas in successive captures as well as UI. Creature positions, projectiles, attack rings and companion effects changed with simulation, so HUD motion was not used as a substitute for a working scene. Graybox roles were recognizable by color/shape at ordinary density; the Dusk fixture's crowded keeper area was harder to parse. Final Blender silhouettes and final combat-effect hierarchy remain production work.

[Production interval sample](../evidence/core-review/production-performance.json): last 12,000 active real-time frame callbacks retained at the end of the run, median 16.7 ms, p95 16.8 ms, p99 17.1 ms, maximum 18.9 ms. It includes movement, dense late play and sparse evolved play, excluding explicit pauses. This is descriptive scheduling evidence from this Intel/D3D11 backend, not a separately warmed, controlled busy-scene benchmark or proof of displayed FPS on other devices. The final sparse sample reported 87 draw calls, 6,152 triangles, 94 geometries and one texture; these are **not** peak busy-scene counters. Formal busy-load profiling and final-asset budgets remain unverified.

## Findings, coverage and decision

No high-impact correctness, usability or core-strategy failure was established, so no repair finding is raised. Two retained nonblocking observations deserve attention during production tuning:

- **CORE-O1 — weak decisions after ascension.** In the natural Worldcoil/Pyre/two-Moth run, the center was nearly empty through wave 11, health recovered, and neither movement nor filling the two freed slots was necessary before the boss. Reproduce by the recorded roster/ascension and center standing; [wave-11 evidence](../evidence/core-review/29-wave11-idle.json) and source Worldcoil range 22 / thirty targets explain the result. This supports the intended power payoff, but also creates a quiet stretch. Treat a renewed movement demand or shorter relief interval as a tuning experiment, not an assumed defect in an intentionally strong reward.
- **CORE-O2 — wanted recruits die before selection.** After Storm, several ordinary lantern openings had no targets even while distant creatures were visible; a needed Thornback required opening after a roughly 0.4-second interception. Storm's range 17 exceeds the lantern's range 13. The successful interception is contrary evidence to impossibility. This can express capture timing skill, but the public UI gives little advance sense of reach. A visible reach cue during planning would make the constraint easier to learn; final effects should preserve the recruit's visibility.

| Coverage | Status |
| --- | --- |
| Public start/learning | Observed pass; uncoached onboarding only, exact boundary disclosed. |
| Ordinary capture, charging, six-slot composition | Observed pass; full-slot release/replacement also scenario-tested. |
| Twelve continuous waves, first/second gates, boss victory | Observed pass on exact frozen production candidate. |
| Setback, adaptive recovery and dominant-strategy attempt | Observed: poison-route change, ingredient sacrifice/recapture, stationary late-pressure challenge. |
| Alternate approach, defeat and both retries | Observed pass; no-capture/stationary route lost. |
| Distinct routes | Three first-tier fixtures observed; mixed Storm/Pyre→Worldcoil ordinary victory. Pure Dusk/Solar/Eclipse full-run viability not exercised independently. |
| Recipe failures/cooldown/parity/reset | Observed UI and scenario checks plus nine passing rule tests. |
| Sustained mouse movement / fixed camera | Observed through public click-to-move across the arena. No free-camera controls apply. |
| Sustained keyboard hold, real blur while holding, long lifecycle soak | Not exercised; supported runtime lacks a held-key operation. Short press/release and pause/retry verified; source blur cleanup inspected only. |
| Production diagnostics isolation | Observed absent UI and no exported mutation-adapter strings; normal observable DOM retained. |
| Final Blender assets/audio/mobile/controller | Outside this core checkpoint; no quality claim. Audio was not listened to. |
| Formal target performance | Unverified; limited ordinary production interval evidence reported above. |

The mechanics are worth developing into final production. The combination choices created an understandable recovery plan, both intended gates produced real clearing, and wave nine retained consequential pressure against a prepared build. Preserve those observed decisions while improving final readability and checking the quieter ascended stretch.
