/**
 * JSON-lines ordinary-input browser harness. The only page inspection is a
 * fixed, read-only DOM snapshot; the harness has no route for invoking game
 * methods or changing game state. A transcript is useful evidence only when
 * its computed label and adaptation metadata support that claim.
 */
import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, relative, resolve } from "node:path";
import { buildFrameModel } from "./trace_frames.mjs";
import {
  EXIT, capabilityError, canonicalJson, inputError, makeHeader, nowIso,
  parseArgs, readJson, resultFromError, sha256, timeoutError, writeJsonAtomic,
} from "./_common.mjs";

const COMMAND_FIELDS = Object.freeze({
  observe: [],
  key: ["key", "action"],
  pointer: ["x", "y", "action", "button"],
  wait: ["ms"],
  capture: ["label"],
  stop: [],
});
const DEFAULT_KEYS = new Set(["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "w", "a", "s", "d", "Space", "Escape", "Enter"]);

function monotonicMs(origin) {
  return Number(process.hrtime.bigint() - origin) / 1e6;
}

function rejectUnknownFields(command, allowed) {
  for (const key of Object.keys(command)) {
    if (key !== "type" && !allowed.includes(key)) {
      throw inputError(`unknown ${command.type} field ${key}; provenance labels are harness-owned`, `/${key}`);
    }
  }
}

function validateCommand(command) {
  if (!command || typeof command !== "object" || Array.isArray(command)) throw inputError("JSONL command must be an object", "/command");
  if (typeof command.type !== "string" || !Object.hasOwn(COMMAND_FIELDS, command.type)) throw inputError(`unsupported command type ${JSON.stringify(command.type)}`, "/type");
  rejectUnknownFields(command, COMMAND_FIELDS[command.type]);
  if (command.type === "key") {
    if (typeof command.key !== "string" || !command.key || command.key.length > 32) throw inputError("key requires a short key name", "/key");
    if (command.action !== "down" && command.action !== "up") throw inputError("key action must be down or up", "/action");
  }
  if (command.type === "pointer") {
    if (!Number.isFinite(command.x) || !Number.isFinite(command.y)) throw inputError("pointer x/y must be finite", "/pointer");
    if (!["move", "down", "up"].includes(command.action)) throw inputError("pointer action must be move, down, or up", "/action");
    if (command.button !== undefined && !["left", "middle", "right"].includes(command.button)) throw inputError("pointer button is invalid", "/button");
  }
  if (command.type === "wait") {
    if (!Number.isFinite(command.ms) || command.ms < 0 || command.ms > 60000) throw inputError("wait ms must be between 0 and 60000", "/ms");
  }
  if (command.type === "capture" && command.label !== undefined && (typeof command.label !== "string" || command.label.length > 120)) throw inputError("capture label must be a short string", "/label");
  return command;
}

function commandHasAdaptation(transcript) {
  return Boolean(deriveAdaptation(transcript, ""));
}

function deriveAdaptation(transcript, rationale = "") {
  const successfulObservation = item => item?.command?.type === "observe" && item.reply?.status === "ok" && item.reply?.snapshot;
  const action = transcript.find(item => ["key", "pointer"].includes(item?.command?.type) && item.reply?.status === "ok");
  if (!action) return null;
  const before = transcript.find(item => successfulObservation(item) && item.reply.sequence < action.reply.sequence);
  const after = transcript.find(item => successfulObservation(item) && item.reply.sequence > action.reply.sequence);
  if (!before || !after) return null;
  return {
    observation_sequence: before.reply.sequence,
    action_sequence: action.reply.sequence,
    subsequent_observation_sequence: after.reply.sequence,
    rationale: String(rationale || "Input selected after inspecting the current rendered game state."),
  };
}

export function classifyTranscript(transcript, config = {}) {
  const sawSimulation = transcript.some(item => item.command.type === "simulate" || item.reply?.status === "simulated");
  if (sawSimulation || config.mode === "simulated") return "simulated";
  if (config.mode === "actual_play" && config.operator && config.independent_context_id && config.headed !== false && commandHasAdaptation(transcript)) return "actual_play";
  return "scripted_input";
}

function commandArgs(config) {
  const server = config.server;
  if (!server || typeof server !== "object") throw inputError("config.server is required", "/server");
  if (server.external !== true && (!Array.isArray(server.command) || server.command.length === 0)) throw inputError("config.server.command must be a non-empty argv array", "/server/command");
  if (server.command !== undefined && (!Array.isArray(server.command) || server.command.some(part => typeof part !== "string" || !part))) throw inputError("server command entries must be non-empty strings", "/server/command");
  if (typeof server.cwd !== "string" || !server.cwd) throw inputError("config.server.cwd is required", "/server/cwd");
  if (typeof server.url !== "string" || !/^https?:\/\//.test(server.url)) throw inputError("config.server.url must be an http(s) URL", "/server/url");
  const browser = config.browser || {};
  if (browser.headless === true) throw capabilityError("actual browser evidence requires a headed render path", "/browser/headless");
  return { server, browser };
}

function stopProcess(child, timeoutMs = 5000) {
  return new Promise(resolvePromise => {
    if (!child || child.exitCode !== null || child.killed) return resolvePromise();
    let finished = false;
    const finish = () => { if (!finished) { finished = true; resolvePromise(); } };
    child.once("exit", finish);
    if (process.platform === "win32") spawn("taskkill", ["/PID", String(child.pid), "/T", "/F"], { windowsHide: true }).once("exit", finish);
    else { try { process.kill(-child.pid, "SIGTERM"); } catch { child.kill("SIGTERM"); } }
    setTimeout(() => {
      if (finished) return;
      if (process.platform === "win32") spawn("taskkill", ["/PID", String(child.pid), "/T", "/F"], { windowsHide: true });
      else { try { process.kill(-child.pid, "SIGKILL"); } catch { child.kill("SIGKILL"); } }
      finish();
    }, timeoutMs).unref();
  });
}

async function loadPlaywright(browserConfig) {
  try {
    const packageName = browserConfig.package || "playwright-core";
    return await import(packageName);
  } catch (error) {
    throw capabilityError(`Playwright is unavailable: ${error.message}`, "/browser/package");
  }
}

async function readOnlySnapshot(page, selectors = {}) {
  const selector = selectors.canvas || "canvas";
  const dom = await page.evaluate(() => {
    const values = (element) => {
      const attrs = {};
      for (const attribute of element.attributes || []) {
        if (attribute.name.startsWith("data-game-") || ["aria-label", "role"].includes(attribute.name)) attrs[attribute.name] = attribute.value;
      }
      return { tag: element.tagName.toLowerCase(), text: (element.textContent || "").trim().slice(0, 240), attrs };
    };
    return {
      title: document.title,
      url: location.href,
      visible_text: (document.body?.innerText || "").trim().slice(0, 1000),
      facts: [...document.querySelectorAll("[data-game-state], [data-game-phase], [data-game-snapshot], [data-game-score], [role=button], [aria-label]")].slice(0, 80).map(values),
      canvases: [...document.querySelectorAll("canvas")].map(canvas => ({ width: canvas.width, height: canvas.height, clientWidth: canvas.clientWidth, clientHeight: canvas.clientHeight, connected: canvas.isConnected })),
    };
  });
  const canvas = page.locator(selector).first();
  const count = await page.locator(selector).count();
  const focused = await page.evaluate(() => document.activeElement ? document.activeElement.tagName.toLowerCase() : null);
  return { ...dom, canvas_selector: selector, canvas_count: count, focused_element: focused };
}

async function screenshot(page, outputPath) {
  const bytes = await page.screenshot({ type: "png" });
  if (outputPath) {
    await mkdir(dirname(outputPath), { recursive: true });
    await writeFile(outputPath, bytes, { flag: "wx" });
  }
  return { screenshot_hash: sha256(bytes), screenshot_base64: bytes.toString("base64") };
}

export async function runHarness(config) {
  const { server, browser: browserConfig } = commandArgs(config);
  const origin = process.hrtime.bigint();
  const startedAt = nowIso();
  const sessionId = config.session_id || `session-${Date.now()}`;
  const artifactCommit = config.artifact_commit || "unbound";
  const child = server.external === true ? null : spawn(server.command[0], server.command.slice(1), {
    cwd: resolve(server.cwd), env: { ...process.env, ...(server.env || {}) },
    shell: false, detached: true, stdio: ["ignore", "pipe", "pipe"], windowsHide: true,
  });
  const serverErrors = [];
  child?.stderr?.on("data", chunk => serverErrors.push(chunk.toString("utf8").slice(-4000)));
  const transcript = [];
  const captureRefs = [];
  let sequence = 0;
  let closed = false;
  let playwright;
  let browser;
  let context;
  let page;
  const consoleDeltas = [];
  const networkDeltas = [];
  try {
    playwright = await loadPlaywright(browserConfig);
    const type = browserConfig.type || "chromium";
    if (!playwright[type]?.launch) throw capabilityError(`Playwright browser type ${type} is unavailable`, "/browser/type");
    browser = await playwright[type].launch({
      headless: false,
      executablePath: browserConfig.executable_path || browserConfig.executablePath,
      timeout: browserConfig.launch_timeout_ms || 30000,
      args: browserConfig.args || [],
    });
    context = await browser.newContext({
      viewport: browserConfig.viewport || { width: 1280, height: 720 },
      deviceScaleFactor: browserConfig.device_scale_factor || 1,
    });
    page = await context.newPage();
    page.on("console", message => consoleDeltas.push({ type: message.type(), text: message.text(), time_ms: monotonicMs(origin) }));
    page.on("requestfailed", request => networkDeltas.push({ type: "requestfailed", url: request.url(), error: request.failure()?.errorText || "unknown", time_ms: monotonicMs(origin) }));
    page.on("response", response => { if (response.status() >= 400) networkDeltas.push({ type: "http-error", url: response.url(), status: response.status(), time_ms: monotonicMs(origin) }); });
    await page.goto(server.url, { waitUntil: "domcontentloaded", timeout: server.startup_timeout_ms || 30000 });
    const canvasSelector = config.game?.canvas_selector || "canvas";
    const canvas = page.locator(canvasSelector).first();
    if (await page.locator(canvasSelector).count() < 1) throw capabilityError(`game canvas selector ${canvasSelector} did not resolve`, "/game/canvas_selector");
    await canvas.focus().catch(async () => { await canvas.click({ position: { x: 1, y: 1 } }); });
    const ready = {
      sequence: ++sequence, monotonic_ms: monotonicMs(origin), wall_time: nowIso(), type: "ready", artifact_commit: artifactCommit, session_id: sessionId,
      status: "ready", snapshot: await readOnlySnapshot(page, { canvas: canvasSelector }), console: [], network: [],
    };
    process.stdout.write(`${JSON.stringify(ready)}\n`);
    const readline = createInterface({ input: process.stdin, crlfDelay: Infinity });
    const held = new Set();
    const heldPointers = new Set();
    const emit = async (command, task) => {
      const beforeConsole = consoleDeltas.length;
      const beforeNetwork = networkDeltas.length;
      const value = await task();
      const reply = {
        sequence: ++sequence, monotonic_ms: monotonicMs(origin), wall_time: nowIso(), type: command.type, artifact_commit: artifactCommit, session_id: sessionId,
        status: "ok", ...value,
        console: consoleDeltas.slice(beforeConsole), network: networkDeltas.slice(beforeNetwork),
      };
      transcript.push({ command: { ...command }, reply: { ...reply, screenshot_base64: undefined } });
      process.stdout.write(`${JSON.stringify(reply)}\n`);
      return reply;
    };
    for await (const raw of readline) {
      if (closed) break;
      let command;
      try {
        command = validateCommand(JSON.parse(raw));
        if (command.type === "key" && !((config.game?.allowed_keys || [...DEFAULT_KEYS]).includes(command.key))) throw inputError(`key ${command.key} is not in the declared control map`, "/key");
        let reply;
        if (command.type === "observe") reply = await emit(command, async () => ({ snapshot: await readOnlySnapshot(page, { canvas: canvasSelector }), ...(await screenshot(page)) }));
        else if (command.type === "key") reply = await emit(command, async () => {
          await canvas.focus().catch(async () => canvas.click({ position: { x: 1, y: 1 } }));
          if (command.action === "down") { await page.keyboard.down(command.key); held.add(command.key); }
          else {
            if (!held.has(command.key)) throw inputError(`key ${command.key} was released without a preceding press`, "/action");
            await page.keyboard.up(command.key); held.delete(command.key);
          }
          return { key: command.key, action: command.action, held_keys: [...held], snapshot: await readOnlySnapshot(page, { canvas: canvasSelector }) };
        });
        else if (command.type === "pointer") reply = await emit(command, async () => {
          await canvas.focus().catch(async () => canvas.click({ position: { x: 1, y: 1 } }));
          const options = command.button ? { button: command.button } : {};
          const pointerButton = command.button || "left";
          if (command.action === "move") await page.mouse.move(command.x, command.y);
          else if (command.action === "down") { await page.mouse.down(options); heldPointers.add(pointerButton); }
          else {
            if (!heldPointers.has(pointerButton)) throw inputError(`pointer ${pointerButton} was released without a preceding press`, "/action");
            await page.mouse.up(options); heldPointers.delete(pointerButton);
          }
          return { pointer: { x: command.x, y: command.y, action: command.action }, snapshot: await readOnlySnapshot(page, { canvas: canvasSelector }) };
        });
        else if (command.type === "wait") reply = await emit(command, async () => { await new Promise(resolvePromise => setTimeout(resolvePromise, command.ms)); return { waited_ms: command.ms, snapshot: await readOnlySnapshot(page, { canvas: canvasSelector }) }; });
        else if (command.type === "capture") {
          const path = config.capture_dir ? resolve(config.capture_dir, `${String(sequence + 1).padStart(4, "0")}-${(command.label || "capture").replace(/[^a-z0-9_-]+/gi, "_")}.png`) : undefined;
          reply = await emit(command, async () => ({ label: command.label || null, snapshot: await readOnlySnapshot(page, { canvas: canvasSelector }), ...(await screenshot(page, path)) }));
          if (path && config.receipt_root) captureRefs.push({ path: relative(resolve(config.receipt_root), path).replaceAll("\\", "/"), sha256: reply.screenshot_hash, sequence: reply.sequence, label: command.label || null });
        } else if (command.type === "stop") {
          for (const key of [...held]) { await page.keyboard.up(key).catch(() => {}); held.delete(key); }
          for (const button of [...heldPointers]) { await page.mouse.up({ button }).catch(() => {}); heldPointers.delete(button); }
          reply = await emit(command, async () => ({ classification: classifyTranscript(transcript, { ...config, headed: true }), snapshot: await readOnlySnapshot(page, { canvas: canvasSelector }) }));
          closed = true;
          readline.close();
          break;
        }
        if (!reply) throw inputError(`command ${command.type} produced no reply`);
      } catch (error) {
        const failure = resultFromError(error).result.error;
        const reply = { sequence: ++sequence, monotonic_ms: monotonicMs(origin), wall_time: nowIso(), type: command?.type || "invalid", status: "error", error: failure, console: [], network: [] };
        if (command) transcript.push({ command: { ...command }, reply });
        process.stdout.write(`${JSON.stringify(reply)}\n`);
      }
    }
    if (!closed) {
      for (const key of [...held]) await page.keyboard.up(key).catch(() => {});
      for (const button of [...heldPointers]) await page.mouse.up({ button }).catch(() => {});
      closed = true;
    }
    const classification = classifyTranscript(transcript, { ...config, headed: true });
    const session = {
      ...makeHeader({ kind: "play-session", id: sessionId, artifactCommit, producer: "browser_harness.mjs", inputs: { config: sha256(canonicalJson(config)) }, environment: { browser: browserConfig.type || "chromium", browser_version: browser.version?.() || "unknown", driver: browserConfig.package || "playwright-core" }, status: "complete" }),
      source: "live-browser",
      classification,
      input_mode: classification,
      headed: true,
      url: server.url,
      operator: config.operator || null,
      independent_context_id: config.independent_context_id || null,
      started_at: startedAt,
      ended_at: nowIso(),
      transcript,
      transcript_hash: sha256(canonicalJson(transcript)),
      ...(config.receipt_root && config.session_out ? {
        transcript_path: relative(resolve(config.receipt_root), `${resolve(config.session_out)}.transcript.json`).replaceAll("\\", "/"),
        transcript_sha256: sha256(canonicalJson(transcript)),
        captures: captureRefs,
      } : {}),
      adaptation: classification === "actual_play" ? deriveAdaptation(transcript, config.adaptation_rationale || config.rationale) : undefined,
      console_errors: consoleDeltas.filter(item => item.type === "error"),
      network_errors: networkDeltas,
      server_errors: serverErrors,
    };
    if (config.session_out) {
      if (config.receipt_root) await writeJsonAtomic(`${resolve(config.session_out)}.transcript.json`, transcript);
      await writeJsonAtomic(resolve(config.session_out), session);
    }
    return session;
  } finally {
    await browser?.close().catch(() => {});
    await stopProcess(child);
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.config || typeof args.config !== "string") throw inputError("--config is required", "/config");
  const { value: config } = await readJson(resolve(args.config));
  const session = await runHarness(config);
  printResult({ status: "ok", classification: session.classification, session_id: session.id, transcript_hash: session.transcript_hash });
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].replaceAll("\\", "/"))) {
  main().catch(error => { const result = resultFromError(error); process.stderr.write(`${result.result.error.message}\n`); process.stdout.write(`${JSON.stringify(result.result)}\n`); process.exitCode = result.exitCode; });
}

function printResult(result) { process.stdout.write(`${JSON.stringify(result)}\n`); }

export { validateCommand, readOnlySnapshot, commandHasAdaptation, deriveAdaptation };
