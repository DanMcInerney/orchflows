# Joined production QA plan

This plan is written before the step-13 asset join. It lists checks to perform, not passing results. The current approved rules and core review remain in `core-baseline.md` and `core-review.md`; step-14 presentation work is described in `production-step14.md`.

Execution is now closed in [production-qa.md](production-qa.md) and [performance.md](performance.md), using ordinary `release-c09f13cac8e9` and separate assisted `qa-c09f13cac8e9`. Preserve this as the prospective plan; the report explicitly identifies unvisited focus-loss/resize/device states and bounded startup conditions instead of turning every planned row into a pass.

## Candidate and operating route

After integrating the final export manifest, freeze a production build with hashes of source, public assets and built outputs. Serve ordinary play from `dist/` on 4191. Compile the diagnostic harness into a separate `test-dist/` output with its own identity and port 4193, using the same game, assets and configuration with only diagnostics enabled. Move fixture construction into that diagnostic dependency path so ordinary release omits the adapter, fixture code and QA page. A URL flag alone is not isolation. The harmless asset viewer remains a separate development inspection route. Observe through supported browser controls and read-only DOM summaries. Record route, build, seed, clock mode and any pauses in every evidence note.

Retry the maker's documented browser selection once after the asset join. If it still returns no browser, the caller can operate a complete ordinary run in its working session and return screenshots and observations for the maker to inspect. Do not substitute a headless script for actual play or describe another operator's actions as the maker's personal run. Keep only one active gameplay browser tab during performance sampling.

## Ordinary complete play

Use actual captures to pursue **Fang + Moth → Dusk**, then retain **Ember + Mire → Eclipse**. Choose additional companions from observed survival needs; record any protection versus future-ingredient tradeoff. Public tactical pause and public Pause are allowed but must be disclosed, including the fact that paused inspection makes this different from uninterrupted human reaction-speed play.

Capture evidence around waves 4/5 and 9/10: spatial crowd pressure, health, nearby threats, squad, charge, movement decision, actual evolution activation and several seconds of resulting combat. Preserve unfavorable outcomes. Continue through the Bellkeeper and outcome, then retry. If the route fails, report the cause and adapt actual choices; do not silently replace the outcome with a seeded victory. This run extends earlier ordinary Solar and independently reviewed Worldcoil coverage to the third lineage and proves the integrated presentation through all twelve waves.

## Targeted scenarios and branch coverage

| Check | Setup and observed action | Evidence that resolves it |
| --- | --- | --- |
| All forms at game scale | `pre-evolution` / `second-evolution`, default, Storm and Dusk variants | Activate each valid recipe through the Field guide; inspect each new model, attacks, ally marks and warnings during subsequent combat. Seeded entry is labeled assisted. |
| Missing ingredients and recovery | `wrong-recipe`, ordinary capture panel | Wrong recipes remain unavailable, actual desired enemy is highlighted, a later charge enables a real corrective capture, and the same rules apply while paused. |
| Hinge motion and crowded identity | `roles` and live `late-pressure` | Several enemy behaviors interact at once; Fang anticipation, Mire warning, Moth healing and ally source cues are distinguishable. Confirm contact/readability against original thresholds, not model bounds. |
| Capture camera and economy | Ordinary left, center and right movement | Full reach and exact target visible in planning; cancel preserves charge/entities; successful bind removes one actual enemy and adds one ally; first ground click after close maps correctly. |
| Slot and recipe economy | Full roster, dismiss, evolve | Six-place limit explained; release permits a new capture; evolution consumes exact ingredients and frees expected places. Existing meaningful rule tests supplement visible checks. |
| Boss and loss | `boss-danger`, plus ordinary final wave | Warning onset, active impact, projectile fan, health changes and defeat explanation visible. Ordinary full run supplies natural boss victory if achieved. |
| Focus and keyboard | Ordinary menu, arena, public pause, focus loss | Native Space/Enter buttons, capture shortcut, release on blur, resume without stuck movement, no accidental reset and usable retry. |
| Resize and presentation | Target desktop 1280×720; also a narrower desktop window and 1920×1080 if the host can resize | HUD/capture/guide remain readable, actionable warnings visible, pointer mapping correct. A viewport check is not mobile or physical-device coverage. |
| Loading, failure and repeated sessions | Cold entry, missing asset inspection, retry several times | Visible readiness/error states, no silent blockout fallback, controls remain usable, resources settle rather than rising each retry. No saved run progression is promised. |

The earlier mechanics comparisons remain evidence for their identified core builds. Presentation integration calls for affected playback rather than repeating every unchanged experiment. If a new collision perception, attack warning or pacing issue is observed, record a hypothesis, change only the implicated presentation/rule and replay that affected case.

## Performance measurement

Measure actual production rendering after warm-up in representative busy ordinary play, including raw wall-frame intervals, not clamped simulation time. The release's bounded read-only frame history tags run/time/wave/hostile count, allowing busy intervals to be selected after the caller's full run. Record browser WebGL backend, viewport, DPR/quality, build, sample duration, hostile/ally composition, renderer triangles/calls and resource counts. Include a matching gameplay screenshot. Additional seeded live stress belongs to the separately identified test build and is marked assisted; it does not replace ordinary release profiling. Manual stepping is not frame-rate evidence.

Compare median/p95 with the provisional 16.7/33.3 ms targets; report long frames above 50/100/200 ms and worst stall. Report the chosen asset budgets of 150k visible triangles/100 calls alongside actual counters. Measure cold load-to-ready separately from steady play, and compare resources after repeated retries. The Intel/D3D11 backend previously observed in this app is the candidate target unless the actual measured session reports another adapter. Do not infer use of the machine's separate NVIDIA GPU.

Optimize from observed bottlenecks. If no budget failure or resource trend is observed, do not add a performance-driven rewrite. Recheck the same workload after any optimization and preserve before/after values. Keep sound claims bounded: generated browser audio can be checked for successful initialization and controls, but audible quality requires actual listening.

The caller dispatches the final fresh reviewer only after the integrated build, this QA record and the asset report are joined. All game and asset source remains frozen during that independent review.
