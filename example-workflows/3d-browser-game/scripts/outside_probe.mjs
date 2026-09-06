/**
 * Close a joined 3D browser-game artifact from outside its child workspaces.
 * This module owns the helper identities and lifecycle. A target supplies a
 * frozen build/server/input configuration; it never supplies package command
 * lines, validators, or a replacement harness.
 */
import { spawn } from "node:child_process";
import { mkdir, readFile, readdir, rm } from "node:fs/promises";
import { createInterface } from "node:readline";
import { dirname, isAbsolute, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { canonicalJson, ensureContained, evidenceError, inputError, nowIso, parseArgs, readJson, resultFromError, sha256, writeJsonAtomic } from "./_common.mjs";
import { validateEvidenceIndex, validateGate } from "./validate_evidence.mjs";
import { validateCommand } from "./browser_harness.mjs";
import { inventory } from "./outside_build.mjs";

const PACKAGE_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const HELPER_PATHS = Object.freeze({
  build: resolve(PACKAGE_ROOT, "scripts/outside_build.mjs"),
  server: resolve(PACKAGE_ROOT, "scripts/outside_server.mjs"),
  harness: resolve(PACKAGE_ROOT, "scripts/outside_harness.mjs"),
});

function run(argv, cwd, timeoutMs = 60000) {
  if (!Array.isArray(argv) || argv.length === 0 || argv.some(value => typeof value !== "string" || !value)) throw inputError("outside probe command must be a non-empty argv array", "/probe/command");
  return new Promise((done, fail) => {
    const child = spawn(argv[0], argv.slice(1), { cwd, shell: false, detached: process.platform !== "win32", stdio: ["ignore", "pipe", "pipe"], windowsHide: true });
    const stdout = [];
    const stderr = [];
    let settled = false;
    let timer;
    let timeoutError;
    const finish = (value, rejected = false) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      rejected ? fail(value) : done(value);
    };
    child.stdout?.on("data", chunk => stdout.push(chunk));
    child.stderr?.on("data", chunk => stderr.push(chunk));
    child.once("error", error => finish(error, true));
    child.once("exit", (code, signal) => {
      if (!timeoutError) finish({ code, signal, stdout: Buffer.concat(stdout).toString("utf8"), stderr: Buffer.concat(stderr).toString("utf8"), pid: child.pid });
    });
    timer = setTimeout(async () => {
      timeoutError = Object.assign(new Error(`outside probe exceeded ${timeoutMs}ms`), { code: "timeout-process-loss", pointer: "/probe/timeout_ms" });
      await terminate(child);
      finish(timeoutError, true);
    }, timeoutMs);
    timer.unref();
  });
}

function terminate(child, timeoutMs = 5000) {
  if (!child || child.exitCode !== null || child.signalCode) return Promise.resolve({ observed: true, code: child?.exitCode ?? null, signal: child?.signalCode ?? null });
  return new Promise(resolvePromise => {
    let finished = false;
    let timer;
    const finish = () => {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      resolvePromise({ observed: child.exitCode !== null || child.signalCode !== null, code: child.exitCode, signal: child.signalCode });
    };
    child.once("exit", finish);
    if (process.platform === "win32") spawn("taskkill", ["/PID", String(child.pid), "/T", "/F"], { windowsHide: true }).once("exit", () => { if (child.exitCode !== null) finish(); });
    else { try { process.kill(-child.pid, "SIGTERM"); } catch { child.kill("SIGTERM"); } }
    timer = setTimeout(() => {
      if (child.exitCode === null && child.signalCode === null) {
        if (process.platform === "win32") spawn("taskkill", ["/PID", String(child.pid), "/T", "/F"], { windowsHide: true });
        else { try { process.kill(-child.pid, "SIGKILL"); } catch { child.kill("SIGKILL"); } }
      }
      finish();
    }, timeoutMs);
    timer.unref();
  });
}

function fixedCommand(helper, args = []) {
  if (!Object.hasOwn(HELPER_PATHS, helper)) throw inputError(`unknown package helper ${helper}`, "/outside_probe/helper");
  if (!Array.isArray(args) || args.some(value => typeof value !== "string" || !value)) throw inputError("package helper arguments must be non-empty strings", "/outside_probe/helper/args");
  return [process.execPath, HELPER_PATHS[helper], ...args];
}

/* Kept as a named seam for callers that inspect package command construction. */
export function packageOwnedCommand(helper, args = []) { return fixedCommand(helper, args); }

function probeTranscript(value, artifactCommit) {
  let lines;
  try { lines = typeof value === "string" ? value.split(/\r?\n/).filter(Boolean).map(line => JSON.parse(line)) : value; }
  catch (error) { throw evidenceError(`outside probe transcript is not valid JSONL: ${error.message}`, "/probe/transcript"); }
  if (!Array.isArray(lines)) throw evidenceError("outside probe transcript must be JSONL or an array", "/probe/transcript");
  if (!lines.length || lines.some(item => !item || typeof item !== "object" || Array.isArray(item))) throw evidenceError("outside probe transcript needs structured browser observations", "/probe/transcript");
  const types = lines.map(item => item?.type);
  const allowed = new Set(["ready", "observe", "key", "pointer", "wait", "capture", "stop"]);
  if (types.some(type => !allowed.has(type)) || !types.includes("ready") || !types.includes("observe")) throw evidenceError("outside probe lacked current ready/observe evidence", "/probe/transcript");
  if (!types.some(type => type === "key" || type === "pointer")) throw evidenceError("outside probe lacked ordinary input", "/probe/transcript");
  if (!types.includes("stop") || types.at(-1) !== "stop") throw evidenceError("outside probe did not close the ordinary-input session", "/probe/transcript");
  let previousSequence = 0;
  let previousMonotonic = -Infinity;
  let previousWall = -Infinity;
  let sessionId = null;
  let ordinaryIndex = -1;
  let beforeObservation = false;
  let afterObservation = false;
  for (const [index, item] of lines.entries()) {
    if (item?.classification === "pass" || item?.input_mode === "actual_play") throw evidenceError("probe transcript cannot self-assign a gate or play label", "/probe/transcript");
    if (item.artifact_commit !== artifactCommit) throw evidenceError("probe observed a missing or different artifact commit", "/probe/transcript/artifact_commit");
    if (!Number.isInteger(item.sequence) || item.sequence <= previousSequence) throw evidenceError("outside probe sequence is not strictly increasing", "/probe/transcript/sequence");
    if (typeof item.wall_time !== "string") throw evidenceError("outside probe facts need causally ordered monotonic and wall timestamps", "/probe/transcript/time");
    const wall = Date.parse(item.wall_time);
    if (!Number.isFinite(item.monotonic_ms) || item.monotonic_ms < 0 || !Number.isFinite(wall) || item.monotonic_ms < previousMonotonic || wall < previousWall) throw evidenceError("outside probe facts need causally ordered monotonic and wall timestamps", "/probe/transcript/time");
    if (typeof item.session_id !== "string" || !item.session_id) throw evidenceError("outside probe facts need a browser session identity", "/probe/transcript/session_id");
    if (sessionId === null) sessionId = item.session_id;
    if (sessionId !== item.session_id) throw evidenceError("outside probe facts mix browser session identities", "/probe/transcript/session_id");
    if (item.type === "ready" && item.status !== "ready") throw evidenceError("outside probe ready event is not a successful readiness observation", "/probe/transcript/status");
    if (item.type !== "ready" && item.status !== "ok") throw evidenceError("outside probe returned an input/runtime error", "/probe/transcript/status");
    if (item.type !== "ready") {
      if (!item.snapshot || typeof item.snapshot !== "object" || typeof item.snapshot.url !== "string" || !item.snapshot.url || !Number.isInteger(item.snapshot.canvas_count) || item.snapshot.canvas_count < 1 || !Array.isArray(item.snapshot.canvases) || !item.snapshot.canvases.some(canvas => canvas && canvas.connected !== false && Number(canvas.width) > 0 && Number(canvas.height) > 0)) throw evidenceError("outside probe ordinary evidence lacks a rendered snapshot", "/probe/transcript/snapshot");
      if (["observe", "capture"].includes(item.type) && typeof item.screenshot_hash !== "string") throw evidenceError(`outside probe ${item.type} lacks a screenshot hash`, "/probe/transcript/screenshot_hash");
    }
    if (["key", "pointer"].includes(item.type)) ordinaryIndex = index;
    if (item.type === "observe" && ordinaryIndex < 0) beforeObservation = true;
    if (item.type === "observe" && ordinaryIndex >= 0) afterObservation = true;
    if (item.type === "stop" && item.status !== "ok") throw evidenceError("outside probe did not close successfully", "/probe/transcript/status");
    previousSequence = item.sequence;
    previousMonotonic = item.monotonic_ms;
    previousWall = wall;
  }
  if (!beforeObservation || !afterObservation) throw evidenceError("outside probe lacks a successful observation before and after ordinary input", "/probe/transcript");
  return { status: "observed", artifact_commit: artifactCommit, observed_at: lines.at(-1).wall_time, lines: lines.length, ordinary_input: true, session_id: sessionId, observations: types.filter(type => type === "observe").length };
}

function relativeWorkspacePath(root, value, pointer) {
  if (typeof value !== "string" || !value || isAbsolute(value)) throw inputError("path must be a non-empty relative string", pointer);
  const target = ensureContained(root, resolve(root, value), pointer);
  const normalized = relative(root, target).replaceAll("\\", "/");
  if (!normalized || normalized === ".") throw inputError("path must name a workspace child", pointer);
  return { target, path: normalized };
}

function validateConfig(config) {
  if (!config || typeof config !== "object" || Array.isArray(config)) throw inputError("outside probe config must be an object", "/outside_probe/config");
  const known = new Set(["build", "server", "harness", "browser", "game", "operator", "independent_context_id"]);
  for (const key of Object.keys(config)) if (!known.has(key)) throw inputError(`outside probe config has unknown field ${key}`, `/outside_probe/config/${key}`);
  const build = config.build;
  const server = config.server;
  const harness = config.harness;
  if (!build || typeof build !== "object" || !Array.isArray(build.command) || !build.command.length) throw inputError("outside probe config requires a build command", "/outside_probe/config/build");
  if (build.command.some(value => typeof value !== "string" || !value)) throw inputError("build.command entries must be non-empty strings", "/outside_probe/config/build/command");
  if (!build.output_dir || typeof build.output_dir !== "string" || isAbsolute(build.output_dir)) throw inputError("build.output_dir must be relative", "/outside_probe/config/build/output_dir");
  if (!server || typeof server !== "object" || !server.output_dir || typeof server.output_dir !== "string" || isAbsolute(server.output_dir)) throw inputError("outside probe config requires a relative server.output_dir", "/outside_probe/config/server/output_dir");
  if (relative(resolve(build.output_dir), resolve(server.output_dir)) !== "" || relative(resolve(server.output_dir), resolve(build.output_dir)) !== "") throw inputError("server.output_dir must exactly match build.output_dir", "/outside_probe/config/server/output_dir");
  if (!server.ready_path || typeof server.ready_path !== "string" || !server.ready_path.startsWith("/") || server.ready_path.includes("..")) throw inputError("server.ready_path must be an absolute URL path without traversal", "/outside_probe/config/server/ready_path");
  if (!harness || typeof harness !== "object" || !Array.isArray(harness.commands) || !harness.commands.length) throw inputError("outside probe config requires harness.commands", "/outside_probe/config/harness/commands");
  for (const [index, command] of harness.commands.entries()) {
    try { validateCommand(command); }
    catch (error) { throw inputError(`invalid ordinary-input scenario command: ${error.message}`, `/outside_probe/config/harness/commands/${index}`); }
  }
  const types = harness.commands.map(command => command.type);
  if (!types.includes("observe") || (!types.includes("key") && !types.includes("pointer")) || types.at(-1) !== "stop") throw inputError("harness.commands must observe, use ordinary input, and end with stop", "/outside_probe/config/harness/commands");
  if (!harness.capture_dir || typeof harness.capture_dir !== "string" || isAbsolute(harness.capture_dir)) throw inputError("harness.capture_dir must be relative", "/outside_probe/config/harness/capture_dir");
  if (!harness.session_out || typeof harness.session_out !== "string" || isAbsolute(harness.session_out)) throw inputError("harness.session_out must be relative", "/outside_probe/config/harness/session_out");
  if (config.browser !== undefined && (!config.browser || typeof config.browser !== "object" || Array.isArray(config.browser) || config.browser.headless === true)) throw inputError("outside probe browser must describe a headed browser", "/outside_probe/config/browser");
  if (config.game !== undefined && (!config.game || typeof config.game !== "object" || Array.isArray(config.game))) throw inputError("outside probe game must be an object", "/outside_probe/config/game");
  return config;
}

async function readProbeConfig(probe, root) {
  if (probe?.config && typeof probe.config === "object" && !Array.isArray(probe.config)) return validateConfig(probe.config);
  if (typeof probe?.config_path === "string" && probe.config_path) {
    const configPath = relativeWorkspacePath(root, probe.config_path, "/outside_probe/config_path");
    const loaded = await readJson(configPath.target);
    if (probe.config_sha256 && loaded.hash !== probe.config_sha256) throw evidenceError("outside probe config hash does not match its bytes", "/outside_probe/config_sha256");
    return validateConfig(loaded.value);
  }
  return null;
}

async function gitHead(root) {
  const result = await run(["git", "rev-parse", "HEAD"], root, 10000);
  if (result.code !== 0) throw evidenceError(`workspace git identity failed: ${result.stderr.trim()}`, "/workspace");
  return result.stdout.trim();
}

async function runPackageJson(helper, args, cwd, timeoutMs, name) {
  const result = await run(fixedCommand(helper, args), cwd, timeoutMs);
  if (result.code !== 0) throw evidenceError(`${name} helper exited ${result.code ?? "unknown"}${result.signal ? ` (${result.signal})` : ""}: ${result.stderr.trim()}`, `/outside_probe/${name}`);
  const lines = result.stdout.split(/\r?\n/).filter(Boolean);
  if (lines.length !== 1) throw evidenceError(`${name} helper must emit exactly one JSON result`, `/outside_probe/${name}/output`);
  try { return JSON.parse(lines[0]); }
  catch (error) { throw evidenceError(`${name} helper output is not valid JSON: ${error.message}`, `/outside_probe/${name}/output`); }
}

async function spawnReadyServer(configPath, root, artifactCommit, outputHash, timeoutMs) {
  const command = fixedCommand("server", ["--config", configPath, "--workspace", root, "--artifact-commit", artifactCommit, "--output-sha256", outputHash]);
  const child = spawn(command[0], command.slice(1), { cwd: PACKAGE_ROOT, shell: false, detached: process.platform !== "win32", windowsHide: true, stdio: ["ignore", "pipe", "pipe"] });
  const stdout = [];
  const stderr = [];
  child.stdout?.on("data", chunk => stdout.push(chunk));
  child.stderr?.on("data", chunk => stderr.push(chunk));
  const ready = await new Promise((resolvePromise, rejectPromise) => {
    const reader = createInterface({ input: child.stdout, crlfDelay: Infinity });
    let settled = false;
    let timer;
    let timeoutError;
    const finish = (value, rejected = false) => { if (settled) return; settled = true; clearTimeout(timer); reader.close(); rejected ? rejectPromise(value) : resolvePromise(value); };
    reader.once("line", line => {
      try {
        const value = JSON.parse(line);
        if (value.status !== "ready" || value.artifact_commit !== artifactCommit || !value.address?.url || !value.output?.sha256) throw evidenceError("server helper did not report a bound readiness observation", "/outside_probe/server/output");
        finish(value);
      } catch (error) { finish(error, true); }
    });
    child.once("error", error => finish(error, true));
    child.once("exit", (code, signal) => {
      if (!timeoutError) finish(evidenceError(`server helper exited before readiness (${code ?? "unknown"}${signal ? `, ${signal}` : ""})`, "/outside_probe/server"), true);
    });
    timer = setTimeout(async () => {
      timeoutError = Object.assign(new Error(`server readiness exceeded ${timeoutMs}ms`), { code: "timeout-process-loss", pointer: "/outside_probe/server/timeout_ms" });
      await terminate(child);
      finish(timeoutError, true);
    }, timeoutMs);
    timer.unref();
  }).catch(async error => { await terminate(child); throw error; });
  return { child, ready, stdout, stderr };
}

async function runInteractiveHarness(configPath, commands, artifactCommit, timeoutMs) {
  const command = fixedCommand("harness", ["--config", configPath]);
  const child = spawn(command[0], command.slice(1), { cwd: PACKAGE_ROOT, shell: false, detached: process.platform !== "win32", windowsHide: true, stdio: ["pipe", "pipe", "pipe"] });
  const stderr = [];
  const parsed = [];
  const reader = createInterface({ input: child.stdout, crlfDelay: Infinity });
  const lines = [];
  let pending = [];
  let streamError;
  const deliver = value => {
    const waiter = pending.shift();
    if (waiter) waiter.resolve(value);
    else lines.push(value);
  };
  reader.on("line", line => {
    try {
      const value = JSON.parse(line);
      parsed.push(value);
      deliver(value);
    } catch (error) {
      streamError = evidenceError(`browser harness output is not valid JSONL: ${error.message}`, "/outside_probe/harness/output");
      for (const waiter of pending.splice(0)) waiter.reject(streamError);
    }
  });
  child.stderr?.on("data", chunk => stderr.push(chunk));
  const nextLine = () => {
    if (streamError) return Promise.reject(streamError);
    const buffered = lines.shift();
    if (buffered) return Promise.resolve(buffered);
    return new Promise((resolvePromise, rejectPromise) => pending.push({ resolve: resolvePromise, reject: rejectPromise }));
  };
  let timer;
  let timeoutError;
  const processExit = new Promise((resolvePromise, rejectPromise) => {
    child.once("error", rejectPromise);
    child.once("exit", (code, signal) => {
      if (timeoutError) return;
      clearTimeout(timer);
      resolvePromise({ code, signal });
      const error = code === 0 ? null : evidenceError(`browser harness exited ${code ?? "unknown"}${signal ? ` (${signal})` : ""}: ${Buffer.concat(stderr).toString("utf8").trim()}`, "/outside_probe/harness");
      for (const waiter of pending.splice(0)) {
        if (error) waiter.reject(error);
        else waiter.reject(evidenceError("browser harness closed before returning its expected JSONL reply", "/outside_probe/harness/output"));
      }
    });
  });
  timer = setTimeout(async () => {
    timeoutError = Object.assign(new Error(`browser harness exceeded ${timeoutMs}ms`), { code: "timeout-process-loss", pointer: "/outside_probe/harness/timeout_ms" });
    for (const waiter of pending.splice(0)) waiter.reject(timeoutError);
    await terminate(child);
  }, timeoutMs);
  timer.unref();
  try {
    const ready = await nextLine();
    if (ready.type !== "ready" || ready.status !== "ready") throw evidenceError("browser harness did not report a successful ready observation", "/outside_probe/harness/output");
    for (const input of commands) {
      child.stdin.write(`${JSON.stringify(input)}\n`);
      const reply = await nextLine();
      if (reply.type !== input.type || reply.status !== "ok") throw evidenceError(`browser harness returned an unsuccessful ${input.type} reply`, "/outside_probe/harness/output");
    }
    child.stdin.end();
    const result = await processExit;
    if (result.code !== 0) throw evidenceError(`browser harness exited ${result.code ?? "unknown"}${result.signal ? ` (${result.signal})` : ""}: ${Buffer.concat(stderr).toString("utf8").trim()}`, "/outside_probe/harness");
  } catch (error) {
    await terminate(child);
    throw error;
  } finally {
    reader.close();
    clearTimeout(timer);
  }
  if (!parsed.length) throw evidenceError("browser harness emitted no JSONL evidence", "/outside_probe/harness/output");
  const summary = parsed.at(-1);
  if (!summary || summary.status !== "observed" || summary.artifact_commit !== artifactCommit) throw evidenceError("browser harness did not return a bound observed result", "/outside_probe/harness/output");
  return { child, result: await processExit, lines: parsed, summary, stderr: Buffer.concat(stderr).toString("utf8") };
}

async function fileInventory(directory) {
  const files = [];
  async function visit(current) {
    const entries = await readdir(current, { withFileTypes: true });
    for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
      const target = resolve(current, entry.name);
      if (entry.isDirectory()) await visit(target);
      else if (entry.isFile()) {
        const bytes = await readFile(target);
        files.push({ path: relative(directory, target).replaceAll("\\", "/"), bytes: bytes.length, sha256: sha256(bytes) });
      } else throw evidenceError(`captured evidence contains unsupported entry ${entry.name}`, "/outside_probe/captures");
    }
  }
  await visit(directory);
  files.sort((left, right) => left.path.localeCompare(right.path));
  return { files, sha256: sha256(canonicalJson(files)), file_count: files.length, bytes: files.reduce((sum, item) => sum + item.bytes, 0) };
}

async function outsideProbe(index, { workspace, baseDir = process.cwd() } = {}) {
  if (!workspace) throw inputError("joined workspace is required", "/workspace");
  const root = resolve(workspace);
  const joinedCommit = await gitHead(root);
  const expectedCommit = String(index.artifact_commit || "").replace(/^git:/, "");
  if (!expectedCommit || joinedCommit.toLowerCase() !== expectedCommit.toLowerCase()) throw evidenceError(`joined commit mismatch: expected ${expectedCommit}, observed ${joinedCommit}`, "/artifact_commit");
  const evidence = await validateEvidenceIndex(index, { baseDir });
  const probe = index.outside_probe || index.probe;
  const config = await readProbeConfig(probe, root);
  if (!config) {
    if (probe?.transcript !== undefined) return { status: "unverified", joined_commit: joinedCommit, evidence_ids: evidence.ids, transcript: probeTranscript(probe.transcript, index.artifact_commit), reason: "no executable production probe declared" };
    throw evidenceError("outside close requires a target-owned frozen production probe config", "/outside_probe/config");
  }
  const configPath = resolve(root, ".orch-notes", `outside-config-${process.pid}-${Date.now()}.json`);
  const capturePath = relativeWorkspacePath(root, config.harness.capture_dir, "/outside_probe/config/harness/capture_dir");
  const sessionPath = relativeWorkspacePath(root, config.harness.session_out, "/outside_probe/config/harness/session_out");
  const buildOutput = relativeWorkspacePath(root, config.build.output_dir, "/outside_probe/config/build/output_dir");
  relativeWorkspacePath(root, config.server.output_dir, "/outside_probe/config/server/output_dir");
  const captureDir = capturePath.target;
  const sessionOut = sessionPath.target;
  await mkdir(dirname(configPath), { recursive: true });
  await writeJsonAtomic(configPath, { ...config, artifact_commit: index.artifact_commit, server: { ...config.server, cwd: root } });
  await rm(captureDir, { recursive: true, force: true });
  await rm(sessionOut, { force: true });
  let serverHandle;
  let harnessHandle;
  let cleanup = { harness: null, server: null };
  try {
    const build = await runPackageJson("build", ["--config", configPath, "--workspace", root, "--artifact-commit", index.artifact_commit], PACKAGE_ROOT, (config.build.timeout_ms || 120000) + 10000, "build");
    if (build.status !== "built" || build.artifact_commit !== index.artifact_commit || build.output?.sha256 === undefined || build.output.path !== buildOutput.path) throw evidenceError("production build result is incomplete or not bound to the target output", "/outside_probe/build/output");
    const server = await spawnReadyServer(configPath, root, index.artifact_commit, build.output.sha256, (config.server.startup_timeout_ms || 30000) + 5000);
    serverHandle = server;
    const harnessConfig = { ...config, artifact_commit: index.artifact_commit, server: { ...config.server, external: true, cwd: root, url: server.ready.address.url }, capture_dir: captureDir, session_out: sessionOut, mode: "scripted_input" };
    await writeJsonAtomic(configPath, harnessConfig);
    harnessHandle = await runInteractiveHarness(configPath, config.harness.commands, index.artifact_commit, (config.harness.timeout_ms || 120000) + 10000);
    if (serverHandle.child.exitCode !== null || serverHandle.child.signalCode !== null) throw evidenceError("production server exited while the ordinary-input harness was running", "/outside_probe/server");
    const sessionDocument = (await readJson(sessionOut)).value;
    const transcriptLines = [{ ...(harnessHandle.lines.find(item => item.type === "ready") || {}), type: "ready" }, ...sessionDocument.transcript.map(item => ({ ...item.reply, type: item.command.type }))];
    const harnessEvidence = probeTranscript(transcriptLines, index.artifact_commit);
    if (sessionDocument.artifact_commit !== index.artifact_commit || sessionDocument.status !== "complete" || sessionDocument.source !== "live-browser" || sessionDocument.headed !== true || sessionDocument.transcript_hash !== harnessHandle.summary.transcript_hash) throw evidenceError("browser session is incomplete or disagrees with the package harness result", "/outside_probe/harness/session");
    const captures = await fileInventory(captureDir);
    if (!captures.file_count || !captures.files.some(file => /\.png$/i.test(file.path) && file.bytes > 0)) throw evidenceError("outside harness did not preserve a captured rendered image", "/outside_probe/captures");
    const finalCommit = await gitHead(root);
    if (finalCommit.toLowerCase() !== expectedCommit.toLowerCase()) throw evidenceError(`joined commit changed during outside close: expected ${expectedCommit}, observed ${finalCommit}`, "/artifact_commit");
    const finalOutput = await inventory(root, buildOutput.target);
    if (finalOutput.sha256 !== build.output.sha256) throw evidenceError("production output changed after the observed harness session", "/outside_probe/build/output");
    const core = await validateGate(index, "core", { baseDir });
    const final = await validateGate(index, "final", { baseDir });
    return { status: "observed", artifact_commit: index.artifact_commit, joined_commit: joinedCommit, observed_at: nowIso(), evidence_ids: evidence.ids, build, server: server.ready, harness: { ...harnessEvidence, session_id: sessionDocument.id, transcript_hash: sessionDocument.transcript_hash, session_path: sessionPath.path }, captures, gates: { core, final }, cleanup };
  } finally {
    if (harnessHandle?.child) cleanup.harness = await terminate(harnessHandle.child);
    if (serverHandle?.child) cleanup.server = await terminate(serverHandle.child);
    await rm(configPath, { force: true });
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.index || !args.workspace) throw inputError("--index and --workspace are required");
  const { value: index } = await readJson(resolve(args.index));
  const result = await outsideProbe(index, { workspace: resolve(args.workspace), baseDir: dirname(resolve(args.index)) });
  process.stdout.write(`${JSON.stringify(result)}\n`);
  if (result.status === "unverified") process.exitCode = 3;
}

if (process.argv[1] && resolve(process.argv[1]) === resolve(fileURLToPath(import.meta.url))) {
  main().catch(error => { const result = resultFromError(error); process.stderr.write(`${result.result.error.message}\n`); process.stdout.write(`${JSON.stringify(result.result)}\n`); process.exitCode = result.exitCode; });
}

export { outsideProbe, probeTranscript, run, validateConfig };
