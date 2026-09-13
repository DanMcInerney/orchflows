# Nightbind

A single night of horde survival. Capture the creatures closing in, build a six-monster circle, and earn two transformations before the twelfth-wave Bellkeeper.

This runnable example lives at `example-workflows/nightbind/`, beside the [3D browser game workflow](../3d-browser-game/README.md) that produced it. See the [final delivery and independent review](notes/delivery.md) for the completed result; earlier production handoff notes below retain their review-time status.

Recorded QA evidence is included with the example. Dependencies, generated preview outputs and logs remain ignored. Git attributes preserve the exact source, model and evidence bytes used by the recorded build fingerprints. References to external temporary workspaces in historical reports describe local trial artifacts.

## Run locally

Requires Node.js 24 and npm. From this directory:

```powershell
npm.cmd ci
npm.cmd run dev
```

Development: http://127.0.0.1:4190/. For the exact production candidate:

```powershell
npm.cmd test
npm.cmd run build
npm.cmd run preview
```

**Play the frozen production candidate:** http://127.0.0.1:4191/ — **release-c09f13cac8e9**. Its build identity appears at the lower right. Thirteen tests passed, and production QA is ready for final independent review. The current release and separate assisted-test identities are in `notes/build-id.txt` and `notes/test-build-id.txt`; `evidence/builds/production-candidate.json` links the exact source, assets, outputs and handoff reports. Do not rebuild while a reviewer is playing the frozen output. The approved earlier core remains archived under `evidence/builds/core-220cfa39951c-runtime/`.

## Play

1. Read the evolution recipes, then light the lantern. One run lasts about five minutes; waves advance every 22 seconds.
2. Click ground to travel, or hold WASD / arrow keys. Companions and the keeper attack automatically. Keep moving away from poison circles and charging creatures.
3. Open **Bind a creature**, or press Space on the arena. Time pauses while choosing. Bind one actual enemy within reach; the lantern recharges in 11 seconds. It holds one charge.
4. Keep complementary companions. **Field guide** shows all recipes and lets you release a companion if your six slots are full. The guide opens at waves 5 and 10; transformations require ingredients you have captured.
5. Dodge the Bellkeeper's warning circles and volleys. Defeat it to win. Zero vitality ends the run. **Light another lantern** starts fresh.

The Pause button or Escape pauses the game. Returning to the night clears old movement, so choose a new destination. Switching away also pauses. Settings provides volume, mute and reduced decorative motion; those preferences persist locally, while run progress does not. Menus support native Space/Enter activation; keyboard focus returns to the arena after closing them.

| First awakening at wave 5 | Ascension at wave 10 | Role |
| --- | --- | --- |
| Emberling + Thornback → Pyre Warden | Pyre Warden + Voltwing + Mourning Moth → Solar Seraph | Broad clearing and protection |
| Voltwing + Mireling → Storm Serpent | Storm Serpent + Thornback + Fangling → Worldcoil | Chains and crowd control |
| Fangling + Mourning Moth → Dusk Reaper | Dusk Reaper + Emberling + Mireling → Eclipse Sovereign | Focus damage and recovery |

## Reproducible development scenarios

The development server shows **Development scenarios · assisted tests**. A separate compiled test output reproduces the same game, assets and rules with that adapter enabled:

```powershell
npm.cmd run build:test
npm.cmd run preview:test
```

Assisted test preview: http://127.0.0.1:4193/. Its output is `test-dist/`; its identity starts with `qa-`. Ordinary release output is `dist/` on 4191 and has a `release-` identity. The build script audits that release JavaScript contains neither the mutating adapter nor seeded fixture code. No URL flag enables cheats in ordinary release. Both identity manifests include the common source digest, so the relationship between a release and its assisted build is explicit.

Choose a scenario and variant, choose **manual** clock, then **Reset scenario**. Reset preserves clock mode. The fresh scenario begins at the title; use **Start scenario** or the normal title button. Other scenarios are already playing. Manual mode has no automatic simulation ticks. Set Move x/z, press Move, then Step ticks (1–600, at 60 ticks/second). Manual stepping respects public pause. Close a public menu before stepping. Setting live resumes real-time simulation; live stepping is rejected.

| Scenario | Purpose |
| --- | --- |
| fresh | Start, normal input parity and reset |
| wrong-recipe | Wave 4 at 78 seconds, an incomplete first recipe and partly charged lantern |
| pre-evolution | Wave 5, a valid pair and 85 mixed enemies |
| late-pressure | Wave 9, the six-companion roster used in the ordinary maker run, 60 enemies |
| second-evolution | Wave 10, valid ascension ingredients and 85 mixed enemies |
| roles | Wave 7 mixed behavior |
| boss / boss-danger | Wave 12, advanced roster; danger starts at low health |

Variants: default; slow-charge (18 seconds); weak-evolution (42% damage); late-baseline (old wave-9 spawn rate); storm-route / dusk-route (alternate ingredients for pre-evolution and second-evolution). All use the same simulation and action rules. Seed defaults to 12345.

**Refresh state** exposes an inspectable snapshot. `#game-observation` contains the read-only full JSON snapshot in both builds; `#performance-observation` contains bounded raw frame history tagged with run/time/wave/hostile counts, draw calls/triangles, asset hashes and the actual graphics backend. Its `fields` array defines the row columns. Frame timing records only live, unpaused play; manual steps are not performance evidence. In the supported browser runtime, read their DOM text. Do not inject state. Public click-to-move supports ordinary agent play without a held-key API.

Export long performance histories as bounded row slices plus metadata, or compute compact summaries with read-only evaluation. A full run can exceed the browser tool's output limit; verify that a saved export parses before using it. Valid production wave-nine rows and a local recalculation command are linked in `notes/performance.md`.

## Authored assets and inspection

All runtime creatures, the keeper/lantern and the bell court use original Blender exports. `public/models/manifest.json` maps every ID to measured geometry, pivots, sockets, portraits and source. The source files and reproducible export/render/validator commands are documented in `notes/assets.md`. To re-export edited saved models:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --factory-startup --python assets/source/build_assets.py -- --stage all --from-saved
```

The development-only inspection route is http://127.0.0.1:4190/asset-preview.html. It uses the game's loader/camera/lighting, explicit asset/facing/view controls, a mixed 180-model arrangement, socket axes and read-only import diagnostics. It is not a gameplay performance benchmark. Missing or invalid required models/portraits block game readiness with a visible retry/error, rather than substituting a blockout.

## Production evidence

`notes/design.md` records brainstorming and the selected loop. `notes/core-playtest.md` contains the two observed mechanic comparisons and maker runs; `notes/core-review.md` is the independent approved core checkpoint. `notes/art-direction.md`, `notes/asset-brief.md` and `notes/assets.md` connect the gameplay needs to editable Blender assets. `notes/production-step14.md` records content/interaction preparation. `notes/production-qa-plan.md` preserves the joined QA plan; **`notes/production-qa.md` records the completed production checks and limits**, with exact source/output checks in `evidence/builds/production-final-verification.json`.

The integrated ordinary Dusk → Eclipse run won at 252.833 seconds with nine captures and exactly two evolutions, after a preserved first-attempt loss. Public pauses supported adaptive browser play. Actual busy play reached 240 enemies; at least 150 enemies occupied 19.334 measured active seconds with a 16.9ms p95 frame interval on the observed Intel/D3D11 backend at 1280×720. See `notes/caller-production-play.md` for decisions and `notes/performance.md` for raw timing, startup/retry conditions and limitations. Alternate final forms were also inspected through the separate assisted build. Missing-asset error/recovery, settings persistence, full-squad release/capture and clean repeated retries were observed.

The earlier core verdict applies to that identified core, not automatically to the integrated production game. Preserve ordinary runs, assisted fixtures and automated rule checks as distinct evidence. Desktop pointer/keyboard play is the target; no mobile, controller or physical held-key automation claim is made. Audio uses original synthesized Web Audio cues and visual equivalents; audible quality is reported only if actually listened to.
