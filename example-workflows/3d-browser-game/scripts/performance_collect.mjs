/**
 * Collect one performance cell. Fixture mode is intentionally explicit and
 * retains the same raw trace/completion path as live mode, making a fixture a
 * qualification probe rather than a claimed measurement.
 */
import { spawn } from "node:child_process";
import { resolve, dirname } from "node:path";
import { pathToFileURL } from "node:url";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import {
  EXIT, capabilityError, inputError, makeHeader, nowIso, parseArgs,
  readJson, resultFromError, sha256, timeoutError, writeJsonAtomic, evidenceError,
} from "./_common.mjs";
import { collectCDPTrace, qualifyPerformance } from "./trace_frames.mjs";

function validateCell(cell) {
  if (!cell || typeof cell !== "object" || Array.isArray(cell)) throw inputError("cell must be an object", "/cell");
  for (const key of ["id", "artifact_commit", "scenario_id"]) if (typeof cell[key] !== "string" || !cell[key]) throw inputError(`cell.${key} is required`, `/cell/${key}`);
  const window = cell.window || {};
  const duration = cell.duration_seconds ?? (cell.duration_ms !== undefined ? Number(cell.duration_ms) / 1000 : ((window.end_ms - window.start_ms) / 1000));
  if (!Number.isFinite(duration) || duration <= 0 || duration > 3600) throw inputError("cell duration_seconds must be finite and between 0 and 3600", "/cell/duration_seconds");
  if (cell.duration_ms !== undefined && (!Number.isFinite(cell.duration_ms) || cell.duration_ms <= 0)) throw inputError("cell.duration_ms must be positive and finite", "/cell/duration_ms");
  for (const [key, value] of [["control_duration_ms", cell.control_duration_ms], ["warmup_duration_ms", cell.warmup_duration_ms]]) {
    if (value !== undefined && (!Number.isFinite(value) || value < 0 || value > 600000)) throw inputError(`cell.${key} must be between 0 and 600000`, `/cell/${key}`);
  }
  if (cell.readback?.max_pending !== undefined
      && (!Number.isInteger(cell.readback.max_pending) || cell.readback.max_pending < 1 || cell.readback.max_pending > MAX_PENDING_READBACKS)) {
    throw inputError(`cell.readback.max_pending must be an integer between 1 and ${MAX_PENDING_READBACKS}`, "/cell/readback/max_pending");
  }
  samplingDeclaration(cell);
  validateSetupCommands(cell);
  return cell;
}

const SAMPLE_COORDINATE_SPACES = new Set(["drawing-buffer", "viewport"]);
const MAX_SAMPLE_PIXELS = 65536;
const MAX_PENDING_READBACKS = 8;

/**
 * Resolve the caller's frozen readback declaration. Coordinates are integer
 * pixels in the selected space; viewport coordinates use CSS pixels with a
 * top-left origin and are converted to the WebGL drawing buffer at runtime.
 */
function samplingDeclaration(cell) {
  const configured = cell.sampling || cell.sample_coverage || cell.game_canvas?.sampling || null;
  if (!configured) return null;
  const region = configured.region || configured.coverage || configured;
  if (!region || typeof region !== "object" || Array.isArray(region)) throw inputError("cell sampling region must be an object", "/cell/sampling/region");
  const coordinateSpace = configured.coordinate_space || configured.coordinateSpace || "drawing-buffer";
  if (!SAMPLE_COORDINATE_SPACES.has(coordinateSpace)) throw inputError("cell sampling coordinate_space must be drawing-buffer or viewport", "/cell/sampling/coordinate_space");
  for (const key of ["x", "y", "width", "height"]) {
    if (!Number.isInteger(region[key]) || region[key] < 0) throw inputError(`cell sampling region.${key} must be a non-negative integer`, `/cell/sampling/region/${key}`);
  }
  if (region.width <= 0 || region.height <= 0) throw inputError("cell sampling region width and height must be positive", "/cell/sampling/region");
  if (region.width * region.height > MAX_SAMPLE_PIXELS) throw inputError(`cell sampling region may contain at most ${MAX_SAMPLE_PIXELS} pixels`, "/cell/sampling/region");
  return {
    explicit: true,
    coordinate_space: coordinateSpace,
    region: {x: region.x, y: region.y, width: region.width, height: region.height},
  };
}

function samplingForCell(cell) {
  return samplingDeclaration(cell) || {
    explicit: false,
    coordinate_space: "drawing-buffer",
    region: {x: 0, y: 0, width: 1, height: 1},
  };
}

function validateSetupCommands(cell) {
  const commands = cell.setup_commands || cell.start_setup || [];
  if (!Array.isArray(commands)) throw inputError("cell.setup_commands must be an array", "/cell/setup_commands");
  for (const [index, command] of commands.entries()) {
    if (!command || typeof command !== "object" || Array.isArray(command) || !["key", "pointer", "wait"].includes(command.type)) {
      throw inputError("setup commands must use key, pointer, or wait from the ordinary input vocabulary", `/cell/setup_commands/${index}`);
    }
    if (command.type === "key" && (typeof command.key !== "string" || !command.key || !["down", "up"].includes(command.action))) throw inputError("setup key requires key and down/up action", `/cell/setup_commands/${index}`);
    if (command.type === "pointer" && (!Number.isFinite(command.x) || !Number.isFinite(command.y) || !["move", "down", "up"].includes(command.action))) throw inputError("setup pointer requires finite x/y and move/down/up action", `/cell/setup_commands/${index}`);
    if (command.type === "wait" && (!Number.isFinite(command.ms) || command.ms < 0 || command.ms > 60000)) throw inputError("setup wait ms must be between 0 and 60000", `/cell/setup_commands/${index}`);
  }
  return commands;
}

function serverChild(server) {
  if (!server || !Array.isArray(server.command) || !server.command.length) throw inputError("live cell server.command is required as argv", "/cell/server/command");
  if (!server.cwd) throw inputError("live cell server.cwd is required", "/cell/server/cwd");
  return spawn(server.command[0], server.command.slice(1), { cwd: resolve(server.cwd), env: { ...process.env, ...(server.env || {}) }, shell: false, detached: true, stdio: ["ignore", "pipe", "pipe"], windowsHide: true });
}

function stopChild(child) {
  return new Promise(done => {
    if (!child || child.exitCode !== null) return done();
    let settled = false;
    const finish = () => { if (!settled) { settled = true; done(); } };
    child.once("exit", finish);
    if (process.platform === "win32") spawn("taskkill", ["/PID", String(child.pid), "/T", "/F"], { windowsHide: true }).once("exit", finish);
    else { try { process.kill(-child.pid, "SIGTERM"); } catch { child.kill("SIGTERM"); } }
    setTimeout(() => { if (!settled) { try { child.kill("SIGKILL"); } catch {} finish(); } }, 5000).unref();
  });
}

async function fixtureTrace(cell, baseDir) {
  let trace = cell.trace;
  if (!trace && cell.trace_file) trace = (await readJson(resolve(baseDir, cell.trace_file))).value;
  if (!trace) throw inputError("fixture cell requires trace or trace_file", "/cell/trace");
  let callbacks = cell.callbacks || [];
  if (cell.callbacks_file) callbacks = (await readJson(resolve(baseDir, cell.callbacks_file))).value;
  return { trace, callbacks };
}

async function clockMarker(page, client) {
  const metrics = await client.send("Performance.getMetrics");
  const timestamp = metrics?.metrics?.find(item => item.name === "Timestamp")?.value;
  const pageNow = await page.evaluate(() => performance.now());
  if (typeof timestamp !== "number" || !Number.isFinite(timestamp) || !Number.isFinite(pageNow)) {
    throw capabilityError("browser did not expose a reconciled monotonic/page clock", "/cell/browser/clock");
  }
  const monotonicMs = timestamp * 1000;
  return { monotonicMs, pageNow, offsetMs: monotonicMs - pageNow };
}

function eventTimeMs(event) {
  const value = event?.timestamp_ms ?? event?.time_ms ?? event?.start_ms ?? event?.ts ?? event?.timestamp;
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return value > 1e8 ? value / 1000 : value;
}

async function installCanvasSampler(page, selector, sampling, readbackOptions = {}) {
  return page.evaluate(({canvasSelector, samplingDeclaration, maxPending}) => {
    const observer = window.__orchPresentationObserver;
    const canvas = document.querySelector(canvasSelector);
    if (!observer) return {installed: false, error: "render-callback observer was not installed"};
    if (!canvas) return {installed: false, error: "canvas selector did not resolve"};
    // PBO readback and zero-timeout fences are WebGL2 APIs. Falling back to a
    // synchronous WebGL1 readPixels call would reintroduce the measured stall,
    // so unsupported capability remains explicitly unverified.
    const gl = canvas.getContext("webgl2");
    const attributes = gl?.getContextAttributes?.() || null;
    if (!gl) return {installed: false, error: "bounded asynchronous sampling requires a WebGL2 drawing buffer"};
    const drawingBuffer = {width: canvas.width, height: canvas.height};
    const viewport = {width: canvas.clientWidth, height: canvas.clientHeight};
    const dpr = window.devicePixelRatio;
    if (!Number.isFinite(dpr) || dpr <= 0) return {installed: false, error: "browser devicePixelRatio is not finite"};
    const region = samplingDeclaration.region;
    let resolved;
    if (samplingDeclaration.coordinate_space === "viewport") {
      const scaleX = viewport.width > 0 ? drawingBuffer.width / viewport.width : dpr;
      const scaleY = viewport.height > 0 ? drawingBuffer.height / viewport.height : dpr;
      const width = Math.max(1, Math.floor(region.width * scaleX));
      const height = Math.max(1, Math.floor(region.height * scaleY));
      const x = Math.floor(region.x * scaleX);
      const top = Math.floor(region.y * scaleY);
      resolved = {x, y: drawingBuffer.height - top - height, width, height};
    } else {
      resolved = {...region};
    }
    if (!Number.isInteger(resolved.x) || !Number.isInteger(resolved.y) || !Number.isInteger(resolved.width) || !Number.isInteger(resolved.height)
        || resolved.x < 0 || resolved.y < 0 || resolved.width <= 0 || resolved.height <= 0
        || resolved.x + resolved.width > drawingBuffer.width || resolved.y + resolved.height > drawingBuffer.height) {
      return {installed: false, error: "frozen sampling coverage is outside the drawing buffer", drawing_buffer: drawingBuffer, viewport, dpr, requested: samplingDeclaration};
    }
    const coverage = {
      explicit: samplingDeclaration.explicit === true,
      coordinate_space: samplingDeclaration.coordinate_space,
      requested_region: {...region},
      resolved_region: resolved,
      drawing_buffer: drawingBuffer,
      viewport,
      dpr,
      sample_pixels: resolved.width * resolved.height,
      bytes_per_sample: resolved.width * resolved.height * 4,
      origin: samplingDeclaration.coordinate_space === "viewport" ? "viewport-top-left-to-webgl-bottom-left" : "webgl-bottom-left",
    };
    const target = {
      selector: canvasSelector,
      coverage,
      gl,
      max_pending: Number.isInteger(maxPending) ? maxPending : 4,
      preserve_drawing_buffer: attributes?.preserveDrawingBuffer === true,
    };
    const configured = observer.configure(target);
    if (!configured.installed) return configured;
    observer.phase = "control";
    return {
      installed: true,
      selector: canvasSelector,
      clock: "performance.now",
      method: configured.method,
      read_only: true,
      presentation: "render-callback-post-callback",
      preserve_drawing_buffer: target.preserve_drawing_buffer,
      sampling: coverage,
      readback: configured.readback,
    };
  }, {canvasSelector: selector, samplingDeclaration: sampling, maxPending: readbackOptions.max_pending});
}

function phaseStats(callbacks, phase, startMs, endMs) {
  const rows = callbacks.filter(item => item.phase === phase && item.timestamp_ms >= startMs && item.timestamp_ms < endMs);
  const intervals = rows.slice(1).map((item, index) => item.timestamp_ms - rows[index].timestamp_ms);
  return {
    status: endMs > startMs ? "observed" : "unverified",
    start_ms: startMs,
    end_ms: endMs,
    observed_ms: Math.max(0, endMs - startMs),
    callbacks: rows.length,
    callback_rate_hz: rows.length / Math.max(0.001, (endMs - startMs) / 1000),
    max_callback_interval_ms: intervals.length ? Math.max(...intervals) : null,
  };
}

function sampleDurationStats(samples) {
  const durations = samples.map(item => item?.duration_ms).filter(value => typeof value === "number" && Number.isFinite(value) && value >= 0).sort((a, b) => a - b);
  if (!durations.length) return {count: 0, total_ms: 0, max_ms: null, p99_ms: null};
  return {
    count: durations.length,
    total_ms: durations.reduce((sum, value) => sum + value, 0),
    max_ms: durations[durations.length - 1],
    p99_ms: durations[Math.min(durations.length - 1, Math.ceil(durations.length * 0.99) - 1)],
  };
}

function fixtureMeasurement(cell) {
  const scenarioId = cell.scenario_id;
  const window = cell.window || {};
  const observedMs = Math.max(0, Number(window.end_ms) - Number(window.start_ms));
  const phase = (status, requestedMs = 0) => ({status, requested_ms: requestedMs, observed_ms: requestedMs, callbacks: 0, callback_rate_hz: 0, max_callback_interval_ms: null});
  return {
    scenario_id: scenarioId,
    observer: "qualification-fixture",
    presentation: "fixture-native-frame-model",
    preserve_drawing_buffer: false,
    sampling: {explicit: false, coordinate_space: "drawing-buffer", requested_region: {x: 0, y: 0, width: 1, height: 1}, resolved_region: null, drawing_buffer: null, viewport: null, dpr: null, sample_pixels: 1, bytes_per_sample: 4, origin: "webgl-bottom-left"},
    lifecycle: {status: "fixture", scenario_id: scenarioId, seed: cell.seed ?? null, configured_url: null, reset: null, phase_transitions: []},
    warmup: phase("fixture", Number(cell.warmup_duration_ms || 0)),
    control: phase("fixture", Number(cell.control_duration_ms || 0)),
    instrumented: {status: "fixture", requested_ms: observedMs, start_ms: window.start_ms, end_ms: window.end_ms, observed_ms: observedMs, callbacks: 0, callback_rate_hz: 0, max_callback_interval_ms: null, samples: 0, readback_errors: 0, sample_duration_ms: {count: 0, total_ms: 0, max_ms: null, p99_ms: null}},
    perturbation: {status: "fixture", basis: "control-vs-instrumented", control_callbacks: 0, instrumented_callbacks: 0, control_callback_rate_hz: 0, instrumented_callback_rate_hz: 0, callback_rate_delta_hz: 0, callback_interval_delta_ms: null, samples: 0, readback_errors: 0, sample_duration_ms: {count: 0, total_ms: 0, max_ms: null, p99_ms: null}},
  };
}

async function canvasBackend(page, selector) {
  return page.evaluate(canvasSelector => {
    const canvas = document.querySelector(canvasSelector);
    if (!canvas) return {kind: "unknown", renderer: null};
    for (const kind of ["webgl2", "webgl"]) {
      const gl = canvas.getContext(kind);
      if (gl) {
        let renderer = null;
        try { renderer = gl.getParameter(gl.RENDERER); } catch { /* masked renderer is still an observed backend */ }
        return {kind, renderer};
      }
    }
    return {kind: canvas.getContext("2d") ? "canvas2d" : "unknown", renderer: null};
  }, selector);
}

async function runSetup(page, canvas, commands) {
  const actions = [];
  await canvas.focus().catch(() => canvas.click({position: {x: 1, y: 1}}));
  for (const command of commands) {
    if (command.type === "key") {
      if (command.action === "down") await page.keyboard.down(command.key);
      else await page.keyboard.up(command.key);
    } else if (command.type === "pointer") {
      await page.mouse.move(command.x, command.y);
      if (command.action === "down") await page.mouse.down({button: command.button || "left"});
      else if (command.action === "up") await page.mouse.up({button: command.button || "left"});
    } else if (command.type === "wait") {
      await new Promise(resolvePromise => setTimeout(resolvePromise, command.ms));
    }
    actions.push({...command, observed: true});
  }
  const state = await page.evaluate(() => ({url: location.href, title: document.title, ready_state: document.readyState, viewport: {width: innerWidth, height: innerHeight}, dpr: devicePixelRatio}));
  return {commands: actions, observed_state: state, observed: true};
}

async function liveTrace(cell) {
  let playwright;
  const browserPackage = cell.browser?.package || "playwright-core";
  const packageSpecifier = /^(?:[A-Za-z]:[\\/]|[\\/])/.test(browserPackage) && !browserPackage.startsWith("file:")
    ? pathToFileURL(resolve(browserPackage)).href : browserPackage;
  try { playwright = await import(packageSpecifier); }
  catch (error) { throw capabilityError(`Playwright is unavailable: ${error.message}`, "/cell/browser/package"); }
  const server = serverChild(cell.server);
  const errors = [];
  server.stderr?.on("data", chunk => errors.push(chunk.toString("utf8").slice(-4000)));
  let browser;
  try {
    const type = cell.browser?.type || "chromium";
    if (!playwright[type]?.launch) throw capabilityError(`browser ${type} is unavailable`, "/cell/browser/type");
    browser = await playwright[type].launch({ headless: false, executablePath: cell.browser?.executable_path, timeout: cell.browser?.launch_timeout_ms || 30000 });
    const context = await browser.newContext({ viewport: cell.viewport || { width: 1280, height: 720 }, deviceScaleFactor: cell.dpr || 1 });
    const page = await context.newPage();
    await page.addInitScript(() => {
      // This wrapper is installed before application code. It samples only
      // after an application's rAF callback returns, while the default WebGL
      // drawing buffer is still available to the browser's presentation
      // step. It has no game-object access and does not schedule or force a
      // redraw. The control phase executes the same wrapper with readback off.
      const digest = value => {
        let hash = 2166136261;
        for (let index = 0; index < value.length; index += 1) {
          hash ^= typeof value === "string" ? value.charCodeAt(index) : value[index];
          hash = Math.imul(hash, 16777619);
        }
        return `fnv1a:${(hash >>> 0).toString(16).padStart(8, "0")}`;
      };
      const READBACK_METHOD = "webgl2.pixel-pack-buffer+fence-sync";
      const observer = {
        phase: "disabled", callbacks: [], samples: [], targets: [], gl: null,
        max_pending: 4, pending: [], available: [], configured: false,
        readback: {
          method: READBACK_METHOD, asynchronous: true,
          api: ["PIXEL_PACK_BUFFER", "readPixels-offset", "fenceSync", "clientWaitSync-timeout-0", "getBufferSubData"],
          max_pending: 4, allocated_buffers: 0, queued: 0, completed: 0,
          lost: 0, errors: 0, context_losses: 0, poll_count: 0,
          pending_at_cleanup: 0, cleanup_observed: false,
          queue_duration_ms: 0, wait_duration_ms: 0, copy_duration_ms: 0, poll_duration_ms: 0,
        },
        // Save and restore mutable readback state around every WebGL call. The
        // observer samples the existing default framebuffer and must not alter
        // the renderer's framebuffer, pixel-store, or pack-buffer bindings.
        withState(gl, operation) {
          const state = {};
          const read = name => {
            try { state[name] = gl.getParameter(gl[name]); } catch { state[name] = undefined; }
          };
          for (const name of ["PIXEL_PACK_BUFFER_BINDING", "READ_FRAMEBUFFER_BINDING", "DRAW_FRAMEBUFFER_BINDING", "PACK_ALIGNMENT", "PACK_ROW_LENGTH", "PACK_SKIP_ROWS", "PACK_SKIP_PIXELS", "READ_BUFFER"]) read(name);
          try { return operation(); }
          finally {
            try { if (state.PIXEL_PACK_BUFFER_BINDING !== undefined) gl.bindBuffer(gl.PIXEL_PACK_BUFFER, state.PIXEL_PACK_BUFFER_BINDING); } catch {}
            try { if (state.READ_FRAMEBUFFER_BINDING !== undefined) gl.bindFramebuffer(gl.READ_FRAMEBUFFER, state.READ_FRAMEBUFFER_BINDING); } catch {}
            try { if (state.DRAW_FRAMEBUFFER_BINDING !== undefined) gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER, state.DRAW_FRAMEBUFFER_BINDING); } catch {}
            for (const name of ["PACK_ALIGNMENT", "PACK_ROW_LENGTH", "PACK_SKIP_ROWS", "PACK_SKIP_PIXELS"]) {
              try { if (state[name] !== undefined) gl.pixelStorei(gl[name], state[name]); } catch {}
            }
            try { if (state.READ_BUFFER !== undefined) gl.readBuffer(state.READ_BUFFER); } catch {}
          }
        },
        configure(target) {
          const gl = target.gl;
          const maxPending = target.max_pending;
          if (!gl || typeof gl.createBuffer !== "function" || typeof gl.fenceSync !== "function"
              || typeof gl.clientWaitSync !== "function" || typeof gl.getBufferSubData !== "function") {
            return {installed: false, error: "bounded asynchronous sampling requires WebGL2 PBO and fenceSync support"};
          }
          this.gl = gl;
          this.max_pending = maxPending;
          this.targets = [target];
          this.pending = [];
          this.available = [];
          this.readback = {
            method: READBACK_METHOD, asynchronous: true,
            api: ["PIXEL_PACK_BUFFER", "readPixels-offset", "fenceSync", "clientWaitSync-timeout-0", "getBufferSubData"],
            max_pending: maxPending, allocated_buffers: 0, queued: 0, completed: 0,
            lost: 0, errors: 0, context_losses: 0, poll_count: 0,
            pending_at_cleanup: 0, cleanup_observed: false,
            queue_duration_ms: 0, wait_duration_ms: 0, copy_duration_ms: 0, poll_duration_ms: 0,
          };
          try {
            this.withState(gl, () => {
              for (let index = 0; index < maxPending; index += 1) {
                const buffer = gl.createBuffer();
                if (!buffer) throw new Error("WebGL2 could not allocate a pixel-pack buffer");
                gl.bindBuffer(gl.PIXEL_PACK_BUFFER, buffer);
                gl.bufferData(gl.PIXEL_PACK_BUFFER, target.coverage.bytes_per_sample, gl.STREAM_READ);
                this.available.push(buffer);
              }
            });
          } catch (error) {
            for (const buffer of this.available) { try { gl.deleteBuffer(buffer); } catch {} }
            this.available = [];
            return {installed: false, error: String(error.message || error)};
          }
          this.readback.allocated_buffers = this.available.length;
          this.configured = true;
          return {installed: true, method: READBACK_METHOD, readback: {...this.readback}};
        },
        recordFailure(item, error, status = "error") {
          const completedAt = performance.now();
          this.readback.errors += 1;
          if (status === "lost") this.readback.lost += 1;
          this.samples.push({
            timestamp_ms: item.origin_timestamp_ms,
            origin_timestamp_ms: item.origin_timestamp_ms,
            callback_index: item.callback_index,
            hash: null,
            source: "render-callback-post-callback",
            method: READBACK_METHOD,
            preserve_drawing_buffer: item.preserve_drawing_buffer,
            coverage: item.coverage,
            completion_status: status,
            completion_timestamp_ms: completedAt,
            queue_duration_ms: item.queue_duration_ms || 0,
            wait_duration_ms: item.wait_duration_ms || 0,
            copy_duration_ms: 0,
            completion_latency_ms: Math.max(0, completedAt - item.origin_timestamp_ms),
            duration_ms: item.queue_duration_ms || 0,
            error: String(error),
          });
        },
        release(item) {
          try { if (item.sync) this.gl.deleteSync(item.sync); } catch {}
          if (item.buffer) this.available.push(item.buffer);
        },
        poll() {
          const gl = this.gl;
          if (!this.configured || !gl || !this.pending.length) return;
          try {
            if (gl.isContextLost?.()) {
              this.readback.context_losses += 1;
              for (const item of this.pending) {
                this.recordFailure(item, "WebGL context was lost before readback completion", "lost");
                this.release(item);
              }
              this.pending = [];
              return;
            }
          } catch {}
          this.readback.poll_count += 1;
          const pollStarted = performance.now();
          const remaining = [];
          for (const item of this.pending) {
            let waitStatus;
            const waitStarted = performance.now();
            try { waitStatus = gl.clientWaitSync(item.sync, 0, 0); }
            catch (error) {
              try { if (gl.isContextLost?.()) this.readback.context_losses += 1; } catch {}
              item.wait_duration_ms = (item.wait_duration_ms || 0) + performance.now() - waitStarted;
              this.recordFailure(item, error, "error");
              this.release(item);
              continue;
            }
            const waitDuration = performance.now() - waitStarted;
            item.wait_duration_ms = (item.wait_duration_ms || 0) + waitDuration;
            this.readback.wait_duration_ms += waitDuration;
            if (waitStatus === gl.TIMEOUT_EXPIRED) { remaining.push(item); continue; }
            if (waitStatus !== gl.ALREADY_SIGNALED && waitStatus !== gl.CONDITION_SATISFIED) {
              this.recordFailure(item, `clientWaitSync returned ${waitStatus}`, "error");
              this.release(item);
              continue;
            }
            const copyStarted = performance.now();
            try {
              const pixels = new Uint8Array(item.coverage.bytes_per_sample);
              this.withState(gl, () => {
                gl.bindBuffer(gl.PIXEL_PACK_BUFFER, item.buffer);
                gl.getBufferSubData(gl.PIXEL_PACK_BUFFER, 0, pixels);
              });
              const copyDuration = performance.now() - copyStarted;
              this.readback.copy_duration_ms += copyDuration;
              this.readback.completed += 1;
              const completedAt = performance.now();
              this.samples.push({
                timestamp_ms: item.origin_timestamp_ms,
                origin_timestamp_ms: item.origin_timestamp_ms,
                callback_index: item.callback_index,
                hash: digest(pixels),
                source: "render-callback-post-callback",
                method: READBACK_METHOD,
                preserve_drawing_buffer: item.preserve_drawing_buffer,
                coverage: item.coverage,
                completion_status: "complete",
                completion_timestamp_ms: completedAt,
                queue_duration_ms: item.queue_duration_ms,
                wait_duration_ms: item.wait_duration_ms,
                copy_duration_ms: copyDuration,
                completion_latency_ms: Math.max(0, completedAt - item.origin_timestamp_ms),
                duration_ms: item.queue_duration_ms + copyDuration,
              });
            } catch (error) {
              try { if (gl.isContextLost?.()) this.readback.context_losses += 1; } catch {}
              this.recordFailure(item, error, "error");
            }
            this.release(item);
          }
          this.pending = remaining;
          this.readback.poll_duration_ms = (this.readback.poll_duration_ms || 0) + performance.now() - pollStarted;
        },
        sample(target, callbackIndex, callbackTimestamp) {
          const originTimestamp = Number.isFinite(callbackTimestamp) ? callbackTimestamp : performance.now();
          this.poll();
          const started = performance.now();
          const item = {
            origin_timestamp_ms: originTimestamp,
            callback_index: callbackIndex,
            coverage: target.coverage,
            preserve_drawing_buffer: target.preserve_drawing_buffer,
            queue_duration_ms: 0,
            wait_duration_ms: 0,
          };
          if (this.pending.length >= this.max_pending || !this.available.length) {
            item.queue_duration_ms = performance.now() - started;
            this.recordFailure(item, "bounded pending readback queue is full", "lost");
            return;
          }
          const gl = this.gl;
          item.buffer = this.available.pop();
          try {
            this.withState(gl, () => {
              const {x, y, width, height} = target.coverage.resolved_region;
              gl.bindFramebuffer(gl.READ_FRAMEBUFFER, null);
              gl.readBuffer(gl.BACK);
              gl.bindBuffer(gl.PIXEL_PACK_BUFFER, item.buffer);
              gl.readPixels(x, y, width, height, gl.RGBA, gl.UNSIGNED_BYTE, 0);
              item.sync = gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE, 0);
              if (!item.sync) throw new Error("WebGL2 could not create a readback fence");
              gl.flush();
            });
            item.queue_duration_ms = performance.now() - started;
            this.readback.queue_duration_ms += item.queue_duration_ms;
            this.readback.queued += 1;
            this.pending.push(item);
          } catch (error) {
            try { if (gl.isContextLost?.()) this.readback.context_losses += 1; } catch {}
            item.queue_duration_ms = performance.now() - started;
            this.readback.queue_duration_ms += item.queue_duration_ms;
            this.recordFailure(item, error, "error");
            this.release(item);
          }
        },
        flush() {
          this.poll();
          const pendingAtCleanup = this.pending.length;
          this.readback.pending_at_cleanup = pendingAtCleanup;
          for (const item of this.pending) {
            this.recordFailure(item, "readback was still pending at observed cleanup", "lost");
            this.release(item);
          }
          this.pending = [];
          for (const buffer of this.available) { try { this.gl?.deleteBuffer(buffer); } catch {} }
          this.available = [];
          this.readback.cleanup_observed = true;
          return {...this.readback};
        },
      };
      const times = [];
      Object.defineProperty(window, "__orchRafTimes", { value: times, configurable: false });
      Object.defineProperty(window, "__orchPresentationObserver", { value: observer, configurable: false });
      const original = window.requestAnimationFrame.bind(window);
      window.requestAnimationFrame = callback => original(time => {
        const callbackIndex = observer.callbacks.length;
        const started = performance.now();
        times.push(time);
        observer.callbacks.push({timestamp_ms: time, started_ms: started, phase: observer.phase});
        try { callback(time); } finally {
          const row = observer.callbacks[callbackIndex];
          row.ended_ms = performance.now();
          if (observer.phase === "instrumented") for (const target of observer.targets) observer.sample(target, callbackIndex, time);
        }
      });
    });
    await page.goto(cell.server.url, { waitUntil: "domcontentloaded", timeout: cell.server.startup_timeout_ms || 30000 });
    const canvas = page.locator(cell.canvas_selector || "canvas").first();
    if (await page.locator(cell.canvas_selector || "canvas").count() < 1) throw capabilityError("game canvas did not resolve", "/cell/canvas_selector");
    await canvas.focus().catch(() => canvas.click({ position: { x: 1, y: 1 } }));
    const client = await context.newCDPSession(page);
    await client.send("Performance.enable");
    const durationMs = cell.duration_ms || Math.round((cell.duration_seconds || 60) * 1000);
    const paddingMs = Number.isFinite(cell.padding_ms) ? cell.padding_ms : 100;
    if (paddingMs < 0 || paddingMs > 10000) throw inputError("cell.padding_ms must be between 0 and 10000", "/cell/padding_ms");
    const controlDurationMs = Number.isFinite(cell.control_duration_ms) ? cell.control_duration_ms : durationMs;
    const warmupDurationMs = Number.isFinite(cell.warmup_duration_ms) ? cell.warmup_duration_ms : Math.max(1000, Math.round(Number(cell.warmup_seconds || 5) * 1000));
    if (controlDurationMs < 250) throw inputError("cell.control_duration_ms must be at least 250", "/cell/control_duration_ms");
    if (controlDurationMs !== durationMs) throw inputError("control_duration_ms must equal the instrumented duration for a comparable pair", "/cell/control_duration_ms");
    if (warmupDurationMs < 0) throw inputError("cell.warmup_duration_ms must not be negative", "/cell/warmup_duration_ms");
    const selector = cell.canvas_selector || cell.game_canvas?.canvas_selector || "canvas";
    const sampling = samplingForCell(cell);
    const sampler = await installCanvasSampler(page, selector, sampling, {max_pending: cell.readback?.max_pending});
    if (!sampler.installed) throw capabilityError(sampler.error || "frozen sampling coverage could not be installed", "/cell/sampling");
    const wait = duration => new Promise(resolvePromise => setTimeout(resolvePromise, duration));
    const setupCommands = validateSetupCommands(cell);
    const initialSetup = await runSetup(page, canvas, setupCommands);
    const lifecycle = {
      scenario_id: cell.scenario_id,
      seed: cell.seed ?? null,
      configured_url: cell.server.url,
      viewport: cell.viewport || {width: 1280, height: 720},
      dpr: cell.dpr || 1,
      start: {method: "page.goto", url: page.url(), observed: true, ready: true, setup: initialSetup},
      reset: null,
      phase_transitions: [],
    };
    await page.evaluate(() => { window.__orchPresentationObserver.phase = "warmup"; });
    await wait(warmupDurationMs);
    const controlClock = await clockMarker(page, client);
    const controlStartPage = await page.evaluate(() => performance.now());
    await page.evaluate(() => { window.__orchPresentationObserver.phase = "control"; });
    lifecycle.phase_transitions.push({phase: "control", method: "observed-render-callbacks", start_observed: true, configured_duration_ms: controlDurationMs});
    await wait(controlDurationMs);
    const controlEndPage = await page.evaluate(() => performance.now());
    const controlObserver = await page.evaluate(() => ({callbacks: window.__orchPresentationObserver.callbacks.slice()}));
    const controlCallbacksObserved = controlObserver.callbacks.map(item => ({...item, timestamp_ms: item.timestamp_ms + controlClock.offsetMs}));

    // Reload the same configured URL before the instrumented phase. This is an
    // observed app reset, so both phases begin from the page's normal startup
    // lifecycle with the same scenario, seed, viewport, and DPR.
    const resetStartedAt = Date.now();
    const resetFromUrl = page.url();
    await page.reload({waitUntil: "domcontentloaded", timeout: cell.server.startup_timeout_ms || 30000});
    const resetCanvas = page.locator(selector).first();
    if (await page.locator(selector).count() < 1) throw capabilityError("game canvas did not resolve after the measured reset", "/cell/sampling/reset");
    await resetCanvas.focus().catch(() => resetCanvas.click({ position: { x: 1, y: 1 } }));
    const instrumentedClient = await context.newCDPSession(page);
    await instrumentedClient.send("Performance.enable");
    const resetReady = await page.evaluate(() => ({url: location.href, title: document.title, viewport: {width: innerWidth, height: innerHeight}, dpr: devicePixelRatio}));
    const resetSetup = await runSetup(page, resetCanvas, setupCommands);
    lifecycle.reset = {method: "page.reload", observed: true, from_url: resetFromUrl, to_url: page.url(), ready: true, elapsed_ms: Date.now() - resetStartedAt, ready_observation: resetReady, setup: resetSetup};
    lifecycle.phase_transitions.push({phase: "instrumented", method: "observed-render-callbacks-after-reset", start_observed: true, configured_duration_ms: durationMs});
    const instrumentedSampler = await installCanvasSampler(page, selector, sampling, {max_pending: cell.readback?.max_pending});
    if (!instrumentedSampler.installed) throw capabilityError(instrumentedSampler.error || "frozen sampling coverage could not be installed after reset", "/cell/sampling/reset");
    const warmupStartPage = await page.evaluate(() => performance.now());
    await page.evaluate(() => { window.__orchPresentationObserver.phase = "warmup"; });
    await wait(warmupDurationMs);
    const warmupEndPage = await page.evaluate(() => performance.now());
    const captureClock = await clockMarker(page, instrumentedClient);
    const window = { start_ms: captureClock.monotonicMs + paddingMs, end_ms: captureClock.monotonicMs + paddingMs + durationMs };
    await page.evaluate(() => { window.__orchPresentationObserver.phase = "instrumented"; });
    const backend = await canvasBackend(page, cell.canvas_selector || cell.game_canvas?.canvas_selector || "canvas");
    const wallStart = Date.now();
    const trace = await collectCDPTrace(instrumentedClient, { durationMs: durationMs + (2 * paddingMs), categories: cell.trace_categories, timeoutMs: cell.trace_timeout_ms || Math.max(120000, durationMs + (2 * paddingMs) + 60000) });
    const observer = await page.evaluate(() => {
      const value = window.__orchPresentationObserver;
      const readback = value.flush();
      return {callbacks: value.callbacks.slice(), samples: value.samples.slice(), readback};
    });
    const callbacksObserved = observer.callbacks.map(item => ({...item, timestamp_ms: item.timestamp_ms + captureClock.offsetMs}));
    const canvasSamples = observer.samples.map(item => ({
      ...item,
      timestamp_ms: item.timestamp_ms + captureClock.offsetMs,
      origin_timestamp_ms: Number.isFinite(item.origin_timestamp_ms) ? item.origin_timestamp_ms + captureClock.offsetMs : item.origin_timestamp_ms,
      completion_timestamp_ms: Number.isFinite(item.completion_timestamp_ms) ? item.completion_timestamp_ms + captureClock.offsetMs : item.completion_timestamp_ms,
    }));
    const callbacks = callbacksObserved.filter(item => item.timestamp_ms >= window.start_ms && item.timestamp_ms < window.end_ms).map(item => item.timestamp_ms);
    const control = phaseStats(controlCallbacksObserved, "control", controlStartPage + controlClock.offsetMs, controlEndPage + controlClock.offsetMs);
    const warmup = phaseStats(callbacksObserved, "warmup", warmupStartPage + captureClock.offsetMs, warmupEndPage + captureClock.offsetMs);
    const instrumented = phaseStats(callbacksObserved, "instrumented", window.start_ms, window.end_ms);
    instrumented.requested_ms = durationMs;
    const instrumentedSamples = canvasSamples.filter(item => item.timestamp_ms >= window.start_ms && item.timestamp_ms < window.end_ms);
    instrumented.samples = instrumentedSamples.length;
    instrumented.readback_errors = instrumentedSamples.filter(item => item.error).length;
    instrumented.sample_duration_ms = sampleDurationStats(instrumentedSamples);
    instrumented.readback = observer.readback;
    const measurement = {
      scenario_id: cell.scenario_id,
      observer: sampler.presentation,
      presentation: sampler.presentation,
      preserve_drawing_buffer: instrumentedSampler.preserve_drawing_buffer,
      sampling: instrumentedSampler.sampling,
      lifecycle,
      warmup: {...warmup, requested_ms: warmupDurationMs},
      control: {...control, requested_ms: controlDurationMs},
      instrumented,
      perturbation: {
        status: control.status === "observed" && instrumented.status === "observed" ? "observed" : "unverified",
        basis: "control-vs-instrumented",
        control_callbacks: control.callbacks,
        instrumented_callbacks: instrumented.callbacks,
        control_callback_rate_hz: control.callback_rate_hz,
        instrumented_callback_rate_hz: instrumented.callback_rate_hz,
        callback_rate_delta_hz: instrumented.callback_rate_hz - control.callback_rate_hz,
        callback_interval_delta_ms: instrumented.max_callback_interval_ms === null || control.max_callback_interval_ms === null ? null : instrumented.max_callback_interval_ms - control.max_callback_interval_ms,
        samples: instrumented.samples,
        readback_errors: instrumented.readback_errors,
        sample_duration_ms: instrumented.sample_duration_ms,
        readback: observer.readback,
      },
    };
    const wallEnd = Date.now();
    const traceTimes = trace.traceEvents.map(eventTimeMs).filter(value => value !== null);
    const parsed = {
      ...trace,
      canvas_samples: canvasSamples,
      canvas_instrumentation: {method: instrumentedSampler.method || sampler.method || "unknown", selector, clock: "performance.now+cdp-offset", read_only: instrumentedSampler.read_only === true, presentation: instrumentedSampler.presentation, measurement_perturbation: measurement.perturbation, preserve_drawing_buffer: instrumentedSampler.preserve_drawing_buffer, sampling: instrumentedSampler.sampling, sample_coverage: instrumentedSampler.sampling, readback: observer.readback, signal: "render-callback-post-callback; async WebGL2 readback; native-frame-association-required-for-presentation", errors: canvasSamples.filter(item => item.error).map(item => item.error)},
      measurement,
      metadata: {
        clock_reconciled: true,
        clock_method: "cdp-performance-timestamp-minus-page-performance-now",
        wall_start_ms: wallStart,
        wall_end_ms: wallEnd,
        capture_start_ms: captureClock.monotonicMs,
        capture_end_ms: traceTimes.length ? traceTimes.reduce((maximum, value) => Math.max(maximum, value), -Infinity) : null,
        window_start_ms: window.start_ms,
        window_end_ms: window.end_ms,
        padding_before_ms: paddingMs,
        padding_after_ms: paddingMs,
        warmup_start_ms: warmup.start_ms,
        warmup_end_ms: warmup.end_ms,
        control_start_ms: control.start_ms,
        control_end_ms: control.end_ms,
      },
    };
    return {
      trace: parsed,
      rawStream: trace.rawStream,
      callbacks,
      window,
      environment: { browser: type, browser_version: browser.version?.() || null, driver: cell.browser?.package || "playwright-core", renderer_backend: backend },
      measurement,
      diagnostics: { server_errors: errors, wall_start_ms: wallStart, wall_end_ms: wallEnd, clock_method: parsed.metadata.clock_method, canvas_sampler: parsed.canvas_instrumentation, readback: observer.readback, measurement },
    };
  } finally {
    await browser?.close().catch(() => {});
    await stopChild(server);
  }
}

export async function collectCell(cell, { baseDir = process.cwd(), outDir } = {}) {
  validateCell(cell);
  const live = !(cell.trace || cell.trace_file);
  const source = live ? await liveTrace(cell) : await fixtureTrace(cell, baseDir);
  const measurement = source.measurement || fixtureMeasurement(cell);
  const measuredCell = source.window ? {
    ...cell,
    window: source.window,
    game_canvas: { ...(cell.game_canvas || {}), canvas_selector: cell.canvas_selector || cell.game_canvas?.canvas_selector || "canvas" },
  } : cell;
  let traceForResult = source.trace;
  if (source.rawStream && outDir) traceForResult = {...source.trace, raw_stream_path: "trace.raw.json"};
  if (outDir && source.rawStream) {
    await mkdir(resolve(outDir), { recursive: true });
    const rawPath = resolve(outDir, "trace.raw.json");
    await writeFile(rawPath, source.rawStream, {flag: "wx"});
    const observed = await readFile(rawPath);
    if (observed.length !== source.rawStream.length || sha256(observed) !== source.trace.raw_stream_hash) {
      throw evidenceError("raw ReturnAsStream bytes changed while writing evidence", "/trace/raw_stream_path");
    }
  }
  const qualification = qualifyPerformance({ cell: measuredCell, trace: traceForResult, callbacks: source.callbacks });
  const result = {
    ...makeHeader({ kind: "performance-cell", id: cell.id, artifactCommit: cell.artifact_commit, producer: "performance_collect.mjs", inputs: { cell: sha256(JSON.stringify(cell)), trace: traceForResult.raw_stream_hash || sha256(JSON.stringify(traceForResult)) }, environment: source.environment || cell.environment || {}, status: qualification.status === "qualified" ? "complete" : "unverified", gaps: (qualification.failures || []).map(item => item.code) }),
    cell: { ...measuredCell, trace: undefined, callbacks: undefined },
    source: live ? "live-browser" : "qualification-fixture",
    measurement,
    diagnostics: source.diagnostics,
    trace: traceForResult,
    callbacks: source.callbacks,
    qualification,
    observed_at: nowIso(),
  };
  if (outDir) {
    await mkdir(resolve(outDir), { recursive: true });
    await writeJsonAtomic(resolve(outDir, "cell-result.json"), result);
    await writeJsonAtomic(resolve(outDir, "trace.json"), traceForResult);
  }
  return result;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.cell || !args.out) throw inputError("--cell and --out are required");
  const { value: cell } = await readJson(resolve(args.cell));
  const result = await collectCell(cell, { baseDir: dirname(resolve(args.cell)), outDir: resolve(args.out) });
  process.stdout.write(`${JSON.stringify({ status: result.status, kind: result.kind, id: result.id, source: result.source, qualification: result.qualification })}\n`);
  if (result.qualification.status !== "qualified") process.exitCode = EXIT.EVIDENCE;
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].replaceAll("\\", "/"))) {
  main().catch(error => { const result = resultFromError(error); process.stderr.write(`${result.result.error.message}\n`); process.stdout.write(`${JSON.stringify(result.result)}\n`); process.exitCode = result.exitCode; });
}

export { validateCell, fixtureTrace, liveTrace };
