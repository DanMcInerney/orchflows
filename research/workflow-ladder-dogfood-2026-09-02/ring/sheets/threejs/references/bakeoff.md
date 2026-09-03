# The engine bake-off, and what it measured

Source: run `20260902T063434Z` in `C:\Users\danhm\tools\vampire-fps`, read at
2026-09-03 from `program/checkpoints/checkpoint-2.findings.json` and
`bench/README.md` in that workspace.

## The cell

One synthetic first-person scene, one Chromium build, one GPU, pinned
candidate versions, vsync and the frame-rate limit disabled. `bench/README.md`
states the boundary itself: "A software-rendered cell is recorded as such and
is not transferable." Every figure below is that cell's and not the shipped
game's.

## Measured (checkpoint-2.findings.json)

- WebGL2 against WebGPU, p95 at n=4000, per family: babylon 0.849 against
  1.172 ms; playcanvas 0.739 against 2.201; three.js instanced 0.788 against
  3.664 (4.65x); three.js unbatched 3.709 against 35.263 (9.51x). Every
  WebGPU arm is slower than its WebGL2 sibling with no overlap.
- WebGPU bundles cost 74–108 KB more gzipped than their WebGL2 siblings.
- On WebGL2 with instancing the four engine families are mutually
  indistinguishable at n=4000: five pairs overlap at 95% confidence. The
  evidence "clears all four under the delegated budgets and ranks none of
  them."
- What the evidence excludes outright: "three.js without instancing at genre
  entity counts (2x-p95 N = 1000 on WebGL2, 500 on WebGPU, one draw call per
  entity), and three.js unbatched on WebGPU above n=2000".

## What this does not settle

GPU time per frame was not measured (`bench/README.md`: "no timer-query path
spans all four candidates"). Physics was never measured at all. A claim about
either is not this evidence's.
