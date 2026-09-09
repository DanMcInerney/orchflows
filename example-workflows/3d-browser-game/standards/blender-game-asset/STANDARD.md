---
name: blender-game-asset
description: Stamp when Blender-specific source, deterministic jobs, renders, exports, and loader checks are judged.
narrows: browser-game-3d-asset
adapter: git
---

Blender work tightens the 3D asset evidence around one job and one fresh
process. The job fixes mode, input hashes, seed, units, axes, pivot,
allowlists, budgets, cameras, render settings, export settings, and expected
outputs. A `.blend` remains source authority; the GLB is runtime delivery.

The job record preserves Blender executable identity and version, script and
package identities, stdout, stderr, exit code, timeout, and partial-output
inventory. Promotion evidence shows a contained nonempty output directory,
structural inspection, preview coverage, hashes, zero-error Khronos
validation, and the target production `GLTFLoader` reading for scale,
materials, animation, and colliders. Rendered views expose clipping, missing
faces, normals, unapplied scale, unexpected animation, and camera-distance
failures.

The review bar includes deterministic rerun inputs, source and export
provenance, transform correctness, mesh and material budgets, intentional
modifiers, naming, animation timing, collider placement, and safe failure
preservation. A process loss, digest mismatch, stale output, or partial
promotion leaves the asset unverified and does not create a runtime claim.
