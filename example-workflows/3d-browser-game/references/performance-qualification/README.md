# Performance qualification fixtures

These small records exercise the native frame model at its seams. `continuous-animation.json`
is the positive animation case. `deliberate-stall.json` and
`canvas-stall-other-layer.json` keep callback or other-layer activity alive while
the game canvas stops changing. `static-idle.json` demonstrates the static path,
which reports frame counts without a 59 Hz claim.

Live cells use the same model with a host-owned render-callback observer. The
observer runs after each application `requestAnimationFrame` callback and
queues a frozen explicit region of the current default WebGL2 drawing buffer in
a pixel-pack buffer. A `fenceSync` is polled with a zero timeout on later
callbacks; completed bytes are copied with `getBufferSubData`, so the observer
never waits for the GPU on the application callback. It leaves
`preserveDrawingBuffer:false` unchanged. Every observer run activates its
headed page with `page.bringToFront()` and records browser-observable
visibility, hidden, document-focus, focus/blur, and pagehide state at measured
boundaries. A missing monitor, hidden/unfocused boundary, or hidden/blur/pagehide
transition makes the result `performance: unverified`; tab activation is not an
OS-window activation claim. A cell's
`sampling` declaration is either in drawing-buffer pixels or CSS viewport
pixels; the result records the resolved contained region, drawing-buffer size,
viewport size, DPR, bytes per sample, and every sample duration. Native
qualification joins those samples to one compositor frame by timestamp and
marks at most one native frame per observed region change; sparse samples never
upgrade intervening frames.

The checked-in cells are portable templates: `server.cwd` is resolved relative
to the cell file's directory, and a live run must materialize its current full
Git artifact commit and actual browser driver before collection. A retained
result is admitted only when those identities are real and the result is
recomputed from its stored trace.

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

`threejs-moving-mesh.html` is the noncentral positive fixture. Its ordinary
Three.js scene renders a box whose x position and rotation change in the right
side of the canvas while the center remains unchanged. Its paired cell freezes
the viewport region `{x:384,y:96,width:160,height:168}` so pixel changes are
observed over the mesh without treating a whole-canvas clear as moving-mesh
evidence.

The collector takes the cell's contained region after each instrumented
callback and records callback origin, completion status, queue/copy timing, and
sample duration. A bounded PBO pool records every queue overflow, readback
error, context loss, and pending item observed during cleanup. Small regions
bound observation work; the region can be placed over a declared moving object
whose motion does not cross the canvas center. A region outside the actual
drawing buffer is rejected before qualification, so a static target canvas
with an animated other DOM layer remains a negative result. WebGL1 or a browser
without the required WebGL2 PBO/fence APIs is unverified rather than silently
falling back to synchronous readback.

`threejs-stalled-canvas-other-layer.html` is a live negative probe. Its default
Three.js canvas is cleared once and left unchanged while a separate promoted
DOM layer moves from an active `requestAnimationFrame` callback. The repaired
collector recorded `120` callbacks and `120` samples with one canvas hash,
then rejected the result with `missing-canvas-attribution` and
`canvas-frame-floor` (`C=0/2`). A live run still needs a headed browser and
records the exact browser, backend, viewport, DPR, seed, and commit in its cell.

Diagnostic cells keep their mode in the cell, measurement, trace metadata, and
canvas-instrumentation record. `observer-only` uses the existing bootstrap with
both tracing and readback disabled; `trace-only` and `readback-only` disable
only their named path. `bare-counter` is a minimally observed baseline: after
the application is ready it attaches one independent rAF timestamp counter,
retains `performance.timeOrigin`, page and wall clock markers, and foreground
lifecycle records, and performs no init script, CDP session, WebGL context
acquisition, GL wrapping, or readback. Bare and observer-only cells are
diagnostics and always fail closed for production qualification.
