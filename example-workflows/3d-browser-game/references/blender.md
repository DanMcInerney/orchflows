# Blender production and handoff

Use for art direction, Blender making and Three.js integration. Record the actual Blender/exporter version and inspect its available operators/settings; exporters change between releases. The [official glTF manual](https://docs.blender.org/manual/en/3.6/addons/import_export/scene_gltf2.html) explains the portable mesh/material/animation model; use documentation matching the installed release for exact options. In newer Blender versions, action slots affect animation export grouping, so verify actual exported clips rather than copying an old NLA naming recipe. [Blender 5.2 exporter documentation](https://docs.blender.org/manual/id/5.2/addons/scene_gltf2.html)

## Asset brief

One compact table can carry the contract:

| Field | Decision needed before production |
| --- | --- |
| Identity and role | Stable asset ID; hero, interactive object, hazard, landmark or modular piece |
| Readability | Silhouette, color/value group, intended camera distance and reference views |
| Scale and assembly | Units, dimensions, origin/pivot, forward/up convention, modular grid and sockets |
| Gameplay fit | Collider dimensions, collision owner, allowed visual extent, aim/interaction point |
| Animation | Clip names, loops, duration, action/impact moments, root-motion ownership |
| Material plan | Palette, surface response, texture resolution/texel density and needed channels |
| Budget | Approximate exported triangles, material slots, texture sizes, file bytes and simultaneous instances |
| Deliverables | Source, textures, scripts/settings, GLB, inspection views and metadata paths |

Budgets are per asset class and target scene, not arbitrary universal polygon limits. Mark intentional exceptions and measure them in runtime. A frequently repeated prop needs a different budget from the hero.

## Modeling and look development

1. Block out the primary masses and compare distinct silhouette/proportion options. Inspect front/side/three-quarter views and the gameplay view before detail.
2. Build secondary shapes and purposeful detail around interaction, motion and visual identity. Establish a modular kit's grid, snap points and seam behavior with two joined pieces.
3. Clean topology/normals where visible or needed for deformation. Decide what should be geometry, baked detail or a material change based on the camera. Preserve the editable high-detail/procedural source where useful.
4. Prepare UVs and consistent texel density if using textures. Avoid seams at focal surfaces. Use padding suitable for mipmaps and avoid unnecessary unique materials. For untextured stylized assets, test the palette and shading instead of inventing unused UV work.
5. Use a glTF-compatible material design. Bake procedural detail to supported maps when needed; inspect baked seams, tangent-space normals and roughness under game-like light. Exported triangulation, hard edges and UV seams may increase vertex count. The runtime export, rather than Blender's viewport statistics, is the budget authority.
6. Rig and animate only assets whose role needs it. Check deformation in extreme poses, action readability, contact, loop transitions and agreed event timing. Bake constraints/simulations into supported animation data when necessary. Verify named clips in the exported GLB; a working Blender action does not prove it was exported.

These glTF limitations and material/animation channels are described in the [Blender glTF manual](https://docs.blender.org/manual/en/3.6/addons/import_export/scene_gltf2.html). Do not apply transforms destructively to an already rigged asset without checking animation; preserve a working source and fix export-space transforms deliberately.

## Export and inspect

Save `.blend` and pack or include referenced resources. Make export selection explicit so test cameras, lights and collision proxies do not enter the visual scene unintentionally. Confirm how Blender's Z-up source is converted to glTF's Y-up output and test forward direction in the game; avoid compensating twice.

For repeatable authoring/export use a project-owned Blender Python script invoked by the discovered executable, for example `blender --background --python <job.py> -- <project arguments>`. Use an isolated source/output directory, explicit selection and paths, deterministic naming and clear failures. A headless script is an authoring method, not evidence that the art looks good. Save source and render contact views that the maker actually inspects.

Inspect the GLB structurally with a glTF validator when available, then load it using the game's actual Three.js loader/settings. Check bounds, transforms, material slots, texture resolution, transparency and clip names/durations. Inspect idle and action poses at gameplay distance in both normal and busy lighting. Give the game maker exported filenames, IDs, measured costs, dependencies, source/export commands and any deviations from the brief. An image of the source cannot substitute for this runtime check.

Use a neutral asset preview scene in the project for early look development; the integrated game's camera and lighting are the final reference. If asset quality requires changes, continue the same asset maker within the production work or the caller's allocated repair pass. Do not create a hidden asset review loop.
