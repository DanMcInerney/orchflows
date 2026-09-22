# Blender production and handoff

Record Blender/exporter versions and inspect available operators/settings. Use matching official documentation for release-sensitive options. The [glTF manual](https://docs.blender.org/manual/en/3.6/addons/import_export/scene_gltf2.html) explains portable mesh/material/animation channels. Newer action slots affect clip grouping; verify exported clips instead of copying old NLA naming recipes. [Blender 5.2 exporter](https://docs.blender.org/manual/en/5.2/addons/scene_gltf2.html).

## Asset brief

| Field | Required decision |
| --- | --- |
| Identity/role | Stable ID; hero, interactive, hazard, landmark or modular piece |
| Readability | Silhouette, color/value group, camera distance, reference views |
| Scale/assembly | Units, dimensions, origin/pivot, forward/up, modular grid, sockets |
| Gameplay fit | Collider dimensions/owner, visual extent, aim/interaction point |
| Animation | Clip names, loops, duration, action/impact moments, root-motion owner |
| Materials | Palette, surface response, resolution/texel density, channels |
| Budget | Exported triangles, material slots, texture sizes, bytes, simultaneous instances |
| Delivery | Source, textures, scripts/settings, GLB, inspected views, metadata paths |

Budget by asset class and target scene; repeated props and heroes differ. Record exceptions and measure runtime costs.

## Model and develop the look

1. Compare primary silhouette/proportion options in front, side, three-quarter and gameplay views before detail.
2. Add secondary shapes/detail for interaction, motion and identity. Test modular grid, snap points and seams with joined pieces.
3. Clean visible/deforming topology and normals. Choose geometry, baked detail or materials by camera needs; preserve useful editable high-detail/procedural sources.
4. For textures, use consistent texel density, focal-surface seam placement and mipmap padding; avoid needless unique materials. Untextured stylization needs palette/shading tests, not unused UV work.
5. Use glTF-compatible materials; bake unsupported procedural detail. Inspect seams, tangent normals and roughness in game-like light. Triangulation, hard edges and UV seams can increase vertex counts: runtime exports own budgets.
6. Rig/animate only when needed. Inspect extreme deformation, readable action, contact, loops and event timing. Bake unsupported constraints/simulations. Verify named clips in GLB; Blender actions alone prove no export.

Preserve working rigged sources; do not apply destructive transforms without checking animation. Correct export-space transforms deliberately.

## Export and inspect

Save `.blend` with packed/included resources. Explicitly select exports to exclude unintended cameras, lights and collision proxies. Verify Z-up to Y-up conversion and game forward direction without compensating twice.

For repeatable production, use a project-owned script, e.g. `blender --background --python <job.py> -- <project arguments>`, with discovered executable, isolated source/output paths, explicit selection, deterministic names and clear failures. Save and inspect source contact renders; headless completion proves no visual quality.

Validate GLB structure when a validator is available, then inspect through the game's actual loader/settings. Check bounds, transforms, material slots, texture resolution, transparency and clip names/durations. Inspect idle/action poses at gameplay distance in normal and busy lighting. Deliver filenames/IDs, measured costs, dependencies, source/export commands and deviations; source images cannot replace runtime inspection.

Use a project-local neutral preview for early work; integrated camera/lighting are final. Continue suitable asset makers for production feedback or a caller-allocated repair pass; add no hidden review loop.
