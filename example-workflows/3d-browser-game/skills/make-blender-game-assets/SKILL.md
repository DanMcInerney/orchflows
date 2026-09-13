---
name: make-blender-game-assets
description: Create original Blender game assets with editable sources, GLB exports and inspection through a game's Three.js loader using one maker.
---

Reuse or establish [library context](../../references/library-context.md). Declare one maker and no reviewer. Resolve the art brief, gameplay camera, asset scope, runtime preview/loader, budgets and owned output directory using the [asset contract](../../references/blender.md). For a standalone asset request, supply a small project-local Three.js preview if the game is unavailable; identify final integration as unverified.

Invoke `orchflows:orch-work` once with resolved Make guidance, the asset contract, actual game baseline and relevant source assets. Give the child this staged assignment, working without children:

1. Inspect Blender/export capabilities and the brief. Plan the asset family, shape language, modular relationships and budget allocation. Resolve unspecified art choices; report a gap if an essential gameplay contract is absent.
2. Create silhouette/proportion blockouts for the key asset and a representative environment piece when in scope. Inspect orthographic/three-quarter and gameplay-camera renders. Choose and refine the forms before fine detail.
3. Complete those representative models, materials, necessary UVs/bakes and animations. Save editable sources and export GLB with explicit object/clip selection. Inspect through the game loader/preview at gameplay scale and communicate any contract conflict before multiplying it through the asset set.
4. Build the remaining set under the proven style/export settings. Follow the Blender reference for topology, material/texture and animation decisions; do not add unused rigging or texture work.
5. Inspect exports structurally and visually, including required clips. Check bounds, pivots/sockets, texture dependencies, collider fit and measured costs. Supply game-camera views alongside source contact views. Report what still needs integrated play verification.
6. Return `.blend`, GLB, dependent assets, scripts/export settings, asset metadata, inspected views, reproduction commands and unresolved deviations.

Use a separate asset directory so code/content work can continue without conflicts. The caller integrates exports and checks actual gameplay. Return the worker handle and expected output path immediately when the caller is gathering parallel work; otherwise await and return the actual result. Continue this same maker for production feedback or a caller-allocated repair pass; no extra review or unbounded remake loop is implied.
