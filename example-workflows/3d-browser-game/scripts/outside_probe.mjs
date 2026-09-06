/**
 * Validate the joined artifact from outside its child workspaces. The probe
 * re-hashes the evidence index, checks the joined git revision, and executes a
 * declared production probe with a wall timeout. Stored verdicts are never a
 * substitute for this observation.
 */
import { spawn } from "node:child_process";
import { resolve, dirname, relative, basename } from "node:path";
import { readJson, parseArgs, resultFromError, inputError, evidenceError, capabilityError, EXIT, ensureContained } from "./_common.mjs";
import { validateEvidenceIndex, validateGate } from "./validate_evidence.mjs";

function run(argv, cwd, timeoutMs = 60000) {
  if (!Array.isArray(argv) || argv.length === 0 || argv.some(value => typeof value !== "string" || !value)) throw inputError("outside probe command must be a non-empty argv array", "/probe/command");
  return new Promise((done, fail) => {
    const child = spawn(argv[0], argv.slice(1), { cwd, shell: false, stdio: ["ignore", "pipe", "pipe"], windowsHide: true });
    const stdout = [];
    const stderr = [];
    let settled = false;
    const finish = (value, isFailure = false) => { if (settled) return; settled = true; clearTimeout(timer); isFailure ? fail(value) : done(value); };
    child.stdout.on("data", chunk => stdout.push(chunk));
    child.stderr.on("data", chunk => stderr.push(chunk));
    child.once("error", error => finish(error, true));
    child.once("exit", (code, signal) => finish({ code, signal, stdout: Buffer.concat(stdout).toString("utf8"), stderr: Buffer.concat(stderr).toString("utf8") }));
    const timer = setTimeout(() => {
      if (process.platform === "win32") spawn("taskkill", ["/PID", String(child.pid), "/T", "/F"], { windowsHide: true });
      else { try { process.kill(-child.pid, "SIGKILL"); } catch { child.kill("SIGKILL"); } }
      finish(Object.assign(new Error(`outside probe exceeded ${timeoutMs}ms`), { code: "timeout-process-loss", pointer: "/probe/timeout_ms" }), true);
    }, timeoutMs);
    timer.unref();
  });
}

function probeTranscript(value, artifactCommit) {
  let lines;
  try { lines = typeof value === "string" ? value.split(/\r?\n/).filter(Boolean).map(line => JSON.parse(line)) : value; }
  catch (error) { throw evidenceError(`outside probe transcript is not valid JSONL: ${error.message}`, "/probe/transcript"); }
  if (!Array.isArray(lines)) throw evidenceError("outside probe transcript must be JSONL or an array", "/probe/transcript");
  if (!lines.length || lines.some(item => !item || typeof item !== "object" || Array.isArray(item))) throw evidenceError("outside probe transcript needs structured browser observations", "/probe/transcript");
  const types = lines.map(item => item?.type);
  const allowed = new Set(["ready", "observe", "key", "pointer", "stop"]);
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
      if (item.type === "observe" && typeof item.screenshot_hash !== "string") throw evidenceError("outside probe observation lacks a screenshot hash", "/probe/transcript/screenshot_hash");
    }
    if (["key", "pointer"].includes(item.type)) {
      ordinaryIndex = index;
      if (beforeObservation) afterObservation = false;
    }
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

function packageOwnedCommand(root, command, pointer) {
  if (!Array.isArray(command) || command.length === 0 || command.some(value => typeof value !== "string" || !value)) throw evidenceError("outside probe operation must be a non-empty argv array", pointer);
  const executable = basename(command[0]).toLowerCase();
  if (![basename(process.execPath).toLowerCase(), "node", "node.exe"].includes(executable)) throw evidenceError("outside probe operation must run through the package Node interpreter", pointer);
  const script = command.find(value => /(?:^|[\\/])[^\\/]+\.mjs$/i.test(value));
  if (!script) throw evidenceError("outside probe operation must name a package-owned .mjs script", pointer);
  const packageRoot = resolve(root, "example-workflows/3d-browser-game");
  const target = resolve(root, script);
  try { ensureContained(packageRoot, target, pointer); }
  catch { throw evidenceError("outside probe operation escaped the package-owned scripts", pointer); }
  const packageRelative = relative(packageRoot, target).replaceAll("\\", "/");
  if (!packageRelative.startsWith("scripts/") || packageRelative === "scripts/outside_probe.mjs") throw evidenceError("outside probe operation must use a package-owned build/server/harness script", pointer);
  return target;
}

async function runPackageOperation(operation, name, root, artifactCommit) {
  if (!operation || typeof operation !== "object") throw evidenceError(`outside close requires a declared ${name} operation`, `/outside_probe/${name}`);
  packageOwnedCommand(root, operation.command, `/outside_probe/${name}/command`);
  const cwd = operation.cwd ? resolve(root, operation.cwd) : root;
  try { ensureContained(root, cwd, `/outside_probe/${name}/cwd`); }
  catch { throw evidenceError(`${name} operation cwd escaped joined workspace`, `/outside_probe/${name}/cwd`); }
  const result = await run(operation.command, cwd, operation.timeout_ms || 120000);
  if (result.code !== 0) throw evidenceError(`${name} operation exited ${result.code ?? "unknown"}${result.signal ? ` (${result.signal})` : ""}`, `/outside_probe/${name}/command`);
  let output;
  try { output = operation.output_json === false ? probeTranscript(result.stdout, artifactCommit) : JSON.parse(result.stdout); }
  catch (error) { throw evidenceError(`${name} operation output was not valid evidence: ${error.message}`, `/outside_probe/${name}/output`); }
  if (!output || typeof output !== "object" || Array.isArray(output) || output.artifact_commit !== artifactCommit || typeof output.observed_at !== "string" || !Number.isFinite(Date.parse(output.observed_at))) throw evidenceError(`${name} operation output is not timestamped and bound to the joined artifact`, `/outside_probe/${name}/output`);
  if (!["ok", "complete", "built", "ready", "observed"].includes(output.status)) throw evidenceError(`${name} operation did not report successful production output`, `/outside_probe/${name}/output/status`);
  return output;
}

export async function outsideProbe(index, { workspace, baseDir = process.cwd() } = {}) {
  if (!workspace) throw inputError("joined workspace is required", "/workspace");
  const root = resolve(workspace);
  const revision = await run(["git", "rev-parse", "HEAD"], root, 10000);
  if (revision.code !== 0) throw evidenceError(`workspace git identity failed: ${revision.stderr.trim()}`, "/workspace");
  const joinedCommit = revision.stdout.trim();
  const expectedCommit = String(index.artifact_commit || "").replace(/^git:/, "");
  if (!expectedCommit || joinedCommit.toLowerCase() !== expectedCommit.toLowerCase()) throw evidenceError(`joined commit mismatch: expected ${expectedCommit}, observed ${joinedCommit}`, "/artifact_commit");
  const evidence = await validateEvidenceIndex(index, { baseDir });
  const probe = index.outside_probe || index.probe;
  if (!probe || !Array.isArray(probe.command)) {
    if (probe?.transcript !== undefined) return { status: "unverified", joined_commit: joinedCommit, evidence_ids: evidence.ids, transcript: probeTranscript(probe.transcript, index.artifact_commit), reason: "no executable production probe declared" };
    throw capabilityError("outside close requires a declared executable production probe", "/outside_probe/command");
  }
  const build = await runPackageOperation(probe.build, "build", root, index.artifact_commit);
  const server = await runPackageOperation(probe.server, "server", root, index.artifact_commit);
  const harness = probe.harness || { command: probe.command, cwd: probe.cwd, timeout_ms: probe.timeout_ms, output_json: probe.output_json };
  packageOwnedCommand(root, harness.command, "/outside_probe/harness/command");
  const harnessCwd = harness.cwd ? resolve(root, harness.cwd) : root;
  try { ensureContained(root, harnessCwd, "/outside_probe/harness/cwd"); }
  catch { throw evidenceError("harness operation cwd escaped joined workspace", "/outside_probe/harness/cwd"); }
  const harnessResult = await run(harness.command, harnessCwd, harness.timeout_ms || 120000);
  if (harnessResult.code !== 0) throw evidenceError(`harness operation exited ${harnessResult.code ?? "unknown"}${harnessResult.signal ? ` (${harnessResult.signal})` : ""}`, "/outside_probe/harness/command");
  let observed;
  try { observed = harness.output_json ? JSON.parse(harnessResult.stdout) : probeTranscript(harnessResult.stdout, index.artifact_commit); }
  catch (error) { throw evidenceError(`outside probe output was not valid evidence: ${error.message}`, "/outside_probe/output"); }
  if (!observed || observed.artifact_commit !== index.artifact_commit || typeof observed.observed_at !== "string" || !Number.isFinite(Date.parse(observed.observed_at)) || !["ok", "complete", "built", "ready", "observed"].includes(observed.status)) throw evidenceError("outside harness output is not timestamped, successful, and bound to the joined artifact", "/outside_probe/harness/output");
  const core = await validateGate(index, "core", { baseDir });
  const final = await validateGate(index, "final", { baseDir });
  return { status: "observed", joined_commit: joinedCommit, evidence_ids: evidence.ids, build, server, harness: observed, gates: { core, final } };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.index || !args.workspace) throw inputError("--index and --workspace are required");
  const { value: index } = await readJson(resolve(args.index));
  const result = await outsideProbe(index, { workspace: resolve(args.workspace), baseDir: dirname(resolve(args.index)) });
  process.stdout.write(`${JSON.stringify(result)}\n`);
  if (result.status === "unverified") process.exitCode = EXIT.CAPABILITY;
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].replaceAll("\\", "/"))) {
  main().catch(error => { const result = resultFromError(error); process.stderr.write(`${result.result.error.message}\n`); process.stdout.write(`${JSON.stringify(result.result)}\n`); process.exitCode = result.exitCode; });
}

export { probeTranscript, run };
