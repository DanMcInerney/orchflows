/**
 * Validate the joined artifact from outside its child workspaces. The probe
 * re-hashes the evidence index, checks the joined git revision, and executes a
 * declared production probe with a wall timeout. Stored verdicts are never a
 * substitute for this observation.
 */
import { spawn } from "node:child_process";
import { resolve, dirname } from "node:path";
import { readJson, parseArgs, resultFromError, inputError, evidenceError, capabilityError, EXIT } from "./_common.mjs";
import { validateEvidenceIndex } from "./validate_evidence.mjs";

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
  const lines = typeof value === "string" ? value.split(/\r?\n/).filter(Boolean).map(line => JSON.parse(line)) : value;
  if (!Array.isArray(lines)) throw evidenceError("outside probe transcript must be JSONL or an array", "/probe/transcript");
  const types = lines.map(item => item?.type);
  if (!types.includes("ready") || !types.includes("observe")) throw evidenceError("outside probe lacked current ready/observe evidence", "/probe/transcript");
  if (!types.some(type => type === "key" || type === "pointer")) throw evidenceError("outside probe lacked ordinary input", "/probe/transcript");
  if (!types.includes("stop")) throw evidenceError("outside probe did not close the ordinary-input session", "/probe/transcript");
  for (const item of lines) {
    if (item?.classification === "pass" || item?.input_mode === "actual_play") throw evidenceError("probe transcript cannot self-assign a gate or play label", "/probe/transcript");
    if (item?.artifact_commit && item.artifact_commit !== artifactCommit) throw evidenceError("probe observed a different artifact commit", "/probe/transcript/artifact_commit");
    if (item?.status === "error") throw evidenceError("outside probe returned an input/runtime error", "/probe/transcript/status");
  }
  return { lines: lines.length, ordinary_input: true };
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
  const result = await run(probe.command, probe.cwd ? resolve(root, probe.cwd) : root, probe.timeout_ms || 60000);
  if (result.code !== 0) throw evidenceError(`outside probe exited ${result.code ?? "unknown"}${result.signal ? ` (${result.signal})` : ""}`, "/outside_probe/command");
  let observed;
  try { observed = probe.output_json ? JSON.parse(result.stdout) : probeTranscript(result.stdout, index.artifact_commit); }
  catch (error) { throw evidenceError(`outside probe output was not valid evidence: ${error.message}`, "/outside_probe/output"); }
  return { status: "observed", joined_commit: joinedCommit, evidence_ids: evidence.ids, probe: observed };
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

