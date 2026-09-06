/**
 * Run a target's declared production build and inventory the bytes it made.
 * The target owns the build argv; this package owns this helper's executable,
 * the clean output boundary, commit check, and result shape.
 */
import { spawn } from "node:child_process";
import { readdir, readFile, realpath, rm, stat } from "node:fs/promises";
import { dirname, isAbsolute, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { canonicalJson, ensureContained, evidenceError, inputError, nowIso, parseArgs, readJson, resultFromError, sha256 } from "./_common.mjs";

const PACKAGE_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");

function relativeTarget(root, value, pointer) {
  if (typeof value !== "string" || !value || isAbsolute(value)) throw inputError("path must be a non-empty relative string", pointer);
  const target = ensureContained(root, resolve(root, value), pointer);
  const normalized = relative(resolve(root), target).replaceAll("\\", "/");
  if (!normalized || normalized === ".") throw inputError("path must name a child directory", pointer);
  if (normalized.split("/").includes(".git")) throw evidenceError("production output cannot be inside Git metadata", pointer);
  return { target, path: normalized };
}

function assertArgv(value, pointer) {
  if (!Array.isArray(value) || value.length === 0 || value.some(item => typeof item !== "string" || !item)) throw inputError("build command must be a non-empty argv array", pointer);
  return [...value];
}

function validateConfig(config) {
  if (!config || typeof config !== "object" || Array.isArray(config)) throw inputError("outside probe config must be an object", "/config");
  const build = config.build;
  if (!build || typeof build !== "object" || Array.isArray(build)) throw inputError("outside probe config requires build", "/build");
  const command = assertArgv(build.command, "/build/command");
  if (typeof build.output_dir !== "string" || !build.output_dir || isAbsolute(build.output_dir)) throw inputError("build.output_dir must be relative", "/build/output_dir");
  if (build.timeout_ms !== undefined && (!Number.isInteger(build.timeout_ms) || build.timeout_ms < 1)) throw inputError("build.timeout_ms must be a positive integer", "/build/timeout_ms");
  return { ...config, build: { ...build, command } };
}

function terminate(child, timeoutMs = 5000) {
  if (!child || child.exitCode !== null || child.signalCode) return Promise.resolve();
  return new Promise(resolvePromise => {
    let finished = false;
    let timer;
    const finish = () => {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      resolvePromise();
    };
    child.once("exit", finish);
    if (process.platform === "win32") spawn("taskkill", ["/PID", String(child.pid), "/T", "/F"], { windowsHide: true }).once("exit", () => {
      if (child.exitCode !== null || child.signalCode !== null) finish();
    });
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

async function ensureOutputBoundary(root, output) {
  const canonicalRoot = await realpath(root);
  let probe = output.target;
  let canonicalProbe;
  while (true) {
    try {
      canonicalProbe = await realpath(probe);
      break;
    } catch (error) {
      if (error.code !== "ENOENT") throw evidenceError(`production output boundary cannot be resolved: ${error.message}`, "/build/output_dir");
      const parent = resolve(probe, "..");
      if (parent === probe) throw evidenceError("production output boundary has no existing parent", "/build/output_dir");
      probe = parent;
    }
  }
  ensureContained(canonicalRoot, canonicalProbe, "/build/output_dir");
}

function run(argv, cwd, timeoutMs) {
  return new Promise((done, fail) => {
    const child = spawn(argv[0], argv.slice(1), { cwd, shell: false, detached: process.platform !== "win32", windowsHide: true, stdio: ["ignore", "pipe", "pipe"] });
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
      if (!timeoutError) finish({ code, signal, stdout: Buffer.concat(stdout), stderr: Buffer.concat(stderr) });
    });
    timer = setTimeout(async () => {
      timeoutError = Object.assign(new Error(`production build exceeded ${timeoutMs}ms`), { code: "timeout-process-loss", pointer: "/build/timeout_ms" });
      await terminate(child);
      finish(timeoutError, true);
    }, timeoutMs);
    timer.unref();
  });
}

async function inventory(root, outputDir) {
  const files = [];
  async function visit(directory) {
    let entries;
    try { entries = await readdir(directory, { withFileTypes: true }); }
    catch (error) { throw evidenceError(`production output cannot be read: ${error.message}`, "/build/output_dir"); }
    for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
      const target = resolve(directory, entry.name);
      const rel = relative(outputDir, target).replaceAll("\\", "/");
      if (entry.isDirectory()) await visit(target);
      else if (entry.isFile()) {
        const bytes = await readFile(target);
        files.push({ path: rel, bytes: bytes.length, sha256: sha256(bytes) });
      } else {
        throw evidenceError(`production output contains unsupported filesystem entry ${rel}`, "/build/output_dir");
      }
    }
  }
  let metadata;
  try { metadata = await stat(outputDir); }
  catch (error) { throw evidenceError(`production build did not create output: ${error.message}`, "/build/output_dir"); }
  if (!metadata.isDirectory()) throw evidenceError("production build output is not a directory", "/build/output_dir");
  await visit(outputDir);
  if (files.length === 0) throw evidenceError("production build output is empty", "/build/output_dir");
  files.sort((left, right) => left.path.localeCompare(right.path));
  return { path: relative(root, outputDir).replaceAll("\\", "/"), files, sha256: sha256(canonicalJson(files)), file_count: files.length, bytes: files.reduce((sum, item) => sum + item.bytes, 0) };
}

async function gitValue(workspace, suffix = "HEAD") {
  const result = await run(["git", "rev-parse", suffix], workspace, 10000);
  if (result.code !== 0) throw evidenceError(`git ${suffix} failed: ${result.stderr.toString("utf8").trim()}`, "/workspace");
  return result.stdout.toString("utf8").trim();
}

async function gitStatus(workspace) {
  const result = await run(["git", "status", "--porcelain", "--untracked-files=no"], workspace, 10000);
  if (result.code !== 0) throw evidenceError(`git status failed: ${result.stderr.toString("utf8").trim()}`, "/workspace");
  return result.stdout.toString("utf8");
}

async function trackedOutput(workspace, output) {
  const result = await run(["git", "ls-files", "-z", "--", output.path], workspace, 10000);
  if (result.code !== 0) throw evidenceError(`git tracked-output check failed: ${result.stderr.toString("utf8").trim()}`, "/build/output_dir");
  if (result.stdout.length) throw evidenceError(`production output overlaps tracked source: ${output.path}`, "/build/output_dir");
}

export async function buildProduction(config, { workspace, artifactCommit, packageRoot = PACKAGE_ROOT } = {}) {
  const checked = validateConfig(config);
  if (!workspace || typeof workspace !== "string") throw inputError("joined workspace is required", "/workspace");
  const root = resolve(workspace);
  const expected = String(artifactCommit || "").replace(/^git:/, "").toLowerCase();
  if (!/^[0-9a-f]{40}$/.test(expected)) throw inputError("artifact_commit must identify a git revision", "/artifact_commit");
  const observedHead = (await gitValue(root)).toLowerCase();
  if (observedHead !== expected) throw evidenceError(`joined commit mismatch before production build: expected ${expected}, observed ${observedHead}`, "/artifact_commit");
  const sourceTree = await gitValue(root, "HEAD^{tree}");
  const output = relativeTarget(root, checked.build.output_dir, "/build/output_dir");
  await ensureOutputBoundary(root, output);
  await trackedOutput(root, output);
  await rm(output.target, { recursive: true, force: true });
  const started = Date.now();
  let result;
  try { result = await run(checked.build.command, root, checked.build.timeout_ms || 120000); }
  catch (error) { await rm(output.target, { recursive: true, force: true }); throw error; }
  let finalHead;
  try { finalHead = (await gitValue(root)).toLowerCase(); }
  catch (error) { await rm(output.target, { recursive: true, force: true }); throw error; }
  if (result.code !== 0) {
    await rm(output.target, { recursive: true, force: true });
    throw evidenceError(`production build exited ${result.code ?? "unknown"}${result.signal ? ` (${result.signal})` : ""}; stale output was removed`, "/build/command");
  }
  if (finalHead !== expected) {
    await rm(output.target, { recursive: true, force: true });
    throw evidenceError(`joined commit changed during production build: expected ${expected}, observed ${finalHead}; output was rejected`, "/artifact_commit");
  }
  const sourceStatus = await gitStatus(root);
  if (sourceStatus.trim()) {
    await rm(output.target, { recursive: true, force: true });
    throw evidenceError("production build changed tracked source bytes; output was rejected", "/workspace");
  }
  const built = await inventory(root, output.target);
  return {
    status: "built", artifact_commit: artifactCommit, observed_at: nowIso(),
    workspace: root, package_root: resolve(packageRoot), source: { commit: `git:${finalHead}`, tree: `git:${sourceTree}`, status_sha256: sha256(sourceStatus) },
    build: { command: checked.build.command, cwd: root, exit_code: result.code, signal: result.signal || null, duration_ms: Date.now() - started, stdout_sha256: sha256(result.stdout), stderr_sha256: sha256(result.stderr) },
    output: built,
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.config || !args.workspace || !args.artifact_commit) throw inputError("--config, --workspace, and --artifact-commit are required");
  const configPath = resolve(args.config);
  const { value: config } = await readJson(configPath);
  const result = await buildProduction(config, { workspace: resolve(args.workspace), artifactCommit: args.artifact_commit });
  process.stdout.write(`${JSON.stringify(result)}\n`);
}

if (process.argv[1] && resolve(process.argv[1]) === resolve(fileURLToPath(import.meta.url))) {
  main().catch(error => { const result = resultFromError(error); process.stderr.write(`${result.result.error.message}\n`); process.stdout.write(`${JSON.stringify(result.result)}\n`); process.exitCode = result.exitCode; });
}

export { inventory, validateConfig };
