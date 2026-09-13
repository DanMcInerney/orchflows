# Production rendering measurements

Candidate **release-c09f13cac8e9**, source **source-c09f13cac8e9**, served from ordinary `dist` at 4191. Status: **observed target budgets met**. This report uses actual live rendering from the ordinary Dusk → Eclipse winning run, not a seeded/manual benchmark. No performance repair or rebuild followed these measurements.

## Conditions and measurement

Supported in-app browser; actual backend `ANGLE (Intel, Intel(R) Graphics (0x00007D67) Direct3D11 vs_5_0 ps_5_0, D3D11)`. Viewport 1280×720, DPR 1, normal motion and default rendering. The renderer uses shared GLBs/instancing, no dynamic shadow maps and no postprocessing. This is not a claim that the machine's separate NVIDIA adapter was used.

The caller operated public movement, capture, guide, Pause and retry. Only one game tab was active during sampling. Public pauses allowed decisions; live segments continued in real time. `#performance-observation` exposes bounded raw RAF intervals, independently from simulation catch-up clamping. Rows are tagged with run, simulation time, wave, hostiles, raw milliseconds, renderer calls and triangles. Only live, unpaused, playing frames enter the history. Manual ticks never count. The full run was run 2 after a preserved ordinary loss/retry; metadata later captured on run 3 retains tagged run-2 rows.

The provisional targets were approximately 16.7ms median, p95 ≤33.3ms, under 150,000 rendered triangles and 100 draw calls. Durations below sum raw active frame intervals; public pauses are excluded. This measures frame cadence, not GPU execution time or continuous uninterrupted play.

| Workload | Samples / raw active seconds | Median | p95 | p99 | Maximum | Max calls / triangles |
| --- | --- | --- | --- | --- | --- | --- |
| Winning run | 15,187 / 253.117 | 16.7ms | 16.8ms | 17.1ms | 18.9ms | 45 / 74,736 |
| ≥150 hostiles, time 179.517–198.8 | 1,160 / 19.334 | 16.7ms | 16.9ms | 17.4ms | 18.9ms | 40 / 74,736 |
| Wave 9, time 176–197.983 | 1,321 / 22.017 | 16.7ms | 16.9ms | 17.4ms | 18.9ms | 40 / 74,736 |

All three populations reached 240 hostiles. **Zero sampled intervals exceeded 50, 100 or 200ms.** The busiest wave-nine composition was Dusk, Ember, Thorn, Volt, Mire and Moth. The keeper crossed from the crowded eastern side to fresh western ground; this was a real mixed horde with poison, lunges, wing motion and ally attacks. The [matching busy image](../evidence/caller/dusk-run/22-wave9-escape-live.png) and [state](../evidence/caller/dusk-run/22-wave9-escape.json) show that workload, including the actual 240-hostile state. This is not a static title or isolated model-viewer count.

## Reproducible evidence

- [Caller full-run and per-wave summary](../evidence/caller/dusk-run/attempt2-performance-summary.json), computed with read-only evaluation over tagged DOM frame rows.
- [Raw wave-nine rows](../evidence/caller/dusk-run/attempt2-wave9-frames.json), 1,321 rows; [metadata](../evidence/caller/dusk-run/performance-metadata-after-retry.json) declares column order, viewport/backend and all loaded asset hashes.
- [Maker recalculation](../evidence/maker/production-wave9-recalculation.json) independently recomputes the exported slice using [the local analysis script](../evidence/maker/analyze-production-performance.py). Linear interpolation yields p99 17.38ms, consistent with the caller's one-decimal 17.4ms. It reproduces p95 16.9ms, maximum 18.9ms and 40 calls / 74,736 triangles.

From the project root, reproduce the slice calculation without running gameplay:

```powershell
python evidence/maker/analyze-production-performance.py evidence/caller/dusk-run/attempt2-wave9-frames.json evidence/caller/dusk-run/performance-metadata-after-retry.json
```

The first two complete-history export attempts hit the browser tool's 200,000-character response cap. They are preserved as `attempt2-performance.truncated.txt` and `after-win-retry-performance.truncated.txt`. They are invalid JSON and must not be used as complete evidence. The caller recovered with a compact aggregate, separate metadata and bounded raw-wave export. The full-run summary is caller-calculated; only the retained wave-nine raw slice is independently recalculated locally.

## Startup and repeated sessions

The ordinary warm reload reported asset/portrait readiness in **91ms**, navigation-to-ready 145.5ms. A first visit to previously unused local origin 4195, serving the same frozen files, reported **90.4ms**, navigation-to-ready 151.2ms, all 22 assets ready, then successful public start/Pause. [Fresh-origin record](../evidence/caller/fresh-origin-load.json). Both measurements stop before first GPU frame/shader compilation. The latter is a first visit to a fresh local origin in an existing browser; neither establishes a clean browser-profile, GPU-cold or real-network startup benchmark.

Three additional public new-run/start/pause cycles returned fresh game state. [Retry resource records](../evidence/caller/dusk-run/repeated-retries.json) retain stable **58 geometries, one texture, 22 loaded models**, with audio voices settling to zero. Models remain loaded/shared across runs. A separate missing-keeper fault copy genuinely blocked loading, showed the specific error, and recovered through public retry after its original export was restored. No geometry/texture growth was observed in the bounded retry series; JavaScript heap retention and very long sessions were not profiled.

AudioContext was running at the ordinary victory, with 1,219 cues reported and no error; voice count fell from four to zero when settled. Controls/persistence were observed. These counters do not prove audible mix quality.

## Decision and limits

The measured workload fits both cadence and rendering budgets, so no optimization change was justified. In particular, manual scenario tick speed and the asset viewer's mixed-180 counter were not used as release performance evidence. No claims extend to other viewport sizes, physical devices, quality modes, browsers, continuous background-tab operation or mobile. The final independent reviewer receives this exact build and can challenge any remaining presentation or gameplay concern without obscuring which machine and conditions produced these numbers.
