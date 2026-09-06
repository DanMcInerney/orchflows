# Performance qualification fixtures

These small records exercise the native frame model at its seams. `continuous-animation.json`
is the positive animation case. `deliberate-stall.json` and
`canvas-stall-other-layer.json` keep callback or other-layer activity alive while
the game canvas stops changing. `static-idle.json` demonstrates the static path,
which reports frame counts without a 59 Hz claim.

Live cells use the same model with a host-owned render-callback observer. The
observer runs after each application `requestAnimationFrame` callback, samples
the current WebGL drawing buffer with read-only `readPixels`, and leaves
`preserveDrawingBuffer:false` unchanged. Native qualification joins those
samples to one compositor frame by timestamp and marks at most one native frame
per observed pixel change; sparse samples never upgrade intervening frames.

Every live result records `cell.scenario_id` and a top-level `measurement`:

- `warmup` is the elapsed, callback-observed warm-up interval;
- `control` is a no-readback callback interval used as the comparison baseline;
- `instrumented` records callback/readback observations in the marked window;
- `perturbation` records the measured `control-vs-instrumented` delta.

The positive browser fixture source is `threejs-default-renderer.html`. It pins
Three.js `0.185.1` and constructs an ordinary `WebGLRenderer` without a
`preserveDrawingBuffer` override. It is a minimal observation target, not a
game acceptance sample. A live run still needs a headed browser and records
the exact browser, backend, viewport, DPR, seed, and commit in its cell.
