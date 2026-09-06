---
name: blender-bpy
description: Author, inspect, render, and export one hash-bound Blender asset in a disposable worker process.
---

Require: a closed `blender-job` document with a unique job id, a pinned
artifact/source identity, seed, scene units/axes/origin, input and output
allowlists, budgets, camera previews, and expected output paths. `generate`
and `edit` jobs also require an authoring Python module and its SHA-256 digest;
the module entrypoint receives a context containing `bpy`, `bmesh`, the job,
the job root, and the reproducible seed. Edited jobs identify their existing
`.blend` source and digest. Every path is relative to the fresh job directory.

Use `bpy.data` and BMesh for deterministic scene construction and edits.
Operators are limited to opening a source, saving a `.blend`, rendering, and
exporting glTF; before each operator, assert the scene, view layer, active
camera or frame, mode/selection when relevant, engine, device, and output
path. Check the operator return set contains `FINISHED`. Never execute Python
received as an expression, load an unbound module, or open a socket/daemon.

The worker writes structural inspection covering object names/types, external
references, transforms/bounds, mesh geometry/UVs/normals, materials, armatures,
clips/poses, and the declared budgets. It renders every gameplay and turntable
camera, saves the source `.blend`, exports runtime `.glb` with the fixed up
axis, and writes an asset manifest binding source, export, inspection, and
preview hashes. Worker output is `complete` only when all declared evidence
exists and is non-empty; exceptions write a failure result and preserve the
traceback for the runner.

Return: one worker result with the job digest echoed, source/export hashes,
output inventory, inspection and preview identities, and any validation
records supplied for the exact exported hash. The host runner owns timeout,
process-tree cleanup, pinned Khronos validation, the production GLTFLoader
probe, and promotion. Missing or mismatched evidence remains unverified and
never becomes a runtime asset.
