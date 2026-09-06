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
`preserveDrawingBuffer` override. It alternates high-contrast clears on each
animation callback so a timestamp alias cannot manufacture a false frame-floor
failure. The live positive probe measured `N=600`, `C=600`, `callbacks=600`,
`preserve_drawing_buffer=false`, and zero readback errors over 10 seconds.

The collector takes one central `1x1` `webgl.readPixels` sample after each
instrumented callback and records the sample duration. This keeps the same
read-only default-buffer seam while bounding observation work; the 10-second
probe's maximum sample duration was `5.5 ms` (p99 `4.8 ms`).

`threejs-stalled-canvas-other-layer.html` is a live negative probe. Its default
Three.js canvas is cleared once and left unchanged while a separate promoted
DOM layer moves from an active `requestAnimationFrame` callback. The repaired
collector recorded `120` callbacks and `120` samples with one canvas hash,
then rejected the result with `missing-canvas-attribution` and
`canvas-frame-floor` (`C=0/2`). A live run still needs a headed browser and
records the exact browser, backend, viewport, DPR, seed, and commit in its cell.
