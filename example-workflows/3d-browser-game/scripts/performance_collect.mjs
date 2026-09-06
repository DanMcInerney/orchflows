/**
 * Collect one performance cell. Fixture mode is intentionally explicit and
 * retains the same raw trace/completion path as live mode, making a fixture a
 * qualification probe rather than a claimed measurement.
 */
import { spawn } from "node:child_process";
import { resolve, dirname } from "node:path";
import { mkdir, writeFile } from "node:fs/promises";
import {
  EXIT, capabilityError, inputError, makeHeader, nowIso, parseArgs,
  readJson, resultFromError, sha256, timeoutError, writeJsonAtomic,
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
    const wallStart = Date.now();
    const trace = await collectCDPTrace(client, { durationMs: durationMs + (2 * paddingMs), categories: cell.trace_categories });
    const callbacks = (await page.evaluate(() => window.__orchRafTimes.slice())).map(value => value + clock.offsetMs);
    const wallEnd = Date.now();
    const traceTimes = trace.traceEvents.map(eventTimeMs).filter(value => value !== null);
    const parsed = {
      ...trace,
      metadata: {
        clock_reconciled: true,
        clock_method: "cdp-performance-timestamp-minus-page-performance-now",
        wall_start_ms: wallStart,
        wall_end_ms: wallEnd,
        capture_start_ms: clock.monotonicMs,
        capture_end_ms: traceTimes.length ? Math.max(...traceTimes) : null,
        window_start_ms: window.start_ms,
        window_end_ms: window.end_ms,
        padding_before_ms: paddingMs,
        padding_after_ms: paddingMs,
      },
    };
    return {
      trace: parsed,
      callbacks,
      window,
      environment: { browser: type, driver: cell.browser?.package || "playwright-core" },
      diagnostics: { server_errors: errors, wall_start_ms: wallStart, wall_end_ms: wallEnd, clock_method: parsed.metadata.clock_method },
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
  const qualification = qualifyPerformance({ cell: measuredCell, trace: source.trace, callbacks: source.callbacks });
  const result = {
    ...makeHeader({ kind: "performance-cell", id: cell.id, artifactCommit: cell.artifact_commit, producer: "performance_collect.mjs", inputs: { cell: sha256(JSON.stringify(cell)), trace: sha256(JSON.stringify(source.trace)) }, environment: source.environment || cell.environment || {}, status: qualification.status === "qualified" ? "complete" : "unverified", gaps: (qualification.failures || []).map(item => item.code) }),
    cell: { ...measuredCell, trace: undefined, callbacks: undefined },
    source: live ? "live-browser" : "qualification-fixture",
    diagnostics: source.diagnostics,
    trace: source.trace,
    callbacks: source.callbacks,
    qualification,
    observed_at: nowIso(),
  };
  if (outDir) {
    await mkdir(resolve(outDir), { recursive: true });
    await writeJsonAtomic(resolve(outDir, "cell-result.json"), result);
    await writeJsonAtomic(resolve(outDir, "trace.json"), source.trace);
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
