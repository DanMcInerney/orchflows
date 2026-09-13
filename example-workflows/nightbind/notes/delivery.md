# Nightbind delivery — 2026-09-13

**READY for the requested local desktop game.** [Play Nightbind](http://127.0.0.1:4191/) on the independently reviewed `release-c09f13cac8e9`. The separate assisted build is `qa-c09f13cac8e9`; both use `source-c09f13cac8e9`.

The full [20-step example workflow](../../../example-workflows/3d-browser-game/skills/3d-browser-game/SKILL.md) has reached delivery. Step 20 requires no repair: the final reviewer found no material blocker, and the reviewed game, assets and builds are unchanged. Existing review and verification evidence is reused without a redundant rebuild or replay. This closeout was added after review; earlier handoff documents retain their historical “ready for final review” status and frozen hashes.

## Play and edit

- One continuous twelve-wave run, with one capture charge every eleven seconds and six companion places. Capture an actual nearby enemy; complementary recruits earn evolutions at waves 5 and 10. The Bellkeeper arrives in wave 12.
- Six distinct base creature roles, three first evolutions and three ascensions support different squad choices. Click ground or use WASD/arrows to move; Space opens capture. The public guide explains recipes and release. Pause, settings, outcomes and retry are available in the game.
- [Source, build/run/test commands and public controls](../README.md). Development remains on 4190; ordinary production on 4191; assisted scenarios on 4193. The preview is local, not publicly deployed.
- [Editable Blender sources](../assets/source/), [asset production and re-export commands](assets.md), [design experiments](core-playtest.md), and [art direction](art-direction.md). The delivery includes 22 GLBs, 24 editable Blender files and 15 capture/guide portraits; all runtime models use the shared production loader.

## Reviewed evidence

| Work | Result |
| --- | --- |
| Independent core play | Ready on `core-220cfa39951c`, with ordinary outcome/retry and no necessary repair. [Core report](core-review.md). |
| Integrated caller play | Preserved first loss, then Dusk → Eclipse victory at 252.833 seconds, nine captures, exactly two evolutions, boss outcome and clean retry. [Caller report](caller-production-play.md). |
| Independent final play | First public-only wave-four loss retained; informed Pyre → Solar victory at 266.95 seconds, seven captures, exactly two evolutions, boss outcome and clean retry. [Final report](final-review.md). |
| Targeted QA | Missing/full recipes, actual-hostile replacement, paused time, alternate evolved forms, boss failure/retry, settings, repeated resets and asset failure/recovery. Ordinary play and assisted scenarios remain separately identified. [Production QA](production-qa.md), [independent checks](../evidence/final-review/checks.md). |
| Correctness and identity | Thirteen game tests passed independently. All 97 fingerprinted source files, 41 release outputs, 43 assisted outputs and 28 reviewed handoff documents matched; diagnostic adapter and fixture code are absent from release. [Independent verification](../evidence/final-review/integrity.json). |
| Performance | Actual ordinary play reached 240 enemies. Its busy frame slice measured p95 16.9 ms/max 18.9 ms on Intel/D3D11 at 1280×720, DPR 1. Independent Solar play also met the target, and the reviewer recalculated the heavier slice. These are active raw frame intervals with public pauses excluded. [Performance conditions and limits](performance.md). |

The final reviewer found two nonblocking issues: capture demand diminishes after the planned squad is assembled and Solar leaves a quiet wave-eleven interval; loss advice is too generic for some causes. They remain visible in the report. A future tuning pass can address those specific situations while preserving earned relief; no unreviewed tuning was included in this delivery.

Other devices/viewports/browsers, sustained keyboard automation, deliberate blur/context loss, audible quality and fully cold startup remain unverified. Public click-to-move supported actual adaptive play. No claim of human enjoyment follows from automated checks or wins.

## Workflow dogfood closeout

The caller used the workflow's four production roles: one continued game maker, a fresh core reviewer, one Blender maker and a fresh final reviewer. Caller-owned asset dispatch/join and production integration were exercised. Both ready checkpoints closed without repairs. Actual defect-repair and failed-checkpoint stopping branches remain unexercised.

The two narrow authoring improvements discovered during this run—an uncoached first-outcome boundary and raw frame timing before simulation clamping—were accepted within the same final review. [Full authoring and trial report](../../../reports/3d-browser-game-rebuild-2026-09-12.md). No fifth production agent or further independent review was added; the library remains source in `example-workflows`, without modifying the active plugin installation.

## Repository location

At the user's request, the complete project moved from `dogfood/nightbind/` to `example-workflows/nightbind/`, beside the workflow library. All 2,416 files matched their original hashes immediately after the move, including editable assets, builds, dependencies and playtest evidence. The game source, models and reviewed outputs remain unchanged; documentation links and run-location wording were then updated. Historical evidence retains its original paths and review-time document hashes. Use the commands in the project README from the new directory.
