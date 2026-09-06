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
  const duration = cell.duration_seconds ?? ((window.end_ms - window.start_ms) / 1000);
  if (!Number.isFinite(duration) || duration <= 0 || duration > 3600) throw inputError("cell duration_seconds must be finite and between 0 and 3600", "/cell/duration_seconds");
  for (const [key, value] of [["control_duration_ms", cell.control_duration_ms], ["warmup_duration_ms", cell.warmup_duration_ms]]) {
    if (value !== undefined && (!Number.isFinite(value) || value < 0 || value > 600000)) throw inputError(`cell.${key} must be between 0 and 600000`, `/cell/${key}`);
  }
  return cell;
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

async function installCanvasSampler(page, selector) {
  return page.evaluate(canvasSelector => {
    const observer = window.__orchPresentationObserver;
    const canvas = document.querySelector(canvasSelector);
    if (!observer) return {installed: false, error: "render-callback observer was not installed"};
    if (!canvas) return {installed: false, error: "canvas selector did not resolve"};
    const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
    const attributes = gl?.getContextAttributes?.() || null;
    observer.targets = [{selector: canvasSelector}];
    observer.phase = "control";
    return {
      installed: true,
      selector: canvasSelector,
      clock: "performance.now",
      method: gl ? "webgl.readPixels" : "canvas.toDataURL",
      read_only: true,
      presentation: "render-callback-post-callback",
      preserve_drawing_buffer: gl ? attributes?.preserveDrawingBuffer : null,
    };
  }, selector);
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
    warmup: phase("fixture", Number(cell.warmup_duration_ms || 0)),
    control: phase("fixture", Number(cell.control_duration_ms || 0)),
    instrumented: {status: "fixture", requested_ms: observedMs, start_ms: window.start_ms, end_ms: window.end_ms, observed_ms: observedMs, callbacks: 0, callback_rate_hz: 0, max_callback_interval_ms: null, samples: 0, readback_errors: 0},
    perturbation: {status: "fixture", basis: "control-vs-instrumented", control_callbacks: 0, instrumented_callbacks: 0, control_callback_rate_hz: 0, instrumented_callback_rate_hz: 0, callback_rate_delta_hz: 0, callback_interval_delta_ms: null, samples: 0, readback_errors: 0},
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
          hash ^= value.charCodeAt(index);
          hash = Math.imul(hash, 16777619);
        }
        return `fnv1a:${(hash >>> 0).toString(16).padStart(8, "0")}`;
      };
      const observer = {
        phase: "disabled", callbacks: [], samples: [], targets: [],
        sample(target, callbackIndex) {
          const timestamp = performance.now();
          const canvas = document.querySelector(target.selector);
          if (!canvas) {
            this.samples.push({timestamp_ms: timestamp, callback_index: callbackIndex, hash: null, source: "render-callback-post-callback", duration_ms: performance.now() - timestamp, error: "canvas selector did not resolve"});
            return;
          }
          try {
            const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
            if (gl) {
              const width = Math.min(1, canvas.width);
              const height = Math.min(1, canvas.height);
              if (!width || !height) throw new Error("canvas drawing buffer has zero size");
              const maxX = Math.max(0, canvas.width - width);
              const maxY = Math.max(0, canvas.height - height);
              const x = Math.floor(maxX / 2);
              const y = Math.floor(maxY / 2);
              const pixels = new Uint8Array(width * height * 4);
              gl.readPixels(x, y, width, height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
              const attributes = gl.getContextAttributes?.() || {};
              this.samples.push({timestamp_ms: timestamp, callback_index: callbackIndex, hash: digest(String.fromCharCode(...pixels)), source: "render-callback-post-callback", method: "webgl.readPixels", preserve_drawing_buffer: attributes.preserveDrawingBuffer === true, duration_ms: performance.now() - timestamp});
            } else {
              this.samples.push({timestamp_ms: timestamp, callback_index: callbackIndex, hash: digest(canvas.toDataURL("image/webp", 0.05)), source: "render-callback-post-callback", method: "canvas.toDataURL", preserve_drawing_buffer: null, duration_ms: performance.now() - timestamp});
            }
          } catch (error) {
            this.samples.push({timestamp_ms: timestamp, callback_index: callbackIndex, hash: null, source: "render-callback-post-callback", duration_ms: performance.now() - timestamp, error: String(error.message || error)});
          }
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
          if (observer.phase === "instrumented") for (const target of observer.targets) observer.sample(target, callbackIndex);
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
    const controlDurationMs = Number.isFinite(cell.control_duration_ms) ? cell.control_duration_ms : 1000;
    const warmupDurationMs = Number.isFinite(cell.warmup_duration_ms) ? cell.warmup_duration_ms : Math.max(1000, Math.round(Number(cell.warmup_seconds || 5) * 1000));
    if (controlDurationMs < 250) throw inputError("cell.control_duration_ms must be at least 250", "/cell/control_duration_ms");
    if (warmupDurationMs < 0) throw inputError("cell.warmup_duration_ms must not be negative", "/cell/warmup_duration_ms");
    const selector = cell.canvas_selector || cell.game_canvas?.canvas_selector || "canvas";
    const sampler = await installCanvasSampler(page, selector);
    const wait = duration => new Promise(resolvePromise => setTimeout(resolvePromise, duration));
    const controlStartPage = await page.evaluate(() => performance.now());
    await page.evaluate(() => { window.__orchPresentationObserver.phase = "control"; });
    await wait(controlDurationMs);
    const controlEndPage = await page.evaluate(() => performance.now());
    const warmupStartPage = controlEndPage;
    await page.evaluate(() => { window.__orchPresentationObserver.phase = "warmup"; });
    await wait(warmupDurationMs);
    const warmupEndPage = await page.evaluate(() => performance.now());
    const captureClock = await clockMarker(page, client);
    const window = { start_ms: captureClock.monotonicMs + paddingMs, end_ms: captureClock.monotonicMs + paddingMs + durationMs };
    await page.evaluate(() => { window.__orchPresentationObserver.phase = "instrumented"; });
    const backend = await canvasBackend(page, cell.canvas_selector || cell.game_canvas?.canvas_selector || "canvas");
    const wallStart = Date.now();
    const trace = await collectCDPTrace(client, { durationMs: durationMs + (2 * paddingMs), categories: cell.trace_categories, timeoutMs: cell.trace_timeout_ms || Math.max(120000, durationMs + (2 * paddingMs) + 60000) });
    const observer = await page.evaluate(() => ({callbacks: window.__orchPresentationObserver.callbacks.slice(), samples: window.__orchPresentationObserver.samples.slice()}));
    const callbacksObserved = observer.callbacks.map(item => ({...item, timestamp_ms: item.timestamp_ms + captureClock.offsetMs}));
    const canvasSamples = observer.samples.map(item => ({...item, timestamp_ms: item.timestamp_ms + captureClock.offsetMs}));
    const callbacks = callbacksObserved.filter(item => item.timestamp_ms >= window.start_ms && item.timestamp_ms < window.end_ms).map(item => item.timestamp_ms);
    const control = phaseStats(callbacksObserved, "control", controlStartPage + captureClock.offsetMs, controlEndPage + captureClock.offsetMs);
    const warmup = phaseStats(callbacksObserved, "warmup", warmupStartPage + captureClock.offsetMs, warmupEndPage + captureClock.offsetMs);
    const instrumented = phaseStats(callbacksObserved, "instrumented", window.start_ms, window.end_ms);
    instrumented.requested_ms = durationMs;
    instrumented.samples = canvasSamples.filter(item => item.timestamp_ms >= window.start_ms && item.timestamp_ms < window.end_ms).length;
    instrumented.readback_errors = canvasSamples.filter(item => item.timestamp_ms >= window.start_ms && item.timestamp_ms < window.end_ms && item.error).length;
    const measurement = {
      scenario_id: cell.scenario_id,
      observer: sampler.presentation,
      presentation: sampler.presentation,
      preserve_drawing_buffer: sampler.preserve_drawing_buffer,
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
      },
    };
    const wallEnd = Date.now();
    const traceTimes = trace.traceEvents.map(eventTimeMs).filter(value => value !== null);
    const parsed = {
      ...trace,
      canvas_samples: canvasSamples,
      canvas_instrumentation: {method: sampler.method || "unknown", selector, clock: "performance.now+cdp-offset", read_only: sampler.read_only === true, presentation: sampler.presentation, measurement_perturbation: measurement.perturbation, preserve_drawing_buffer: sampler.preserve_drawing_buffer, signal: "render-callback-post-callback; native-frame-association-required-for-presentation", errors: canvasSamples.filter(item => item.error).map(item => item.error)},
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
      diagnostics: { server_errors: errors, wall_start_ms: wallStart, wall_end_ms: wallEnd, clock_method: parsed.metadata.clock_method, canvas_sampler: parsed.canvas_instrumentation, measurement },
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
    if (source.rawStream) {
      const rawPath = resolve(outDir, "trace.raw.json");
      await writeFile(rawPath, source.rawStream, {flag: "wx"});
      const observed = await readFile(rawPath);
      if (observed.length !== source.rawStream.length || sha256(observed) !== source.trace.raw_stream_hash) {
        throw evidenceError("raw ReturnAsStream bytes changed while writing evidence", "/trace/raw_stream_path");
      }
    }
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
