# Performance qualification fixtures

These small records exercise the native frame model at its seams. `continuous-animation.json`
is the positive animation case. `deliberate-stall.json` and
`canvas-stall-other-layer.json` keep callback or other-layer activity alive while
the game canvas stops changing. `static-idle.json` demonstrates the static path,
which reports frame counts without a 59 Hz claim.

Live cells use the same model with a host-owned render-callback observer. The
observer runs after each application `requestAnimationFrame` callback, samples
a frozen explicit region of the current WebGL drawing buffer with read-only
`readPixels`, and leaves `preserveDrawingBuffer:false` unchanged. A cell's
`sampling` declaration is either in drawing-buffer pixels or CSS viewport
pixels; the result records the resolved contained region, drawing-buffer size,
viewport size, DPR, bytes per sample, and every sample duration. Native
qualification joins those samples to one compositor frame by timestamp and
marks at most one native frame per observed region change; sparse samples never
upgrade intervening frames.

Every live result records `cell.scenario_id` and a top-level `measurement`:

- `warmup` is the elapsed, callback-observed warm-up interval;
- `control` is a no-readback callback interval used as the comparison baseline;
- `instrumented` records callback/readback observations in the marked window;
- `perturbation` records the measured `control-vs-instrumented` delta.
- `sampling` records the explicit frozen coverage and its drawing-buffer/
  viewport/DPR resolution;
- `lifecycle` records the configured URL, seed, observed startup, measured
  control phase, and the observed page reload before the instrumented phase.

A live cell pins a comparable pair by setting `control_duration_ms` equal to
`duration_ms` (or `duration_seconds` when `duration_ms` is omitted), and pins
the same `scenario_id`, seed, URL, viewport, DPR, and sampling region in both
phases. Optional `setup_commands` are a frozen sequence of ordinary `key`,
`pointer`, and `wait` commands used to leave a menu or enter the declared
scenario; the collector records each applied command and a read-only state
observation. The collector observes startup and warm-up, measures control with
readback disabled, reloads the configured URL, reapplies the same setup and
warm-up, then measures the same duration with readback enabled. A caller flag
or repeated scenario label is not treated as lifecycle evidence.

The positive browser fixture source is `threejs-default-renderer.html`. It pins
Three.js `0.185.1` and constructs an ordinary `WebGLRenderer` without a
`preserveDrawingBuffer` override. It alternates high-contrast clears on each
animation callback so a timestamp alias cannot manufacture a false frame-floor
failure. The live positive probe measured `N=600`, `C=600`, `callbacks=600`,
`preserve_drawing_buffer=false`, and zero readback errors over 10 seconds.

The collector takes the cell's contained region after each instrumented
callback and records the sample duration. Small regions bound observation work;
the region can be placed over a declared moving object whose motion does not
cross the canvas center. A region outside the actual drawing buffer is rejected
before qualification, so a static target canvas with an animated other DOM
layer remains a negative result.

`threejs-stalled-canvas-other-layer.html` is a live negative probe. Its default
Three.js canvas is cleared once and left unchanged while a separate promoted
DOM layer moves from an active `requestAnimationFrame` callback. The repaired
collector recorded `120` callbacks and `120` samples with one canvas hash,
then rejected the result with `missing-canvas-attribution` and
`canvas-frame-floor` (`C=0/2`). A live run still needs a headed browser and
records the exact browser, backend, viewport, DPR, seed, and commit in its cell.
