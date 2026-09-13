# Nightbind Blender asset handoff

The 22 original models are ready for game integration. They were authored, saved and exported with **Blender 5.2.1 LTS**, build `9e2066aef7ef`, using **Khronos glTF Blender I/O v5.2.40**. Every delivered GLB loaded through the game's shared Three.js loader in `/asset-preview.html`; the recorded runtime SHA-256 values match the final manifest. All 22 pass Khronos glTF Validator `2.0.0-dev.3.10` with **zero errors and zero warnings**. Its informational `NODE_EMPTY` messages identify the intentional sockets.

This is the asset production join for approved core `core-220cfa39951c`. Final integrated movement, attack timing, crowd readability and frame-rate acceptance remain the game maker/caller's work. The static preview is not evidence of a completed gameplay run.

## Delivered files and reproduction

- `public/models/manifest.json` is the canonical schema-version-1 inventory: file/source mapping, measured bounds, triangles, vertices, mesh-part pivots and parent names, materials, sockets, suggested rigid motion, bytes and SHA-256 for each model.
- `public/models/<id>.glb` contains each of the 22 IDs in the table below. No GLB references an external buffer, image, texture, rig or animation file.
- `assets/source/<id>.blend` contains the corresponding editable source, root, mesh parts, vertex palette and sockets. There are 22 individual sources plus `keeper-assembly.blend` and `arch-rim-assembly.blend`, which preserve the positioned lantern and two joined rim pieces with the suspended bell. Inspection cameras/lights exist only in those source assemblies, not GLBs.
- `public/models/portraits/<id>.png` supplies 15 transparent 192×192 actual-model portraits: keeper, lantern, six bases, six evolved forms and boss. Each is rendered after reimporting its delivered GLB. Lossless PNG compression keeps the largest at 30,951 bytes. `evidence/assets/portraits-192.png` and `portraits-48.png` show the complete set at render and UI sizes.
- Authoring/export code: `assets/source/build_assets.py`, `meshkit.py`, `representatives.py`, `creatures.py`, `environment.py`. Source and actual-GLB rendering: `render_views.py`. Contact sheets/lossless PNG compression: `contact_sheets.py`. Structural validation: `validate_exports.cjs`, with reproducible npm dependencies in `validator/package.json` and `validator/package-lock.json`.

Run from the game's root directory (the folder containing `package.json`) in PowerShell:

```powershell
# Regenerate the original authored set from the project scripts.
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --factory-startup --python assets/source/build_assets.py -- --stage all

# Re-export edited .blend sources without regenerating their geometry instead.
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --factory-startup --python assets/source/build_assets.py -- --stage all --from-saved

# Rebuild source contact views, inspection assemblies and actual-export portraits.
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --factory-startup --python assets/source/render_views.py
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --factory-startup --python assets/source/render_views.py -- --lineups
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --factory-startup --python assets/source/render_views.py -- --portraits
& 'C:/Users/danhm/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' assets/source/contact_sheets.py

# The validator package is development-only; no game dependency was added.
npm ci --prefix assets/source/validator --no-audit --no-fund
node assets/source/validate_exports.cjs
```

The bundled Python path supplies Pillow for contact sheets/compression. The Blender scripts use Blender's Python and standard library only. `--stage representatives`, `bases`, `evolved` and `environment` support the staged production subsets. `evidence/assets/source-reexport-check.json` records an actual `--from-saved` export of all 22 files with **zero SHA-256 mismatches** against the authored exports.

## Measured export costs

All GLBs together are **485,472 bytes** and **5,914 unique triangles**, below every class cap. Parts count authored mesh nodes; a node with the optional glow material becomes two runtime primitives. The boss has four authored mesh nodes and five runtime primitives. Runtime figures and exact transforms are in `evidence/assets/runtime-import-all.json`.

| ID | Triangles | Exported vertices | Parts | Materials | GLB bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| keeper | 284 | 528 | 2 | 1 | 23036 |
| lantern | 188 | 376 | 1 | 2 | 16900 |
| rim_segment | 32 | 60 | 1 | 1 | 3676 |
| bell_arch | 296 | 516 | 1 | 1 | 21616 |
| hanging_bell | 152 | 300 | 1 | 1 | 12936 |
| ember | 180 | 346 | 1 | 2 | 15800 |
| thorn | 168 | 318 | 1 | 1 | 13764 |
| volt | 120 | 240 | 3 | 1 | 12456 |
| mire | 204 | 358 | 1 | 1 | 15508 |
| fang | 310 | 630 | 3 | 1 | 27692 |
| moth | 200 | 396 | 3 | 1 | 18532 |
| pyre | 382 | 688 | 1 | 2 | 29408 |
| storm | 292 | 528 | 2 | 1 | 23020 |
| dusk | 286 | 542 | 3 | 1 | 24328 |
| solar | 354 | 702 | 3 | 2 | 31396 |
| world | 436 | 830 | 3 | 1 | 35740 |
| eclipse | 410 | 748 | 1 | 2 | 31824 |
| boss | 626 | 1158 | 4 | 2 | 50368 |
| arena_floor | 702 | 1281 | 1 | 1 | 51564 |
| shrine_plinth | 124 | 216 | 1 | 1 | 9712 |
| votive | 108 | 222 | 1 | 2 | 10776 |
| rubble_cluster | 60 | 108 | 1 | 1 | 5420 |

The supplied kit assembled as one floor, 24 rim pieces, one arch/bell, one shrine, three votives and two rubble clusters costs 2,486 triangles. An arithmetic upper workload of 240 Fanglings, six Worldcoils, keeper/lantern, boss, that kit and 20k effect triangles is about 100.6k triangles. That is a planning calculation, not a production frame measurement.

The actual 180-base mixed preview at 1280×720/DPR1 recorded **36,164 triangles and 21 draw calls**, including its scale/warning references (`mixed180-runtime-import.json`). Backend: `ANGLE (Intel, Intel(R) Graphics (0x00007D67) Direct3D11 vs_5_0 ps_5_0, D3D11)`. No discrete-GPU or final-game FPS claim is made.

## Scale, materials and motion

The source uses Z up and −Y forward; the standard exporter converts once to runtime Y up and +Z forward. Root transforms are neutral. Creature bounds match the contracted target dimensions, with these intentional details: Voltwing, Moth and Solar have 0.12-unit ground clearance; boss exported depth is 3.28 rather than 3.40. Keeper bounds are 1.410×2.100×0.829, preserving the broad mantle with a shallower cloak. The held assembly is 1.755 units wide. Lantern's base has 0.02 clearance. Hanging bell is 1.60×1.58×1.43 rather than 1.60×1.80×1.50 and hangs below its suspension origin; do not ground-align its origin in assembly. Rubble depth is 1.03 rather than 1.10. The floor's inlay extends only 0.006 above its Y=0 top.

All surfaces are opaque vertex-colored Principled materials: roughness .86, metallic .08. There are no UV/texture/bake dependencies. Materials retain Blender's double-sided setting; interior skins are modeled for visible cups and bell cavities. The shared small glow material exports an explicit warm emissive factor `[0.615736, 0.436772, 0.156260]`. The first linked vertex-color emission exported white because glTF has no corresponding vertex emission channel; the final explicit factor fixes that portability issue. Base color remains `COLOR_0` under both Blender and the actual Three.js importer.

All GLBs have `animations: []`, no armatures, no skins and no morph targets, as agreed. The manifest proposes idle/travel/attack/windup gestures without changing simulation timing. Wing hinges are `wing_l`/`wing_r` on Volt, Moth, Dusk and Solar. Fang and World have `head` and `jaw`; Storm has `head`; boss has `arm_l`, `arm_r`, `clapper`; keeper has `arm_r`. The remaining geometry is `body`. Hinges retain neutral local translations/quaternions. The preview's rigid Volt wing flap and Fang head/jaw pose were inspected; captures are `volt-runtime-motion-a.png`, `-b.png`, `fang-runtime-motion.png`, with `rigid-motion-runtime.json`. These are game-owned pose checks, not exported animation clips or proof of integrated combat timing.

Every creature and keeper has `socket_attack`. Keeper also has `socket_capture` and `socket_lantern`; lantern has `socket_core`; Pyre/Solar/World/Eclipse/boss have `socket_core`; arch has `socket_bell`; rim has `socket_start`/`socket_end`. Manifest socket quaternions are identity. Keeper's lantern attachment is runtime `[0.76,0.36,0.45]`, with capture at `[0.76,0.81,0.45]`. Attach the lantern without additional basis rotation. No visual file changes capture range, contact thresholds, colliders, damage centers or timing.

## Inspected evidence and production decisions

The representative keeper/lantern and arch/rim set was exported and inspected before the creature set. Source front, side, three-quarter and game-angle images established the wide mantle, dark hood and split hem. Runtime inspection caught the first 90° socket rotation tipping the lantern forward. It was corrected at source, reexported and observed upright at the hand before expansion. `keeper-runtime-detail-before-socket.png` retains the failed assembly; `keeper-runtime-detail.png` and `keeper-runtime-import.json` show the correction. Final material appearance is in the updated keeper four-facing images and lantern detail.

`arch-rim-source-joint.png`, `arch-rim-source-game-angle.png`, `rim-runtime-joint.png` and `arch-bell-runtime-assembly.png` show the joined modular pieces and suspension. The standalone bell initially disappeared beneath the preview floor because of its top pivot; the game maker added an explicit viewer lift and the real arch attachment, without altering the asset pivot. The final visible bell is in `hanging_bell-runtime-detail.png` and `hanging-bell-runtime-import.json`.

`bases-source-front.png`, `bases-source-three-quarter.png`, `bases-source-game-angle.png` and the equivalent `evolved-source-*` images were inspected from the saved Blender sources. The first Storm rise projected into a nearly straight band; changing its path to expose the S in depth improved the game view. Four-facing runtime views then showed the first ascension tilt losing its openings at back-facing angles. Solar's sunwheel, World's coil and Eclipse's crescent were flattened toward the overhead view, retaining open centers through the four facings. The initial runtime contact sheet is retained as `evolved-runtime-four-facings-initial.png`.

Final actual-camera views are `<id>-runtime-yaw0/90/180/270.png` for keeper and all 13 creatures, collected without rescaling in `bases-runtime-four-facings.png` and `evolved-runtime-four-facings.png`. An initial overly fast capture sometimes preceded the next rendered frame; the settled capture uses a brief frame allowance, and `bases-runtime-four-facings-initial.png` retains that failed evidence. The final views separate the base silhouettes and retain Dusk's muzzle, Solar's rays, World's ring and Eclipse's crescent. Storm still foreshortens from behind, but its open bend, cups and forked head remain visible; the close check is `storm-runtime-back-detail.png`.

`bases-runtime-mixed-final.png` shows the final 180-base scene with poison/boss scale rings still visible. The 48-pixel portrait sheet retains the arena identities. Source contact images use Blender Cycles CPU, 16 samples and AgX; they establish source form only. Actual runtime captures use the shared game's ACES/exposure/light settings and fixed camera. `gltf-validation.json` stores the unfiltered structural reports. `runtime-import-all.json` stores the matching actual-import measurements for all 22 files.

All geometry and portraits are original project work; no borrowed art, generated concept billboard or third-party texture is a final asset. The development-only Khronos validator retains its npm package provenance and license. There are no unresolved asset-import errors. Final integrated collision perception, allied 0.85 scale, source trails, warning occlusion during movement, production frame-rate and full-run play remain explicitly unverified by this asset-only phase.
