# Blender asset handoff — Nightbind

Produce the designed creature set and reusable bell-court kit in `art-direction.md` for approved core `core-220cfa39951c`. This is workflow step 13. The game maker retains all renderer, loader, integration and gameplay code. Use Blender 5.2.1 LTS available on this host, inspect its actual exporter options, and report the exact executable/version used.

## Ownership, order and deliverables

Own `assets/source/`, `public/models/` (including portraits), `evidence/assets/` and `notes/assets.md`. Do not modify `src/`, root HTML/config/build scripts, gameplay notes or core evidence. The concept files in `notes/art-study/` are reference only.

1. Model a representative **keeper with lantern** and **bell-arch / rim joint** first. Save source and export. Inspect front/side/three-quarter silhouettes in Blender, then the actual GLBs in the game maker's runtime preview using the contract below. Resolve scale, axis, material and readability issues before expanding the set.
2. Make the six bases with distinct silhouettes; inspect in a mixed lineup and at game distance. Then author the six evolved forms and Bellkeeper, retaining the designed lineage rather than reusing scaled bases.
3. Complete the restrained environment kit. Render portraits from the corresponding actual models. Validate costs, pivots and export dependencies. Deliver source, scripts, all GLBs, metadata, inspection views and a candid deviation list.

Suggested source files: `assets/source/nightbind-keeper.blend`, `nightbind-creatures.blend`, `nightbind-arena.blend`. A different grouping is fine if object IDs remain stable. Reproducible author/export entry point: `assets/source/build_assets.py` with explicit arguments/paths. Include any helper files and instructions in `notes/assets.md`; no hidden external fonts, images or procedural material resources.

Runtime files: `public/models/<id>.glb`; `public/models/manifest.json`; `public/models/portraits/<id>.png`. Preview/contact outputs go to `evidence/assets/` (representative source views, runtime game-distance captures, dense lineup, metadata/validator output). Editable source plus deterministic scripts are required; a successful Blender subprocess alone is not acceptance.

## Coordinates, pivots and geometry contract

- One unit = one meter-like gameplay unit. **Blender: Z up, -Y forward, X right. GLB/game: Y up, +Z forward, X right.** The standard export conversion should perform this once. Verify with a visible forward marker in the representative preview; do not compensate by rotating again in the game.
- Every asset has a root named exactly its stable ID, at the ground-projected center (0,0,0). Export root scale 1 and no unintended offset/rotation. Apply mesh scale before final pivots; preserve transform hierarchy deliberately. Record measured GLB bounds, not only Blender dimensions.
- Creature/keeper origins are on the ground plane beneath the main mass. Flying bodies are modeled above the origin; runtime bob is small additional motion. Feet start at Y=0 for grounded actors. Do not bake ally-specific size or orbit into files; game uses the same base asset for enemy and captured ally.
- Keep thin protrusions outside the principal collision mass visibly lightweight. The game's enemy contact thresholds are center distance 0.72 (base) and 2 (boss); no mesh-generated collider will be imported. Capture distance is measured to entity center. No collider objects, cameras, lights or study rulers in visual exports.
- Meshes are opaque and outward-facing, with clean normals and no coincident internal faces. Intentional open cavities need modeled inner surfaces where visible. No negative scale mirroring in runtime exports. Mirror and apply carefully in source.
- Named rigid parts are permitted. Use a small explicit hierarchy: `body`, `head`, `jaw`, `wing_l`, `wing_r`, `tail`, etc., only as needed. Pivot each moving part at its hinge; parent it under the root/body as appropriate. Do not add arbitrary empty wrapper chains. Preserve pivot transform metadata so the loader can instance geometry and apply part motion.
- Sockets are empty nodes named `socket_attack`, and `socket_capture` on keeper. Use `socket_lantern` on keeper and root on the separate lantern asset. Optional `socket_core` on boss/ascensions locates the central VFX. +Z at an attack socket is its forward firing direction. Include socket transform arrays in metadata. Sockets have no geometry cost.

## Creature sizes and budgets

Dimensions are **GLB X width × Y height × Z depth**, in units, before the current allied 0.85 visual scale. Targets allow about ±10% where shaping warrants; report deviations. Silhouette separation and collision readability outrank filling the box. Base central solid bodies should be about 0.8–1.1 units wide; wings/ears/tails may extend to the wider limits below. Costs below are **exported triangles across all parts**, not source quads. Rigid mesh-part limits also constrain instanced draw calls.

Inspect yaw 0°, 90°, 180° and 270° at the gameplay camera. Major negative spaces (Pyre furnace, Solar center, Worldcoil loop and Eclipse moon gap) should remain visible at useful facings, with roughly 0.4 units of clear opening rather than a subpixel slit. Tilt or shape rings in depth deliberately for the elevated camera. The concept crowd uses flat billboards and cannot prove this. Protect Dusk's long jackal muzzle and split veil so its 3D silhouette does not collapse into a generic upright figure.

| Stable ID | Size target | Main construction / required detail | Triangle target / cap | Mesh parts cap |
| --- | --- | --- | --- | --- |
| `ember` | 1.05 × 1.35 × 0.95 | Pear furnace body, split flame prongs, dark face opening, tiny grounded feet; attack socket in face | 240 / 280 | 2 |
| `thorn` | 1.40 × 1.25 × 1.30 | Broad shield shell, three blunt ridge thorns, square muzzle, four short feet; shoulders read wider than head | 320 / 380 | 2 |
| `volt` | 1.80 × 1.10 × 1.15 | Hooked chevron wings, narrow body, fork tail; left/right wing hinges at body | 240 / 280 | 3 |
| `mire` | 1.35 × 1.10 × 1.40 | Low crescent foot, asymmetric hollow cup head and three unequal spouts; attack socket at largest spout | 300 / 360 | 2 |
| `fang` | 1.05 × 1.20 × 1.55 | Lean forward jackal stance, long wedge muzzle, paired lower fangs, readable rear legs; neck/jaw hinge | 340 / 420 | 3 |
| `moth` | 1.70 × 1.20 × 1.15 | Four rounded opaque lobes grouped into two hinged sides, narrow dark thorax, short streamers | 250 / 300 | 3 |
| `pyre` | 2.10 × 2.35 × 1.65 | Hollow upright furnace, paired shield shoulders, three crown vents, legs; ember cavity remains open | 750 / 900 | 3 |
| `storm` | 2.65 × 1.70 × 2.00 | Open S ribbon, fork frill, vessel body sections, split tail; real depth and negative space | 800 / 950 | 4 |
| `dusk` | 2.35 × 2.35 × 1.90 | Reared jackal with veiled shoulder wings and long hooked tail; readable muzzle under veil | 850 / 1000 | 4 |
| `solar` | 3.25 × 2.70 × 2.25 | Open sunwheel body, six swept rays/feathers, hanging paired vanes, exposed furnace; no opaque filled disc | 1250 / 1500 | 5 |
| `world` | 3.15 × 2.30 × 2.70 | Nearly closed serpent ring, visible central hole, thorn head crown and fanged jaw; coils remain separated | 1250 / 1500 | 5 |
| `eclipse` | 3.00 × 2.70 × 2.55 | Crescent predator with open moon gap, paired vessel horns and split hot core | 1250 / 1500 | 5 |
| `boss` | 4.20 × 4.60 × 3.40 | Asymmetric hollow bell, clapper, crooked legs, large bracer hands and broken arch shoulder | 1900 / 2400 | 5 |
| `keeper` | 1.35 × 2.10 × 1.00, excluding held lantern | Wide ivory mantle, split hem/feet, dark hood cavity, right hand/arm socket; no point cone body | 800 / 1100 | 4 |
| `lantern` | 0.65 × 0.92 × 0.57 | Caged light with four clear bars, handle loop, top/bottom brass cap, small core; open gaps | 250 / 350 | 2 |

The keeper holding the lantern may span ~2.0 units horizontally. The keeper/lantern size was increased 18% in the concept study after the first actual-camera image made the anchor too small; preserve the wider bright mantle and its dark central split. Keep its core centered; the offhand light deliberately identifies facing. A separate lantern GLB is used both at the hand and for the UI/loading/evolution motif; also include a positioned lantern in source preview assembly. Avoid duplicate lantern mesh embedded in the keeper export if the game will attach the separate GLB. Integration must recheck perceived contact because this visual size changes while the simulation's contact thresholds remain fixed.

One shared surface material and at most one glow material per asset. Per-asset GLB byte caps: bases 90 KB, tier 1 180 KB, tier 2 260 KB, keeper/lantern together 220 KB, boss 360 KB. These are uncompressed, texture-free geometry budgets; report any needed exception rather than hiding it. All GLBs together should remain below 3.5 MB before portraits. Portraits: 192×192 transparent PNG, cap 40 KB each; inspect their 48×48 downscaled appearance.

Runtime workload budget: 240 enemies, up to six companions, keeper, one boss, environment and effects. Largest base worst case 240×420 ≈101k triangles; allow another ~10k companions, 3.9k keeper/lantern/boss, 8k environment and ~20k transient effects. Target **≤150k visible triangles and ≤100 draw calls** at normal busy play. Budgets are hypotheses to be measured on the actual Intel/D3D11 browser; exported per-part costs determine feasibility. Base shared meshes must instance across hostiles and allies. No per-enemy material clone, texture or skeleton.

## Arena kit

All environment pieces use the same two or fewer surface materials with muted vertex palette. Grid 0.25 units. Ground attachments align to Y=0 in GLB. Coordinates below describe assembly by the game maker; the Blender maker exports reusable pieces plus a source demonstration of two joined rim segments and the arch assembly.

| ID | Dimensions / pivot | Construction / placement | Export cap |
| --- | --- | --- | --- |
| `arena_floor` | Radius 20.2, thickness 0.6; center/top Y=0 | Broad slate courses and sparse interrupted brass binding inlay; no raised obstacles, no visual clutter in center radius 12 | 2600 tris, 240 KB |
| `rim_segment` | 15° curved sector, inner radius 19.7, outer radius 21.1; rise ≤0.25 | Root at circle center for angular repeat; provide `socket_start` / `socket_end`; 24 repetitions, join without gaps. High edge begins outside walkable radius 19. | 140 tris, 25 KB |
| `bell_arch` | 6.2 × 5.8 × 1.6; ground midpoint | Broken asymmetrical stone arch with two piers, brass tie bands; place at (18.5,0,-12), yaw atan2(-18.5,12), facing inward; all tall geometry outside radius 20.5 | 900 tris, 110 KB |
| `hanging_bell` | 1.6 × 1.8 × 1.5; pivot at top suspension | Hollow split bronze bell; attach at arch's `socket_bell`; echoes boss cavity, lower detail | 450 tris, 60 KB |
| `shrine_plinth` | 2.4 × 1.25 × 1.8; ground center | Low stepped reliquary with recessed plaque; western landmark at (-22,0,0) | 260 tris, 35 KB |
| `votive` | 0.7 × 1.65 × 0.7; ground center | Tapered stone lantern niche with small warm core; three grouped near eastern boundary, not repeated around every angle | 180 tris, 30 KB |
| `rubble_cluster` | 2.0 × 0.35 × 1.1; ground center | Three purposeful chipped slabs; sparse, outside radius 20.5, no noisy pebble scatter | 120 tris, 20 KB |

Keep total visible kit below ~8k triangles through instancing and limited repetition. The floor itself is one mesh with compatible palette/material. Do not export a high-sided duplicated cylinder beneath an existing floor; game maker replaces the old blockout floor. Boundary kit never changes traversal or enemy spawn rules.

## Material and animation export

Use glTF-compatible Principled BSDF materials, opaque, roughness about 0.75–0.95, metallic 0–0.15 (up to 0.35 on small brass pieces). Bake broad color decisions to a vertex color attribute exported as `COLOR_0` or use equivalent compact compatible material assignments within the two-material cap. Verify vertex colors and base factors after loading; do not assume Blender viewport equals ACES output. A small emissive material is allowed for cores; avoid excessive emission that clips their shape. No texture maps are required for this style. If maps prove necessary, keep one shared 512² atlas and document its channels, color space and bytes before adding it.

**Exported animation clips: none required (`animations: []`).** This is intentional rigid instanced animation. Do not add an armature/mixer to every creature. Deliver neutral authored pose, named hinged parts and their pivots. Put the proposed motion specification in metadata: `idle` loop, `travel` loop, `attack` pulse, `windup` where relevant. These are game animation states, not claimed GLB clips.

Suggested visual ranges: base travel root bob ≤0.06 units; wing hinges flap ±18° (Volt faster than Moth), Mire body squash at most 5%, Fang head/torso lean up to 12° during the existing .7-second anticipation, then recoil after impact. Tier 1/2 gestures should breathe or open without solidly covering warning rings. Boss clapper/forearm motion can telegraph its existing attacks; no root displacement. Supply neutral pivot transforms and limits, not simulation code. If a rigid clip becomes necessary, agree it with the game maker and report its exact exported name/duration/channels; no silently introduced animation dependency.

## Shared runtime preview contract

The game maker will implement **`http://127.0.0.1:4190/asset-preview.html` during step 14** while the representative keeper/arch pair is modeled. It is not ready at the moment this brief is issued. Notify the caller when representative GLBs/manifest entries exist, then use this route when the game maker announces readiness. Do not build a separate incompatible renderer to claim runtime acceptance.

The route will use Three.js r186, the shared production GLTFLoader and the approved settings: camera (0,36,28) looking at origin, orthographic half-height 18 at 1280×720; ACESFilmic tone mapping, exposure 1.3, sRGB output, fog `#101C23` density .014; hemisphere `#C4E5ED`/`#3F3C37` intensity 2; key `#FFDBA5` intensity 3 at (-14,24,9); rim `#729FDB` intensity 2 at (10,12,-18). Use DPR 1 for matched captures, then verify regular capped DPR behavior later.

Visible controls: asset selector, game-scale/detail view, facing turn, mixed/busy lineup and portrait framing, with explicit load/error status. Read-only diagnostics expose ID, loaded path, bounds, triangles, mesh/material counts, texture bytes, socket locations and clip names. It must display missing/bad assets as errors rather than silently substitute a blockout. Game-distance views include keeper/ally scale references and representative warning circles; the busy view instances repeated supplied bases. This preview checks import and readability, not final gameplay balance or production frame-rate acceptance.

A representative asset passes handoff when it loads here without errors, is correctly oriented and sized, keeps its intended silhouette at game scale, preserves materials and socket/pivot locations, and meets measured export budgets. Both Blender and runtime images must be actually inspected before producing the rest of the set. The final integrated game's movement and hazards remain the ultimate readability check.

## Manifest schema and integration agreement

Write `public/models/manifest.json` with `schemaVersion: 1`, `blenderVersion`, `basis: {sourceUp:'Z', sourceForward:'-Y', runtimeUp:'Y', runtimeForward:'+Z', units:'game-unit'}`, and an `assets` array. Each asset entry includes:

```json
{
  "id": "ember",
  "file": "/models/ember.glb",
  "source": "assets/source/nightbind-creatures.blend",
  "root": "ember",
  "portrait": "/models/portraits/ember.png",
  "bounds": {"min": [-0.525, 0, -0.475], "max": [0.525, 1.35, 0.475]},
  "triangles": 0,
  "vertices": 0,
  "meshParts": [],
  "materials": [],
  "bytes": 0,
  "textures": [],
  "animations": [],
  "sockets": [],
  "motions": [],
  "sha256": "measured export digest"
}
```

The example bounds are a target, not measurements; all actual numeric costs/bounds must come from exported GLB inspection. `meshParts` entries name the node, parent, pivot/local transform and intended rigid motion if any; `sockets` name the empty node and local transform (translation/quaternion/scale). `motions` names the visual state, controlled nodes, axis, range and phase suggestion. Include `dependencies` if any resource is not embedded. Omit portrait for environment pieces; provide keeper/lantern and all thirteen monster portraits where requested (six bases, six evolved, boss).

The loader will preserve part-local transforms and build compatible instanced batches. It may bake static mesh transforms into geometry but must retain required hinge pivots and socket transforms. Game-owned pose uses entity ID/time, not a separate animation clock. The same asset serves hostile and ally; orbit, 0.85 ally scale, binding seal, contact shadow, attack origin and color-safe UI treatment are game-maker responsibilities. Geometry cannot alter capture range, contact threshold, attack range, damage or timing. Any apparent hitbox/readability mismatch is reported to the game maker for an affected play check.

## Final maker report

In `notes/assets.md`, give exact export commands, Blender/exporter version, source and exported file inventory, measured budgets, actual sockets/parts/clips, portrait mapping, representative source/runtime inspection findings, deviations, and unresolved issues. Include two joined kit pieces and game-scale mixed creatures in evidence. Do not label a Blender beauty render as proof of runtime correctness, or a static viewer as proof of busy gameplay performance.
