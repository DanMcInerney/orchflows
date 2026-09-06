---
name: blender-asset
description: Produce one post-core Blender asset batch with source, render, export, manifest, and runtime evidence.
disable-model-invocation: true
---

Require: accepted core `artifact:` identity, frozen gameplay baseline, approved
concept-art evidence, one bounded asset job, target workspace, and parent
frame journal.

Read the journal and open one job under the Blender-specific standard and
applied `blender-bpy` method:

    tickets.py do <run> --standard blender-game-asset --skill blender-bpy --parent <frame> --goal-file <asset-job-goal> --isolation required

The job fixes its source and input hashes, seed, units, axes, pivot, allowlists,
budgets, cameras, render/export settings, and expected outputs. One fresh
Blender process and directory preserve stdout, stderr, job, and partial output
inventory. A successful handoff contains the `.blend` source, rendered
previews, GLB export, asset manifest, hashes, zero-error Khronos validation,
and a pinned production `GLTFLoader` scale/material/animation/collider probe.

Have a separate judge assess the returned batch before integration:

    tickets.py judge <run> --standard browser-game-3d-asset --standard blender-game-asset --parent <frame> --artifacts <asset-artifact> --goal-file <asset-judge-goal> --isolation required

Failure promotes nothing and records the exact diagnosis. A gameplay-altering
scale, collider, animation, timing, camera, or readability change invalidates
the affected core evidence and returns that seam to the gameplay gate.
Missing Blender or image capability records `unverified` and parks only
dependent asset work while preserving viable core evidence.

Never install system software, purchase or accept unapproved assets, fabricate
renders or manifests, overwrite a source authority, or call cosmetic output a
runtime-qualified asset.

Return: completed ticket carrying `artifact:` for the asset batch, source/render
and export identities, manifest and runtime evidence, independent findings,
invalidation set, and declared gaps.
