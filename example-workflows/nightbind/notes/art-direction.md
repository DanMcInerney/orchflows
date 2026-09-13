# Nightbind art direction — the drowned bell garden

The keeper stands in the last dry circle of a sunken bell court. Its creatures look like living reliquaries: glazed bone, burned wood, fungal vessels, worn brass and small lights protected inside dark cavities. The mood is ominous and intimate, with a warm lantern as the visual anchor. Earned transformations turn those modest shapes into heraldic monsters with unmistakable new silhouettes.

This is a stylized, deliberately modeled low-poly direction. Broad curved or planar masses and a few purposeful cuts should survive the actual camera. Small bevels and surface chips support form; they do not substitute for it. Avoid smooth generic balls with accessory spikes, same-body recolors, and inflation as an evolution design.

## Visual hierarchy

1. **Keeper:** the brightest stable ivory mass, asymmetric amber lantern at the right hand, dark hood cavity. A split cloak hem and small visible feet show facing and locomotion. The lantern's cage and handle read as a tool, distinct from the creature body language.
2. **Threat instructions:** poison perimeter, charge direction and boss warning remain readable on dark ground. Enemy windup changes posture; warning shapes carry the action. Highlights must not become a continuous wash across the floor.
3. **Monsters:** one defining contour and one broad role color area per species. Preserve dark separations between appendages. Moth's rounded four lobes and Voltwing's broken chevron must be distinguishable without color.
4. **Allies:** retain the captured enemy's actual shape and role color. A pale mint ground seal and a modest binding accent identify allegiance. Do not recolor all allied bodies green, which would erase species identity.
5. **Environment:** desaturated blue-green slate, worn curved brass channels and three deliberate landmarks outside movement. Background contrast stays below actors and warnings.

At 1280×720 the approved camera has an orthographic half-height of 18, hence a full vertical frustum of 36 units and 20 horizontal pixels per world unit. Base bodies occupy roughly 21–36 pixels horizontally before facing rotation; allied bases use the existing 0.85 visual scale. Actual height and depth project together from the elevated camera, so the top silhouette matters as much as a front portrait. At least two-thirds of identifying visual information should come from masses, posture and negative space, rather than eye detail.

## Color and surface language

| Use | sRGB swatches | Surface / value treatment |
| --- | --- | --- |
| Night ground / crevices | `#101C23`, `#1C343D`, `#283E42` | Matte, dark, quiet; a few broad facet variations |
| Glazed stone / keeper hood | `#3F696B`, `#435C5D` | Muted teal, rough glaze, pale edges used sparingly |
| Bone / cloak | `#D9D3B8`, `#EEE2BB` | Warm matte ivory; brightest large area reserved for keeper |
| Brass / lantern structure | `#9B7852` | Tarnished, subdued, broad geometry highlights; no mirror finish |
| Lantern / earned dawn | `#F1CF82`, `#F2D494` | Small emissive cores, large non-emissive forms; bloom is optional later, not required for legibility |
| Ember / Fang | `#E69A55`, `#C48371` | Orange furnace versus warm clay jaw; distinct silhouettes and darker Fang back |
| Thorn / Moth | `#9DAB72`, `#D4C58D` | Thorn moss shield versus pale ochre wing veils |
| Volt / Mire | `#75BFD7`, `#AC8CBB` | Cool cyan edge/frill versus muted lilac vessels |
| Ally seal / boss menace | `#D7FCD4`, `#AD95B2` | Small mint binding mark; oxidized mauve boss with dark open bell cavity |

Base materials are opaque, with vertex-colored broad areas. No alpha-blended wings. Moth wings are opaque lobes with modeled gaps; this avoids overlapping translucent sheets in a horde. The palette should look like painted/glazed objects under the game's ACES color pipeline, not neon plastic. One common rough surface material plus a small emissive accent material is the default. No procedural Blender-only shader dependencies.

## Designed families and evolution inheritance

| Creature | Primary identity | Inheritance / change |
| --- | --- | --- |
| Emberling | Coal-black pear body, warm split furnace face, two irregular upward flame prongs, tiny legs | Compact vertical flame; orange is concentrated around the cavity |
| Thornback | Low broad shield carapace, square blunt snout, squat feet, three thick ivory ridge thorns | Its shield width and planted posture express ward/knockback |
| Voltwing | Sharp boomerang wings with two hooked tips, narrow dart body and fork tail | Angular swept flight silhouette; avoid a four-lobed butterfly |
| Mireling | Low crescent snail-like foot, large tilted vessel head and three unequal open spouts | Asymmetric rear-heavy form and cups communicate poison emission |
| Fangling | Lean jackal quadruped, long wedge muzzle, high shoulders, low haunches and two large lower fangs | Forward-loaded stance makes its charge direction readable |
| Mourning Moth | Four broad rounded veil lobes, narrow thorax and two drooping tail streamers | Rounded lantern-petal pattern with a dark diamond at the wing center |
| Pyre Warden | Upright hollow furnace torso, two shield shoulders, planted short legs and vent crown | Ember furnace enclosed by Thorn armor; changed bipedal architecture, not a larger Thornback |
| Storm Serpent | Open S-shaped body, Volt forked head frill, Mire vessel segments and split trailing fin | Long flowing negative space replaces both base body plans |
| Dusk Reaper | Reared jackal chest and long muzzle under two sweeping split veil wings, scythe-like tail | Fang stance and Moth veil combine into a tall hunting apparition |
| Solar Seraph | Open sunwheel torso, six swept feather/shield rays, small central furnace and long paired lower vanes | Pyre furnace opens outward; Volt angular rays and Moth rounded veil ends. Preserve open gaps so it does not become a solid disc over warnings. |
| Worldcoil | A near-closed coiled serpent ring, thorn crown over a forward fanged head, visible hole through the center | Storm's ribbon becomes a ring; Thorn crown and Fang jaw clearly persist. Ring gap/open center matter at game scale. |
| Eclipse Sovereign | Crescent-backed lunging predator, hollow moon between shoulder arch and tail, paired vessel horns | Dusk predator posture plus Ember split cavity and Mire vessels; new crescent form, not a bigger wing sheet |
| Bellkeeper | Heavy hollow bell body on two crooked supports, one broken shoulder arch, suspended visible clapper, oversized bracer hands | Architecture and monster meet. Tall asymmetric hollow form differs from every companion; the opening frames a threatening core. |

Ascensions may carry a few larger gesture shapes; give each two or three strong landmarks rather than many tiny decorations. Tier dimensions increase moderately. Ability coverage and the transformation effect provide much of the spectacle; do not hide the keeper under a giant opaque monster.

## Keeper and place

The concept study's keeper uses an ivory shoulder mantle over a midnight teal hood, a dark face gap and two cloak panels. The cage lantern sits to the right, exposing its amber light through structural openings. Final modeling should improve the hand/handle connection, articulate a clearer forward brim and keep the face cavity darker than the light. The silhouette needs a wide upper mantle and narrower feet, not a single cone.

The arena is a circular dry bell court, radius 20.2. Broad concentric slate courses and thin interrupted brass channels imply an old binding ritual. A broken bell arch at northeast, a low covered shrine west, and a three-part votive arrangement east give spatial identity. All tall pieces sit outside radius 20.5; the playable circle remains open. Low engraved/inlaid geometry can sit inside but should not look like collision. No forest of pillars or random debris field.

Environment kit: one broad floor treatment, one curved rim segment repeated around the edge, a joined pillar/arch pair, a broken bell, a low shrine plinth, a small votive and a limited rubble cluster. Repeat geometry, rotate for variation and vary only a few palette values. A boundary joint should be deliberately shown in the Blender preview. The floor and rim should still read as one authored place when the horde is cleared after ascension.

## Motion, effects and UI direction

Animation is game-owned rigid part motion. No individual skeleton/mixer for hundreds of enemies. The modeler supplies purposeful pivots and attack sockets; the game supplies travel bob, wing flap, jaw/neck gesture and the existing windup. Root motion never moves the simulation. Fang's .7-second warning and boss's 1.6-second zone warning remain authoritative. Attacks may recoil on the damage tick; animation must not shift damage to a later apparent impact.

Source ability light and trails from the acting companion's socket, then show the existing target/radius result. An outward visual connection can explain a keeper-centered ability without changing its damage center. The lantern closes around a small colored spark during capture; evolution briefly folds ingredient-colored arcs into the new form, then reveals the silhouette. Keep the keeper and ground warnings visible during both.

Portraits are consistent three-quarter renders of the actual exported models: dark transparent surround, lit upper-left, readable silhouette at 48 pixels. Use them in capture choices, Field guide and squad slots with the same species name/color. A portrait must never present a different design from the arena. Retain text roles and disabled-state explanations. During later UI work, add a visible capture-reach cue while planning, addressing CORE-O2 without extending the radius or slowing enemy death.

Audio direction for later implementation: small resonant lantern latch, dry ceramic foot/tap textures, short pitched role accents, a low bell at the boss and a two-stage harmonic bloom on evolution. Avoid continuous dense attack chatter. Provide mute/volume and keep every critical cue visual as well. No audio assets are requested from this Blender assignment.

## Bounded study and inspection

Study source: `notes/art-study/index.html` and `study.js`, served on development at `/notes/art-study/index.html`. It contains one rough 3D keeper/lantern, a representative floor/rim/arch/shrine treatment, and authored flat silhouette proposals for the creature lineages. It is art direction, not an export scaffold or final asset set.

The **Gameplay camera** view matches core camera/lighting/color settings. **Keeper detail** is an enlarged inspection view; **Busy arrangement** places 90 flat base-silhouette billboards at declared widths among retained ground warnings. **Lineage plate** compares black silhouettes without color. The billboard crowd tests proposed size/contour separation only; it cannot establish 3D facing, GLB material quality, animation or occlusion. Actual export inspection at the forthcoming asset preview and integrated game remains required.

I inspected the actual captured images at 1280×720. The caller operated its supported browser because the maker's previous browser connection had disconnected and discovery remained empty; I inspected the saved image outputs locally. This is a transparent division of operation and visual judgment, not a substitute render claim.

The first busy view was empty despite an observable count of 90: SVG textures without explicit raster dimensions did not display. That failed capture is retained as `evidence/art-direction/busy-arrangement.png`. Adding SVG width/height and tighter view bounds produced visible creatures on recapture; it is the v2 view that supports the contour check.

The first keeper was too slight at the fixed camera, so the concept's body/lantern assembly was increased 18%. The v2 measured assembly bounds are 2.0396 × 2.1122 × 1.1410 units; the corresponding final keeper/lantern targets are in the brief. Its ivory split mantle now anchors the center among the colored shapes, though face/cage detail still belongs in close portraits. The first northern arch was clipped by the camera; moving it to (18.5,0,-12), facing inward, made the whole landmark visible without entering traversal. Thorn's first sharp crown also resembled Ember too closely, so it became a broader shield with three blunt crenellations.

In the successful 90-silhouette view, the narrow flame, broad shield, angled wings, three-cup Mire, stretched Fang and rounded Moth separate by contour. The poison/warning rings remain visible through this arrangement. This is a useful concept-scale check; it does not prove behavior readability or full 3D occlusion. The black lineup shows materially different evolved forms, especially the upright Pyre, open S Storm, closed Worldcoil and crescent Eclipse. Dusk needs its jackal muzzle and veil separation protected during 3D modeling, because its small front silhouette can read as a generic upright figure.

Inspected outputs: `evidence/art-direction/gameplay-camera-v2.png`, `keeper-detail-v2.png`, `busy-arrangement-v2.png`, `lineage-plate-v2.png`. The four initial images remain alongside them. The independent asset maker should use the drawings as shape targets, improve their three-dimensional construction, and preserve the operational contract in `asset-brief.md`.
