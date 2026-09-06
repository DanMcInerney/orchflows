/**
 * Collect one performance cell. Fixture mode is intentionally explicit and
 * retains the same raw trace/completion path as live mode, making a fixture a
 * qualification probe rather than a claimed measurement.
 */
import { spawn } from "node:child_process";
import { resolve, dirname } from "node:path";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import {
  EXIT, capabilityError, inputError, makeHeader, nowIso, parseArgs,
  readJson, resultFromError, sha256, timeoutError, writeJsonAtomic, evidenceError,
} from "./_common.mjs";
import { collectCDPTrace, qualifyPerformance } from "./trace_frames.mjs";

function validateCell(cell) {
  if (!cell || typeof cell !== "object" || Array.isArray(cell)) throw inputError("cell must be an object", "/cell");
  for (const key of ["id", "artifact_commit"]) if (typeof cell[key] !== "string" || !cell[key]) throw inputError(`cell.${key} is required`, `/cell/${key}`);
  const window = cell.window || {};
  const duration = cell.duration_seconds ?? ((window.end_ms - window.start_ms) / 1000);
  if (!Number.isFinite(duration) || duration <= 0 || duration > 3600) throw inputError("cell duration_seconds must be finite and between 0 and 3600", "/cell/duration_seconds");
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

async function installCanvasSampler(page, selector, intervalMs) {
  return page.evaluate(({canvasSelector, period}) => {
    const canvas = document.querySelector(canvasSelector);
    if (!canvas) return {installed: false, error: "canvas selector did not resolve"};
    const samples = [];
    const digest = value => {
      let hash = 2166136261;
      for (let index = 0; index < value.length; index += 1) {
        hash ^= value.charCodeAt(index);
        hash = Math.imul(hash, 16777619);
      }
      return `fnv1a:${(hash >>> 0).toString(16).padStart(8, "0")}`;
    };
    const sample = () => {
      const timestamp = performance.now();
      try {
        // toDataURL reads the presented canvas pixels. It exposes no game
        // object and makes no state/time changes; the sampling clock is the
        // page's normal performance.now() clock.
        samples.push({timestamp_ms: timestamp, hash: digest(canvas.toDataURL("image/webp", 0.05))});
      } catch (error) {
        samples.push({timestamp_ms: timestamp, hash: null, error: String(error.message || error)});
      }
    };
    sample();
    const timer = setInterval(sample, period);
    Object.defineProperty(window, "__orchCanvasSampler", {
      configurable: false,
      value: {samples, timer, selector: canvasSelector, interval_ms: period, clock: "performance.now", read_only: true},
    });
    return {installed: true, interval_ms: period, clock: "performance.now", read_only: true};
  }, {canvasSelector: selector, period: intervalMs});
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
  try { playwright = await import(cell.browser?.package || "playwright-core"); }
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
      // The wrapper only records callback timestamps and invokes the original.
      // It exposes no game object and cannot mutate game state.
      const original = window.requestAnimationFrame.bind(window);
      const times = [];
      Object.defineProperty(window, "__orchRafTimes", { value: times, configurable: false });
      window.requestAnimationFrame = (callback) => original((time) => { times.push(time); callback(time); });
    });
    await page.goto(cell.server.url, { waitUntil: "domcontentloaded", timeout: cell.server.startup_timeout_ms || 30000 });
    const canvas = page.locator(cell.canvas_selector || "canvas").first();
    if (await page.locator(cell.canvas_selector || "canvas").count() < 1) throw capabilityError("game canvas did not resolve", "/cell/canvas_selector");
    await canvas.focus().catch(() => canvas.click({ position: { x: 1, y: 1 } }));
    const client = await context.newCDPSession(page);
    await client.send("Performance.enable");
    const clock = await clockMarker(page, client);
    const durationMs = cell.duration_ms || Math.round((cell.duration_seconds || 60) * 1000);
    const paddingMs = Number.isFinite(cell.padding_ms) ? cell.padding_ms : 100;
    if (paddingMs < 0 || paddingMs > 10000) throw inputError("cell.padding_ms must be between 0 and 10000", "/cell/padding_ms");
    const window = { start_ms: clock.monotonicMs + paddingMs, end_ms: clock.monotonicMs + paddingMs + durationMs };
    const samplerIntervalMs = Number.isFinite(cell.canvas_sampling_interval_ms) ? cell.canvas_sampling_interval_ms : 250;
    if (samplerIntervalMs < 50 || samplerIntervalMs > 5000) throw inputError("cell.canvas_sampling_interval_ms must be between 50 and 5000", "/cell/canvas_sampling_interval_ms");
    const sampler = await installCanvasSampler(page, cell.canvas_selector || cell.game_canvas?.canvas_selector || "canvas", samplerIntervalMs);
    const backend = await canvasBackend(page, cell.canvas_selector || cell.game_canvas?.canvas_selector || "canvas");
    const wallStart = Date.now();
    const trace = await collectCDPTrace(client, { durationMs: durationMs + (2 * paddingMs), categories: cell.trace_categories, timeoutMs: cell.trace_timeout_ms || Math.max(120000, durationMs + (2 * paddingMs) + 60000) });
    const callbacks = (await page.evaluate(() => window.__orchRafTimes.slice())).map(value => value + clock.offsetMs);
    const canvasSamples = (await page.evaluate(() => window.__orchCanvasSampler?.samples || []))
      .map(item => ({...item, timestamp_ms: item.timestamp_ms + clock.offsetMs}));
    const wallEnd = Date.now();
    const traceTimes = trace.traceEvents.map(eventTimeMs).filter(value => value !== null);
    const parsed = {
      ...trace,
      canvas_samples: canvasSamples,
      canvas_instrumentation: {method: "canvas.toDataURL", selector: cell.canvas_selector || cell.game_canvas?.canvas_selector || "canvas", interval_ms: samplerIntervalMs, clock: "performance.now+cdp-offset", read_only: sampler.installed === true, errors: canvasSamples.filter(item => item.error).map(item => item.error)},
      metadata: {
        clock_reconciled: true,
        clock_method: "cdp-performance-timestamp-minus-page-performance-now",
        wall_start_ms: wallStart,
        wall_end_ms: wallEnd,
        capture_start_ms: clock.monotonicMs,
        capture_end_ms: traceTimes.reduce((maximum, value) => Math.max(maximum, value), -Infinity),
        window_start_ms: window.start_ms,
        window_end_ms: window.end_ms,
        padding_before_ms: paddingMs,
        padding_after_ms: paddingMs,
      },
    };
    return {
      trace: parsed,
      rawStream: trace.rawStream,
      callbacks,
      window,
      environment: { browser: type, browser_version: browser.version?.() || null, driver: cell.browser?.package || "playwright-core", renderer_backend: backend },
      diagnostics: { server_errors: errors, wall_start_ms: wallStart, wall_end_ms: wallEnd, clock_method: parsed.metadata.clock_method, canvas_sampler: parsed.canvas_instrumentation },
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
    if (source.rawStream) {
      const rawPath = resolve(outDir, "trace.raw.json");
      await writeFile(rawPath, source.rawStream, {flag: "wx"});
      const observed = await readFile(rawPath);
      if (observed.length !== source.rawStream.length || sha256(observed) !== source.trace.raw_stream_hash) {
        throw evidenceError("raw ReturnAsStream bytes changed while writing evidence", "/trace/raw_stream_path");
      }
    }
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
